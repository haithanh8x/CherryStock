from __future__ import annotations

import json
import os
import secrets
import time
import uuid
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

APP_NAME = "CherryStock Bedrock Proxy"
AWS_PROFILE = os.getenv("AWS_PROFILE", "cherrystock-bedrock")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
DEFAULT_MODEL = os.getenv(
    "BEDROCK_DEFAULT_MODEL",
    "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
)
PROXY_API_KEY = os.getenv("BEDROCK_PROXY_API_KEY", "")

MODEL_ALIASES = {
    "claude-sonnet-4.5": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "claude-opus-4.6": "global.anthropic.claude-opus-4-6-v1",
    "nova-2-lite": "global.amazon.nova-2-lite-v1:0",
}

app = FastAPI(title=APP_NAME, version="0.1.0")


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str = DEFAULT_MODEL
    messages: list[dict[str, Any]]
    temperature: float | None = Field(default=None, ge=0, le=1)
    top_p: float | None = Field(default=None, gt=0, le=1)
    max_tokens: int = Field(default=4096, ge=1, le=32768)
    stream: bool = False
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any = "auto"


def bedrock_client():
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    return session.client("bedrock-runtime", region_name=AWS_REGION)


def authorize(authorization: str | None) -> None:
    if not PROXY_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="BEDROCK_PROXY_API_KEY is not configured. Set a local proxy key before starting.",
        )
    expected = f"Bearer {PROXY_API_KEY}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token.")


def resolve_model(name: str) -> str:
    return MODEL_ALIASES.get(name, name)


def convert_messages(messages: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    system: list[dict] = []
    conversation: list[dict] = []
    for item in messages:
        role = item.get("role")
        content = item.get("content", "")
        if role == "system" or role == "developer":
            text = content if isinstance(content, str) else " ".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
            if text:
                system.append({"text": text})
            continue
        if role == "tool":
            tool_id = item.get("tool_call_id")
            if not tool_id:
                raise HTTPException(400, detail="tool messages require tool_call_id")
            result_text = content if isinstance(content, str) else json.dumps(content)
            block = {"toolResult": {
                "toolUseId": tool_id,
                "content": [{"text": result_text}],
            }}
            if conversation and conversation[-1]["role"] == "user":
                conversation[-1]["content"].append(block)
            else:
                conversation.append({"role": "user", "content": [block]})
            continue
        if role not in ("user", "assistant"):
            raise HTTPException(400, detail=f"Unsupported message role: {role}")
        blocks = []
        if isinstance(content, str):
            if content:
                blocks.append({"text": content})
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    blocks.append({"text": part.get("text", "")})
                elif isinstance(part, dict) and "text" in part:
                    blocks.append({"text": part["text"]})
        if role == "assistant" and item.get("tool_calls"):
            for call in item["tool_calls"]:
                function = call.get("function", {})
                try:
                    arguments = json.loads(function.get("arguments") or "{}")
                except json.JSONDecodeError as exc:
                    raise HTTPException(400, detail="Invalid JSON in tool call arguments") from exc
                blocks.append({"toolUse": {
                    "toolUseId": call.get("id") or f"call_{uuid.uuid4().hex[:12]}",
                    "name": function.get("name"),
                    "input": arguments,
                }})
        if blocks:
            conversation.append({"role": role, "content": blocks})
    if not conversation:
        raise HTTPException(400, detail="At least one user or assistant message is required")
    return system, conversation


def convert_tools(tools: list[dict[str, Any]] | None) -> list[dict] | None:
    if not tools:
        return None
    result = []
    for item in tools:
        if item.get("type") != "function":
            continue
        fn = item.get("function", {})
        name = fn.get("name")
        if not name:
            continue
        result.append({"toolSpec": {
            "name": name,
            "description": fn.get("description", ""),
            "inputSchema": {"json": fn.get("parameters") or {"type": "object"}},
        }})
    return result or None


def make_payload(req: ChatRequest) -> tuple[str, dict]:
    system, messages = convert_messages(req.messages)
    payload: dict[str, Any] = {"modelId": resolve_model(req.model), "messages": messages}
    if system:
        payload["system"] = system
    inference: dict[str, Any] = {"maxTokens": req.max_tokens}
    # Claude Sonnet 4.5 on Bedrock rejects requests that specify both
    # temperature and topP. VS Code Copilot Chat may send both, so prefer
    # temperature when present and only fall back to topP.
    if req.temperature is not None:
        inference["temperature"] = req.temperature
    elif req.top_p is not None:
        inference["topP"] = req.top_p
    payload["inferenceConfig"] = inference
    tools = convert_tools(req.tools)
    if tools and req.tool_choice != "none":
        payload["toolConfig"] = {"tools": tools}
    return resolve_model(req.model), payload


def to_openai_response(result: dict, model: str, started: float) -> dict:
    output = result.get("output", {}).get("message", {})
    text_parts = []
    tool_calls = []
    for index, block in enumerate(output.get("content", [])):
        if "text" in block:
            text_parts.append(block["text"])
        elif "toolUse" in block:
            tool = block["toolUse"]
            tool_calls.append({
                "id": tool["toolUseId"],
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "arguments": json.dumps(tool.get("input", {}), ensure_ascii=False),
                },
            })
    message: dict[str, Any] = {"role": "assistant", "content": "".join(text_parts) or None}
    if tool_calls:
        message["tool_calls"] = tool_calls
    usage = result.get("usage", {})
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": message,
            "finish_reason": "tool_calls" if tool_calls else "stop",
        }],
        "usage": {
            "prompt_tokens": usage.get("inputTokens", 0),
            "completion_tokens": usage.get("outputTokens", 0),
            "total_tokens": usage.get("totalTokens", 0),
        },
        "system_fingerprint": f"bedrock-{int((time.monotonic() - started) * 1000)}ms",
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": APP_NAME, "region": AWS_REGION, "profile": AWS_PROFILE}


