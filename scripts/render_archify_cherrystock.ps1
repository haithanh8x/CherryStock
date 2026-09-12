param(
    [string]$Input = "docs/architecture/diagrams/cherrystock-high-level.architecture.json",
    [string]$Output = "docs/architecture/generated/CherryStock_High_Level.html",
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

    Write-Host "[1/3] Validate Archify architecture (showcase)..."
    & node $archify validate architecture $Input --repo-root . --quality showcase --json
    if ($LASTEXITCODE -ne 0) {
        throw "Archify validation failed. Fix diagnostics before rendering."
    }

    $outputDir = Split-Path -Parent $Output
    if ($outputDir) {
        New-Item -ItemType Directory -Force $outputDir | Out-Null
    }

    Write-Host "[2/3] Deliver interactive HTML..."
    & node $archify deliver architecture $Input $Output --repo-root . --quality showcase --json
    if ($LASTEXITCODE -ne 0) {
        throw "Archify deliver failed."
    }

    Write-Host "[3/3] Apply CherryStock typography (sans titles + Archify mono technical text)..."
    & python scripts/customize_archify_typography.py $Output --sans-font $SansFont
    if ($LASTEXITCODE -ne 0) {
        throw "CherryStock typography post-processing failed."
    }

    $resolvedOutput = (Resolve-Path $Output).Path
    Write-Host "Rendered: $resolvedOutput"
    Write-Host "Typography: node/boundary titles = $SansFont; technical text = Archify JetBrains Mono"

    if (-not $NoOpen) {
        Start-Process $resolvedOutput
    }
}
finally {
    Pop-Location
}
