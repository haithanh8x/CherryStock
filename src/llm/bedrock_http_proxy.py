#!/usr/bin/env python3
"""
Local HTTP proxy in front of Bedrock (data-app-sit) for tools that can only talk
HTTP + bearer token — e.g. draw.io Desktop's custom AI config.

Why this exists: draw.io posts to an HTTP URL with an optional `Authorization`
header. Bedrock on data-app-sit is reached with an AWS SSO profile (SigV4), not
a static token. This proxy bridges the two: it listens on localhost, and for
each request it calls Bedrock through the shared `llm_client` layer (same SSO
profile, same SSL/CA handling, same verified tier models), then returns a
Converse-shaped JSON so a single responsePath works.

Run:
    python3 scripts/aws-login.py --profile data-app-sit        # refresh SSO first
    python3 scripts/bedrock_http_proxy.py                      # :8765 by default

Options (env vars):
    DRAWIO_PROXY_HOST    bind host           (default 127.0.0.1 — localhost only)
    DRAWIO_PROXY_PORT    bind port           (default 8765)
    DRAWIO_PROXY_TOKEN   if set, requests must send  Authorization: Bearer <token>
    DRAWIO_PROXY_TOKEN_FILE  optional mounted token file (overrides token env)
    DRAWIO_PROXY_ALLOWED_MODELS  comma-separated model allowlist (optional locally)
    DRAWIO_PROXY_MAX_BODY_BYTES  request limit (default 4194304)
    DRAWIO_PROXY_MAX_OUTPUT_TOKENS  output token limit (default 131072)
    LLM_PROFILE          AWS profile         (default data-app-sit)
    LLM_REGION           AWS region          (default ap-southeast-1)
    LLM_BACKEND          direct | lambda     (default direct)
    LLM_TIER             low | medium | high (default low — used when no model given)

Request body (any of these keys accepted, so it matches both the draw.io
template and the ODE_bedrockInvoke contract):
    model_id / model          -> Bedrock model id (optional; falls back to LLM_TIER)
    user_message / prompt     -> the user text (required)
    system_message / system   -> system prompt (optional)
    max_tokens                -> int (optional, default 8192)

OpenAI chat-completions (`messages[]`, e.g. OpenCode): with "stream": true the
proxy relays Bedrock converse_stream token by token as SSE (chunked transfer),
including incremental tool_call arguments. Without "stream" it returns one
chat.completion JSON. LLM_TIMEOUT (default 300s) is the max gap between chunks
when streaming, and the max total wait when not.

Response body (draw.io / Lambda shape, Converse-shaped):
    {"output": {"message": {"content": [{"text": "..."}]}},
     "usage": {...}, "latency_s": 1.23, "model_id": "..."}
    -> responsePath:  $.output.message.content[0].text

Security notes (financial-grade):
    - Binds to 127.0.0.1 by default — not reachable off-machine. Only widen the
      host if you understand the exposure.
    - The optional bearer token is read from env or a mounted file, never hardcoded.
    - AWS certificate verification is enabled independently of listener TLS.
    - Does not log prompt/response bodies (may contain PII) — only status + timing.
    - Read-only toward AWS: it just invokes the model, nothing destructive.
"""

import openssl_conf  # noqa: F401 — MUST be first (sets OPENSSL_CONF + CA bundle before boto3)

import json
import hmac
import os
import ssl
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import time
import uuid

from llm_client import LLMClient, LLMError, DEFAULT_MAX_TOKENS, MODEL_TIERS

HOST = os.environ.get("DRAWIO_PROXY_HOST", "127.0.0.1")
PORT = int(os.environ.get("DRAWIO_PROXY_PORT", "8765"))
TOKEN = os.environ.get("DRAWIO_PROXY_TOKEN")  # None => no auth required
if os.environ.get("DRAWIO_PROXY_TOKEN_FILE"):
    with open(os.environ["DRAWIO_PROXY_TOKEN_FILE"], encoding="utf-8") as token_file:
        TOKEN = token_file.read().strip()
    if not TOKEN:
        raise ValueError("Proxy token file is empty")
