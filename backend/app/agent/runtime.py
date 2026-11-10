"""Agent runtime: one chat turn = load agent -> memory -> RAG -> prompt -> LLM (stream) -> persist.

`ChatRuntime.prepare()` performs all validation up-front (so HTTP errors are returned as JSON before
any SSE byte is sent). `iter_events()` is a synchronous generator of protocol events:

    meta       {conversation_id, user_message_id, assistant_message_id, agent_id, model}
    citations  {items: [...]}
    tool       {name, arguments, result | error}
    delta      {content}
    done       {message_id, status, usage, finish_reason, latency_ms}
    error      {code, message, message_id}
"""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.agent.memory_manager import load_history
from app.agent.prompt_manager import DEFAULT_REFUSE, build_system_prompt, wrap_attachments
from app.agent.tool_manager import ToolError, tool_manager
from app.core.database import SessionLocal, utcnow
from app.core.exceptions import BadRequest, Forbidden, NotFound
from app.llm.base import LLMError, TokenUsage
from app.llm.provider_manager import build_provider, record_call, resolve_chat_config
from app.models import Agent, AgentKnowledgeBase, Conversation, KnowledgeBase, Message, UploadedFile, User
from app.rag.retriever import RetrievedChunk, retrieve
from app.services.agent_access import can_user_access_agent
from app.utils.cancel import clear_cancel, is_cancelled
from app.utils.tokens import estimate_messages_tokens, estimate_tokens

logger = logging.getLogger(__name__)
MAX_TOOL_ROUNDS = 4
MAX_ATTACHMENT_CHARS = 8000


