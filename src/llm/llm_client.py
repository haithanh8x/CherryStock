#!/usr/bin/env python3
"""
LLM client — shared interface to the Bedrock LLM behind the ODE_bedrockInvoke Lambda.

Other scripts import this module and treat it as the LLM "endpoint". The Lambda
runs on the data-app accounts (SIT/PRD) and wraps Bedrock; this module handles
the boto3 session, SSL quirks of the corporate proxy, the request envelope the
Lambda expects, and parsing the Converse-API response back into plain text.

Quick use (one-shot, stateless — the default):
    from llm_client import ask_llm
    text = ask_llm("Summarize this in one line: ...")          # tier="low" (Haiku)

Pick capability by tier (low=default / medium / high):
    ask_llm("Draft a design note", tier="medium")             # Sonnet 5.5
    ask_llm("Reason over this hard case", tier="high")        # Fable 5.1
    # or override entirely with a raw model id:
    ask_llm("...", model="global.anthropic.claude-haiku-4-5-20251001-v1:0")

Backend (how we reach Bedrock):
    - "direct" (DEFAULT): we call bedrock-runtime Converse ourselves. Needed for
      the tier models (Haiku 5.5 / Sonnet 5.5 / Fable 5.1) — the Lambda sends a
      `temperature` field and tiny maxTokens these models reject.
    - "lambda": route via ODE_bedrockInvoke (OCR-app parity; older models only).
    ask_llm("...", backend="lambda", model="global.anthropic.claude-haiku-4-5-20251001-v1:0")

Same helper, conversation mode (remembers earlier calls with the same session):
    from llm_client import ask_llm
    ask_llm("My table is orders(id, amount).", mode="conversation", session_id="sql")
    ask_llm("Write daily revenue query.",      mode="conversation", session_id="sql")

Reusable client (many calls — reuses one boto3 connection):
    from llm_client import LLMClient
    llm = LLMClient(profile="data-app-sit")
    r1 = llm.invoke("First question")      # -> LLMResult
    print(r1.text, r1.usage, r1.latency_s)
    r2 = llm.invoke("Second question", system="You are terse.")

Multi-turn conversation (the model remembers earlier turns):
    from llm_client import LLMClient
    chat = LLMClient().conversation(system="You are a terse SQL helper.")
    chat.ask("My table is orders(id, amount, created_at).")
    print(chat.ask("Write a query for daily revenue."))   # remembers the table
    chat.save_json("logs/chat1.json")                     # persist / resume later

Error handling:
    from llm_client import LLMClient, LLMError
    try:
        text = LLMClient().ask("hello")
    except LLMError as e:
        ...   # e carries a human hint (expired SSO, SSL proxy, access denied, ...)

Note: the Lambda is STATELESS and takes only one user_message, so Conversation
keeps the history client-side and replays it each turn. Cost/latency grow with
length — cap it with conversation(max_history_turns=N).

The Lambda event contract:
    {model_id, user_message, system_message, max_tokens}

Requires: boto3. Log in first:  python3 scripts/aws-login.py --profile data-app-sit
"""

import openssl_conf  # noqa: F401 — MUST be first import, before boto3 (sets OPENSSL_CONF + CA bundle)

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import boto3
from botocore.config import Config

# ----------------------------------------------------------------------------
# Defaults — keep in sync with the OCR app's call to ODE_bedrockInvoke.
# ----------------------------------------------------------------------------
LAMBDA_FUNCTION = "ODE_bedrockInvoke"
DEFAULT_REGION = "ap-southeast-1"
DEFAULT_PROFILE = "data-app-sit"

