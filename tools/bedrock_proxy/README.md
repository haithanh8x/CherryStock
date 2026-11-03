# CherryStock Bedrock Proxy

A localhost-only OpenAI-compatible API that forwards chat requests to Amazon Bedrock using the AWS SDK credential chain and an AWS CLI IAM Identity Center profile. It does not read or copy SSO cache tokens.

## Requirements

- Python 3.13+
- AWS CLI v2 with an authenticated IAM Identity Center profile
- IAM permission to invoke the selected Bedrock inference profile

## Install (Windows PowerShell)

From the CherryStock repository root:

```powershell
python -m pip install -e ".[bedrock-proxy]"
$env:AWS_PROFILE = "cherrystock-bedrock"
$env:AWS_REGION = "ap-southeast-1"
$env:BEDROCK_DEFAULT_MODEL = "claude-sonnet-4.5"
$env:BEDROCK_PROXY_API_KEY = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
python -m uvicorn tools.bedrock_proxy.app:app --host 127.0.0.1 --port 8787
```

Keep the terminal running. The API key is local process configuration; do not commit it or put it in workspace settings.

If the SSO session expires, refresh it in another PowerShell window:

```powershell
aws sso login --profile cherrystock-bedrock
```

## Verify

```powershell
$headers = @{ Authorization = "Bearer $env:BEDROCK_PROXY_API_KEY" }
Invoke-RestMethod http://127.0.0.1:8787/health
Invoke-RestMethod http://127.0.0.1:8787/v1/models -Headers $headers
```

Chat completion:

```powershell
$body = @{
  model = "claude-sonnet-4.5"
  messages = @(@{ role = "user"; content = "Reply with exactly: CherryStock proxy OK" })
  max_tokens = 128
} | ConvertTo-Json -Depth 10
Invoke-RestMethod http://127.0.0.1:8787/v1/chat/completions -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

## API

- `GET /health` — local liveness check (no auth)
- `GET /v1/models` — model aliases (Bearer token required)
- `POST /v1/chat/completions` — OpenAI-compatible chat completions, streaming, and function tool definitions

Model aliases:
- `claude-sonnet-4.5` — global Claude Sonnet 4.5
- `claude-opus-4.6` — global Claude Opus 4.6
- `nova-2-lite` — global Amazon Nova 2 Lite

You can also pass a full Bedrock inference profile ID as `model`.

## VS Code agent settings

Use the agent's OpenAI-compatible provider configuration:

- Base URL: `http://127.0.0.1:8787/v1`
- API key: value of `BEDROCK_PROXY_API_KEY`
- Model: `claude-sonnet-4.5`

Exact setting names vary by extension. Do not put the API key in a committed `.vscode/settings.json`.

## Security and limitations

- The server binds only to loopback (`127.0.0.1`); do not change this to `0.0.0.0` unless you add a proper network security design.
- The proxy requires a non-empty bearer key and compares it in constant time.
- AWS credentials are resolved by Boto3 from the configured AWS profile. The proxy never reads SSO cache files directly.
- The first version maps text messages and function tool definitions to Bedrock Converse. Streaming forwards text deltas; streamed tool-call deltas and multimodal image/audio payloads are not yet exposed in OpenAI format.
- This service is intended for a trusted local development machine, not internet-facing deployment.