class ChatRuntime:
    def __init__(self, *, user_id: int, agent_id: int | None, content: str, conversation_id: int | None = None,
                 attachment_ids: list[int] | None = None, regenerate: bool = False, db: Session | None = None):
        self.user_id = user_id
        self.agent_id = agent_id
        self.content = (content or "").strip()
        self.conversation_id = conversation_id
        self.attachment_ids = attachment_ids or []
        self.regenerate = regenerate
        self.db = db or SessionLocal()
        self._own_db = db is None
        self.citations: list[RetrievedChunk] = []
        self.usage = TokenUsage()
        self._parts: list[str] = []
        self._finalized = False
        self._started = 0.0

    # ------------------------------------------------------------------ setup
    def prepare(self) -> None:
        db = self.db
        user = db.get(User, self.user_id)
        if user is None or user.status != "active":
            raise Forbidden("用户不可用")

        if self.conversation_id:
            conv = db.get(Conversation, self.conversation_id)
            if conv is None or conv.deleted_at is not None:
                raise NotFound("会话不存在")
            if conv.user_id != self.user_id:  # ownership check: no cross-user access
                raise NotFound("会话不存在")
            if self.agent_id and self.agent_id != conv.agent_id:
                raise BadRequest("会话与智能体不匹配")
            self.agent_id = conv.agent_id
        else:
            conv = None
        if not self.agent_id:
            raise BadRequest("请选择智能体")

        agent = db.get(Agent, self.agent_id)
        if agent is None or agent.deleted_at is not None or agent.status != "published":
            raise NotFound("智能体不存在或未发布")
        if not can_user_access_agent(db, user.id, agent):
            raise Forbidden("您没有访问该智能体的权限")
        self.agent = agent

        self.cfg = resolve_chat_config(db, agent.llm_config_id)

        if self.regenerate:
            if conv is None:
                raise BadRequest("重新生成需要指定会话")
            last_user = db.scalars(select(Message).where(
                Message.conversation_id == conv.id, Message.role == "user", Message.deleted_at.is_(None))
                .order_by(Message.id.desc()).limit(1)).first()
            if last_user is None:
                raise BadRequest("没有可重新生成的消息")
            db.execute(update(Message).where(Message.conversation_id == conv.id, Message.id > last_user.id,
                                             Message.deleted_at.is_(None)).values(deleted_at=utcnow()))
            self.user_msg = last_user
            self.content = last_user.content
            attachments = last_user.attachments or []
        else:
            if not self.content and not self.attachment_ids:
                raise BadRequest("消息内容不能为空")
            if len(self.content) > 8000:
                raise BadRequest("消息过长（最多 8000 字）")
            attachments = self._load_attachments()
            if conv is None:
                title = (self.content or (attachments[0]["name"] if attachments else "新对话"))[:30]
                conv = Conversation(user_id=user.id, agent_id=agent.id, title=title, message_count=0)
                db.add(conv)
                db.flush()
            self.user_msg = Message(conversation_id=conv.id, role="user", content=self.content,
                                    message_type="text", status="completed",
                                    attachments=[{k: v for k, v in a.items() if k != "text"} for a in attachments] or None)
            db.add(self.user_msg)
            conv.message_count += 1
        self.conv = conv
        self._attachments = attachments

        self.assistant_msg = Message(conversation_id=conv.id, role="assistant", content="", message_type="markdown",
                                     status="streaming", model=self.cfg.chat_model)
        db.add(self.assistant_msg)
        conv.message_count += 1
        conv.last_message_at = utcnow()
        db.commit()

    def _load_attachments(self) -> list[dict]:
        if not self.attachment_ids:
            return []
        if len(self.attachment_ids) > 5:
            raise BadRequest("单条消息最多 5 个附件")
        files = list(self.db.scalars(select(UploadedFile).where(UploadedFile.id.in_(self.attachment_ids))))
        if len(files) != len(set(self.attachment_ids)) or any(f.user_id != self.user_id for f in files):
            raise NotFound("附件不存在")
        out = []
        for f in files:
            kind = "image" if f.file_type in ("png", "jpg", "gif", "webp") else "file"
            item = {"file_id": f.id, "name": f.filename, "type": kind, "file_type": f.file_type, "size": f.file_size}
            if kind == "file" and f.extracted_text:
                item["text"] = f.extracted_text[:MAX_ATTACHMENT_CHARS]
            out.append(item)
        return out

    # ------------------------------------------------------------------ prompt
    def _build_messages(self) -> list[dict]:
        agent = self.agent
        system = build_system_prompt(agent, rag_enabled=self._rag_enabled, chunks=self.citations,
                                     conversation_summary=self.conv.summary,
                                     tools_enabled=bool(agent.enable_tools and agent.tools))
        history = load_history(self.db, self.conv.id, agent, before_message_id=self.user_msg.id)
        user_text = wrap_attachments(self.content, self._attachments)
        images = [a for a in self._attachments if a["type"] == "image"]
        if images:
            # TODO: multimodal (image_url) input for vision models; for now the model is told an image was attached.
            user_text += "\n\n（用户上传了图片：" + "、".join(a["name"] for a in images) + "，当前模型未开启图像理解）"
        return [{"role": "system", "content": system}, *history, {"role": "user", "content": user_text}]

    def _kbs(self) -> list[KnowledgeBase]:
        ids = list(self.db.scalars(select(AgentKnowledgeBase.knowledge_base_id)
                                   .where(AgentKnowledgeBase.agent_id == self.agent.id)))
        if not ids:
            return []
        return list(self.db.scalars(select(KnowledgeBase).where(KnowledgeBase.id.in_(ids),
                                                                KnowledgeBase.deleted_at.is_(None))))

    # ------------------------------------------------------------------ run
    def iter_events(self) -> Iterator[dict]:
        self._started = time.time()
        self._status, self._finish_reason = "completed", None
        self._provider = None
        self._stream = None
        try:
            yield from self._run()
        except GeneratorExit:
            self._cleanup()
            self.finalize("interrupted", self._finish_reason)  # client disconnected / aborted
            raise
        except LLMError as e:
            self._status, self._error = "error", e.message
            yield {"event": "error", "data": {"code": 50200, "message": e.message, "message_id": self.assistant_msg.id}}
        except Exception:  # noqa: BLE001
            logger.exception("Chat runtime failure")
            self._status, self._error = "error", "生成回答时发生内部错误"
            yield {"event": "error", "data": {"code": 50000, "message": self._error, "message_id": self.assistant_msg.id}}
        self._cleanup()
        self.finalize(self._status, self._finish_reason)
        yield {"event": "done", "data": self._done_payload(self._finish_reason)}

    def _cleanup(self) -> None:
        if self._stream is not None:
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._provider is not None:
            self._provider.close()
            self._provider = None

    def _run(self) -> Iterator[dict]:
        agent = self.agent
        yield {"event": "meta", "data": {"conversation_id": self.conv.id, "user_message_id": self.user_msg.id,
                                         "assistant_message_id": self.assistant_msg.id, "agent_id": agent.id,
                                         "model": self.cfg.chat_model, "title": self.conv.title}}
        # 1) RAG retrieval
        kbs = self._kbs() if agent.enable_rag else []
        self._rag_enabled = bool(agent.enable_rag and kbs)
        if self._rag_enabled and self.content:
            try:
                self.citations = retrieve(self.db, kbs, self.content, top_k=agent.rag_top_k,
                                          score_threshold=agent.rag_score_threshold)
            except Exception as e:  # retrieval failure should not kill the chat
                logger.warning("Retrieval failed for agent %s: %s", agent.id, e)
                self.citations = []
            yield {"event": "citations", "data": {"items": [c.to_citation(i) for i, c in
                                                            enumerate(self.citations, start=1)]}}
            if not self.citations and agent.rag_no_result_policy == "strict":
                text = agent.rag_refuse_message or DEFAULT_REFUSE
                self._parts.append(text)
                self._finish_reason = "no_knowledge"
                yield {"event": "delta", "data": {"content": text}}
                return

        messages = self._messages = self._build_messages()
        self._provider = provider = build_provider(self.cfg)
        params = {"temperature": agent.temperature if agent.temperature is not None else self.cfg.temperature,
                  "max_tokens": agent.max_tokens or self.cfg.max_tokens}

        # 2) optional tool-calling rounds (non-streaming); final answer emitted as deltas
        allowed = list(agent.tools or []) if agent.enable_tools else []
        if allowed:
            for _ in range(MAX_TOOL_ROUNDS):
                res = provider.chat(messages, tools=tool_manager.schemas(allowed), **params)
                self._add_usage(res.usage)
                if not res.tool_calls:
                    self._finish_reason = res.finish_reason
                    for i in range(0, len(res.content), 20):
                        if self._cancelled():
                            self._status = "interrupted"
                            return
                        piece = res.content[i:i + 20]
                        self._parts.append(piece)
                        yield {"event": "delta", "data": {"content": piece}}
                    return
                messages.append(res.raw_message)
                for tc in res.tool_calls:
                    name, args = tc["function"]["name"], tc["function"]["arguments"]
                    try:
                        result = tool_manager.execute(name, args, allowed)
                        yield {"event": "tool", "data": {"name": name, "arguments": args, "result": result[:500]}}
                    except ToolError as e:
                        result = f"工具调用失败: {e}"
                        yield {"event": "tool", "data": {"name": name, "arguments": args, "error": str(e)}}
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
            # rounds exhausted: fall through to a final streamed answer without tools

        # 3) streamed answer
        self._stream = provider.stream_chat(messages, **params)
        last_check = time.time()
        for chunk in self._stream:
            if chunk.usage is not None:
                self._add_usage(chunk.usage)
                self._finish_reason = chunk.finish_reason
                continue
            if chunk.delta:
                self._parts.append(chunk.delta)
                yield {"event": "delta", "data": {"content": chunk.delta}}
            if time.time() - last_check > 0.3:
                last_check = time.time()
                if self._cancelled():
                    self._status = "interrupted"
                    return

    def _cancelled(self) -> bool:
        return is_cancelled(self.assistant_msg.id)

    def _add_usage(self, u: TokenUsage) -> None:
        self.usage.prompt_tokens += u.prompt_tokens
        self.usage.completion_tokens += u.completion_tokens
        self.usage.total_tokens += u.total_tokens
        self.usage.estimated = self.usage.estimated or u.estimated

    def _done_payload(self, finish_reason) -> dict:
        m = self.assistant_msg
        return {"message_id": m.id, "status": m.status, "usage": m.token_usage, "finish_reason": finish_reason,
                "latency_ms": m.latency_ms}

    def finalize(self, status: str, finish_reason: str | None = None) -> None:
        if self._finalized:
            return
        self._finalized = True
        db = self.db
        try:
            latency = int((time.time() - self._started) * 1000) if self._started else 0
            m = self.assistant_msg
            m.content = "".join(self._parts)
            if status == "error" and not m.content:
                m.content = getattr(self, "_error", "生成失败")
                m.message_type = "error"
            m.status = status
            m.citations = [c.to_citation(i) for i, c in enumerate(self.citations, start=1)] or None
            if self.usage.total_tokens == 0 and m.content and getattr(self, "_messages", None):
                # interrupted before the provider reported usage -> estimate
                p, c = estimate_messages_tokens(self._messages), estimate_tokens(m.content)
                self.usage = TokenUsage(p, c, p + c, estimated=True)
            m.token_usage = self.usage.as_dict()
            m.latency_ms = latency
            self.conv.last_message_at = utcnow()
            db.commit()
            clear_cancel(m.id)
            if finish_reason != "no_knowledge" or self.usage.total_tokens:
                record_call(cfg=self.cfg, call_type="stream", usage=self.usage, latency_ms=latency,
                            status="failed" if status == "error" else "success",
                            error=getattr(self, "_error", None), agent_id=self.agent.id, user_id=self.user_id,
                            conversation_id=self.conv.id, model=self.cfg.chat_model)
        except Exception:
            logger.exception("Failed to persist assistant message")
            db.rollback()

    def run_blocking(self) -> dict:
        """Non-streaming convenience used by POST /chat/completions."""
        events = list(self.iter_events())
        err = next((e["data"] for e in events if e["event"] == "error"), None)
        cites = next((e["data"]["items"] for e in events if e["event"] == "citations"), [])
        tools = [e["data"] for e in events if e["event"] == "tool"]
        m = self.assistant_msg
        return {"conversation_id": self.conv.id, "user_message_id": self.user_msg.id, "message_id": m.id,
                "content": m.content, "message_type": m.message_type, "status": m.status, "citations": cites,
                "tool_calls": tools, "usage": m.token_usage, "error": err}

    def close(self) -> None:
        if self._own_db:
            self.db.close()


def sse_format(event: dict) -> str:
    return f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
