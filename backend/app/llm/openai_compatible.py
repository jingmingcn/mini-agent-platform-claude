"""OpenAI-compatible provider (OpenAI, DeepSeek, Moonshot/Kimi, Qwen DashScope, SiliconFlow, ...)."""
from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any

import openai
from openai import OpenAI

from app.core.logging import redact
from app.llm.base import BaseLLMProvider, ChatResult, EmbeddingResult, LLMError, StreamChunk, TokenUsage
from app.utils.tokens import estimate_messages_tokens, estimate_tokens

logger = logging.getLogger(__name__)


def _translate(e: Exception) -> LLMError:
    if isinstance(e, openai.AuthenticationError):
        return LLMError("API Key 无效或无权限 (401)", status_code=401)
    if isinstance(e, openai.PermissionDeniedError):
        return LLMError("无权访问该模型 (403)", status_code=403)
    if isinstance(e, openai.NotFoundError):
        return LLMError("模型或接口地址不存在 (404)，请检查 Base URL 和模型名", status_code=404)
    if isinstance(e, openai.RateLimitError):
        return LLMError("模型服务限流或余额不足 (429)", retryable=True, status_code=429)
    if isinstance(e, openai.APITimeoutError):
        return LLMError("模型服务请求超时", retryable=True)
    if isinstance(e, openai.APIConnectionError):
        return LLMError("无法连接模型服务，请检查网络和 Base URL", retryable=True)
    if isinstance(e, openai.BadRequestError):
        return LLMError(f"请求参数错误: {redact(str(e))[:300]}", status_code=400)
    if isinstance(e, openai.APIStatusError):
        return LLMError(f"模型服务错误 ({e.status_code}): {redact(str(e))[:300]}", retryable=e.status_code >= 500,
                        status_code=e.status_code)
    return LLMError(f"模型调用失败: {redact(str(e))[:300]}")


