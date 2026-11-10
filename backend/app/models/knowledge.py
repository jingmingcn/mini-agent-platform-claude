from __future__ import annotations

from sqlalchemy import JSON, BigInteger, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigId, LongText, SoftDeleteMixin, TimestampMixin


class KnowledgeBase(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024))
    category: Mapped[str | None] = mapped_column(String(64))
    # Embedding: an llm_config whose embedding_model is used, or NULL + "local-hash" builtin embedder
    embedding_llm_config_id: Mapped[int | None] = mapped_column(ForeignKey("llm_configs.id", ondelete="SET NULL"))
    embedding_model: Mapped[str | None] = mapped_column(String(128))
    embedding_dim: Mapped[int | None] = mapped_column(Integer)
    vector_store: Mapped[str] = mapped_column(String(32), default="qdrant", nullable=False)
    collection_name: Mapped[str | None] = mapped_column(String(128))
    chunk_size: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=80, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    score_threshold: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)  # active / disabled
    created_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))


class Document(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True,
                                                   nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    # pending / processing / completed / failed
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stage: Mapped[str | None] = mapped_column(String(32))
    error_message: Mapped[str | None] = mapped_column(Text)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    task_id: Mapped[str | None] = mapped_column(String(64))
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))


class DocumentChunk(Base, TimestampMixin):
    """Chunk metadata; the embedding vector itself lives in the vector DB under point id == chunk_id."""
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    chunk_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True,
                                                   nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(LongText, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    meta: Mapped[dict | None] = mapped_column("metadata", JSON)
