from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel


class KBBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(None, max_length=1024)
    category: str | None = Field(None, max_length=64)
    embedding_llm_config_id: int | None = Field(None, description="为空则使用内置 local-hash 离线向量化")
    embedding_model: str | None = Field(None, max_length=128, description="覆盖模型配置中的 embedding_model")
    chunk_size: int = Field(500, ge=100, le=4000)
    chunk_overlap: int = Field(80, ge=0, le=1000)
    top_k: int = Field(5, ge=1, le=20)
    score_threshold: float = Field(0.3, ge=0, le=1)
    status: Literal["active", "disabled"] = "active"

    @model_validator(mode="after")
    def _overlap(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        return self


class KBCreate(KBBase):
    pass


class KBUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = Field(None, max_length=1024)
    category: str | None = Field(None, max_length=64)
    embedding_llm_config_id: int | None = None
    embedding_model: str | None = Field(None, max_length=128)
    chunk_size: int | None = Field(None, ge=100, le=4000)
    chunk_overlap: int | None = Field(None, ge=0, le=1000)
    top_k: int | None = Field(None, ge=1, le=20)
    score_threshold: float | None = Field(None, ge=0, le=1)
    status: Literal["active", "disabled"] | None = None


class KBOut(ORMModel):
    id: int
    name: str
    description: str | None
    category: str | None
    embedding_llm_config_id: int | None
    embedding_model: str | None
    embedding_dim: int | None
    vector_store: str
    collection_name: str | None
    chunk_size: int
    chunk_overlap: int
    top_k: int
    score_threshold: float
    status: str
    document_count: int = 0
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentOut(ORMModel):
    id: int
    knowledge_base_id: int
    filename: str
    file_type: str
    file_size: int
    status: str
    progress: int
    stage: str | None
    error_message: str | None
    chunk_count: int
    char_count: int
    task_id: str | None
    created_at: datetime
    updated_at: datetime


class ChunkOut(ORMModel):
    id: int
    chunk_id: str
    document_id: int
    knowledge_base_id: int
    chunk_index: int
    content: str
    char_count: int
    page_number: int | None
    meta: dict | None = None


class SearchIn(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int | None = Field(None, ge=1, le=20)
    score_threshold: float | None = Field(None, ge=0, le=1)