@app.get("/v1/models")
def models(authorization: str | None = Header(default=None)):
    authorize(authorization)
    names = list(MODEL_ALIASES) + [DEFAULT_MODEL]
    return {
        "object": "list",
        "data": [{"id": name, "object": "model", "created": 0, "owned_by": "amazon-bedrock"} for name in dict.fromkeys(names)],
    }


@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest, authorization: str | None = Header(default=None)):
    authorize(authorization)
    model, payload = make_payload(req)
    client = bedrock_client()
    started = time.monotonic()
    try:
        if req.stream:
            response = client.converse_stream(**payload)
            return StreamingResponse(stream_response(response, model), media_type="text/event-stream")
        result = client.converse(**payload)
        return JSONResponse(to_openai_response(result, model, started))
    except (ClientError, BotoCoreError, NoCredentialsError) as exc:
        code = "BedrockRequestFailed"
        message = "The Bedrock request failed. Check AWS SSO session, IAM permissions, model access, and region."
        if isinstance(exc, ClientError):
            code = exc.response.get("Error", {}).get("Code", code)
            message = exc.response.get("Error", {}).get("Message", message)
        raise HTTPException(status_code=502, detail={"code": code, "message": message}) from exc


def stream_response(response: dict, model: str):
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    try:
        for event in response.get("stream", []):
            delta = event.get("contentBlockDelta", {}).get("delta", {})
            text = delta.get("text")
            if text:
                chunk = {
                    "id": completion_id, "object": "chat.completion.chunk",
                    "created": created, "model": model,
                    "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            stop = event.get("messageStop", {})
            if stop:
                chunk = {
                    "id": completion_id, "object": "chat.completion.chunk",
                    "created": created, "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"
    except (ClientError, BotoCoreError):
        error = {"error": {"message": "Bedrock streaming request failed", "type": "bedrock_error"}}
        yield f"data: {json.dumps(error)}\n\n"
        yield "data: [DONE]\n\n"