# Capability tiers — pick by effort/cost instead of memorizing model ids.
#   low    = cheapest / fastest    (default)
#   medium = balanced
#   high   = most capable
# Change a tier's model id here in ONE place.
#
# Verified 2026-10-26 via the "direct" backend (bedrock-runtime Converse):
#   - low  (Haiku 5.5)  : OK
#   - medium (Sonnet 5.5): OK
#   - high (Fable 5.1)  : NOT working yet — Converse rejects with
#       "data retention mode 'default' is not available for this model".
#     Needs a data-retention config we haven't confirmed; don't guess it.
MODEL_TIERS = {
    "low": "global.anthropic.claude-haiku-5-5",      # direct: OK
    "medium": "global.anthropic.claude-sonnet-5-5",  # direct: OK
    "high": "global.anthropic.claude-fable-5-1",     # direct: FAIL (data-retention config TBD)
}
DEFAULT_TIER = "low"
DEFAULT_MODEL = MODEL_TIERS[DEFAULT_TIER]  # global.anthropic.claude-haiku-5-5

# Backend that actually talks to Bedrock:
#   "direct" (DEFAULT) — call bedrock-runtime Converse ourselves. Works with the
#     newer tier models (Haiku 5.5 / Sonnet 5.5 / Fable 5.1) because we control
#     the request: we do NOT send `temperature` and we enforce a minimum
#     maxTokens, both of which the Lambda gets wrong for these models.
#   "lambda" — go through the ODE_bedrockInvoke Lambda (matches the OCR app).
#     Only older models (Haiku 4.5, Sonnet 4.5, Claude 3.x, Nova) work here.
DEFAULT_BACKEND = "direct"

DEFAULT_SYSTEM = "You are a helpful assistant."
DEFAULT_MAX_TOKENS = 8192
# Some newer models reject very small limits ("Invalid max_output_tokens: below
# minimum"); floor the direct Converse request at this value.
MIN_DIRECT_MAX_TOKENS = 16


def resolve_model(model: Optional[str] = None, tier: Optional[str] = None) -> str:
    """Resolve the model id to send to the Lambda.

    Precedence: explicit `model` id > `tier` (low/medium/high) > DEFAULT_MODEL.
    An unknown tier raises ValueError so typos fail loudly rather than silently
    falling back.
    """
    if model:
        return model
    if tier:
        key = tier.lower()
        if key not in MODEL_TIERS:
            raise ValueError(f"Unknown tier {tier!r}. Use one of {list(MODEL_TIERS)}.")
        return MODEL_TIERS[key]
    return DEFAULT_MODEL


class LLMError(RuntimeError):
    """Raised when the LLM call fails (transport, Lambda FunctionError, or no text).

    The message includes a short hint about the likely cause when recognizable
    (expired SSO session, SSL proxy, missing function, access denied).
    """


@dataclass
class LLMResult:
    """Full result of one LLM call."""

    text: str                              # extracted model text ("" if none found)
    latency_s: float                       # round-trip time of the invoke
    status_code: Optional[int] = None      # Lambda HTTP StatusCode (200 expected)
    function_error: Optional[str] = None   # set if the Lambda itself raised
    usage: dict[str, Any] = field(default_factory=dict)  # token usage, if present
    raw: Any = None                        # full parsed Lambda payload

    def __str__(self) -> str:  # so `print(result)` shows the text
        return self.text


