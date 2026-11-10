"""Fixed-window rate limiting middleware (Redis when available, in-memory fallback)."""
from __future__ import annotations

import logging
import threading
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.utils.redis_client import get_redis

logger = logging.getLogger(__name__)


class _MemoryCounter:
    def __init__(self) -> None:
        self._data: dict[str, tuple[int, int]] = {}
        self._lock = threading.Lock()

    def incr(self, key: str, window: int) -> int:
        with self._lock:
            if len(self._data) > 50_000:
                self._data.clear()
            count, w = self._data.get(key, (0, window))
            if w != window:
                count = 0
            count += 1
            self._data[key] = (count, window)
            return count


_memory = _MemoryCounter()


def _client_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth:
        return "t:" + auth[-24:]
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    return "ip:" + ip


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith(settings.API_PREFIX) or request.method == "OPTIONS":
            return await call_next(request)
        is_chat = path.startswith(f"{settings.API_PREFIX}/chat")
        is_login = path.startswith(f"{settings.API_PREFIX}/auth/") and request.method == "POST"
        limit = settings.CHAT_RATE_LIMIT_PER_MINUTE if is_chat else settings.RATE_LIMIT_PER_MINUTE
        bucket = "chat" if is_chat else ("login" if is_login else "api")
        if is_login:
            limit = 20
        window = int(time.time() // 60)
        key = f"rl:{bucket}:{_client_key(request)}:{window}"
        count = None
        r = get_redis()
        if r is not None:
            try:
                count = r.incr(key)
                if count == 1:
                    r.expire(key, 70)
            except Exception:  # Redis down -> degrade to memory
                count = None
        if count is None:
            count = _memory.incr(key, window)
        if count > limit:
            return JSONResponse(status_code=429, content={"code": 42900, "message": "请求过于频繁，请稍后再试", "data": None})
        return await call_next(request)
