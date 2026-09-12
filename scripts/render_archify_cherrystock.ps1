param(
    [Alias("Input")]
    [string]$InputPath = "docs/architecture/diagrams/cherrystock-high-level.architecture.json",
    [Alias("Output")]
    [string]$OutputPath = "docs/architecture/generated/CherryStock_High_Level.html",
    [string]$SansFont = "Inter",
    [string]$NavigationConfig = "docs/architecture/diagrams/cherrystock-archify-navigation.json",
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

    $preflightArgs = @(
        "scripts/validate_archify_source.py",
        $resolvedInput,
        "--repo-root", $repoRoot,
        "--output", $resolvedOutput
    )
    if (Test-Path $NavigationConfig -PathType Leaf) {
        $resolvedNavigationConfig = (Resolve-Path $NavigationConfig).Path
        $preflightArgs += @("--navigation-config", $resolvedNavigationConfig)
    }
    else {
        $resolvedNavigationConfig = $null
    }

    Write-Host "[1/5] CherryStock Archify preflight..."
    Write-Host "Input: $resolvedInput"
    & python @preflightArgs
    if ($LASTEXITCODE -ne 0) {
        throw "CherryStock Archify preflight failed. Fix repository-owned source/navigation invariants before invoking Archify."
    }

    Write-Host "[2/5] Validate Archify architecture (showcase)..."
    & node $archify validate architecture $resolvedInput --repo-root $repoRoot --quality showcase --json
    if ($LASTEXITCODE -ne 0) {
        throw "Archify validation failed. Fix schema/layout/composition diagnostics before rendering."
    }

    Write-Host "[3/5] Deliver interactive HTML..."
    & node $archify deliver architecture $resolvedInput $resolvedOutput --repo-root $repoRoot --quality showcase --json
    if ($LASTEXITCODE -ne 0) {
        throw "Archify deliver failed."
    }

    Write-Host "[4/5] Apply CherryStock typography + runtime font picker..."
    & python scripts/customize_archify_typography.py $resolvedOutput --sans-font $SansFont
    if ($LASTEXITCODE -ne 0) {
        throw "CherryStock typography post-processing failed."
    }

    Write-Host "[5/5] Apply CherryStock drill-down navigation..."
    if ($resolvedNavigationConfig) {
        & python scripts/customize_archify_navigation.py $resolvedOutput --config $resolvedNavigationConfig
        if ($LASTEXITCODE -ne 0) {
            throw "CherryStock Archify navigation post-processing failed."
        }
    }
    else {
        Write-Host "Navigation config not found; skipped: $NavigationConfig"
    }

    Write-Host "Rendered: $resolvedOutput"
    Write-Host "Default title font: $SansFont"
    Write-Host "HTML font picker: Inter / Segoe UI / IBM Plex Sans / Arial / system-ui / JetBrains Mono"
    Write-Host "Technical text remains Archify JetBrains Mono."
    if ($resolvedNavigationConfig) {
        Write-Host "Drill-down navigation applied from: $resolvedNavigationConfig"
    }

    if (-not $NoOpen) {
        Start-Process $resolvedOutput
    }
}
finally {
    Pop-Location
}