# ----------------------------------------------------------------------------
# Response parsing
# ----------------------------------------------------------------------------
def extract_text(payload: Any) -> Optional[str]:
    """Best-effort pull of the model's text from the Lambda response envelope.

    Handles the shapes seen from ODE_bedrockInvoke and common fallbacks:
      - Bedrock Converse:  {"output": {"message": {"content": [{"text": ...}]}}}
      - API-Gateway wrap:  {"statusCode":200, "body": "{...json...}"}
      - Messages API:      {"content": [{"type":"text","text":"..."}], ...}
      - single fields:     {"completion": "..."} / {"output_text": "..."} / ...
    Returns the first non-empty text found, or None.
    """
    # Unwrap a JSON-string (or dict) `body` one level if present.
    if isinstance(payload, dict) and "body" in payload:
        body = payload["body"]
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except (ValueError, TypeError):
                return body or None  # plain-text body
        return extract_text(body) if isinstance(body, (dict, list)) else (str(body) or None)

    if isinstance(payload, dict):
        # Bedrock Converse API
        out = payload.get("output")
        if isinstance(out, dict):
            msg = out.get("message")
            if isinstance(msg, dict):
                nested = extract_text(msg)
                if nested:
                    return nested

        # Anthropic Messages API: content is a list of blocks with .text
        content = payload.get("content")
        if isinstance(content, list):
            parts = [b.get("text", "") for b in content if isinstance(b, dict)]
            joined = "".join(parts).strip()
            if joined:
                return joined
        if isinstance(content, str) and content.strip():
            return content.strip()

        # Common single-field variants
        for key in ("completion", "output_text", "text", "message", "answer", "result"):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
            if isinstance(val, (dict, list)):
                nested = extract_text(val)
                if nested:
                    return nested

    if isinstance(payload, list):
        for item in payload:
            nested = extract_text(item)
            if nested:
                return nested
    return None


def _extract_usage(payload: Any) -> dict[str, Any]:
    """Pull a token-usage dict out of the payload if the Lambda returned one."""
    if isinstance(payload, dict):
        if isinstance(payload.get("usage"), dict):
            return payload["usage"]
        # peek one level into a body wrapper
        body = payload.get("body")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except (ValueError, TypeError):
                body = None
        if isinstance(body, dict) and isinstance(body.get("usage"), dict):
            return body["usage"]
    return {}


def _hint_for(err: Exception, profile: str, region: str, function: str) -> str:
    """Return a human hint appended to LLMError messages for common failures."""
    msg = str(err)
    if "ExpiredToken" in msg or "expired" in msg.lower() or "credential" in msg.lower():
        return f"SSO session likely expired — run: python3 scripts/aws-login.py --profile {profile}"
    if "CERTIFICATE_VERIFY_FAILED" in msg or "self-signed" in msg:
        return "Corporate SSL proxy — construct the client with verify_ssl=False."
    if "ResourceNotFound" in msg or "Function not found" in msg:
        return f"Lambda '{function}' not found in {region} for profile {profile}."
    if "AccessDenied" in msg:
        return "Profile lacks lambda:InvokeFunction on this function."
    return ""


