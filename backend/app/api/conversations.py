from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db, utcnow
from app.core.exceptions import NotFound
from app.core.permissions import Principal, get_current_user, get_principal
from app.core.response import ok
from app.models import Agent, Conversation, Message, User
from app.schemas.chat import ConversationOut, ConversationRename, FeedbackIn, MessageOut

router = APIRouter(tags=["会话"])


def _conv_for(db: Session, conv_id: int, p: Principal) -> Conversation:
    c = db.get(Conversation, conv_id)
    if c is None or c.deleted_at is not None or (not p.is_admin and c.user_id != p.id):
        raise NotFound("会话不存在")  # 404 rather than 403 to avoid leaking existence
    return c


def _conv_out(c: Conversation, agents: dict[int, Agent], users: dict[int, User] | None = None) -> dict:
    d = ConversationOut.model_validate(c).model_dump(mode="json")
    a = agents.get(c.agent_id)
    d["agent_name"] = a.name if a else None
    d["agent_avatar"] = a.avatar if a else None
    if users is not None:
        u = users.get(c.user_id)
        d["user_nickname"] = u.nickname if u else None
    return d


@router.get("/conversations", summary="会话列表（用户：自己的；管理员：全部，可筛选）")
def list_conversations(agent_id: int | None = None, user_id: int | None = None, keyword: str | None = None,
                       page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                       db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    q = select(Conversation).where(Conversation.deleted_at.is_(None))
    if not p.is_admin:
        q = q.where(Conversation.user_id == p.id)
    elif user_id:
        q = q.where(Conversation.user_id == user_id)
    if agent_id:
        q = q.where(Conversation.agent_id == agent_id)
    if keyword:
        q = q.where(Conversation.title.contains(keyword))
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(db.scalars(q.order_by(func.coalesce(Conversation.last_message_at, Conversation.created_at).desc(),
                                      Conversation.id.desc()).offset((page - 1) * page_size).limit(page_size)))
    agents = {a.id: a for a in db.scalars(select(Agent).where(Agent.id.in_({c.agent_id for c in rows})))} if rows else {}
    users = None
    if p.is_admin and rows:
        users = {u.id: u for u in db.scalars(select(User).where(User.id.in_({c.user_id for c in rows})))}
    return ok({"items": [_conv_out(c, agents, users) for c in rows], "total": total, "page": page,
               "page_size": page_size})


def _with_urls(request: Request, m: Message) -> dict:
    from app.api.files import file_url
    from app.models import UploadedFile

    d = MessageOut.model_validate(m).model_dump(mode="json")
    if d.get("attachments"):
        for a in d["attachments"]:
            if a.get("file_id"):
                a["url"] = file_url(request, UploadedFile(id=a["file_id"]))
    return d


@router.get("/conversations/{conv_id}/messages", summary="会话消息")
def messages(conv_id: int, request: Request, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    c = _conv_for(db, conv_id, p)
    rows = db.scalars(select(Message).where(Message.conversation_id == c.id, Message.deleted_at.is_(None))
                      .order_by(Message.id))
    agent = db.get(Agent, c.agent_id)
    return ok({"conversation": _conv_out(c, {agent.id: agent} if agent else {}),
               "items": [_with_urls(request, m) for m in rows]})


@router.patch("/conversations/{conv_id}", summary="重命名会话")
def rename(conv_id: int, body: ConversationRename, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = _conv_for(db, conv_id, Principal(kind="user", user=user))
    c.title = body.title
    db.commit()
    return ok()


@router.delete("/conversations/{conv_id}", summary="删除会话")
def delete(conv_id: int, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    if p.is_admin and p.admin.role == "viewer":  # type: ignore[union-attr]
        from app.core.exceptions import Forbidden
        raise Forbidden("只读角色不能删除会话")
    c = _conv_for(db, conv_id, p)
    c.deleted_at = utcnow()
    db.commit()
    return ok()


@router.post("/messages/{message_id}/feedback", summary="点赞/点踩 (1 / -1 / 0 取消)")
def feedback(message_id: int, body: FeedbackIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = db.get(Message, message_id)
    if m is None or m.deleted_at is not None or m.role != "assistant":
        raise NotFound("消息不存在")
    _conv_for(db, m.conversation_id, Principal(kind="user", user=user))
    m.feedback = body.rating or None
    m.feedback_comment = body.comment
    db.commit()
    return ok({"message_id": m.id, "feedback": m.feedback})
