from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigId, SoftDeleteMixin, TimestampMixin


class LLMConfig(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "llm_configs"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)  # openai/deepseek/moonshot/qwen/custom
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(String(2048), nullable=False)
    api_key_last4: Mapped[str | None] = mapped_column(String(8))
    chat_model: Mapped[str | None] = mapped_column(String(128))
    embedding_model: Mapped[str | None] = mapped_column(String(128))
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    max_tokens: Mapped[int | None] = mapped_column(Integer)
    timeout_seconds: Mapped[float | None] = mapped_column(Float)
    max_retries: Mapped[int | None] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    last_test_status: Mapped[str | None] = mapped_column(String(16))  # success / failed
    last_test_message: Mapped[str | None] = mapped_column(String(512))
