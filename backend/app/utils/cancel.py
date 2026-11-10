"""Cross-process cancellation flags for streaming generations (Redis, memory fallback)."""
from __future__ import annotations

import threading
import time

from app.utils.redis_client import get_redis

_mem: dict[int, float] = {}
_lock = threading.Lock()


def request_cancel(message_id: int) -> None:
    r = get_redis()
    if r is not None:
        try:
            r.setex(f"chat:cancel:{message_id}", 600, "1")
            return
        except Exception:
            pass
    with _lock:
        _mem[message_id] = time.time()


def is_cancelled(message_id: int) -> bool:
    r = get_redis()
    if r is not None:
        try:
            return bool(r.exists(f"chat:cancel:{message_id}"))
        except Exception:
            pass
    with _lock:
        return message_id in _mem


def clear_cancel(message_id: int) -> None:
    r = get_redis()
    if r is not None:
        try:
            r.delete(f"chat:cancel:{message_id}")
        except Exception:
            pass
    with _lock:
        _mem.pop(message_id, None)
