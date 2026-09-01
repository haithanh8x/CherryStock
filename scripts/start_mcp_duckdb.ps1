param(
    [ValidateSet("stdio", "http")]
    [string]$Transport = "http",

    [string]$HostAddress = "127.0.0.1",

    [ValidateRange(1, 65535)]
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $Python = $VenvPython
}
else {
    $PythonCommand = Get-Command python -ErrorAction Stop
    $Python = $PythonCommand.Source
}

Write-Host "Starting CherryStock DuckDB MCP"
Write-Host "Transport: $Transport"

$Arguments = @(
    "-m",
    "src.mcp_server.duckdb_mcp",
    "--transport",
    $Transport
)

if ($Transport -eq "http") {
    Write-Host "Endpoint: http://${HostAddress}:$Port/mcp"
    $Arguments += @("--host", $HostAddress, "--port", "$Port")
}

& $Python @Arguments
exit $LASTEXITCODE