ALLOWED_MODELS = tuple(filter(None, (
    value.strip() for value in os.environ.get("DRAWIO_PROXY_ALLOWED_MODELS", "").split(",")
)))
# Models verified working on data-app-sit (2026-11-07, direct Converse). Used as
# the default allowlist so a known-good model id is never rejected, while an
# unknown id (e.g. one typed by hand) still gets a fast 403 instead of being
# forwarded to Bedrock where it would hang until read_timeout and break the
# client socket. Override the whole set with DRAWIO_PROXY_ALLOWED_MODELS.
VERIFIED_MODELS = (
    "global.openai.gpt-6-astra",
    "global.anthropic.claude-opus-5-5",
    "global.openai.gpt-6.1-sol",
    "global.anthropic.claude-sonnet-5-5",
    "global.openai.gpt-6-sol",
    "global.openai.gpt-6.1-terra",
    "global.anthropic.claude-haiku-5-5",
    "global.openai.gpt-6-luna",
)
# Keep the tier models in the set too, then dedupe while preserving order.
EFFECTIVE_ALLOWED_MODELS = ALLOWED_MODELS or tuple(
    dict.fromkeys(VERIFIED_MODELS + tuple(MODEL_TIERS.values()))
)
MAX_BODY_BYTES = int(os.environ.get("DRAWIO_PROXY_MAX_BODY_BYTES", "4194304"))
MAX_OUTPUT_TOKENS = int(os.environ.get("DRAWIO_PROXY_MAX_OUTPUT_TOKENS", "131072"))
PROFILE = os.environ.get("LLM_PROFILE", "data-app-sit")
REGION = os.environ.get("LLM_REGION", "ap-southeast-1")
BACKEND = os.environ.get("LLM_BACKEND", "direct")
TIER = os.environ.get("LLM_TIER", "low")
# Bedrock read timeout per call. Default 300s: a GPT/tool-calling turn with a
# large context and long output can take well over the old 120s (a 2.8k-token
# answer alone measured ~64s), which was causing ReadTimeoutError mid-chat.
# Keep this >= the client's (OpenCode's) own request timeout so the proxy
# surfaces a clean error rather than the client cutting the socket first.
TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "300"))

# TLS: draw.io Desktop (Electron) refuses plain http:// localhost calls — the
# request is cancelled before leaving the app ("Error: 0", nothing reaches us).
# Serving HTTPS fixes it. Default ON; set DRAWIO_PROXY_TLS=0 to force plain HTTP.
USE_TLS = os.environ.get("DRAWIO_PROXY_TLS", "1") != "0"
_CERT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".proxy_certs")
CERT_FILE = os.path.join(_CERT_DIR, "proxy-cert.pem")
KEY_FILE = os.path.join(_CERT_DIR, "proxy-key.pem")


def ensure_self_signed_cert() -> tuple[str, str]:
    """Create a self-signed cert for localhost/127.0.0.1 once, return (cert, key).

    Uses the system openssl. SAN covers 127.0.0.1 + localhost so the cert matches
    whatever host draw.io connects to. Regenerated only if missing.
    """
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        return CERT_FILE, KEY_FILE
    os.makedirs(_CERT_DIR, exist_ok=True)
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", KEY_FILE, "-out", CERT_FILE, "-days", "3650",
            "-subj", "/CN=localhost",
            "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
        ],
        check=True,
        capture_output=True,
    )
    print(f"generated self-signed cert at {CERT_FILE}")
    return CERT_FILE, KEY_FILE

# One shared client, reused across requests. botocore clients are thread-safe
# for operation calls, so ThreadingHTTPServer can call it concurrently.
_client = LLMClient(
    profile=PROFILE, region=REGION, backend=BACKEND, tier=TIER,
    verify_ssl=True, timeout=TIMEOUT,
)
if _client.model not in EFFECTIVE_ALLOWED_MODELS:
    raise ValueError("Default model is not in the proxy allowlist")
# No per-request lock: botocore clients are safe for concurrent operation calls
# from multiple threads, and LLMClient keeps no mutable per-call state. A shared
# lock here would serialize every request — so two open chats would queue behind
# each other, and a slow Bedrock turn on the first could push the second past
# read_timeout (120s) and break its socket. ThreadingHTTPServer handles each
# request on its own thread; they call Bedrock in parallel.


