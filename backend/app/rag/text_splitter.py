"""Recursive character text splitter (Chinese + English aware)."""
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", ". ", "! ", "? ", "; ", "，", ", ", " ", ""]


@dataclass
class TextChunk:
    content: str
    index: int
    page_number: int | None = None


class RecursiveTextSplitter:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80, separators: list[str] | None = None):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if not 0 <= chunk_overlap < chunk_size:
            raise ValueError("chunk_overlap must be in [0, chunk_size)")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or DEFAULT_SEPARATORS

    def _split(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]
        sep, rest = separators[0], separators[1:]
        if sep == "":
            step = self.chunk_size - self.chunk_overlap
            return [text[i:i + self.chunk_size] for i in range(0, len(text), step)]
        if sep not in text:
            return self._split(text, rest)
        pieces = [p + sep for p in text.split(sep)]
        pieces[-1] = pieces[-1][: -len(sep)]
        out: list[str] = []
        for p in pieces:
            if not p:
                continue
            if len(p) > self.chunk_size:
                out.extend(self._split(p, rest))
            else:
                out.append(p)
        return out

    def _merge(self, pieces: list[str]) -> list[str]:
        chunks: list[str] = []
        current = ""
        for p in pieces:
            if len(current) + len(p) <= self.chunk_size:
                current += p
                continue
            if current.strip():
                chunks.append(current.strip())
            # carry an overlap tail from the previous chunk
            tail = current[-self.chunk_overlap:] if self.chunk_overlap else ""
            current = tail + p if len(tail) + len(p) <= self.chunk_size else p
        if current.strip():
            chunks.append(current.strip())
        return chunks

    def split_text(self, text: str) -> list[str]:
        if not text.strip():
            return []
        return self._merge(self._split(text, self.separators))

    def split_pages(self, pages: list[tuple[str, int | None]]) -> list[TextChunk]:
        result: list[TextChunk] = []
        for text, page in pages:
            for c in self.split_text(text):
                result.append(TextChunk(content=c, index=len(result), page_number=page))
        return result
