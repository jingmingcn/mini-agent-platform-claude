from __future__ import annotations

from datetime import date

from sqlalchemy import JSON, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigId, TimestampMixin


class ApiLog(Base, TimestampMixin):
    """One row per model invocation (chat / stream / embedding / test)."""
    __tablename__ = "api_logs"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    llm_config_id: Mapped[int | None] = mapped_column(ForeignKey("llm_configs.id", ondelete="SET NULL"), index=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    conversation_id: Mapped[int | None] = mapped_column(BigId)
    call_type: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(128))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="success", nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)


class UsageStatistic(Base, TimestampMixin):
    """Daily aggregated usage per (user, agent, model)."""
    __tablename__ = "usage_statistics"
    __table_args__ = (UniqueConstraint("stat_date", "user_id", "agent_id", "llm_config_id", name="uq_usage_dim"),)

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    stat_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"), index=True)
    llm_config_id: Mapped[int | None] = mapped_column(ForeignKey("llm_configs.id", ondelete="SET NULL"))
    request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[dict | None] = mapped_column(JSON)
    ip: Mapped[str | None] = mapped_column(String(64))


class SystemSetting(Base, TimestampMixin):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    value: Mapped[dict | list | str | int | None] = mapped_column(JSON)
