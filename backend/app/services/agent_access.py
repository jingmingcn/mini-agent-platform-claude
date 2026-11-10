from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent, UserAgentPermission


def can_user_access_agent(db: Session, user_id: int, agent: Agent) -> bool:
    if agent.access_level != "restricted":
        return True
    return db.scalar(select(UserAgentPermission.id).where(UserAgentPermission.user_id == user_id,
                                                          UserAgentPermission.agent_id == agent.id)) is not None


def accessible_agent_ids(db: Session, user_id: int) -> set[int]:
    return set(db.scalars(select(UserAgentPermission.agent_id).where(UserAgentPermission.user_id == user_id)))
