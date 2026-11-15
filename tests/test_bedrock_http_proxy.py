"""ADR-0011 local HTTP adapter checks; fake Bedrock only, no AWS credentials/calls."""

from __future__ import annotations

import base64
import importlib.util
import json
import sys
import threading
import types
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest


class FakeClient:
    model = "global.anthropic.claude-haiku-5-5"

    def __init__(self, **kwargs):
        self.calls = []
        self.barrier = None

    def converse_raw(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        if self.barrier:
            self.barrier.wait(timeout=3)
        return {"text": "synthetic reply", "usage": {"totalTokens": 3}}

    def converse_stream_raw(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return iter_events([
            {"contentBlockDelta": {"delta": {"text": "synthetic "}}},
            {"contentBlockDelta": {"delta": {"reasoningContent": {"text": "reason"}}}},
            {"contentBlockDelta": {"delta": {"text": "reply"}}},
            {"contentBlockStart": {"contentBlockIndex": 1, "start": {
                "toolUse": {"toolUseId": "call_test", "name": "read_file"}}}},
            {"contentBlockDelta": {"contentBlockIndex": 1, "delta": {
                "toolUse": {"input": '{"path":"synthetic.txt"}'}}}},
            {"messageStop": {"stopReason": "tool_use"}},
            {"metadata": {"usage": {"inputTokens": 1, "outputTokens": 2, "totalTokens": 3}}},
        ])

    def invoke(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return types.SimpleNamespace(text="synthetic reply", usage={}, latency_s=0)


def iter_events(events):
    yield from events


@pytest.fixture
def proxy(monkeypatch):
    # Load the actual standalone entry point without constructing an AWS client.
    stub = types.ModuleType("llm_client")
    stub.LLMClient = FakeClient
    stub.LLMError = RuntimeError
    stub.DEFAULT_MAX_TOKENS = 8192
    monkeypatch.setitem(sys.modules, "llm_client", stub)
    for key in ("DRAWIO_PROXY_ALLOWED_MODELS", "DRAWIO_PROXY_TOKEN", "DRAWIO_PROXY_TOKEN_FILE",
                "DRAWIO_PROXY_MAX_BODY_BYTES", "DRAWIO_PROXY_MAX_IMAGE_BYTES", "DRAWIO_PROXY_MAX_IMAGES"):
        monkeypatch.delenv(key, raising=False)
    path = Path(__file__).resolve().parents[1] / "src/llm/bedrock_http_proxy.py"
    spec = importlib.util.spec_from_file_location("http_proxy_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def server(proxy):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), proxy.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd.server_port
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=3)


def request(port, body=None, *, method="POST", path="/v1/chat/completions", headers=None):
    connection = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        payload = json.dumps(body) if body is not None else None
        connection.request(method, path, payload, headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read().decode()
    finally:
        connection.close()


def image_part(url=None):
    # Synthetic bytes only: the adapter passes bytes, it does not inspect pixels.
    return {"type": "image_url", "image_url": {"url": url or "data:image/png;base64,c3ludGhldGlj"}}


def chat(content=None, **kwargs):
    return {"messages": [{"role": "user", "content": content if content is not None else "synthetic"}], **kwargs}


@pytest.mark.parametrize("mime,fmt", [
    ("png", "png"), ("jpeg", "jpeg"), ("jpg", "jpeg"), ("gif", "gif"), ("webp", "webp"),
])
@pytest.mark.parametrize("string_url", [False, True])
def test_images_preserve_bytes_and_text(proxy, mime, fmt, string_url):
    url = f"data:image/{mime};base64,c3ludGhldGlj"
    part = image_part(url)
    if string_url:
        part["image_url"] = url
    messages, system = proxy._oai_messages_to_converse(chat([
        {"type": "text", "text": "synthetic"}, part])["messages"])
    assert system == ""
    assert messages[0]["content"] == [
        {"text": "synthetic"}, {"image": {"format": fmt, "source": {"bytes": b"synthetic"}}}]


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("part,code", [
    (image_part("https://example.invalid/private-marker"), "remote_image_url_not_supported"),
    (image_part("data:image/png;base64,%%%private-marker"), "invalid_image_data"),
    (image_part("data:image/png;base64,c3lu\ndGhldGlj"), "invalid_image_data"),
    (image_part("data:image/png;base64,"), "invalid_image_data"),
    (image_part("data:image/png,synthetic"), "invalid_image_data"),
    (image_part("data:image/svg+xml;base64,c3ludGhldGlj"), "unsupported_image_format"),
    ({"type": "input_audio", "data": "private-marker"}, "unsupported_content_part"),
    ({"type": "input_image", "image_url": "private-marker"}, "unsupported_content_part"),
    (None, "unsupported_content_part"),
])
def test_rejection_before_bedrock_and_sse(proxy, server, capsys, stream, part, code):
    status, headers, payload = request(server, chat([part], stream=stream))
    assert status == 400
    assert "application/json" in headers["Content-Type"]
    assert json.loads(payload)["error"] == code
    assert not proxy._client.calls
    assert "private-marker" not in capsys.readouterr().out


@pytest.mark.parametrize("role", ["system", "developer", "assistant", "tool"])
def test_images_rejected_in_non_user_roles(proxy, server, role):
    body = {"messages": [{"role": role, "content": [image_part()]}], "stream": True}
    status, _, payload = request(server, body)
    assert status == 400
    assert json.loads(payload)["error"] == "image_not_supported_for_role"
    assert not proxy._client.calls


def test_image_size_boundary(proxy, server, monkeypatch):
    monkeypatch.setattr(proxy, "MAX_IMAGE_BYTES", 9)
    assert request(server, chat([image_part()]))[0] == 200
    oversized = "data:image/png;base64," + base64.b64encode(b"x" * 10).decode()
    status, _, payload = request(server, chat([image_part(oversized)], stream=True))
    assert status == 413
    assert json.loads(payload)["error"] == "image_too_large"
    assert len(proxy._client.calls) == 1


def test_total_image_count_across_history(proxy, server):
    assert proxy.MAX_IMAGES == 20
    assert request(server, chat([image_part()] * 20))[0] == 200
    body = chat([image_part()] * 10)
    body["messages"] += [{"role": "assistant", "content": "synthetic"},
                         {"role": "user", "content": [image_part()] * 11}]
    status, _, payload = request(server, body)
    assert status == 400
    assert json.loads(payload)["error"] == "too_many_images"
    assert len(proxy._client.calls) == 1


@pytest.mark.parametrize("stream", [False, True])
def test_image_response_and_safe_counts(proxy, server, capsys, stream):
    status, headers, payload = request(server, chat([image_part()], stream=stream))
    assert status == 200
    assert "images_in=1" in capsys.readouterr().out
    assert proxy._client.calls[0][0][0]["content"][0]["image"]["source"]["bytes"] == b"synthetic"
    if stream:
        assert headers["Transfer-Encoding"] == "chunked"
        assert payload.endswith("data: [DONE]\n\n")
        chunks = [json.loads(frame[6:]) for frame in payload.split("\n\n") if frame and frame != "data: [DONE]"]
        deltas = [chunk["choices"][0]["delta"] for chunk in chunks]
        assert "".join(d.get("content", "") for d in deltas) == "synthetic reply"
        assert any(d.get("reasoning_content") == "reason" for d in deltas)
        assert chunks[-1]["choices"][0]["finish_reason"] == "tool_calls"
        assert chunks[-1]["usage"]["total_tokens"] == 3
        assert any(d.get("tool_calls") for d in deltas)
    else:
        assert json.loads(payload)["choices"][0]["message"]["content"] == "synthetic reply"


def test_allowlist_and_health(proxy, server):
    assert request(server, method="GET", path="/health")[0] == 200
    status, _, payload = request(server, method="GET", path="/v1/models")
    models = [item["id"] for item in json.loads(payload)["data"]]
    assert status == 200
    assert models == list(proxy.VERIFIED_MODELS)
    assert len(models) == 8
    for model in ("global.anthropic.claude-fable-5-1", "global.zai.glm-5-3"):
        status, _, payload = request(server, chat(model=model))
        assert status == 403
        assert json.loads(payload)["error"] == "model_not_allowed"
    assert not proxy._client.calls


def test_body_limit_auth_and_tokens(proxy, server, monkeypatch):
    assert proxy.MAX_BODY_BYTES == 20 * 1024 * 1024
    monkeypatch.setattr(proxy, "TOKEN", "synthetic-token")
    assert request(server, chat())[0] == 401
    assert request(server, chat(), headers={"Authorization": "Bearer wrong"})[0] == 401
    headers = {"Authorization": "Bearer synthetic-token"}
    assert request(server, chat(), headers=headers)[0] == 200
    for value in (0, 131073):
        status, _, payload = request(server, chat(max_tokens=value), headers=headers)
        assert status == 400
        assert json.loads(payload)["error"] == "max_tokens_out_of_range"
    monkeypatch.setattr(proxy, "MAX_BODY_BYTES", 10)
    status, _, payload = request(server, chat(), headers=headers)
    assert status == 413
    assert json.loads(payload)["error"] == "request_too_large"


def test_tool_round_trip_and_parallel_requests(proxy, server):
    body = chat()
    body["messages"] += [
        {"role": "assistant", "content": None, "tool_calls": [{"id": "call_test",
            "function": {"name": "read_file", "arguments": '{"path":"synthetic.txt"}'}}]},
        {"role": "tool", "tool_call_id": "call_test", "content": "synthetic result"},
    ]
    assert request(server, body)[0] == 200
    messages = proxy._client.calls[0][0]
    assert messages[1]["content"][0]["toolUse"]["name"] == "read_file"
    assert messages[2]["content"][0]["toolResult"]["toolUseId"] == "call_test"
    proxy._client.barrier = threading.Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(request, server, chat()) for _ in range(2)]
        assert all(future.result()[0] == 200 for future in futures)


def test_drawio_stays_text_only(proxy, server):
    assert request(server, {"prompt": "synthetic"})[0] == 200
    status, _, payload = request(server, {"prompt": [image_part()]})
    assert status == 400
    assert json.loads(payload)["error"] == "image_not_supported_for_role"
    assert len(proxy._client.calls) == 1
