# Local Bedrock proxy — ADR-0011 upgrade

Scope: local `src/llm/bedrock_http_proxy.py` only; no ECS, IAM, security-group,
OCR or client-endpoint changes. The SIT snapshot in
[ADR-0011](../adr/0011-bedrock-proxy-sit-api-contract-image-support.md) is not
evidence of this Windows runtime's live model permissions.

## Local contract

- Default allowlist: exactly the eight `VERIFIED_MODELS`; tier mappings do not add
  Fable or other unverified models. An explicit environment allowlist still overrides it.
- Body limit: 20 MiB; decoded image limit: 3,750,000 bytes; at most 20 images across
  all user messages in the submitted history. Environment overrides are supported.
- User `image_url` parts accept embedded base64 PNG/JPEG/JPG/GIF/WebP data URLs.
  Bytes are forwarded unchanged to Converse. No URL fetching or pixel validation.
- Invalid base64, unsupported parts/formats, remote URLs, images in non-user roles
  and excessive image counts return ADR-0011 errors before Bedrock/SSE headers.
- Completion logs include `images_in` for JSON and SSE, never image/prompt content.
- Existing streaming, tool calling, stateless history and text-only draw.io calls
  are retained. AWS TLS verification remains enabled.

## Developer checks (no AWS calls)

From repository root, using the Python environment with pytest installed:

```powershell
python -m pytest tests/test_bedrock_http_proxy.py -o addopts= -q
python -m py_compile src/llm/bedrock_http_proxy.py
git diff --check
```

Tests replace the Bedrock client before importing the actual entry point. They
exercise conversion, HTTP errors/limits/auth, image counts, chunked SSE, tools
and parallel requests using synthetic data only. They do not prove actual model
access or OpenCode attachment delivery.

## Apply locally

`tools/opencode_windows/Start-BedrockProxy.ps1` uses the bundled snapshot when
present; otherwise it executes this checkout's source using system Python.
Confirm the running process command line before restarting so the intended source
is upgraded. Do not overwrite a separate snapshot or installer manifest blindly.

Stop only that confirmed proxy process (interrupts in-flight requests), then run:

```powershell
.\tools\opencode_windows\Start-BedrockProxy.ps1 -LogToFile
```

The current checkout launcher binds the connected physical Wi-Fi IPv4 address,
not loopback, with no listener TLS/authentication. This upgrade does not change
that pre-existing exposure, firewall rules or the OpenCode endpoint. Restrict
access appropriately; changing listener security is a separate explicit action.
Never disable verification of outbound AWS TLS.

Using the existing listener address, check `/health` and `/v1/models`. Expect HTTP
200 and eight models; neither endpoint invokes Bedrock. Submit a synthetic remote
image URL and expect `400 remote_image_url_not_supported`, without a Bedrock call.
For SSO expiration, stop and ask the user to log in; do not handle MFA automatically.

Real text/tool/image end-to-end checks require valid SSO and paid model calls.
Use only synthetic prompts/generated images, small token limits and explicit
approval. OpenCode also needs `attachment: true` and image input modalities for
the selected model; this proxy-only upgrade does not alter client configuration.

## Rollback

Keep the original source from the pre-upgrade Git revision or a reviewed backup.
Stop only the identified local proxy, restore only the upgrade-owned changes after
checking for user edits, then restart the same launcher. Do not use broad resets.
No AWS rollback is needed. Earlier local behavior may silently omit invalid images
or admit Fable through tier mappings; prefer fixing forward when possible.
