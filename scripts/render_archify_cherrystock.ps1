param(
    [Alias("Input")]
    [string]$InputPath = "docs/architecture/diagrams/cherrystock-high-level.architecture.json",
    [Alias("Output")]
    [string]$OutputPath = "docs/architecture/generated/CherryStock_High_Level.html",
    [string]$SansFont = "Inter",
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot
try {
    $archify = Join-Path $env:USERPROFILE ".agents\skills\archify\bin\archify.mjs"
    if (-not (Test-Path $archify)) {
        throw "Archify CLI not found at $archify. Install the Archify skill first."
    }

    if (-not (Test-Path $InputPath -PathType Leaf)) {
        throw "Archify input JSON not found: $InputPath"
    }
    $resolvedInput = (Resolve-Path $InputPath).Path

    $outputDir = Split-Path -Parent $OutputPath
    if ($outputDir) {
        New-Item -ItemType Directory -Force $outputDir | Out-Null
    }
    $resolvedOutput = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputPath))

    Write-Host "[1/3] Validate Archify architecture (showcase)..."
    Write-Host "Input: $resolvedInput"
    & node $archify validate architecture $resolvedInput --repo-root $repoRoot --quality showcase --json
    if ($LASTEXITCODE -ne 0) {
        throw "Archify validation failed. Fix diagnostics before rendering."
    }

    Write-Host "[2/3] Deliver interactive HTML..."
    & node $archify deliver architecture $resolvedInput $resolvedOutput --repo-root $repoRoot --quality showcase --json
    if ($LASTEXITCODE -ne 0) {
        throw "Archify deliver failed."
    }

    Write-Host "[3/3] Apply CherryStock typography + runtime font picker..."
    & python scripts/customize_archify_typography.py $resolvedOutput --sans-font $SansFont
    if ($LASTEXITCODE -ne 0) {
        throw "CherryStock typography post-processing failed."
    }

    Write-Host "Rendered: $resolvedOutput"
    Write-Host "Default title font: $SansFont"
    Write-Host "HTML font picker: Inter / Segoe UI / IBM Plex Sans / Arial / system-ui / JetBrains Mono"
    Write-Host "Technical text remains Archify JetBrains Mono."

    if (-not $NoOpen) {
        Start-Process $resolvedOutput
    }
}
finally {
    Pop-Location
}