class OpenAICompatibleProvider(BaseLLMProvider):
    provider_name = "openai_compatible"

    def __init__(self, *, api_key: str, base_url: str, chat_model: str | None = None,
                 embedding_model: str | None = None, temperature: float = 0.7, max_tokens: int | None = None,
                 timeout: float = 60.0, max_retries: int = 2, provider: str = "openai_compatible",
                 client: OpenAI | None = None):
        self.provider_name = provider
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        # The SDK retries connection errors, 408/409/429 and 5xx with exponential backoff.
        self.client = client or OpenAI(api_key=api_key, base_url=base_url.rstrip("/"), timeout=timeout,
                                       max_retries=max_retries)

    # ------------------------------------------------------------------ helpers
    def _params(self, messages: list[dict], kwargs: dict) -> dict:
        model = kwargs.pop("model", None) or self.chat_model
        if not model:
            raise LLMError("该模型配置未设置 Chat Model")
        params: dict[str, Any] = {"model": model, "messages": messages,
                                  "temperature": kwargs.pop("temperature", None)}
        if params["temperature"] is None:
            params["temperature"] = self.temperature
        max_tokens = kwargs.pop("max_tokens", None) or self.max_tokens
        if max_tokens:
            params["max_tokens"] = max_tokens
        tools = kwargs.pop("tools", None)
        if tools:
            params["tools"] = tools
        params.update({k: v for k, v in kwargs.items() if v is not None})
        return params

    @staticmethod
    def _usage(u: Any, messages: list[dict], completion: str) -> TokenUsage:
        if u is not None and getattr(u, "total_tokens", None):
            return TokenUsage(u.prompt_tokens or 0, u.completion_tokens or 0, u.total_tokens or 0)
        p, c = estimate_messages_tokens(messages), estimate_tokens(completion)
        return TokenUsage(p, c, p + c, estimated=True)

    # ------------------------------------------------------------------ API
    def chat(self, messages: list[dict], **kwargs: Any) -> ChatResult:
        params = self._params(messages, dict(kwargs))
        try:
            resp = self.client.chat.completions.create(**params)
        except Exception as e:
            raise _translate(e) from e
        choice = resp.choices[0]
        msg = choice.message
        content = msg.content or ""
        tool_calls = []
        for tc in msg.tool_calls or []:
            tool_calls.append({"id": tc.id, "type": "function",
                               "function": {"name": tc.function.name, "arguments": tc.function.arguments}})
        raw = {"role": "assistant", "content": content}
        if tool_calls:
            raw["tool_calls"] = tool_calls
        return ChatResult(content=content, usage=self._usage(resp.usage, messages, content), model=resp.model or params["model"],
                          finish_reason=choice.finish_reason, tool_calls=tool_calls, raw_message=raw)

    def stream_chat(self, messages: list[dict], **kwargs: Any) -> Iterator[StreamChunk]:
        params = self._params(messages, dict(kwargs))
        params["stream"] = True
        try:
            try:
                stream = self.client.chat.completions.create(stream_options={"include_usage": True}, **params)
            except openai.BadRequestError as e:
                # Some compatible servers reject stream_options; retry without it.
                if "stream_options" not in str(e):
                    raise
                stream = self.client.chat.completions.create(**params)
        except LLMError:
            raise
        except Exception as e:
            raise _translate(e) from e

        parts: list[str] = []
        usage: TokenUsage | None = None
        finish = None
        try:
            for event in stream:
                if getattr(event, "usage", None) and event.usage.total_tokens:
                    usage = TokenUsage(event.usage.prompt_tokens or 0, event.usage.completion_tokens or 0,
                                       event.usage.total_tokens or 0)
                if not event.choices:
                    continue
                ch = event.choices[0]
                if ch.finish_reason:
                    finish = ch.finish_reason
                delta = getattr(ch.delta, "content", None) or ""
                if delta:
                    parts.append(delta)
                    yield StreamChunk(delta=delta)
        except GeneratorExit:
            stream.close()  # client cancelled -> abort upstream HTTP request
            raise
        except Exception as e:
            stream.close()
            raise _translate(e) from e
        if usage is None:
            usage = self._usage(None, messages, "".join(parts))
        yield StreamChunk(usage=usage, finish_reason=finish)

    def embeddings(self, texts: list[str], **kwargs: Any) -> EmbeddingResult:
        model = kwargs.pop("model", None) or self.embedding_model
        if not model:
            raise LLMError("该模型配置未设置 Embedding Model（DeepSeek/Kimi 暂无 Embedding 接口，可使用 Qwen/OpenAI/SiliconFlow 等）")
        batch_size = int(kwargs.pop("batch_size", 10))  # DashScope limits batch to 10
        vectors: list[list[float]] = []
        total = 0
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                resp = self.client.embeddings.create(model=model, input=batch, **kwargs)
            except Exception as e:
                raise _translate(e) from e
            data = sorted(resp.data, key=lambda d: d.index)
            vectors.extend([list(d.embedding) for d in data])
            total += (resp.usage.total_tokens if resp.usage else sum(estimate_tokens(t) for t in batch))
        return EmbeddingResult(vectors=vectors, usage=TokenUsage(total, 0, total), model=model)

    def test_connection(self) -> dict:
        result: dict[str, Any] = {"chat": None, "embedding": None}
        if self.chat_model:
            t0 = time.time()
            r = self.chat([{"role": "user", "content": "ping，请只回复 pong"}], max_tokens=16, temperature=0)
            result["chat"] = {"ok": True, "model": r.model, "reply": r.content[:100],
                              "latency_ms": int((time.time() - t0) * 1000), "usage": r.usage.as_dict()}
        if self.embedding_model:
            t0 = time.time()
            e = self.embeddings(["连接测试"])
            result["embedding"] = {"ok": True, "model": e.model, "dimension": len(e.vectors[0]) if e.vectors else 0,
                                   "latency_ms": int((time.time() - t0) * 1000)}
        if not self.chat_model and not self.embedding_model:
            raise LLMError("未配置 Chat Model 或 Embedding Model")
        return result

    def close(self) -> None:
        try:
            self.client.close()
        except Exception:  # pragma: no cover
            pass
