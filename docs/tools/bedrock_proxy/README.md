# CherryStock Bedrock Proxy

Local OpenAI-compatible gateway for VS Code agents. It accepts chat-completion requests at `/v1/chat/completions`, authenticates them with a local bearer key, and forwards supported requests to Amazon Bedrock using Boto3 and the configured AWS profile.

> Current implementation: the `bedrock_converse` adapter only. A model must support the Bedrock Converse API and be accessible to the configured AWS account/region. A Bedrock model ID by itself does not imply that its API protocol is supported.

## 1. Requirements

- Windows + PowerShell (commands below are for Windows).
- Python 3.13 or later.
- AWS CLI v2.
- An AWS IAM Identity Center profile named `cherrystock-bedrock` (or set `AWS_PROFILE` to another profile).
- Bedrock model access and IAM permissions for the selected model/inference profile, including the Converse/ConverseStream actions.

The proxy uses the normal Boto3 credential provider chain through the AWS profile. It does not read SSO cache files or store AWS credentials.

## 2. Install and start

Run from the CherryStock repository root (`C:\\Github\\CherryStock` in the example):

```powershell
cd C:\\Github\\CherryStock

# Install the optional proxy dependencies into the active Python environment
python -m pip install -e ".[bedrock-proxy]"

# AWS configuration
$env:AWS_PROFILE = "cherrystock-bedrock"
$env:AWS_REGION = "ap-southeast-1"
$env:BEDROCK_DEFAULT_MODEL = "claude-sonnet-4.5"

# Generate a random local API key (PowerShell-compatible)
$bytes = New-Object byte[] 32
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$env:BEDROCK_PROXY_API_KEY = [Convert]::ToBase64String($bytes)
$rng.Dispose()

# Start the API on loopback only
python -m uvicorn tools.bedrock_proxy.app:app --host 127.0.0.1 --port 8787
```

Keep this terminal open while using the proxy. The generated key belongs to this PowerShell process; if you open a new terminal or restart the process, generate/set the key again and update the VS Code provider configuration to match.

If the AWS SSO session has expired, authenticate in another PowerShell window:

```powershell
aws sso login --profile cherrystock-bedrock
```

Then restart the proxy if the running process has stale credentials.

### Optional environment variables

| Variable | Default | Purpose |
|---|---|---|
| `AWS_PROFILE` | `cherrystock-bedrock` | AWS CLI/Boto3 profile |
| `AWS_REGION` | `ap-southeast-1` | Bedrock Runtime region |
| `BEDROCK_DEFAULT_MODEL` | `claude-sonnet-4.5` | Model used when request omits `model` |
| `BEDROCK_MODEL_REGISTRY` | `tools/bedrock_proxy/models.json` | Optional path to model registry |
| `BEDROCK_PROXY_API_KEY` | empty | Required local bearer token |

The server intentionally refuses authenticated endpoints if `BEDROCK_PROXY_API_KEY` is empty.

## 3. Configure VS Code

Configure the OpenAI-compatible provider in the agent/extension:

| Setting | Value |
|---|---|
| Base URL | `http://127.0.0.1:8787/v1` |
| Chat completions URL (if the client asks for the full URL) | `http://127.0.0.1:8787/v1/chat/completions` |
| API key | The value of `BEDROCK_PROXY_API_KEY` |
| Model | An alias from `models.json`, e.g. `claude-sonnet-4.5` |

Do not commit the API key to `.vscode/settings.json`, source control, or shared configuration. Exact setting names vary by VS Code extension.

## 4. Verify the local service

Open a second PowerShell window. Set the same key in that window (or copy it securely from the process that launched the proxy):

```powershell
$headers = @{ Authorization = "Bearer <YOUR_PROXY_API_KEY>" }

# Liveness (does not require a key)
Invoke-RestMethod http://127.0.0.1:8787/health

# Registered model aliases (requires bearer key)
Invoke-RestMethod http://127.0.0.1:8787/v1/models -Headers $headers
```

For a one-shot, non-streaming diagnostic request, explicitly set `stream = $false`:

```powershell
$body = @{
  model = "claude-sonnet-4.5"
  messages = @(@{ role = "user"; content = "Reply with exactly: CherryStock proxy OK" })
  max_tokens = 128
  stream = $false
} | ConvertTo-Json -Depth 10

Invoke-RestMethod http://127.0.0.1:8787/v1/chat/completions -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

For streaming, set `"stream": true`. The default is `false` (a single JSON response, matching the OpenAI API), so the response is Server-Sent Events (SSE) only when requested. Use an SSE-capable client such as `curl.exe -N` to observe chunks.

## 5. HTTP API

| Method | Path | Authentication | Description |
|---|---|---|---|
| GET | `/health` | None | Liveness and configured AWS profile/region |
| GET | `/v1/models` | Bearer | Lists aliases loaded from `models.json` plus the default model |
| POST | `/v1/chat/completions` | Bearer | OpenAI-compatible chat completion endpoint |

Example streaming request:

```powershell
$headers = @{
  Authorization = "Bearer $env:BEDROCK_PROXY_API_KEY"
  "Content-Type" = "application/json"
}
$body = @{
  model = "claude-sonnet-4.5"
  messages = @(@{ role = "user"; content = "Explain what ConverseStream does." })
  max_tokens = 512
  stream = $true
} | ConvertTo-Json -Depth 10

