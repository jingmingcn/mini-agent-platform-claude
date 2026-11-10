"""Conversation memory: loads recent turns and trims them to a token budget."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent, Message
from app.utils.tokens import estimate_tokens


def load_history(db: Session, conversation_id: int, agent: Agent, *, before_message_id: int | None = None) -> list[dict]:
    """Return [{'role','content'}...] oldest->newest within agent.memory_max_messages / memory_max_tokens.

    Truncation drops the oldest turns first and keeps user/assistant pairs aligned.
    TODO: summary compression of dropped turns into conversations.summary (column already exists).
    """
    if not agent.enable_memory:
        return []
    q = select(Message).where(Message.conversation_id == conversation_id, Message.deleted_at.is_(None),
                              Message.role.in_(("user", "assistant")),
                              Message.status.in_(("completed", "interrupted")),
                              Message.message_type != "error")
    if before_message_id is not None:
        q = q.where(Message.id < before_message_id)
    rows = list(db.scalars(q.order_by(Message.id.desc()).limit(max(agent.memory_max_messages, 0))))
    rows.reverse()
    history = [{"role": m.role, "content": m.content} for m in rows if m.content]
    budget = agent.memory_max_tokens
    total = sum(estimate_tokens(m["content"]) + 4 for m in history)
    while history and total > budget:
        dropped = history.pop(0)
        total -= estimate_tokens(dropped["content"]) + 4
    # never start the window with a dangling assistant reply
    while history and history[0]["role"] == "assistant":
        history.pop(0)
    return history
