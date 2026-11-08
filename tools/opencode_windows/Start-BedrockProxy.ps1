param(
    [string]$Profile = "data-app-sit",
    [string]$Region = "ap-southeast-1",
    [switch]$LogToFile
)
$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$source = Join-Path $PSScriptRoot "snapshot\src\llm\bedrock_http_proxy.py"
if (-not (Test-Path -LiteralPath $source)) {
    # In a checkout, run the repository source instead of the kit snapshot.
    $source = Join-Path $PSScriptRoot "..\..\src\llm\bedrock_http_proxy.py"
    $python = (Get-Command python -CommandType Application -ErrorAction Stop).Source
} elseif (-not (Test-Path -LiteralPath $python)) {
    throw "Run Install.ps1 first."
}
if (-not (Test-Path -LiteralPath $source)) { throw "Bedrock proxy source not found." }

# Bind to the connected physical Wi-Fi interface, not a VPN or virtual adapter.
$wifi = @(Get-NetAdapter -Physical | Where-Object { $_.Status -eq 'Up' -and $_.NdisPhysicalMedium -eq 9 })
if ($wifi.Count -ne 1) { throw "Expected one connected physical Wi-Fi adapter; found $($wifi.Count)." }
$addresses = @(Get-NetIPAddress -InterfaceIndex $wifi[0].ifIndex -AddressFamily IPv4 |
    Where-Object { $_.AddressState -eq 'Preferred' -and $_.IPAddress -notlike '169.254.*' })
if ($addresses.Count -ne 1) { throw "Expected one preferred Wi-Fi IPv4 address; found $($addresses.Count)." }
$env:DRAWIO_PROXY_HOST = $addresses[0].IPAddress
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
Write-Warning "LAN HTTP listener $($env:DRAWIO_PROXY_HOST):$($env:DRAWIO_PROXY_PORT) has no authentication or TLS. Restrict access with Windows Firewall."
# Do not overwrite certificate/proxy settings established by the user's IT team.
if ($LogToFile) {
    $logs = Join-Path $PSScriptRoot "logs"
    New-Item -ItemType Directory -Path $logs -Force | Out-Null
    & $python $source *> (Join-Path $logs ("proxy-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss")))
} else {
    & $python $source
}
if ($LASTEXITCODE -ne 0) { throw "Bedrock proxy exited with code $LASTEXITCODE. Check profile/SSO and logs." }
