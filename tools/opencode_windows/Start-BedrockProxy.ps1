param(
    [string]$Profile = "data-app-sit",
    [string]$Region = "ap-southeast-1",
    [switch]$LogToFile
)
$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$source = Join-Path $PSScriptRoot "snapshot\src\llm\bedrock_http_proxy.py"
if (-not (Test-Path -LiteralPath $python)) { throw "Run Install.ps1 first." }
# Explicit local HTTP for OpenCode; never expose this unauthenticated listener.
$env:DRAWIO_PROXY_HOST = "127.0.0.1"
$env:DRAWIO_PROXY_PORT = "8765"
$env:DRAWIO_PROXY_TLS = "0"
$env:DRAWIO_PROXY_TOKEN = ""
$env:DRAWIO_PROXY_TOKEN_FILE = ""
$env:DRAWIO_PROXY_ALLOWED_MODELS = ""
$env:LLM_PROFILE = $Profile
$env:LLM_REGION = $Region
$env:LLM_BACKEND = "direct"
$env:LLM_TIER = "low"
$env:LLM_TIMEOUT = "300"
$env:PYTHONUNBUFFERED = "1"
$env:AWS_EC2_METADATA_DISABLED = "true"
# Do not overwrite certificate/proxy settings established by the user's IT team.
if ($LogToFile) {
    $logs = Join-Path $PSScriptRoot "logs"
    New-Item -ItemType Directory -Path $logs -Force | Out-Null
    & $python $source *> (Join-Path $logs ("proxy-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss")))
} else {
    & $python $source
}
if ($LASTEXITCODE -ne 0) { throw "Bedrock proxy exited with code $LASTEXITCODE. Check profile/SSO and logs." }
