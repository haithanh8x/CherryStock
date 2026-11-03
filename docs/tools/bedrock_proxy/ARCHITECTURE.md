# Bedrock Proxy — Architecture and Method Reference

This note describes the implementation in `tools/bedrock_proxy/app.py`. For installation and operating commands, see [README.md](README.md).

## Component map

```text
VS Code agent / OpenAI-compatible client
              |
              | POST /v1/chat/completions
              | Authorization: Bearer <local key>
              v
      FastAPI: tools/bedrock_proxy/app.py
              |
              +-- authorize()
              |
              +-- resolve_model() <--- models.json
              |
              +-- convert_messages()
              +-- convert_tools()
              +-- make_payload()
              |
              +-- stream=true (default) ----> boto3 converse_stream()
              |                                  |
              |                                  v
              |                            stream_response()
              |                                  |
              |                                  v
              |                              SSE chunks
              |
              +-- stream=false --------------> boto3 converse()
                                                 |
                                                 v
                                          to_openai_response()
                                                 |
                                                 v
                                           JSON response

              Boto3 credential chain
                       |
                       v
              AWS_PROFILE / IAM Identity Center
                       |
                       v
                 Amazon Bedrock
```

## 1. Startup and configuration

At process startup, the module:

1. Reads environment variables for AWS profile, region, default model, registry path, and local proxy key.
2. Loads and validates `models.json` into `MODEL_REGISTRY`.
3. Creates the FastAPI application.
4. Waits for Uvicorn to serve requests.

The registry is loaded once at startup. Changes to `models.json` require a proxy restart.

The Bedrock client is created for the configured region using `boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)`. Authentication is delegated to Boto3/AWS CLI; the proxy does not manage SSO tokens.

## 2. Authentication

All endpoints except `GET /health` require:

```http
Authorization: Bearer <BEDROCK_PROXY_API_KEY>
```

The key is required at startup/request time and compared using `secrets.compare_digest`. This is a local shared-secret gate, not a user identity or authorization system.

## 3. Model resolution

A request's `model` value is resolved in this order:

1. Exact alias lookup in `models.json`.
2. If no alias matches and the value contains a dot, it is treated as a complete Bedrock model/inference-profile ID and sent through the Converse adapter.
3. Otherwise the proxy returns HTTP 400 for an unknown alias.

Prefer aliases in `models.json` so provider routing is explicit and maintainable. The direct-ID fallback does not verify that a model ID is valid or supports Converse; AWS will reject unsupported IDs/protocols.

The registry currently accepts only `provider: bedrock_converse`. Adding another provider requires implementing its request/response adapter and dispatch logic in `app.py`, not just adding a JSON entry.

## 4. OpenAI-to-Bedrock request mapping

| OpenAI-compatible input | Bedrock Converse representation |
|---|---|
| `model` | Resolved `modelId` |
| `system` / `developer` message | Top-level `system: [{text: ...}]` |
| `user` / `assistant` text message | `messages[].content[].text` |
| Assistant `tool_calls` | `messages[].content[].toolUse` |
| `tool` result message | `messages[].content[].toolResult` |
| Function tool schema | `toolConfig.tools[].toolSpec` |
| `max_tokens` | `inferenceConfig.maxTokens` |
| `temperature`, `top_p` | Accepted by request schema but intentionally not forwarded |
| `stream` | Chooses ConverseStream or Converse |

The current request schema limits `max_tokens` to 1–32768. If omitted, the proxy uses 4096.

### Why sampling parameters are omitted

Bedrock model families and model versions do not share identical inference-parameter support. A field that is valid for one model can trigger a Bedrock `ValidationException` for another. Copilot clients may also send sampling fields automatically.

To keep the shared Converse adapter compatible across the configured model set, the proxy currently sends only `maxTokens` in `inferenceConfig`. Bedrock therefore uses each model's default sampling behavior. This is a deliberate compatibility trade-off: client-specified temperature/top-p values do not affect generation.

If sampling controls are reintroduced later, implement model-specific capability metadata in the registry and validate it against the exact Bedrock model/API documentation. Do not infer capability from a model name substring.

## 5. Converse versus ConverseStream

### Converse (non-streaming)

- SDK operation: `bedrock-runtime.converse(**payload)`.
- Bedrock returns after generation completes.
- `to_openai_response()` converts the assistant message, tool-use blocks, and usage counts to a single OpenAI-compatible `chat.completion` JSON object.
- Selected only when the request explicitly includes `"stream": false`.

### ConverseStream (streaming)

- SDK operation: `bedrock-runtime.converse_stream(**payload)`.
- Bedrock emits events while generating.
- `stream_response()` reads text deltas from `contentBlockDelta` events and converts them to SSE `chat.completion.chunk` messages.
- A stop event produces a finish chunk; the stream ends with `data: [DONE]`.
- Selected when `"stream": true` or when `stream` is omitted. The Pydantic default is `True`.

Streaming improves time-to-first-token for interactive coding assistants. It does not change the underlying model or guarantee a faster total generation time.

## 6. Response mapping

Non-streaming response includes:

- `id`, `object: chat.completion`, `created`, `model`.
- `choices[0].message.content` for assistant text.
- `choices[0].message.tool_calls` when the final Bedrock response contains tool-use blocks.
- `usage.prompt_tokens`, `completion_tokens`, and `total_tokens` mapped from Bedrock usage.

Streaming response includes:

- `object: chat.completion.chunk`.
- Text in `choices[0].delta.content`.
- `finish_reason: stop` on the final chunk.
- `data: [DONE]` terminator.

## 7. Current scope and known limitations

- Only the `bedrock_converse` provider is implemented.
- Only text message content is converted. Image, audio, video, and other multimodal payloads are not mapped.
- Non-streaming response conversion includes tool-use blocks, but streaming currently forwards text deltas only; streamed tool-use deltas are not converted into OpenAI tool-call chunks.
- The current stream converter emits a generic `stop` finish reason and does not yet map all Bedrock stop reasons or detailed streaming usage metadata.
- The proxy does not implement retries, request cancellation propagation, rate limiting, per-user quotas, or production-grade observability.
- The model registry is static for the lifetime of the process and has no hot reload.
- The proxy does not validate model availability/access in advance; Bedrock validates the model ID, region, permissions, and request fields at invocation time.
- The local API key protects the endpoint but does not replace AWS IAM authorization.

## 8. Extension points

When extending the proxy:

1. Keep the OpenAI-compatible HTTP contract stable for VS Code clients.
2. Add provider-specific adapters behind explicit `provider` values.
3. Keep model capabilities (streaming, tool use, vision, sampling fields, token limits) as explicit registry metadata where needed.
4. Convert both streaming and non-streaming responses for each adapter.
5. Preserve useful AWS error codes/messages while avoiding disclosure of credentials or sensitive request content.
6. Update README and this architecture note whenever request routing, environment variables, supported modalities, or response behavior changes.
