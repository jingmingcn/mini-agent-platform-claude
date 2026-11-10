from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ChatIn(BaseModel):
    agent_id: int | None = None
    conversation_id: int | None = None
    content: str = Field("", max_length=8000)
    attachment_ids: list[int] = Field(default_factory=list, max_length=5)
    regenerate: bool = False


class StopIn(BaseModel):
    message_id: int


class FeedbackIn(BaseModel):
    rating: Literal[1, -1, 0]
    comment: str | None = Field(None, max_length=512)


class ConversationOut(ORMModel):
    id: int
    user_id: int
    agent_id: int
    agent_name: str | None = None
    agent_avatar: str | None = None
    title: str
    message_count: int
    last_message_at: datetime | None
    created_at: datetime


class ConversationRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class MessageOut(ORMModel):
    id: int
    conversation_id: int
    role: str
    content: str
    message_type: str
    status: str
    attachments: list | None
    citations: list | None
    token_usage: dict | None
    model: str | None
    feedback: int | None
    latency_ms: int | None
    created_at: datetime


class UploadedFileOut(ORMModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    url: str | None = None
    has_text: bool = False
