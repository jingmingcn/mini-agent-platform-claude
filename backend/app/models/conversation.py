from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigId, LongText, SoftDeleteMixin, TimestampMixin


class Conversation(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="新对话", nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[str | None] = mapped_column(LongText)  # compressed memory of truncated history
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)


class Message(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True,
                                                 nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # system/user/assistant/tool
    content: Mapped[str] = mapped_column(LongText, default="", nullable=False)
    # text/markdown/image/table/card/file/error
    message_type: Mapped[str] = mapped_column(String(16), default="text", nullable=False)
    # streaming/completed/interrupted/error
    status: Mapped[str] = mapped_column(String(16), default="completed", nullable=False)
    attachments: Mapped[list | None] = mapped_column(JSON)
    citations: Mapped[list | None] = mapped_column(JSON)
    token_usage: Mapped[dict | None] = mapped_column(JSON)
    model: Mapped[str | None] = mapped_column(String(128))
    feedback: Mapped[int | None] = mapped_column(SmallInteger)  # 1 like / -1 dislike
    feedback_comment: Mapped[str | None] = mapped_column(String(512))
    latency_ms: Mapped[int | None] = mapped_column(Integer)


class UploadedFile(Base, TimestampMixin):
    """Files uploaded by end users in chat (images / documents)."""
    __tablename__ = "uploaded_files"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(LongText)