$body | curl.exe -N http://127.0.0.1:8787/v1/chat/completions -H "Authorization: Bearer $env:BEDROCK_PROXY_API_KEY" -H "Content-Type: application/json" --data-binary "@-"
```

## 6. Request processing and Bedrock methods

The endpoint chooses the Bedrock operation from the OpenAI request's `stream` flag:

| Incoming request | Bedrock operation | Proxy response |
|---|---|---|
| `stream` omitted (default) or `false` | `Converse` | One JSON OpenAI chat-completion response |
| `stream: true` | `ConverseStream` | SSE chunks in OpenAI chat-completion-chunk format, followed by `data: [DONE]` |

Streaming must be requested explicitly, matching the OpenAI API default. Clients such as draw.io's AI dialog, which send no `stream` field and expect one JSON response, rely on this.

### Converse

`Converse` waits for the model to finish and returns one response object. The proxy converts the returned assistant text, tool-use blocks, and usage counters into an OpenAI-compatible JSON response. Use it for clients that do not support SSE or for simple diagnostics.

### ConverseStream

`ConverseStream` returns an event stream while the model is generating. The proxy reads Bedrock stream events, forwards text deltas as SSE chunks, converts `toolUse` blocks into OpenAI `delta.tool_calls` chunks, sends a finish chunk, and terminates with `[DONE]`. This is the default because interactive coding assistants benefit from incremental output.

Streaming behavior details:

- `contentBlockStart` with a `toolUse` payload emits the first tool-call chunk (`id`, `type: "function"`, `name`, empty `arguments`); each following `contentBlockDelta` appends an `arguments` fragment to the same `index`.
- `messageStop.stopReason` maps to an OpenAI `finish_reason`: `end_turn`/`stop_sequence` → `stop`, `max_tokens` → `length`, `tool_use` → `tool_calls`, `guardrail_intervened`/`content_filtered` → `content_filter`, anything else → `stop`.
- When the request includes `"stream_options": {"include_usage": true}`, the proxy ends with one usage-only chunk (`choices: []`) carrying `prompt_tokens`, `completion_tokens`, `total_tokens`. Absent that option, no usage chunk is sent.

### Shared request conversion

The current adapter:

1. Resolves the requested alias using `models.json` (or accepts a complete Bedrock ID).
2. Moves system/developer messages to Bedrock's `system` field.
3. Converts user/assistant text messages into Bedrock message content blocks.
4. Converts OpenAI function tool definitions to Bedrock `toolConfig`.
5. Sends `maxTokens` in `inferenceConfig`.
6. Deliberately omits `temperature` and `topP` for every model. Bedrock models have different sampling-parameter support; omitting both avoids forwarding unsupported fields and lets each model use its defaults.
7. Calls `Converse` or `ConverseStream` based on `stream`.

The Pydantic request schema currently accepts `temperature` and `top_p` for client compatibility, but those values are not forwarded to Bedrock. The current maximum accepted `max_tokens` value is 32768.

More implementation details and current limitations: [ARCHITECTURE.md](ARCHITECTURE.md).

## 7. Model registry

Edit `tools/bedrock_proxy/models.json`:

```json
{
  "my-model-alias": {
    "model_id": "exact-bedrock-model-or-inference-profile-id",
    "provider": "bedrock_converse"
  }
}
```

- The JSON key is the public alias sent by VS Code.
- `model_id` is the exact Bedrock foundation model ID or inference-profile ID.
- `provider` selects the adapter. Currently only `bedrock_converse` is accepted.
- Restart the proxy after editing the registry; it is loaded at process startup.
- Check model/API support, inference-profile availability in the selected region, account model access, and IAM permissions before adding an entry.

Do not add GPT/Mantle or any other model that requires a different Bedrock API by simply labelling it `bedrock_converse`. A separate adapter is required when the model is not supported by Converse/ConverseStream.

## 8. Troubleshooting

| Symptom | Likely cause and action |
|---|---|
| `503 BEDROCK_PROXY_API_KEY is not configured` | Set a non-empty `BEDROCK_PROXY_API_KEY` in the same terminal that starts Uvicorn, then restart. |
| `401 Invalid or missing bearer token` | The VS Code/API key does not match the proxy process key. |
| `Unable to locate credentials` / SSO token error | Run `aws sso login --profile cherrystock-bedrock`; verify `AWS_PROFILE`. |
| `Unknown model alias` | Check spelling and that the alias exists in `models.json`; restart after editing. |
| Bedrock `ValidationException` for model ID | Verify the exact foundation model or inference-profile ID and that it is available to the account in `AWS_REGION`. |
| Bedrock `ValidationException` for an inference field | Check whether the model supports the field. This proxy currently omits `temperature` and `topP` globally. |
| Access denied / model access error | Verify IAM permissions and Bedrock model access for the selected inference profile. |
| Port 8787 already in use | Stop the previous Uvicorn process or choose another port and update the VS Code URL. |

## 9. Security notes

- Bind to `127.0.0.1` only. Do not expose this development proxy on `0.0.0.0` or the public internet.
- Keep the proxy key private and out of Git.
- AWS authentication remains in the AWS CLI/Boto3 credential chain; do not copy SSO tokens into this application.
- This is a local development adapter, not a production multi-user gateway.
