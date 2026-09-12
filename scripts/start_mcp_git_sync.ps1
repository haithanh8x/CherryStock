param(
    [ValidateSet("http", "stdio")]
    [string]$Transport = "http",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"
$RepoPath = Split-Path -Parent $PSScriptRoot
Set-Location $RepoPath

$Python = Join-Path $RepoPath ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

Write-Host "========================================"
Write-Host "CherryStock Git Sync MCP"
Write-Host "========================================"
Write-Host "Repository: $RepoPath"
Write-Host "Transport:  $Transport"

if ($Transport -eq "http") {
    Write-Host "Endpoint:   http://${HostAddress}:${Port}/mcp"
    & $Python -m src.mcp_server.git_sync_mcp --transport http --host $HostAddress --port $Port
}
else {
    & $Python -m src.mcp_server.git_sync_mcp --transport stdio
}

if ($LASTEXITCODE -ne 0) {
    throw "Git Sync MCP exited with code $LASTEXITCODE"
}
