"""Test fixtures: isolated SQLite DB, in-memory Qdrant, synchronous jobs and a fake LLM provider."""
from __future__ import annotations

import json
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="mini_agent_test_")
os.environ.update({
    "DATABASE_URL": os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_tmp}/test.db",
    "REDIS_URL": "",
    "UPLOAD_DIR": f"{_tmp}/uploads",
    "WECHAT_DEV_LOGIN": "true",
    "WECHAT_APPID": "",
    "SECRET_KEY": "test-secret-key-for-unit-tests-0123456789",
    "RATE_LIMIT_PER_MINUTE": "100000",
    "CHAT_RATE_LIMIT_PER_MINUTE": "100000",
    "CELERY_ENABLED": "false",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402

import app.models  # noqa: E402,F401
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.llm.base import BaseLLMProvider, ChatResult, EmbeddingResult, StreamChunk, TokenUsage  # noqa: E402
from app.llm import provider_manager  # noqa: E402
from app.rag.embedding import LocalHashEmbedder  # noqa: E402
from app.rag.vector_store import QdrantVectorStore, set_vector_store  # noqa: E402
from app.tasks import dispatcher  # noqa: E402


class FakeProvider(BaseLLMProvider):
    """Echoes back whether knowledge was injected; records the last request for assertions."""
    last_messages: list[dict] = []
    last_kwargs: dict = {}

    def __init__(self, cfg):
        self.cfg = cfg

    def _answer(self, messages):
        system = messages[0]["content"]
        if "<knowledge>" in system:
            return "根据知识库资料，答案如下 [1]。"
        return "这是模型的回答。"

    def chat(self, messages, **kwargs):
        FakeProvider.last_messages, FakeProvider.last_kwargs = messages, kwargs
        tools = kwargs.get("tools")
        if tools and not any(m["role"] == "tool" for m in messages):
            return ChatResult(content="", usage=TokenUsage(10, 5, 15), model="fake", finish_reason="tool_calls",
                              tool_calls=[{"id": "c1", "type": "function", "function": {
                                  "name": "calculator", "arguments": json.dumps({"expression": "6*7"})}}],
                              raw_message={"role": "assistant", "content": "", "tool_calls": []})
        if tools:
            return ChatResult(content="计算结果是 42", usage=TokenUsage(20, 5, 25), model="fake", finish_reason="stop")
        return ChatResult(content=self._answer(messages), usage=TokenUsage(10, 5, 15), model="fake",
                          finish_reason="stop")

    def stream_chat(self, messages, **kwargs):
        FakeProvider.last_messages, FakeProvider.last_kwargs = messages, kwargs
        text = self._answer(messages)
        for i in range(0, len(text), 4):
            yield StreamChunk(delta=text[i:i + 4])
        yield StreamChunk(usage=TokenUsage(30, 10, 40), finish_reason="stop")

    def embeddings(self, texts, **kwargs):
        return EmbeddingResult(vectors=LocalHashEmbedder(dim=64).embed(texts), usage=TokenUsage(len(texts), 0, len(texts)),
                               model="fake-embed")

    def test_connection(self):
        return {"chat": {"ok": True, "model": "fake", "reply": "pong", "latency_ms": 1,
                         "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}}


@pytest.fixture(scope="session", autouse=True)
def _setup():
    Base.metadata.drop_all(engine)  # TEST_DATABASE_URL may point at a reused MySQL schema
    Base.metadata.create_all(engine)
    set_vector_store(QdrantVectorStore(client=QdrantClient(":memory:")))
    dispatcher.RUN_SYNC = True
    provider_manager.set_provider_factory(lambda cfg: FakeProvider(cfg))
    from app.scripts.init_db import seed
    db = SessionLocal()
    seed(db)
    db.close()
    yield


@pytest.fixture(scope="session")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_headers(client):
    r = client.post("/api/v1/auth/admin/login", json={"username": "admin", "password": "Admin@123456"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


def wechat_login(client, code: str) -> dict:
    r = client.post("/api/v1/auth/wechat/login", json={"code": code, "nickname": code})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.split("\n\n"):
        ev, data = None, None
        for line in block.split("\n"):
            if line.startswith("event:"):
                ev = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
        if ev:
            events.append((ev, data))
    return events
