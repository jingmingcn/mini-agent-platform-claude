from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigId, SoftDeleteMixin, TimestampMixin


class AdminUser(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(64))
    # super_admin: everything incl. admin accounts; admin: manage resources; viewer: read-only
    role: Mapped[str] = mapped_column(String(32), default="admin", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)


class User(Base, TimestampMixin, SoftDeleteMixin):
    """WeChat mini program end user."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    unionid: Mapped[str | None] = mapped_column(String(128), index=True)
    nickname: Mapped[str | None] = mapped_column(String(64))
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    # active / disabled
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
