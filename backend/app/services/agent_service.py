from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.agent.tool_manager import tool_manager
from app.core.database import utcnow
from app.core.exceptions import BadRequest, NotFound
from app.models import Agent, AgentKnowledgeBase, AgentPrompt, AdminUser, KnowledgeBase, LLMConfig, User, UserAgentPermission
from app.schemas.agent import AgentCreate, AgentOut, AgentUpdate


def get_or_404(db: Session, agent_id: int) -> Agent:
    a = db.get(Agent, agent_id)
    if a is None or a.deleted_at is not None:
        raise NotFound("智能体不存在")
    return a


def kb_ids_of(db: Session, agent_id: int) -> list[int]:
    return list(db.scalars(select(AgentKnowledgeBase.knowledge_base_id).where(AgentKnowledgeBase.agent_id == agent_id)
                           .order_by(AgentKnowledgeBase.id)))


def to_out(db: Session, a: Agent) -> dict:
    data = AgentOut.model_validate(a).model_dump(mode="json")
    data["knowledge_base_ids"] = kb_ids_of(db, a.id)
    if a.llm_config_id:
        cfg = db.get(LLMConfig, a.llm_config_id)
        data["llm_config_name"] = cfg.name if cfg and cfg.deleted_at is None else None
    return data


def _validate_refs(db: Session, llm_config_id: int | None, kb_ids: list[int] | None, tools: list[str] | None) -> None:
    if llm_config_id:
        cfg = db.get(LLMConfig, llm_config_id)
        if cfg is None or cfg.deleted_at is not None:
            raise BadRequest("绑定的模型配置不存在")
        if not cfg.chat_model:
            raise BadRequest("绑定的模型配置未设置 Chat Model")
    if kb_ids:
        found = set(db.scalars(select(KnowledgeBase.id).where(KnowledgeBase.id.in_(kb_ids),
                                                              KnowledgeBase.deleted_at.is_(None))))
        missing = set(kb_ids) - found
        if missing:
            raise BadRequest(f"知识库不存在: {sorted(missing)}")
    if tools:
        known = {t.name for t in tool_manager.list()}
        unknown = set(tools) - known
        if unknown:
            raise BadRequest(f"未知工具: {sorted(unknown)}")


def _set_kbs(db: Session, agent_id: int, kb_ids: list[int]) -> None:
    db.execute(delete(AgentKnowledgeBase).where(AgentKnowledgeBase.agent_id == agent_id))
    for kb_id in dict.fromkeys(kb_ids):
        db.add(AgentKnowledgeBase(agent_id=agent_id, knowledge_base_id=kb_id))


def _save_prompt_version(db: Session, agent: Agent, admin: AdminUser | None) -> None:
    last = db.scalar(select(func.max(AgentPrompt.version)).where(AgentPrompt.agent_id == agent.id,
                                                                  AgentPrompt.kind == "version")) or 0
    db.add(AgentPrompt(agent_id=agent.id, name=f"{agent.name} v{last + 1}", content=agent.system_prompt or "",
                       version=last + 1, kind="version", created_by=admin.id if admin else None))


def list_agents(db: Session, *, keyword: str | None = None, status: str | None = None) -> list[Agent]:
    q = select(Agent).where(Agent.deleted_at.is_(None))
    if keyword:
        q = q.where(Agent.name.contains(keyword))
    if status:
        q = q.where(Agent.status == status)
    return list(db.scalars(q.order_by(Agent.sort_order.desc(), Agent.id.desc())))


def create_agent(db: Session, data: AgentCreate, admin: AdminUser | None) -> Agent:
    _validate_refs(db, data.llm_config_id, data.knowledge_base_ids, data.tools)
    a = Agent(**data.model_dump(exclude={"knowledge_base_ids"}), created_by=admin.id if admin else None)
    db.add(a)
    db.flush()
    _set_kbs(db, a.id, data.knowledge_base_ids)
    if a.system_prompt:
        _save_prompt_version(db, a, admin)
    db.commit()
    return a


def update_agent(db: Session, a: Agent, data: AgentUpdate, admin: AdminUser | None) -> Agent:
    patch = data.model_dump(exclude_unset=True)
    kb_ids = patch.pop("knowledge_base_ids", None)
    _validate_refs(db, patch.get("llm_config_id"), kb_ids, patch.get("tools"))
    prompt_changed = "system_prompt" in patch and patch["system_prompt"] != a.system_prompt
    for k, v in patch.items():
        setattr(a, k, v)
    if kb_ids is not None:
        _set_kbs(db, a.id, kb_ids)
    if prompt_changed:
        _save_prompt_version(db, a, admin)
    db.commit()
    return a


def publish(db: Session, a: Agent, publish_: bool = True) -> Agent:
    if publish_:
        if not a.system_prompt.strip():
            raise BadRequest("请先配置系统提示词")
        if a.enable_rag and not kb_ids_of(db, a.id):
            raise BadRequest("已开启 RAG 但未关联知识库")
    a.status = "published" if publish_ else "offline"
    db.commit()
    return a


def delete_agent(db: Session, a: Agent) -> None:
    a.deleted_at = utcnow()
    a.status = "offline"
    db.commit()


def get_permissions(db: Session, agent_id: int) -> list[dict]:
    rows = db.execute(select(User.id, User.nickname, User.avatar_url).join(
        UserAgentPermission, UserAgentPermission.user_id == User.id).where(UserAgentPermission.agent_id == agent_id))
    return [{"id": r.id, "nickname": r.nickname, "avatar_url": r.avatar_url} for r in rows]


def set_permissions(db: Session, agent_id: int, user_ids: list[int]) -> None:
    valid = set(db.scalars(select(User.id).where(User.id.in_(user_ids)))) if user_ids else set()
    db.execute(delete(UserAgentPermission).where(UserAgentPermission.agent_id == agent_id))
    for uid in valid:
        db.add(UserAgentPermission(user_id=uid, agent_id=agent_id))
    db.commit()
