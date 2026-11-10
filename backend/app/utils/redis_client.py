from __future__ import annotations

import logging
import time

from app.core.config import settings

logger = logging.getLogger(__name__)
_client = None
_last_fail = 0.0


def get_redis():
    """Return a connected redis client or None (cached; retried at most every 30s after failure)."""
    global _client, _last_fail
    if not settings.REDIS_URL:
        return None
    if _client is not None:
        return _client
    if time.time() - _last_fail < 30:
        return None
    try:
        import redis

        c = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5, socket_timeout=1, decode_responses=True)
        c.ping()
        _client = c
        return c
    except Exception as e:  # pragma: no cover - depends on env
        _last_fail = time.time()
        logger.warning("Redis unavailable (%s); falling back to in-memory implementations", type(e).__name__)
        return None
