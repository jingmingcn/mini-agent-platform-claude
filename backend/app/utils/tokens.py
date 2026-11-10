"""Lightweight token estimation (no external tokenizer download required).

CJK characters ~= 1 token each, other text ~= 4 chars per token. Used for context budgeting
and as a fallback when the provider does not report usage.
"""
from __future__ import annotations

import re

_CJK = re.compile(r"[　-〿぀-ヿ㐀-䶿一-鿿가-힯＀-￯]")


def estimate_tokens(text: str | None) -> int:
    if not text:
        return 0
    cjk = len(_CJK.findall(text))
    other = len(text) - cjk
    return cjk + (other + 3) // 4


def estimate_messages_tokens(messages: list[dict]) -> int:
    total = 0
    for m in messages:
        c = m.get("content")
        total += 4 + estimate_tokens(c if isinstance(c, str) else str(c))
    return total + 2
