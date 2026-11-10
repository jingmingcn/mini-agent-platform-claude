from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.schemas.common import ORMModel


class LLMConfigBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    provider: str = Field(..., min_length=1, max_length=64)
    base_url: HttpUrl
    chat_model: str | None = Field(None, max_length=128)
    embedding_model: str | None = Field(None, max_length=128)
    temperature: float = Field(0.7, ge=0, le=2)
    max_tokens: int | None = Field(None, ge=1, le=200_000)
    timeout_seconds: float | None = Field(None, ge=1, le=600)
    max_retries: int | None = Field(None, ge=0, le=10)
    enabled: bool = True
    is_default: bool = False

    @field_validator("chat_model", "embedding_model")
    @classmethod
    def _blank_none(cls, v):
        return v.strip() or None if isinstance(v, str) else v


class LLMConfigCreate(LLMConfigBase):
    api_key: str = Field(..., min_length=1, max_length=1024)


class LLMConfigUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    provider: str | None = Field(None, max_length=64)
    base_url: HttpUrl | None = None
    api_key: str | None = Field(None, max_length=1024, description="留空表示不修改")
    chat_model: str | None = Field(None, max_length=128)
    embedding_model: str | None = Field(None, max_length=128)
    temperature: float | None = Field(None, ge=0, le=2)
    max_tokens: int | None = Field(None, ge=1, le=200_000)
    timeout_seconds: float | None = Field(None, ge=1, le=600)
    max_retries: int | None = Field(None, ge=0, le=10)
    enabled: bool | None = None
    is_default: bool | None = None


class LLMConfigOut(ORMModel):
    """Never contains the API key — only a masked hint."""
    id: int
    name: str
    provider: str
    base_url: str
    api_key_masked: str
    chat_model: str | None
    embedding_model: str | None
    temperature: float
    max_tokens: int | None
    timeout_seconds: float | None
    max_retries: int | None
    enabled: bool
    is_default: bool
    last_test_status: str | None
    last_test_message: str | None
    created_at: datetime
    updated_at: datetime


class LLMTestIn(BaseModel):
    """Optionally test unsaved settings (api_key omitted => use stored key)."""
    pass