# ----------------------------------------------------------------------------
# Client
# ----------------------------------------------------------------------------
class LLMClient:
    """Reusable LLM endpoint for Bedrock.

    Two backends (see DEFAULT_BACKEND):
      - "direct" (default): calls bedrock-runtime Converse itself — supports the
        newer tier models and avoids the Lambda's temperature/maxTokens issues.
      - "lambda": routes through the ODE_bedrockInvoke Lambda (OCR-app parity).

    One instance builds one boto3 client and reuses it. Thread-safe enough for
    sequential use; create one per thread for concurrent calls.
    """

    def __init__(
        self,
        profile: str = DEFAULT_PROFILE,
        region: str = DEFAULT_REGION,
        function: str = LAMBDA_FUNCTION,
        model: Optional[str] = None,
        tier: str = DEFAULT_TIER,
        backend: str = DEFAULT_BACKEND,
        verify_ssl: bool = False,
        timeout: int = 120,
    ):
        if backend not in ("direct", "lambda"):
            raise ValueError(f"Unknown backend {backend!r}. Use 'direct' or 'lambda'.")
        self.profile = profile
        self.region = region
        self.function = function
        self.backend = backend
        # Default model for this client: explicit model id wins, else the tier.
        self.model = resolve_model(model, tier)
        self.verify_ssl = verify_ssl
        self.timeout = timeout

        if not verify_ssl:
            # Match the app's verify=False and silence the proxy warning spam.
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        cfg = Config(
            read_timeout=timeout,
            connect_timeout=15,
            retries={"max_attempts": 2, "mode": "standard"},
        )
        # When verifying, point boto3 at the corporate CA bundle if present.
        # boto3's verify=True ignores AWS_CA_BUNDLE and uses Python's default
        # trust store, which lacks the internal TCB CA — behind the SSL
        # inspection proxy that fails with "self-signed certificate in chain".
        # Passing the bundle path keeps full verification using the right CA.
        verify_arg: object = verify_ssl
        if verify_ssl:
            import openssl_conf  # noqa: F401 — ensures OPENSSL_CONF/CA are set
            ca_bundle = openssl_conf.CA_BUNDLE_PATH
            if os.path.exists(ca_bundle):
                verify_arg = ca_bundle
        try:
            # Empty profile uses the SDK credential chain (ECS task role on Fargate).
            session = boto3.Session(profile_name=profile or None, region_name=region)
            service = "bedrock-runtime" if backend == "direct" else "lambda"
            self._client = session.client(service, config=cfg, verify=verify_arg)
        except Exception as e:  # noqa: BLE001
            hint = _hint_for(e, profile, region, function)
            raise LLMError(f"Could not create {backend} client: {e}" + (f"\nHint: {hint}" if hint else "")) from e

    # -- core call ---------------------------------------------------------
    def invoke(
        self,
        prompt: str,
        system: str = DEFAULT_SYSTEM,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        model: Optional[str] = None,
        tier: Optional[str] = None,
    ) -> LLMResult:
        """Send one prompt; return a full LLMResult. Raises LLMError on failure.

        Model precedence: explicit `model` > `tier` (low/medium/high) >
        this client's default model. Dispatches to the configured backend.
        """
        model_id = resolve_model(model, tier) if (model or tier) else self.model
        if self.backend == "direct":
            return self._invoke_direct(model_id, prompt, system, max_tokens)
        return self._invoke_lambda(model_id, prompt, system, max_tokens)

    def converse_raw(
        self,
        messages: list,
        system: Optional[str] = None,
        tools: Optional[list] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        model: Optional[str] = None,
        tier: Optional[str] = None,
    ) -> dict:
        """Low-level Converse call for the agent loop (direct backend only).

        Pass a full Bedrock `messages` list and an optional Converse `tools`
        list (each {"toolSpec": {...}}). Returns a dict:
            {message, stop_reason, usage, tool_uses, text, latency_s, raw}
        where tool_uses is a list of {toolUseId, name, input} the model wants
        run. No text extraction/validation — the caller drives the loop.
        """
        if self.backend != "direct":
            raise LLMError("converse_raw requires backend='direct' (tool use is not supported via the Lambda).")
        model_id, req = self._build_converse_req(messages, system, tools, max_tokens, model, tier)

        start = time.time()
        try:
            resp = self._client.converse(**req)
        except Exception as e:  # noqa: BLE001
            hint = _hint_for(e, self.profile, self.region, self.function)
            if "AccessDenied" in str(e):
                hint = "Profile lacks bedrock:InvokeModel on this model/inference-profile."
            raise LLMError(f"converse failed [{model_id}]: {e}" + (f"\nHint: {hint}" if hint else "")) from e
        latency = time.time() - start

        msg = resp.get("output", {}).get("message", {})
        content = msg.get("content", []) or []
        tool_uses = [b["toolUse"] for b in content if isinstance(b, dict) and "toolUse" in b]
        text = "".join(b.get("text", "") for b in content if isinstance(b, dict) and "text" in b)
        return {
            "message": msg,
            "stop_reason": resp.get("stopReason"),
            "usage": resp.get("usage", {}) or {},
            "tool_uses": tool_uses,
            "text": text,
            "latency_s": latency,
            "raw": resp,
        }

    def _build_converse_req(self, messages, system, tools, max_tokens, model, tier):
        """Shared Converse request body for converse_raw / converse_stream_raw."""
        model_id = resolve_model(model, tier) if (model or tier) else self.model
        req = {
            "modelId": model_id,
            "messages": messages,
            "inferenceConfig": {"maxTokens": max(int(max_tokens), MIN_DIRECT_MAX_TOKENS)},
        }
        if system:
            req["system"] = [{"text": system}]
        if tools:
            req["toolConfig"] = {"tools": tools}
        return model_id, req

    def converse_stream_raw(
        self,
        messages: list,
        system: Optional[str] = None,
        tools: Optional[list] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        model: Optional[str] = None,
        tier: Optional[str] = None,
    ):
        """Streaming Converse (direct backend only).

        The API call is made eagerly, so request-level failures (expired SSO,
        access denied, bad model id) raise LLMError here, before the caller has
        sent anything to its own client. Returns an iterator of raw Bedrock
        stream events (messageStart, contentBlockStart/Delta/Stop, messageStop,
        metadata, or an *Exception event). Errors while iterating raise
        LLMError. Call .close() on the iterator to abort and release the
        Bedrock connection early (e.g. when the downstream client disconnects).

        read_timeout applies to the gap between stream chunks, not the whole
        answer, so long outputs no longer hit the timeout as long as tokens flow.
        """
        if self.backend != "direct":
            raise LLMError("converse_stream_raw requires backend='direct'.")
        model_id, req = self._build_converse_req(messages, system, tools, max_tokens, model, tier)
        try:
            resp = self._client.converse_stream(**req)
        except Exception as e:  # noqa: BLE001
            hint = _hint_for(e, self.profile, self.region, self.function)
            if "AccessDenied" in str(e):
                hint = "Profile lacks bedrock:InvokeModel on this model/inference-profile."
            raise LLMError(f"converse_stream failed [{model_id}]: {e}" + (f"\nHint: {hint}" if hint else "")) from e

        stream = resp["stream"]

        def _events():
            try:
                for ev in stream:
                    yield ev
            except GeneratorExit:
                raise
            except Exception as e:  # noqa: BLE001
                raise LLMError(f"stream interrupted [{model_id}]: {e}") from e
            finally:
                try:
                    stream.close()
                except Exception:  # noqa: BLE001
                    pass

        return _events()

    def _invoke_direct(self, model_id, prompt, system, max_tokens) -> LLMResult:
        """Call bedrock-runtime Converse directly.

        Deliberately omits `temperature` (newer models reject it) and floors
        maxTokens at MIN_DIRECT_MAX_TOKENS (they reject tiny limits).
        """
        req = {
            "modelId": model_id,
            "messages": [{"role": "user", "content": [{"text": (prompt or "").strip()}]}],
            "inferenceConfig": {"maxTokens": max(int(max_tokens), MIN_DIRECT_MAX_TOKENS)},
        }
        sys_text = (system or "").strip()
        if sys_text:
            req["system"] = [{"text": sys_text}]

        start = time.time()
        try:
            resp = self._client.converse(**req)
        except Exception as e:  # noqa: BLE001
            hint = _hint_for(e, self.profile, self.region, self.function)
            if "AccessDenied" in str(e):
                hint = "Profile lacks bedrock:InvokeModel on this model/inference-profile."
            raise LLMError(f"direct converse failed [{model_id}]: {e}" + (f"\nHint: {hint}" if hint else "")) from e
        latency = time.time() - start

        text = extract_text(resp) or ""
        return LLMResult(
            text=text,
            latency_s=latency,
            status_code=resp.get("ResponseMetadata", {}).get("HTTPStatusCode"),
            function_error=None,
            usage=resp.get("usage", {}) or {},
            raw=resp,
        )

    def _invoke_lambda(self, model_id, prompt, system, max_tokens) -> LLMResult:
        """Call the ODE_bedrockInvoke Lambda (OCR-app parity)."""
        event = {
            "model_id": model_id,
            "user_message": (prompt or "").strip(),
            "system_message": (system or "").strip(),
            "max_tokens": max_tokens,
        }

        start = time.time()
        try:
            response = self._client.invoke(
                FunctionName=self.function,
                InvocationType="RequestResponse",
                Payload=json.dumps(event),
            )
        except Exception as e:  # noqa: BLE001
            hint = _hint_for(e, self.profile, self.region, self.function)
            raise LLMError(f"invoke failed: {e}" + (f"\nHint: {hint}" if hint else "")) from e
        latency = time.time() - start

        status = response.get("StatusCode")
        func_error = response.get("FunctionError")
        raw_bytes = response["Payload"].read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw_bytes)
        except (ValueError, TypeError):
            parsed = raw_bytes

        if func_error:
            detail = extract_text(parsed) or (parsed if isinstance(parsed, str) else json.dumps(parsed))
            raise LLMError(f"Lambda FunctionError ({func_error}): {detail}")

        text = extract_text(parsed) or ""
        return LLMResult(
            text=text,
            latency_s=latency,
            status_code=status,
            function_error=func_error,
            usage=_extract_usage(parsed),
            raw=parsed,
        )

    # -- convenience -------------------------------------------------------
    def ask(
        self,
        prompt: str,
        system: str = DEFAULT_SYSTEM,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        model: Optional[str] = None,
        tier: Optional[str] = None,
    ) -> str:
        """Send one prompt; return just the model text. Raises LLMError on failure."""
        result = self.invoke(prompt, system=system, max_tokens=max_tokens, model=model, tier=tier)
        if not result.text:
            raise LLMError(
                "Invoke succeeded but no model text was found in the response. "
                f"Raw payload: {json.dumps(result.raw, ensure_ascii=False)[:500]}"
            )
        return result.text

    def conversation(
        self,
        system: str = DEFAULT_SYSTEM,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        max_history_turns: Optional[int] = None,
        model: Optional[str] = None,
        tier: Optional[str] = None,
    ) -> "Conversation":
        """Start a stateful multi-turn conversation bound to this client.

        Pins a model for the whole conversation via `model` or `tier`
        (low/medium/high). If neither is given, uses the client's default.
        """
        return Conversation(
            self,
            system=system,
            max_tokens=max_tokens,
            max_history_turns=max_history_turns,
            model=resolve_model(model, tier) if (model or tier) else None,
        )


