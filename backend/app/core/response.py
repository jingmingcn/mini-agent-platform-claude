"""Unified response envelope: {"code": 0, "message": "ok", "data": ...}."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T | None = None


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def ok(data=None, message: str = "ok") -> dict:
    return {"code": 0, "message": message, "data": data}
