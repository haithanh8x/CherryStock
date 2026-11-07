"""Tests for the Bedrock proxy streaming conversion.

These cover the OpenAI-compatible SSE contract only; no AWS call is made.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytest.importorskip("boto3", reason="bedrock-proxy extra is not installed")
pytest.importorskip("fastapi", reason="bedrock-proxy extra is not installed")

from tools.bedrock_proxy.app import ChatRequest, stream_response  # noqa: E402


def test_request_defaults_to_non_streaming() -> None:
    """draw.io's AI dialog omits `stream` and expects one JSON response."""
    request = ChatRequest(messages=[{"role": "user", "content": "hi"}])

    assert request.stream is False


def collect_chunks(events: list[dict[str, Any]], *, include_usage: bool = False) -> list[dict]:
    stream = {"stream": events}
    frames = list(stream_response(stream, "test-model", include_usage))
    assert frames[-1] == "data: [DONE]\n\n"
    chunks = []
    for frame in frames[:-1]:
        assert frame.startswith("data: ")
        chunks.append(json.loads(frame[len("data: "):]))
    return chunks


def finish_reason_of(chunks: list[dict]) -> str | None:
    for chunk in reversed(chunks):
        for choice in chunk.get("choices", []):
            if choice.get("finish_reason"):
                return choice["finish_reason"]
    return None


def test_text_stream_emits_content_and_stop() -> None:
    chunks = collect_chunks([
        {"messageStart": {"role": "assistant"}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": "Hello"}}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": " world"}}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"messageStop": {"stopReason": "end_turn"}},
        {"metadata": {"usage": {"inputTokens": 11, "outputTokens": 2, "totalTokens": 13}}},
    ])

    text = "".join(
        choice["delta"].get("content", "")
        for chunk in chunks
        for choice in chunk.get("choices", [])
    )
    assert text == "Hello world"
    assert finish_reason_of(chunks) == "stop"
    assert all("usage" not in chunk for chunk in chunks)


def test_tool_use_stream_emits_openai_tool_call_chunks() -> None:
    chunks = collect_chunks([
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"contentBlockIndex": 0, "start": {}}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": "Checking."}}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"contentBlockStart": {
            "contentBlockIndex": 1,
            "start": {"toolUse": {"toolUseId": "tooluse_abc", "name": "read_file"}},
        }},
        {"contentBlockDelta": {"contentBlockIndex": 1, "delta": {"toolUse": {"input": '{"path":'}}}},
        {"contentBlockDelta": {"contentBlockIndex": 1, "delta": {"toolUse": {"input": '"a.txt"}'}}}},
        {"contentBlockStop": {"contentBlockIndex": 1}},
        {"messageStop": {"stopReason": "tool_use"}},
        {"metadata": {"usage": {"inputTokens": 40, "outputTokens": 9, "totalTokens": 49}}},
    ], include_usage=True)

    tool_chunks = [
        call
        for chunk in chunks
        for choice in chunk.get("choices", [])
        for call in choice["delta"].get("tool_calls", [])
    ]

    assert tool_chunks[0]["id"] == "tooluse_abc"
    assert tool_chunks[0]["type"] == "function"
    assert tool_chunks[0]["function"]["name"] == "read_file"
    assert tool_chunks[0]["function"]["arguments"] == ""
    assert all(call["index"] == 0 for call in tool_chunks)
    arguments = "".join(call["function"].get("arguments", "") for call in tool_chunks)
    assert json.loads(arguments) == {"path": "a.txt"}
    assert finish_reason_of(chunks) == "tool_calls"

    usage_chunks = [chunk for chunk in chunks if "usage" in chunk]
    assert len(usage_chunks) == 1
    assert usage_chunks[0]["choices"] == []
    assert usage_chunks[0]["usage"] == {
        "prompt_tokens": 40,
        "completion_tokens": 9,
        "total_tokens": 49,
    }


@pytest.mark.parametrize(
    ("stop_reason", "expected"),
    [
        ("end_turn", "stop"),
        ("stop_sequence", "stop"),
        ("max_tokens", "length"),
        ("tool_use", "tool_calls"),
        ("guardrail_intervened", "content_filter"),
        ("something_new", "stop"),
    ],
)
def test_stop_reason_mapping(stop_reason: str, expected: str) -> None:
    chunks = collect_chunks([
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": "x"}}},
        {"messageStop": {"stopReason": stop_reason}},
    ])

    assert finish_reason_of(chunks) == expected
