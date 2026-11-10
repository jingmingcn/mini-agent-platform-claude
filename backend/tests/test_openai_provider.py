"""Protocol tests for the OpenAI-compatible provider against a mocked HTTP server
(same wire format used by OpenAI / DeepSeek / Kimi / Qwen compatible-mode)."""
import json

import httpx
import pytest
from openai import OpenAI

from app.llm.base import LLMError
from app.llm.openai_compatible import OpenAICompatibleProvider


def _provider(handler, **kw):
    client = OpenAI(api_key="sk-test", base_url="https://mock.local/v1", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    return OpenAICompatibleProvider(api_key="sk-test", base_url="https://mock.local/v1", client=client, **kw)


def test_chat_and_usage():
    seen = {}

    def handler(req: httpx.Request):
        seen.update(json.loads(req.content))
        assert req.headers["authorization"] == "Bearer sk-test"
        return httpx.Response(200, json={"id": "1", "object": "chat.completion", "created": 0, "model": "deepseek-chat",
                                         "choices": [{"index": 0, "finish_reason": "stop",
                                                      "message": {"role": "assistant", "content": "pong"}}],
                                         "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6}})

    p = _provider(handler, chat_model="deepseek-chat", temperature=0.3)
    r = p.chat([{"role": "user", "content": "ping"}])
    assert r.content == "pong" and r.usage.total_tokens == 6 and not r.usage.estimated
    assert seen["model"] == "deepseek-chat" and seen["temperature"] == 0.3


def test_stream_chat_with_usage_chunk():
    def handler(req):
        body = json.loads(req.content)
        assert body["stream"] is True and body["stream_options"] == {"include_usage": True}
        lines = []
        for piece in ["你", "好"]:
            lines.append({"id": "1", "object": "chat.completion.chunk", "created": 0, "model": "m",
                          "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}]})
        lines.append({"id": "1", "object": "chat.completion.chunk", "created": 0, "model": "m",
                      "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
        lines.append({"id": "1", "object": "chat.completion.chunk", "created": 0, "model": "m", "choices": [],
                      "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}})
        sse = "".join(f"data: {json.dumps(x)}\n\n" for x in lines) + "data: [DONE]\n\n"
        return httpx.Response(200, content=sse.encode(), headers={"content-type": "text/event-stream"})

    chunks = list(_provider(handler, chat_model="m").stream_chat([{"role": "user", "content": "hi"}]))
    assert "".join(c.delta for c in chunks) == "你好"
    assert chunks[-1].usage.total_tokens == 5 and chunks[-1].finish_reason == "stop"


def test_stream_without_usage_falls_back_to_estimate():
    def handler(req):
        chunk = {"id": "1", "object": "chat.completion.chunk", "created": 0, "model": "m",
                 "choices": [{"index": 0, "delta": {"content": "hello"}, "finish_reason": "stop"}]}
        return httpx.Response(200, content=f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n".encode(),
                              headers={"content-type": "text/event-stream"})

    chunks = list(_provider(handler, chat_model="m").stream_chat([{"role": "user", "content": "hi"}]))
    assert chunks[-1].usage.estimated and chunks[-1].usage.completion_tokens > 0


def test_embeddings_batched_and_ordered():
    calls = []

    def handler(req):
        body = json.loads(req.content)
        calls.append(len(body["input"]))
        data = [{"object": "embedding", "index": i, "embedding": [float(i), 1.0]} for i in reversed(range(len(body["input"])))]
        return httpx.Response(200, json={"object": "list", "data": data, "model": "e",
                                         "usage": {"prompt_tokens": 3, "total_tokens": 3}})

    r = _provider(handler, embedding_model="e").embeddings([f"t{i}" for i in range(25)])
    assert calls == [10, 10, 5] and len(r.vectors) == 25 and r.vectors[1][0] == 1.0


@pytest.mark.parametrize("status,needle", [(401, "API Key"), (404, "Base URL"), (429, "限流"), (500, "500")])
def test_error_mapping(status, needle):
    p = _provider(lambda req: httpx.Response(status, json={"error": {"message": "boom"}}), chat_model="m")
    with pytest.raises(LLMError) as ei:
        p.chat([{"role": "user", "content": "x"}])
    assert needle in ei.value.message


def test_missing_embedding_model_message():
    p = _provider(lambda req: httpx.Response(200), chat_model="deepseek-chat")
    with pytest.raises(LLMError) as ei:
        p.embeddings(["x"])
    assert "Embedding" in ei.value.message
