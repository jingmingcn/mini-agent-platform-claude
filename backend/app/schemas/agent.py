from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AgentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(None, max_length=1024)
    avatar: str | None = Field(None, max_length=512)
    category: str | None = Field(None, max_length=64)
    system_prompt: str = Field("", max_length=20000)
    welcome_message: str | None = Field(None, max_length=2000)
    suggested_questions: list[str] = Field(default_factory=list, max_length=10)
    llm_config_id: int | None = None
    temperature: float | None = Field(None, ge=0, le=2)
    max_tokens: int | None = Field(None, ge=1, le=200_000)
    knowledge_base_ids: list[int] = Field(default_factory=list, max_length=20)
    enable_rag: bool = False
    rag_top_k: int = Field(5, ge=1, le=20)
    rag_score_threshold: float = Field(0.3, ge=0, le=1)
    rag_no_result_policy: Literal["fallback", "strict"] = "fallback"
    rag_refuse_message: str | None = Field(None, max_length=512)
    enable_memory: bool = True
    memory_max_messages: int = Field(20, ge=0, le=200)
    memory_max_tokens: int = Field(4000, ge=200, le=128_000)
    enable_tools: bool = False
    tools: list[str] = Field(default_factory=list)
    access_level: Literal["public", "restricted"] = "public"
    sort_order: int = 0
    is_featured: bool = False


class AgentCreate(AgentBase):
    status: Literal["draft", "published", "offline"] = "draft"


class AgentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = Field(None, max_length=1024)
    avatar: str | None = Field(None, max_length=512)
    category: str | None = Field(None, max_length=64)
    system_prompt: str | None = Field(None, max_length=20000)
    welcome_message: str | None = Field(None, max_length=2000)
    suggested_questions: list[str] | None = Field(None, max_length=10)
    llm_config_id: int | None = None
    temperature: float | None = Field(None, ge=0, le=2)
    max_tokens: int | None = Field(None, ge=1, le=200_000)
    knowledge_base_ids: list[int] | None = Field(None, max_length=20)
    enable_rag: bool | None = None
    rag_top_k: int | None = Field(None, ge=1, le=20)
    rag_score_threshold: float | None = Field(None, ge=0, le=1)
    rag_no_result_policy: Literal["fallback", "strict"] | None = None
    rag_refuse_message: str | None = Field(None, max_length=512)
    enable_memory: bool | None = None
    memory_max_messages: int | None = Field(None, ge=0, le=200)
    memory_max_tokens: int | None = Field(None, ge=200, le=128_000)
    enable_tools: bool | None = None
    tools: list[str] | None = None
    access_level: Literal["public", "restricted"] | None = None
    sort_order: int | None = None
    is_featured: bool | None = None


class AgentOut(ORMModel):
    id: int
    name: str
    description: str | None
    avatar: str | None
    category: str | None
    system_prompt: str
    welcome_message: str | None
    suggested_questions: list[str] | None
    llm_config_id: int | None
    llm_config_name: str | None = None
    temperature: float | None
    max_tokens: int | None
    knowledge_base_ids: list[int] = []
    enable_rag: bool
    rag_top_k: int
    rag_score_threshold: float
    rag_no_result_policy: str
    rag_refuse_message: str | None
    enable_memory: bool
    memory_max_messages: int
    memory_max_tokens: int
    enable_tools: bool
    tools: list[str] | None
    status: str
    access_level: str
    sort_order: int
    is_featured: bool
    created_at: datetime
    updated_at: datetime


class AgentPublicOut(ORMModel):
    """What end users see: no system prompt, no model/KB configuration."""
    id: int
    name: str
    description: str | None
    avatar: str | None
    category: str | None
    welcome_message: str | None
    suggested_questions: list[str] | None
    enable_rag: bool
    is_featured: bool


class AgentPermissionsIn(BaseModel):
    user_ids: list[int] = Field(default_factory=list, max_length=5000)


class PromptBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(None, max_length=512)
    content: str = Field(..., min_length=1, max_length=20000)


class PromptUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = Field(None, max_length=512)
    content: str | None = Field(None, min_length=1, max_length=20000)


class PromptOut(ORMModel):
    id: int
    agent_id: int | None
    name: str
    description: str | None
    content: str
    version: int
    kind: str
    created_at: datetime
    updated_at: datetime