# ----------------------------------------------------------------------------
# Multi-turn conversation
# ----------------------------------------------------------------------------
# The ODE_bedrockInvoke Lambda is STATELESS and accepts only a single
# `user_message` (probed: sending a `messages[]` array crashes it with
# KeyError 'user_message'). So to hold a conversation the client must keep the
# history itself and replay it as a flattened transcript inside user_message on
# every turn. The model then "remembers" earlier turns from that transcript.

_ROLE_LABELS = {"user": "User", "assistant": "Assistant"}


@dataclass
class Turn:
    role: str   # "user" | "assistant"
    text: str


class Conversation:
    """A stateful multi-turn chat on top of the stateless LLM endpoint.

    Usage:
        from llm_client import LLMClient
        chat = LLMClient().conversation(system="You are a terse SQL helper.")
        print(chat.ask("My table is orders(id, amount, created_at)."))
        print(chat.ask("Write a query for daily revenue."))   # remembers the table

    How it works: each .ask() appends the user turn, replays the WHOLE history
    as a labelled transcript in the Lambda's single user_message, then appends
    the assistant reply. Because the full history is resent every turn, cost and
    latency grow with length — use max_history_turns to cap it.

    Persistence:
        chat.save_json("logs/chat1.json")
        chat = Conversation.load_json("logs/chat1.json", client)
    """

    def __init__(
        self,
        client: "LLMClient",
        system: str = DEFAULT_SYSTEM,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        max_history_turns: Optional[int] = None,
        model: Optional[str] = None,
    ):
        self.client = client
        self.system = system
        self.max_tokens = max_tokens
        # Keep the most recent N turns (user+assistant each count as 1). None = unbounded.
        self.max_history_turns = max_history_turns
        self.model = model
        self.turns: list[Turn] = []
        self.last_result: Optional[LLMResult] = None

    # -- history management ------------------------------------------------
    def _trim(self) -> None:
        if self.max_history_turns is not None and len(self.turns) > self.max_history_turns:
            self.turns = self.turns[-self.max_history_turns:]

    def _build_user_message(self, pending_user: str) -> str:
        """Flatten history + the pending user turn into one labelled transcript."""
        lines = []
        for t in self.turns:
            label = _ROLE_LABELS.get(t.role, t.role.capitalize())
            lines.append(f"{label}: {t.text}")
        lines.append(f"{_ROLE_LABELS['user']}: {pending_user}")
        # Nudge the model to answer as the assistant for the last user turn.
        lines.append(f"{_ROLE_LABELS['assistant']}:")
        return "\n".join(lines)

    # -- core turn ---------------------------------------------------------
    def ask(self, user_text: str) -> str:
        """Add a user turn, call the model with full history, return its reply."""
        result = self.send(user_text)
        return result.text

    def send(self, user_text: str) -> LLMResult:
        """Like ask() but returns the full LLMResult (text + usage + latency)."""
        user_text = (user_text or "").strip()
        transcript = self._build_user_message(user_text)

        # Carry the running history as system context too, so the labelled
        # transcript is interpreted as prior dialogue, not a single question.
        system = (
            f"{self.system}\n\n"
            "You are continuing a multi-turn conversation. The user_message "
            "contains the transcript so far, with 'User:' and 'Assistant:' "
            "labels. Reply ONLY as the assistant's next turn — do not repeat the "
            "transcript or add a label."
        )

        result = self.client.invoke(
            transcript,
            system=system,
            max_tokens=self.max_tokens,
            model=self.model,
        )

        # Commit both turns only after a successful call.
        self.turns.append(Turn("user", user_text))
        self.turns.append(Turn("assistant", result.text))
        self._trim()
        self.last_result = result
        return result

    # -- utilities ---------------------------------------------------------
    def reset(self) -> None:
        """Forget all turns (keeps system + settings)."""
        self.turns = []
        self.last_result = None

    def history(self) -> list[dict[str, str]]:
        """Return the conversation as a list of {role, text} dicts."""
        return [{"role": t.role, "text": t.text} for t in self.turns]

    def total_usage(self) -> dict[str, int]:
        """Token usage of the LAST turn (the endpoint reports per-call usage)."""
        return dict(self.last_result.usage) if self.last_result else {}

    def save_json(self, path: str) -> None:
        """Persist system + turns to a JSON file."""
        import os

        data = {
            "system": self.system,
            "max_tokens": self.max_tokens,
            "max_history_turns": self.max_history_turns,
            "model": self.model,
            "turns": self.history(),
        }
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load_json(cls, path: str, client: "LLMClient") -> "Conversation":
        """Restore a saved conversation and bind it to a (possibly new) client."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        conv = cls(
            client,
            system=data.get("system", DEFAULT_SYSTEM),
            max_tokens=data.get("max_tokens", DEFAULT_MAX_TOKENS),
            max_history_turns=data.get("max_history_turns"),
            model=data.get("model"),
        )
        conv.turns = [Turn(t["role"], t["text"]) for t in data.get("turns", [])]
        return conv


# ----------------------------------------------------------------------------
# Shared client + conversation-session registries (for the module-level helper)
# ----------------------------------------------------------------------------
# Cache one LLMClient per (profile, region, model, verify_ssl, timeout) so
# repeated ask_llm() calls don't rebuild a boto3 client every time.
_CLIENT_CACHE: dict[tuple, "LLMClient"] = {}
# Named conversation sessions for mode="conversation".
_SESSIONS: dict[str, "Conversation"] = {}


def _get_cached_client(
    profile: str, region: str, model: str, backend: str, verify_ssl: bool, timeout: int
) -> "LLMClient":
    key = (profile, region, model, backend, verify_ssl, timeout)
    client = _CLIENT_CACHE.get(key)
    if client is None:
        client = LLMClient(
            profile=profile, region=region, model=model, backend=backend,
            verify_ssl=verify_ssl, timeout=timeout,
        )
        _CLIENT_CACHE[key] = client
    return client


def get_conversation(session_id: str) -> Optional["Conversation"]:
    """Return the live Conversation for a session_id, or None if not started."""
    return _SESSIONS.get(session_id)


def reset_conversation(session_id: str) -> None:
    """Drop a named conversation session (forgets its history)."""
    _SESSIONS.pop(session_id, None)


def clear_conversations() -> None:
    """Drop ALL in-memory conversation sessions."""
    _SESSIONS.clear()


# ----------------------------------------------------------------------------
# Module-level helper — stateless (default) or conversation mode
# ----------------------------------------------------------------------------
def ask_llm(
    prompt: str,
    system: str = DEFAULT_SYSTEM,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    model: Optional[str] = None,
    tier: str = DEFAULT_TIER,
    backend: str = DEFAULT_BACKEND,
    profile: str = DEFAULT_PROFILE,
    region: str = DEFAULT_REGION,
    verify_ssl: bool = False,
    timeout: int = 120,
    mode: str = "stateless",
    session_id: str = "default",
    max_history_turns: Optional[int] = None,
    persist_path: Optional[str] = None,
) -> str:
    """Ask the LLM and return the model text.

    model selection:
      - tier="low" (DEFAULT) / "medium" / "high" picks the model by capability
        (low=Haiku 5.5, medium=Sonnet 5.5, high=Fable 5.1 — see MODEL_TIERS).
      - pass an explicit `model` id to override the tier entirely.

    backend:
      - "direct" (DEFAULT): call bedrock-runtime Converse directly — required for
        the tier models above.
      - "lambda": route via ODE_bedrockInvoke (older models only).

    mode:
      - "stateless" (DEFAULT): each call is independent — no memory of prior
        calls. Identical to a one-shot LLMClient().ask(). Use for OCR extraction,
        summaries, classification — anything where each prompt stands alone.
      - "conversation": the model remembers earlier calls that share the same
        session_id. History is kept client-side (see Conversation) and replayed
        each turn, so token cost grows with length — cap it with
        max_history_turns. Sessions live in-memory for the process; pass
        persist_path to also save/restore the session as JSON across runs.

    session_id:       only used in conversation mode (default: "default").
    max_history_turns: conversation mode — keep only the most recent N turns.
    persist_path:     conversation mode — JSON file to load on first use and
                      save after each turn (survives process restarts).

    Manage sessions via get_conversation(), reset_conversation(), clear_conversations().
    """
    model_id = resolve_model(model, tier)
    client = _get_cached_client(profile, region, model_id, backend, verify_ssl, timeout)

    if mode == "stateless":
        return client.ask(prompt, system=system, max_tokens=max_tokens)

    if mode == "conversation":
        import os

        chat = _SESSIONS.get(session_id)
        if chat is None:
            # Resume from disk if a persisted session exists, else start fresh.
            if persist_path and os.path.exists(persist_path):
                chat = Conversation.load_json(persist_path, client)
            else:
                chat = client.conversation(
                    system=system, max_tokens=max_tokens, max_history_turns=max_history_turns
                )
            _SESSIONS[session_id] = chat

        text = chat.ask(prompt)
        if persist_path:
            chat.save_json(persist_path)
        return text

    raise ValueError(f"Unknown mode {mode!r}. Use 'stateless' or 'conversation'.")


if __name__ == "__main__":
    # Tiny smoke test when run directly.
    import sys

    q = " ".join(sys.argv[1:]) or "Reply with OK_LLM_PING and nothing else."
    try:
        r = LLMClient().invoke(q)
        print(r.text)
        print(f"\n[latency {r.latency_s:.2f}s | usage {r.usage}]")
    except LLMError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
