from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigId, LongText, SoftDeleteMixin, TimestampMixin


class Agent(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024))
    avatar: Mapped[str | None] = mapped_column(String(512))  # URL or emoji
    category: Mapped[str | None] = mapped_column(String(64))
    system_prompt: Mapped[str] = mapped_column(LongText, default="", nullable=False)
    welcome_message: Mapped[str | None] = mapped_column(Text)
    suggested_questions: Mapped[list | None] = mapped_column(JSON)
    # null => use the platform default model
    llm_config_id: Mapped[int | None] = mapped_column(ForeignKey("llm_configs.id", ondelete="SET NULL"), index=True)
    temperature: Mapped[float | None] = mapped_column(Float)
    max_tokens: Mapped[int | None] = mapped_column(Integer)

    # RAG
    enable_rag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rag_top_k: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    rag_score_threshold: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)
    # strict: refuse when nothing relevant; fallback: answer with model knowledge but say so
    rag_no_result_policy: Mapped[str] = mapped_column(String(16), default="fallback", nullable=False)
    rag_refuse_message: Mapped[str | None] = mapped_column(String(512))

    # Memory
    enable_memory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    memory_max_messages: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    memory_max_tokens: Mapped[int] = mapped_column(Integer, default=4000, nullable=False)

    # Tools
    enable_tools: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tools: Mapped[list | None] = mapped_column(JSON)  # list of tool names

    # Publishing / access
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False, index=True)  # draft/published/offline
    access_level: Mapped[str] = mapped_column(String(16), default="public", nullable=False)  # public/restricted
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))


class AgentKnowledgeBase(Base, TimestampMixin):
    __tablename__ = "agent_knowledge_bases"
    __table_args__ = (UniqueConstraint("agent_id", "knowledge_base_id", name="uq_agent_kb"),)

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True,
                                                   nullable=False)


class UserAgentPermission(Base, TimestampMixin):
    __tablename__ = "user_agent_permissions"
    __table_args__ = (UniqueConstraint("user_id", "agent_id", name="uq_user_agent"),)

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)


class AgentPrompt(Base, TimestampMixin, SoftDeleteMixin):
    """Prompt library entries (agent_id NULL) and per-agent system prompt versions."""
    __tablename__ = "agent_prompts"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(LongText, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="template", nullable=False)  # template / version
    created_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))
