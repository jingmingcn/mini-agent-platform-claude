"""VectorStore abstraction with a Qdrant implementation."""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VectorRecord:
    id: str  # == chunk_id (uuid)
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorHit:
    id: str
    score: float
    payload: dict[str, Any]


class VectorStore:
    def ensure_collection(self, name: str, dim: int) -> None: ...
    def upsert(self, name: str, records: list[VectorRecord]) -> None: ...
    def delete_by_filter(self, name: str, filters: dict[str, Any]) -> None: ...
    def delete_collection(self, name: str) -> None: ...
    def search(self, name: str, vector: list[float], top_k: int = 5, score_threshold: float | None = None,
               filters: dict[str, Any] | None = None) -> list[VectorHit]: ...
    def count(self, name: str, filters: dict[str, Any] | None = None) -> int: ...
    def close(self) -> None: ...


class QdrantVectorStore(VectorStore):
    def __init__(self, client=None):
        from qdrant_client import QdrantClient

        if client is not None:
            self.client = client
        elif settings.QDRANT_URL:
            self.client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY, timeout=30)
        else:
            # Embedded mode: data persisted on disk, single process only (no Celery worker sharing).
            self.client = QdrantClient(path=settings.QDRANT_PATH)

    @staticmethod
    def _filter(filters: dict[str, Any] | None):
        from qdrant_client import models as m

        if not filters:
            return None
        must = []
        for k, v in filters.items():
            if isinstance(v, (list, tuple, set)):
                must.append(m.FieldCondition(key=k, match=m.MatchAny(any=list(v))))
            else:
                must.append(m.FieldCondition(key=k, match=m.MatchValue(value=v)))
        return m.Filter(must=must)

    def ensure_collection(self, name: str, dim: int) -> None:
        from qdrant_client import models as m

        if self.client.collection_exists(name):
            info = self.client.get_collection(name)
            existing = info.config.params.vectors.size  # type: ignore[union-attr]
            if existing != dim:
                raise ValueError(f"向量维度不一致: 集合 {existing}, 新向量 {dim}。请重建知识库")
            return
        self.client.create_collection(name, vectors_config=m.VectorParams(size=dim, distance=m.Distance.COSINE))
        for key in ("document_id", "knowledge_base_id"):
            try:
                self.client.create_payload_index(name, key, field_schema=m.PayloadSchemaType.INTEGER)
            except Exception:  # embedded mode ignores indexes
                pass

    def upsert(self, name: str, records: list[VectorRecord]) -> None:
        from qdrant_client import models as m

        for i in range(0, len(records), 128):
            batch = records[i:i + 128]
            self.client.upsert(name, points=[m.PointStruct(id=r.id, vector=r.vector, payload=r.payload) for r in batch])

    def delete_by_filter(self, name: str, filters: dict[str, Any]) -> None:
        from qdrant_client import models as m

        if not self.client.collection_exists(name):
            return
        self.client.delete(name, points_selector=m.FilterSelector(filter=self._filter(filters)))

    def delete_collection(self, name: str) -> None:
        if self.client.collection_exists(name):
            self.client.delete_collection(name)

    def search(self, name, vector, top_k=5, score_threshold=None, filters=None) -> list[VectorHit]:
        if not self.client.collection_exists(name):
            return []
        res = self.client.query_points(name, query=vector, limit=top_k, score_threshold=score_threshold,
                                       query_filter=self._filter(filters), with_payload=True)
        return [VectorHit(id=str(p.id), score=float(p.score), payload=p.payload or {}) for p in res.points]

    def count(self, name, filters=None) -> int:
        if not self.client.collection_exists(name):
            return 0
        return self.client.count(name, count_filter=self._filter(filters), exact=True).count


    def close(self) -> None:
        try:
            self.client.close()
        except Exception:  # pragma: no cover
            pass


_store: VectorStore | None = None
_lock = threading.Lock()


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        with _lock:
            if _store is None:
                _store = QdrantVectorStore()
    return _store


def set_vector_store(store: VectorStore | None) -> None:
    """Testing hook."""
    global _store
    _store = store


def collection_for_kb(kb_id: int) -> str:
    return f"kb_{kb_id}"
