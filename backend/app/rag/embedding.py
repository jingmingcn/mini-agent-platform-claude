"""Embedding backends behind one interface."""
from __future__ import annotations

import hashlib
import math
import re
import time
from collections import Counter

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequest
from app.llm.base import TokenUsage
from app.llm.provider_manager import build_provider, record_call
from app.models import KnowledgeBase, LLMConfig

LOCAL_HASH_MODEL = "local-hash"


class BaseEmbedder:
    model_name: str = ""

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


class LocalHashEmbedder(BaseEmbedder):
    """Offline feature-hashing embedder (CJK char uni/bi-grams + latin words).

    Lexical, not semantic: intended for demos and environments without an embedding API
    (e.g. DeepSeek/Kimi-only setups). Use a real embedding model for production quality.
    """
    model_name = LOCAL_HASH_MODEL
    _TOKEN = re.compile(r"[a-z0-9]+|[一-鿿]")

    def __init__(self, dim: int = 1024):
        self.dim = dim

    def _features(self, text: str) -> Counter:
        toks = self._TOKEN.findall(text.lower())
        feats: Counter = Counter()
        for i, t in enumerate(toks):
            feats[t] += 1
            if i + 1 < len(toks):
                feats[t + toks[i + 1]] += 1.5
        return feats

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for f, w in self._features(text).items():
                h = int.from_bytes(hashlib.md5(f.encode()).digest()[:8], "little")
                vec[h % self.dim] += (1.0 if (h >> 63) & 1 else -1.0) * (1 + math.log(w))
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


class ProviderEmbedder(BaseEmbedder):
    def __init__(self, cfg: LLMConfig, model: str | None = None):
        self.cfg = cfg
        self.model_name = model or cfg.embedding_model or ""
        if not self.model_name:
            raise BadRequest(f"模型配置「{cfg.name}」未设置 Embedding Model")
        self.provider = build_provider(cfg)

    def embed(self, texts: list[str]) -> list[list[float]]:
        t0 = time.time()
        try:
            res = self.provider.embeddings(texts, model=self.model_name)
        except Exception as e:
            record_call(cfg=self.cfg, call_type="embedding", usage=None, latency_ms=int((time.time() - t0) * 1000),
                        status="failed", error=str(e), model=self.model_name)
            raise
        record_call(cfg=self.cfg, call_type="embedding", usage=res.usage or TokenUsage(),
                    latency_ms=int((time.time() - t0) * 1000), model=self.model_name)
        return res.vectors


def get_embedder(db: Session, kb: KnowledgeBase) -> BaseEmbedder:
    if kb.embedding_llm_config_id:
        cfg = db.get(LLMConfig, kb.embedding_llm_config_id)
        if cfg is None or cfg.deleted_at is not None:
            raise BadRequest(f"知识库「{kb.name}」绑定的 Embedding 模型配置已不存在")
        if not cfg.enabled:
            raise BadRequest(f"知识库「{kb.name}」绑定的 Embedding 模型配置已停用")
        return ProviderEmbedder(cfg, kb.embedding_model)
    return LocalHashEmbedder()


def embedder_key(kb: KnowledgeBase) -> tuple:
    """KBs with the same key can share one query embedding."""
    return (kb.embedding_llm_config_id, kb.embedding_model if kb.embedding_llm_config_id else LOCAL_HASH_MODEL)
