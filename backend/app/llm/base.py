"""Unified LLM provider interface."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated: bool = False

    def as_dict(self) -> dict:
        return {"prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens,
                "total_tokens": self.total_tokens, "estimated": self.estimated}


@dataclass
class ChatResult:
    content: str
    usage: TokenUsage
    model: str
    finish_reason: str | None = None
    tool_calls: list[dict] = field(default_factory=list)
    raw_message: dict | None = None


@dataclass
class StreamChunk:
    """One streaming event: either a content delta, or a final usage report."""
    delta: str = ""
    usage: TokenUsage | None = None
    finish_reason: str | None = None


@dataclass
class EmbeddingResult:
    vectors: list[list[float]]
    usage: TokenUsage
    model: str


class LLMError(Exception):
    def __init__(self, message: str, *, retryable: bool = False, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.status_code = status_code


class BaseLLMProvider:
    """All model backends implement this interface; business code never imports a vendor SDK directly."""

    provider_name: str = "base"

    def chat(self, messages: list[dict], **kwargs: Any) -> ChatResult:
        raise NotImplementedError

    def stream_chat(self, messages: list[dict], **kwargs: Any) -> Iterator[StreamChunk]:
        raise NotImplementedError

    def embeddings(self, texts: list[str], **kwargs: Any) -> EmbeddingResult:
        raise NotImplementedError

    def test_connection(self) -> dict:
        raise NotImplementedError

    def close(self) -> None:  # optional
        return None
