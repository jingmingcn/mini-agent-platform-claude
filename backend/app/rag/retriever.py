"""Multi knowledge-base retrieval with score threshold, de-dup and optional rerank."""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, KnowledgeBase
from app.rag.embedding import embedder_key, get_embedder
from app.rag.vector_store import collection_for_kb, get_vector_store

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: int
    document_name: str
    knowledge_base_id: int
    knowledge_base_name: str
    content: str
    score: float
    page_number: int | None = None
    chunk_index: int | None = None

    def to_citation(self, index: int, snippet_len: int = 300) -> dict:
        d = asdict(self)
        d["index"] = index
        d["score"] = round(self.score, 4)
        d["snippet"] = self.content[:snippet_len]
        return d


class BaseReranker:
    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        return chunks


# TODO: plug a cross-encoder / rerank API (e.g. bge-reranker, DashScope gte-rerank) via BaseReranker.
default_reranker = BaseReranker()


def preprocess_query(q: str) -> str:
    return " ".join(q.strip().split())[:1000]


def retrieve(db: Session, kbs: list[KnowledgeBase], query: str, top_k: int = 5,
             score_threshold: float | None = None, reranker: BaseReranker | None = None) -> list[RetrievedChunk]:
    query = preprocess_query(query)
    kbs = [kb for kb in kbs if kb.deleted_at is None and kb.status == "active"]
    if not query or not kbs:
        return []
    store = get_vector_store()
    groups: dict[tuple, list[KnowledgeBase]] = {}
    for kb in kbs:
        groups.setdefault(embedder_key(kb), []).append(kb)

    hits: list[tuple[KnowledgeBase, object]] = []
    for _, group in groups.items():
        vec = get_embedder(db, group[0]).embed_query(query)
        for kb in group:
            if kb.embedding_dim and kb.embedding_dim != len(vec):
                logger.warning("KB %s dimension mismatch, skip", kb.id)
                continue
            thr = score_threshold if score_threshold is not None else kb.score_threshold
            for h in store.search(collection_for_kb(kb.id), vec, top_k=top_k, score_threshold=thr):
                hits.append((kb, h))

    doc_ids = {int(h.payload.get("document_id", 0)) for _, h in hits}
    docs = {d.id: d for d in db.scalars(select(Document).where(Document.id.in_(doc_ids)))} if doc_ids else {}
    results: list[RetrievedChunk] = []
    seen: set[str] = set()
    for kb, h in sorted(hits, key=lambda x: x[1].score, reverse=True):
        p = h.payload
        doc = docs.get(int(p.get("document_id", 0)))
        if doc is None or doc.deleted_at is not None or doc.status != "completed":
            continue  # stale vector of a removed / reprocessing document
        content = p.get("content", "")
        key = content.strip()[:200]
        if key in seen:
            continue
        seen.add(key)
        results.append(RetrievedChunk(chunk_id=str(p.get("chunk_id", h.id)), document_id=doc.id,
                                      document_name=doc.filename, knowledge_base_id=kb.id,
                                      knowledge_base_name=kb.name, content=content, score=h.score,
                                      page_number=p.get("page_number"), chunk_index=p.get("chunk_index")))
    results = (reranker or default_reranker).rerank(query, results)
    return results[:top_k]
