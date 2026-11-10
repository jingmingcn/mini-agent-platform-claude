"""Logging setup with secret redaction."""
from __future__ import annotations

import logging
import re

_PATTERNS = [
    (re.compile(r"(sk-[A-Za-z0-9_\-]{6})[A-Za-z0-9_\-]+"), r"\1***"),
    (re.compile(r"(?i)(api[_-]?key['\"]?\s*[:=]\s*['\"]?)[^'\"\s,}]+"), r"\1***"),
    (re.compile(r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?bearer\s+)[^'\"\s,}]+"), r"\1***"),
    (re.compile(r"(?i)(password['\"]?\s*[:=]\s*['\"]?)[^'\"\s,}]+"), r"\1***"),
]


def redact(text: str) -> str:
    for pat, repl in _PATTERNS:
        text = pat.sub(repl, text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:  # pragma: no cover
            return True
        record.msg = redact(msg)
        record.args = ()
        return True


def setup_logging(debug: bool = False) -> None:
    root = logging.getLogger()
    if getattr(root, "_mini_agent_configured", False):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    handler.addFilter(RedactingFilter())
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    for noisy in ("httpx", "httpcore", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    root._mini_agent_configured = True  # type: ignore[attr-defined]