def _pick(body: dict, *keys, default=None):
    """Return the first present, non-empty value among keys."""
    for k in keys:
        v = body.get(k)
        if v not in (None, ""):
            return v
    return default


def _content_to_text(content) -> str:
    """OpenAI message content can be a string or a list of parts; flatten to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict):
                parts.append(p.get("text") or p.get("content") or "")
            elif isinstance(p, str):
                parts.append(p)
        return "\n".join(x for x in parts if x)
    return "" if content is None else str(content)


def _messages_to_prompt(messages: list) -> tuple[str, str]:
    """Flatten an OpenAI messages[] array into (prompt, system).

    System turns are concatenated into the system prompt. User/assistant turns
    are replayed as a labelled transcript so the single-prompt backend keeps
    multi-turn context (same approach as llm_client.Conversation).
    """
    system_parts, lines = [], []
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = (m.get("role") or "user").lower()
        text = _content_to_text(m.get("content"))
        if not text:
            continue
        if role == "system":
            system_parts.append(text)
        elif role == "assistant":
            lines.append(f"Assistant: {text}")
        else:
            lines.append(f"User: {text}")
    # If it's just one user turn, send it raw (no transcript labelling noise).
    if len(lines) == 1 and lines[0].startswith("User: "):
        prompt = lines[0][len("User: "):]
    else:
        prompt = "\n".join(lines)
    system = "\n\n".join(system_parts)
    return prompt, system


# ---------------------------------------------------------------------------
# OpenAI chat-completions <-> Bedrock Converse (with tool calling)
# ---------------------------------------------------------------------------

def _oai_tools_to_converse(tools) -> list:
    """OpenAI tools[] -> Converse toolConfig.tools[] ({"toolSpec": ...})."""
    out = []
    for t in tools or []:
        fn = (t or {}).get("function") if isinstance(t, dict) else None
        if not fn or not fn.get("name"):
            continue
        schema = fn.get("parameters") or {"type": "object", "properties": {}}
        out.append({"toolSpec": {
            "name": fn["name"],
            "description": (fn.get("description") or fn["name"])[:10000],
            "inputSchema": {"json": schema},
        }})
    return out


def _parse_args(raw):
    """Tool-call arguments arrive as a JSON string; Converse needs an object."""
    if isinstance(raw, dict):
        return raw
    try:
        v = json.loads(raw or "{}")
        return v if isinstance(v, dict) else {"value": v}
    except (ValueError, TypeError):
        return {"raw": str(raw)}


def _oai_messages_to_converse(messages) -> tuple[list, str]:
    """OpenAI messages[] -> (Converse messages[], system text).

    Converse rules handled here: roles alternate user/assistant, first turn is
    user, tool results are user-side toolResult blocks, empty text is dropped.
    """
    system_parts, conv = [], []

    def push(role, blocks):
        blocks = [b for b in blocks if b]
        if not blocks:
            return
        if conv and conv[-1]["role"] == role:
            conv[-1]["content"].extend(blocks)  # merge consecutive same-role turns
        else:
            conv.append({"role": role, "content": blocks})

    for m in messages or []:
        if not isinstance(m, dict):
            continue
        role = (m.get("role") or "user").lower()
        text = _content_to_text(m.get("content"))
        if role in ("system", "developer"):
            if text:
                system_parts.append(text)
        elif role == "assistant":
            blocks = [{"text": text}] if text.strip() else []
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function") or {}
                blocks.append({"toolUse": {
                    "toolUseId": tc.get("id") or f"call_{uuid.uuid4().hex[:12]}",
                    "name": fn.get("name") or "unknown",
                    "input": _parse_args(fn.get("arguments")),
                }})
            push("assistant", blocks)
        elif role == "tool":
            push("user", [{"toolResult": {
                "toolUseId": m.get("tool_call_id") or "unknown",
                "content": [{"text": text or "(empty)"}],
            }}])
        else:
            push("user", [{"text": text}] if text.strip() else [])

    if conv and conv[0]["role"] != "user":
        conv.insert(0, {"role": "user", "content": [{"text": "(continue)"}]})
    return conv, "\n\n".join(system_parts)


def _converse_to_oai_message(out: dict) -> tuple[dict, str]:
    """converse_raw() result -> (OpenAI assistant message, finish_reason)."""
    msg = {"role": "assistant", "content": out.get("text") or None}
    calls = [{
        "id": tu.get("toolUseId"),
        "type": "function",
        "function": {"name": tu.get("name"),
                     "arguments": json.dumps(tu.get("input") or {}, ensure_ascii=False)},
    } for tu in out.get("tool_uses") or []]
    if calls:
        msg["tool_calls"] = calls
        return msg, "tool_calls"
    stop = out.get("stop_reason")
    return msg, ("length" if stop == "max_tokens" else "stop")


class Handler(BaseHTTPRequestHandler):
    server_version = "BedrockHTTPProxy/1.0"
    # HTTP/1.1 so Electron's fetch gets a clean, length-delimited response.
    # Default HTTP/1.0 closes the socket in a way Electron reports as
    # ERR_CONNECTION_RESET even when the body was sent.
    protocol_version = "HTTP/1.1"

    # Quiet the default per-request stderr logging (avoid leaking paths/timing noise).
    def log_message(self, fmt, *args):  # noqa: A003
        pass

    def handle_one_request(self):
        # Wrap the whole request so a client that disconnects mid-flight (e.g. it
        # timed out waiting for a long Bedrock turn) raises BrokenPipeError /
        # ConnectionResetError here instead of dumping a traceback to stderr and
        # killing the worker thread. One slow/abandoned chat must not take the
        # proxy down for the others.
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            self.close_connection = True
            print(f"[{self.address_string()}] client disconnected (socket closed)")

    def _cors_headers(self):
        # draw.io Desktop (Electron) issues cross-origin requests; without these
        # the browser engine blocks the POST at the preflight stage and the chat
        # shows "Error: 0" (the request never reaches us).
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")
        # Chrome Private Network Access: a page on a public origin (app.diagrams.net)
        # calling into localhost triggers a PNA preflight that requires this header,
        # otherwise the request is blocked before reaching us.
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def _send_json(self, status: int, obj: dict):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        note = obj.get("error", "ok") if isinstance(obj, dict) else ""
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(data)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            # Client gave up waiting (e.g. a long Bedrock turn exceeded its
            # client-side timeout) and closed the socket before we could reply.
            # Nothing to send to — log it and move on without crashing the thread.
            print(f"[{self.address_string()}] -> {status} {note} (client disconnected)")
            return
        # status + error key only — never the prompt/response text (PII-safe).
        print(f"[{self.address_string()}] -> {status} {note}")

    def do_OPTIONS(self):
        # CORS preflight — answer 204 with the allow headers, no body.
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self._cors_headers()
        self.end_headers()
        self.wfile.flush()
        print(f"[{self.address_string()}] OPTIONS {self.path} -> 204 (preflight)")

    def _unauthorized(self, reason: str):
        self._send_json(401, {"error": "unauthorized", "detail": reason})

    def do_GET(self):
        # Simple health check — no auth, no model call.
        if self.path.rstrip("/") in ("", "/health", "/healthz"):
            self._send_json(200, {"status": "ok", "profile": PROFILE,
                                   "region": REGION, "backend": BACKEND, "tier": TIER})
            return
        # OpenAI-compatible model listing so chat clients (e.g. VSCode custom
        # endpoint with apiType=chatCompletions) can populate their model picker.
        if self.path.rstrip("/") in ("/v1/models", "/models"):
            now = int(time.time())
            data = [
                {"id": mid, "object": "model", "created": now, "owned_by": "bedrock"}
                for mid in EFFECTIVE_ALLOWED_MODELS
            ]
            self._send_json(200, {"object": "list", "data": data})
            return
        self._send_json(404, {"error": "not_found"})

    def _handle_openai_native(self, body: dict):
        """OpenAI chat-completions with real tool calling, via Converse."""
        messages, sys_text = _oai_messages_to_converse(body.get("messages"))
        if not messages:
            self._send_json(400, {"error": "missing_prompt",
                                  "detail": "messages[] has no usable content"})
            return
        tools = _oai_tools_to_converse(body.get("tools"))
        model = _pick(body, "model_id", "model")
        # Reject unknown models here too (not just the draw.io path), so a bad
        # id fails fast with 403 rather than hanging on Bedrock until timeout.
        if model and model not in EFFECTIVE_ALLOWED_MODELS:
            self._send_json(403, {"error": "model_not_allowed", "detail": model,
                                  "allowed": list(EFFECTIVE_ALLOWED_MODELS)})
            return
        try:
            max_tokens = int(_pick(body, "max_tokens", "max_completion_tokens",
                                   default=DEFAULT_MAX_TOKENS))
        except (ValueError, TypeError):
            max_tokens = DEFAULT_MAX_TOKENS

        if body.get("stream"):
            # Real token streaming via Bedrock converse_stream.
            self._stream_openai(messages, sys_text, tools, max_tokens, model)
            return

        try:
            out = _client.converse_raw(messages, system=sys_text or None,
                                       tools=tools or None,
                                       max_tokens=max_tokens, model=model)
        except LLMError as e:
            self._send_json(502, {"error": "llm_error", "detail": str(e)})
            return
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": "internal", "detail": str(e)})
            return

        msg, finish = _converse_to_oai_message(out)
        u = out.get("usage") or {}
        usage = {"prompt_tokens": u.get("inputTokens", 0),
                 "completion_tokens": u.get("outputTokens", 0),
                 "total_tokens": u.get("totalTokens", 0)}
        cid = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        created = int(time.time())
        model_id = model or _client.model

        self._send_json(200, {
            "id": cid, "object": "chat.completion", "created": created,
            "model": model_id,
            "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
            "usage": usage,
        })

    def _write_chunk(self, data: bytes):
        """Write one HTTP/1.1 chunked-transfer frame and flush it to the client.

        An empty `data` writes the terminating zero-length chunk.
        """
        self.wfile.write(f"{len(data):X}\r\n".encode("ascii") + data + b"\r\n")
        self.wfile.flush()

    def _stream_openai(self, messages, sys_text, tools, max_tokens, model):
        """Relay Bedrock converse_stream to the client as OpenAI SSE, token by token.

        Mapping (Converse event -> OpenAI chat.completion.chunk delta):
          contentBlockDelta.text          -> {"content": text}
          contentBlockStart.toolUse       -> {"tool_calls":[{index,id,type,function:{name,arguments:""}}]}
          contentBlockDelta.toolUse.input -> {"tool_calls":[{index,function:{arguments:<partial json>}}]}
          messageStop.stopReason          -> finish_reason (tool_use->tool_calls, max_tokens->length)
          metadata.usage                  -> usage on the final chunk
        """
        model_id = model or _client.model
        # Eager call: SSO/access/model errors surface as a normal 502 JSON
        # before any streaming headers are sent.
        try:
            events = _client.converse_stream_raw(messages, system=sys_text or None,
                                                 tools=tools or None,
                                                 max_tokens=max_tokens, model=model)
        except LLMError as e:
            self._send_json(502, {"error": "llm_error", "detail": str(e)})
            return
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": "internal", "detail": str(e)})
            return

        cid = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        created = int(time.time())

        def emit(delta, fin=None, use=None):
            o = {"id": cid, "object": "chat.completion.chunk", "created": created,
                 "model": model_id,
                 "choices": [{"index": 0, "delta": delta, "finish_reason": fin}]}
            if use is not None:
                o["usage"] = use
            self._write_chunk(f"data: {json.dumps(o, ensure_ascii=False)}\n\n".encode("utf-8"))

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Connection", "close")
        self._cors_headers()
        self.end_headers()

        tool_index = {}   # Converse contentBlockIndex -> OpenAI tool_calls index
        finish, usage, error = "stop", None, None
        stream_errors = ("internalServerException", "modelStreamErrorException",
                         "throttlingException", "validationException",
                         "serviceUnavailableException")
        try:
            emit({"role": "assistant", "content": ""})
            for ev in events:
                if "contentBlockDelta" in ev:
                    d = ev["contentBlockDelta"]
                    delta = d.get("delta") or {}
                    if delta.get("text"):
                        emit({"content": delta["text"]})
                    elif "toolUse" in delta:
                        i = tool_index.get(d.get("contentBlockIndex"))
                        if i is not None:
                            emit({"tool_calls": [{"index": i, "function": {
                                "arguments": delta["toolUse"].get("input", "")}}]})
                    elif (delta.get("reasoningContent") or {}).get("text"):
                        # Model "thinking" text, as the reasoning_content field that
                        # OpenAI-compatible clients (OpenCode / ai-sdk) display
                        # separately. Signatures are not forwarded.
                        emit({"reasoning_content": delta["reasoningContent"]["text"]})
                elif "contentBlockStart" in ev:
                    s = ev["contentBlockStart"]
                    tu = (s.get("start") or {}).get("toolUse")
                    if tu:
                        i = len(tool_index)
                        tool_index[s.get("contentBlockIndex")] = i
                        emit({"tool_calls": [{"index": i, "id": tu.get("toolUseId"),
                                              "type": "function",
                                              "function": {"name": tu.get("name"),
                                                           "arguments": ""}}]})
                elif "messageStop" in ev:
                    stop = ev["messageStop"].get("stopReason")
                    finish = ("tool_calls" if stop == "tool_use"
                              else "length" if stop == "max_tokens" else "stop")
                elif "metadata" in ev:
                    u = ev["metadata"].get("usage") or {}
                    usage = {"prompt_tokens": u.get("inputTokens", 0),
                             "completion_tokens": u.get("outputTokens", 0),
                             "total_tokens": u.get("totalTokens", 0)}
                else:
                    for k in stream_errors:
                        if k in ev:
                            raise LLMError(f"{k}: {(ev[k] or {}).get('message', '')}")
            emit({}, finish, usage)
        except (BrokenPipeError, ConnectionResetError):
            # Client went away mid-stream. `finally` closes the Bedrock stream so
            # we stop generating (and paying for) tokens nobody reads.
            raise  # handled quietly in handle_one_request
        except Exception as e:  # noqa: BLE001
            # Headers are already sent, so report the failure in-band.
            error = str(e)[:500]
            self._write_chunk(("data: " + json.dumps(
                {"error": {"message": error, "type": "llm_error"}},
                ensure_ascii=False) + "\n\n").encode("utf-8"))
        finally:
            events.close()

        self._write_chunk(b"data: [DONE]\n\n")
        self._write_chunk(b"")  # end of chunked body
        # status + counts only, never prompt/response text (PII-safe)
        print(f"[{self.address_string()}] -> 200 {'stream_error' if error else 'ok'} "
              f"(stream, finish={finish}, tools_in={len(tools)}, tool_calls={len(tool_index)})")

    def do_POST(self):
        print(f"[{self.address_string()}] POST {self.path}")
        # Optional bearer-token gate.
        if TOKEN:
            auth = self.headers.get("Authorization", "")
            if not hmac.compare_digest(auth.encode("utf-8"), f"Bearer {TOKEN}".encode("utf-8")):
                self._unauthorized("missing or invalid bearer token")
                return

        if self.headers.get("Transfer-Encoding"):
            self._send_json(400, {"error": "unsupported_transfer_encoding"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "invalid_content_length"})
            return
        if length < 0 or length > MAX_BODY_BYTES:
            self._send_json(413, {"error": "request_too_large"})
            return
        raw = self.rfile.read(length) if length else b""

        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except (ValueError, UnicodeDecodeError) as e:
            self._send_json(400, {"error": "bad_json", "detail": str(e)})
            return

        if not isinstance(body, dict):
            self._send_json(400, {"error": "body_must_be_object"})
            return
        model = _pick(body, "model_id", "model", default=_client.model)
        if model not in EFFECTIVE_ALLOWED_MODELS:
            self._send_json(403, {"error": "model_not_allowed", "detail": model,
                                  "allowed": list(EFFECTIVE_ALLOWED_MODELS)})
            return
        try:
            requested_tokens = int(_pick(body, "max_tokens", "max_completion_tokens",
                                         default=DEFAULT_MAX_TOKENS))
        except (ValueError, TypeError):
            self._send_json(400, {"error": "invalid_max_tokens"})
            return
        if not 1 <= requested_tokens <= MAX_OUTPUT_TOKENS:
            self._send_json(400, {"error": "max_tokens_out_of_range"})
            return

        # Two request shapes supported:
        #   - OpenAI chat completions: {"messages":[...], "model": ...}  -> OpenAI response
        #   - draw.io / Lambda contract: {"user_message"|"prompt": ...}  -> Converse response
        openai_mode = isinstance(body.get("messages"), list) and bool(body.get("messages"))

        if openai_mode:
            # Native path: real Converse messages + tool calling, so agents like
            # OpenCode can actually run tools (bash, read, edit...).
            self._handle_openai_native(body)
            return

        if openai_mode:  # legacy flattened path (kept for reference, unreachable)
            prompt, sys_from_msgs = _messages_to_prompt(body["messages"])
            if not prompt:
                self._send_json(400, {"error": "missing_prompt",
                                      "detail": "messages[] has no usable content"})
                return
            system = _pick(body, "system_message", "system",
                           default=sys_from_msgs or "You are a helpful assistant.")
        else:
            prompt = _pick(body, "user_message", "prompt")
            if not prompt:
                self._send_json(400, {"error": "missing_prompt",
                                      "detail": "provide 'user_message', 'prompt', or 'messages'"})
                return
            system = _pick(body, "system_message", "system", default="You are a helpful assistant.")

        model = _pick(body, "model_id", "model")  # None => client's tier default
        try:
            max_tokens = int(_pick(body, "max_tokens", default=DEFAULT_MAX_TOKENS))
        except (ValueError, TypeError):
            max_tokens = DEFAULT_MAX_TOKENS

        try:
            result = _client.invoke(prompt, system=system,
                                    max_tokens=max_tokens, model=model)
        except LLMError as e:
            # Surface the hint (expired SSO, SSL, access denied) without echoing the prompt.
            self._send_json(502, {"error": "llm_error", "detail": str(e)})
            return
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": "internal", "detail": str(e)})
            return

        model_id = model or _client.model
        if openai_mode and body.get("stream"):
            # Clients like OpenCode always stream. Backend isn't streaming, so emit
            # the full answer as one SSE delta chunk, then a stop chunk and [DONE].
            cid = f"chatcmpl-{uuid.uuid4().hex[:24]}"
            created = int(time.time())

            def _chunk(delta, finish=None, usage=None):
                obj = {"id": cid, "object": "chat.completion.chunk", "created": created,
                       "model": model_id,
                       "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
                if usage is not None:
                    obj["usage"] = usage
                return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

            u = result.usage or {}
            payload = (
                _chunk({"role": "assistant", "content": result.text})
                + _chunk({}, "stop", {
                    "prompt_tokens": u.get("inputTokens", 0),
                    "completion_tokens": u.get("outputTokens", 0),
                    "total_tokens": u.get("totalTokens", 0)})
                + "data: [DONE]\n\n"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(payload)
            self.wfile.flush()
            print(f"[{self.address_string()}] -> 200 ok (sse)")
            return

        if openai_mode:
            # OpenAI chat-completions response shape -> $.choices[0].message.content
            u = result.usage or {}
            self._send_json(200, {
                "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_id,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": result.text},
                    "finish_reason": "stop",
                }],
                "usage": {
                    "prompt_tokens": u.get("inputTokens", 0),
                    "completion_tokens": u.get("outputTokens", 0),
                    "total_tokens": u.get("totalTokens", 0),
                },
            })
            return

        # draw.io / Lambda Converse shape -> $.output.message.content[0].text
        self._send_json(200, {
            "output": {"message": {"content": [{"text": result.text}]}},
            "usage": result.usage or {},
            "latency_s": round(result.latency_s, 3),
            "model_id": model_id,
        })


def main():
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    scheme = "http"
    if USE_TLS:
        cert, key = ensure_self_signed_cert()
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=cert, keyfile=key)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        scheme = "https"

    auth = "bearer-token required" if TOKEN else "no auth"
    print(f"Bedrock proxy listening on {scheme}://{HOST}:{PORT}  "
          f"(profile={PROFILE}, region={REGION}, backend={BACKEND}, tier={TIER}, "
          f"timeout={TIMEOUT}s, {auth})")
    print(f"  health:  curl -k {scheme}://{HOST}:{PORT}/health")
    if USE_TLS:
        print("  note:    self-signed cert — draw.io must accept it (see below if it refuses)")
    print("  stop:    Ctrl-C")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down.")
        httpd.shutdown()


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        print(f"[ERROR] could not bind {HOST}:{PORT}: {e}", file=sys.stderr)
        sys.exit(1)
