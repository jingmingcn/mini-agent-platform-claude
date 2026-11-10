from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_role
from app.core.response import ok
from app.models import (AdminUser, Agent, ApiLog, AuditLog, Conversation, Document, KnowledgeBase, LLMConfig, Message,
                        UsageStatistic, User)

router = APIRouter(tags=["日志与统计"])


def _log_out(r: ApiLog) -> dict:
    return {"id": r.id, "llm_config_id": r.llm_config_id, "agent_id": r.agent_id, "user_id": r.user_id,
            "conversation_id": r.conversation_id, "call_type": r.call_type, "provider": r.provider, "model": r.model,
            "prompt_tokens": r.prompt_tokens, "completion_tokens": r.completion_tokens, "total_tokens": r.total_tokens,
            "latency_ms": r.latency_ms, "status": r.status, "error_message": r.error_message,
            "created_at": r.created_at.isoformat()}


@router.get("/logs/api", summary="模型调用日志")
def api_logs(call_type: str | None = None, status: str | None = None, agent_id: int | None = None,
             page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db),
             _: AdminUser = Depends(require_role("viewer"))):
    q = select(ApiLog)
    if call_type:
        q = q.where(ApiLog.call_type == call_type)
    if status:
        q = q.where(ApiLog.status == status)
    if agent_id:
        q = q.where(ApiLog.agent_id == agent_id)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(ApiLog.id.desc()).offset((page - 1) * page_size).limit(page_size))
    return ok({"items": [_log_out(r) for r in rows], "total": total, "page": page, "page_size": page_size})


@router.get("/logs/audit", summary="管理员操作审计日志")
def audit_logs(action: str | None = None, resource_type: str | None = None, page: int = Query(1, ge=1),
               page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db),
               _: AdminUser = Depends(require_role("admin"))):
    q = select(AuditLog, AdminUser.username).outerjoin(AdminUser, AdminUser.id == AuditLog.admin_id)
    if action:
        q = q.where(AuditLog.action == action)
    if resource_type:
        q = q.where(AuditLog.resource_type == resource_type)
    total = db.scalar(select(func.count(AuditLog.id)).where(
        *( [AuditLog.action == action] if action else []), *([AuditLog.resource_type == resource_type] if resource_type else []))) or 0
    rows = db.execute(q.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    items = [{"id": a.id, "admin_id": a.admin_id, "admin_username": u, "action": a.action,
              "resource_type": a.resource_type, "resource_id": a.resource_id, "detail": a.detail, "ip": a.ip,
              "created_at": a.created_at.isoformat()} for a, u in rows]
    return ok({"items": items, "total": total, "page": page, "page_size": page_size})


@router.get("/stats/overview", summary="系统概览")
def overview(db: Session = Depends(get_db), _: AdminUser = Depends(require_role("viewer"))):
    today_start = datetime.combine(date.today(), datetime.min.time())

    def count(model, *conds):
        return db.scalar(select(func.count(model.id)).where(*conds)) or 0

    today_calls = count(ApiLog, ApiLog.created_at >= today_start, ApiLog.call_type.in_(("chat", "stream")))
    today_tokens = db.scalar(select(func.coalesce(func.sum(ApiLog.total_tokens), 0)).where(
        ApiLog.created_at >= today_start)) or 0
    total_tokens = db.scalar(select(func.coalesce(func.sum(UsageStatistic.total_tokens), 0))) or 0
    since = date.today() - timedelta(days=13)
    trend_rows = db.execute(select(UsageStatistic.stat_date, func.sum(UsageStatistic.request_count),
                                   func.sum(UsageStatistic.total_tokens))
                            .where(UsageStatistic.stat_date >= since).group_by(UsageStatistic.stat_date)).all()
    trend_map = {r[0]: (int(r[1] or 0), int(r[2] or 0)) for r in trend_rows}
    trend = []
    for i in range(14):
        d = since + timedelta(days=i)
        req, tok = trend_map.get(d, (0, 0))
        trend.append({"date": d.isoformat(), "requests": req, "tokens": tok})
    top_agents = db.execute(select(Agent.id, Agent.name, func.sum(UsageStatistic.request_count).label("n"))
                            .join(UsageStatistic, UsageStatistic.agent_id == Agent.id)
                            .where(UsageStatistic.stat_date >= since)
                            .group_by(Agent.id, Agent.name).order_by(func.sum(UsageStatistic.request_count).desc())
                            .limit(5)).all()
    recent = db.scalars(select(ApiLog).order_by(ApiLog.id.desc()).limit(10))
    feedback = dict(db.execute(select(Message.feedback, func.count(Message.id)).where(
        Message.feedback.is_not(None)).group_by(Message.feedback)).all())
    return ok({
        "agents": count(Agent, Agent.deleted_at.is_(None)),
        "published_agents": count(Agent, Agent.deleted_at.is_(None), Agent.status == "published"),
        "models": count(LLMConfig, LLMConfig.deleted_at.is_(None)),
        "knowledge_bases": count(KnowledgeBase, KnowledgeBase.deleted_at.is_(None)),
        "documents": count(Document, Document.deleted_at.is_(None)),
        "users": count(User, User.deleted_at.is_(None)),
        "conversations": count(Conversation, Conversation.deleted_at.is_(None)),
        "today_calls": today_calls, "today_tokens": int(today_tokens), "total_tokens": int(total_tokens),
        "likes": int(feedback.get(1, 0)), "dislikes": int(feedback.get(-1, 0)),
        "trend": trend,
        "top_agents": [{"id": r[0], "name": r[1], "requests": int(r[2] or 0)} for r in top_agents],
        "recent_logs": [_log_out(r) for r in recent],
    })
