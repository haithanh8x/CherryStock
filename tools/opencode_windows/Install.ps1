param(
    [Parameter(Mandatory=$true)][string]$RepoPath,
    [switch]$ReplaceGlobalConfig
)
$ErrorActionPreference = "Stop"
function Run-Checked([string]$Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Exe failed (exit $LASTEXITCODE)." }
}
if ($env:OS -ne "Windows_NT") { throw "Windows only." }
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot "manifest.json") -Raw | ConvertFrom-Json
foreach ($entry in $manifest.files.PSObject.Properties) {
    $file = Join-Path $PSScriptRoot $entry.Name
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) {
        throw "Package checksum mismatch: $($entry.Name)"
    }
}
$RepoPath = (Resolve-Path -LiteralPath $RepoPath).Path
$remote = & git -C $RepoPath remote get-url origin
if ($LASTEXITCODE -ne 0 -or $remote -notin @("https://github.com/haithanh8x/CherryStock.git", "git@github.com:haithanh8x/CherryStock.git")) {
    throw "RepoPath must be a CherryStock GitHub checkout with origin configured."
}
$configRoot = if ($env:XDG_CONFIG_HOME) { Join-Path $env:XDG_CONFIG_HOME "opencode" } else { Join-Path $HOME ".config\opencode" }
$targetConfig = Join-Path $configRoot "opencode.json"
if (((Test-Path $targetConfig) -or (Test-Path (Join-Path $configRoot "opencode.jsonc"))) -and -not $ReplaceGlobalConfig) {
    throw "Existing global config. Review template; use -ReplaceGlobalConfig only to replace it after backup."
}
if (Test-Path (Join-Path $configRoot "opencode.jsonc")) {
    throw "Existing opencode.jsonc: merge the template manually; installer will not change JSONC."
}
# Refuse to overwrite different local files; list conflicts before any overlay.
$snapshot = Join-Path $PSScriptRoot "snapshot"
$conflicts = @()
foreach ($f in Get-ChildItem -LiteralPath $snapshot -File -Recurse -Force) {
    $rel = $f.FullName.Substring($snapshot.Length + 1)
    $dst = Join-Path $RepoPath $rel
    if ((Test-Path -LiteralPath $dst) -and (Get-FileHash -LiteralPath $dst).Hash -ne (Get-FileHash -LiteralPath $f.FullName).Hash) {
        $conflicts += $rel
    }
}
if ($conflicts.Count) {
    throw ("Snapshot differs from target checkout. Review/merge these files manually, then rerun. No overwrite: `n" + ($conflicts -join "`n"))
}
Get-Command py, aws, opencode, git -ErrorAction Stop | Out-Null
Run-Checked "py" @("-3.13", "-c", "import sys; assert sys.version_info >= (3,13)")
$venv = Join-Path $PSScriptRoot ".venv"
Run-Checked "py" @("-3.13", "-m", "venv", $venv)
$python = Join-Path $venv "Scripts\python.exe"
Run-Checked $python @("-m", "pip", "install", "-r", (Join-Path $PSScriptRoot "requirements.txt"))
Run-Checked $python @("-m", "pip", "check")
Run-Checked $python @("-c", "import boto3,botocore; print('SDK imports OK')")
$arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLowerInvariant()
if ($arch -notin @("x64", "arm64")) { throw "Unsupported Windows architecture: $arch" }
$assetArch = if ($arch -eq "x64") { "x86_64" } else { "arm64" }
$asset = "github-mcp-server_Windows_$assetArch.zip"
$base = "https://github.com/github/github-mcp-server/releases/download/v2.1.0"
$bin = Join-Path $PSScriptRoot "bin"
New-Item -ItemType Directory -Path $bin -Force | Out-Null
$exe = Join-Path $bin "github-mcp-server.exe"
if (Test-Path $exe) { throw "Existing GitHub MCP binary: review/remove it manually before reinstalling." }
$download = Join-Path $bin $asset
Invoke-WebRequest -UseBasicParsing "$base/$asset" -OutFile $download
$checks = (Invoke-WebRequest -UseBasicParsing "$base/github-mcp-server_2.1.0_checksums.txt").Content
$line = ($checks -split "`n" | Where-Object { $_.Trim().EndsWith($asset) })
if (@($line).Count -ne 1) { throw "Missing/ambiguous release checksum." }
$expected = ($line.Trim() -split "\s+")[0]
if ((Get-FileHash $download -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw "GitHub MCP checksum mismatch." }
Expand-Archive -LiteralPath $download -DestinationPath $bin
if (-not (Test-Path $exe)) { throw "Expected GitHub MCP executable missing." }
foreach ($f in Get-ChildItem -LiteralPath $snapshot -File -Recurse -Force) {
    $dst = Join-Path $RepoPath $f.FullName.Substring($snapshot.Length + 1)
    New-Item -ItemType Directory -Path (Split-Path $dst) -Force | Out-Null
    if (-not (Test-Path -LiteralPath $dst)) { Copy-Item -LiteralPath $f.FullName -Destination $dst }
}
New-Item -ItemType Directory -Path $configRoot -Force | Out-Null
if (Test-Path $targetConfig) {
    Copy-Item -LiteralPath $targetConfig -Destination ($targetConfig + ".backup-" + [Guid]::NewGuid().ToString("N"))
}
$template = Get-Content -LiteralPath (Join-Path $PSScriptRoot "opencode.windows.template.json") -Raw | ConvertFrom-Json
$template.mcp.servers.github.command[0] = $exe
$text = $template | ConvertTo-Json -Depth 40
[System.IO.File]::WriteAllText($targetConfig, $text, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Setup installed. AWS SSO/MCP OAuth must be configured on this Windows user."
Write-Host "No remote access, task registration, or model invocation has been performed."
