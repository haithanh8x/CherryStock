param(
    [Alias("Input")]
    [string]$InputPath = "docs/architecture/diagrams/cherrystock-adlc-agent-harness.workflow.json",
    [Alias("Output")]
    [string]$OutputPath = "docs/architecture/generated/CherryStock_ADLC_Agent_Harness.html",
    [string]$DetailsPath = "docs/architecture/diagrams/cherrystock-adlc-agent-harness.passport.json",
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
        throw "Archify workflow input JSON not found: $InputPath"
    }
    if (-not (Test-Path $DetailsPath -PathType Leaf)) {
        throw "CherryStock agent passport sidecar not found: $DetailsPath"
    }

    $resolvedInput = (Resolve-Path $InputPath).Path
    $resolvedDetails = (Resolve-Path $DetailsPath).Path
    $outputDir = Split-Path -Parent $OutputPath
    if ($outputDir) {
        New-Item -ItemType Directory -Force $outputDir | Out-Null
    }
    $resolvedOutput = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputPath))

    Write-Host "[1/4] Validate CherryStock ADLC workflow (showcase)..."
    & node $archify validate workflow $resolvedInput --quality showcase --json
    if ($LASTEXITCODE -ne 0) {
        throw "Archify workflow validation failed. Fix schema/layout/composition diagnostics before rendering."
    }

    Write-Host "[2/4] Deliver CherryStock ADLC workflow HTML..."
    & node $archify deliver workflow $resolvedInput $resolvedOutput --quality showcase --json
    if ($LASTEXITCODE -ne 0) {
        throw "Archify workflow deliver failed."
    }

    Write-Host "[3/4] Apply CherryStock typography + runtime font picker..."
    & python scripts/customize_archify_typography.py $resolvedOutput --sans-font $SansFont
    if ($LASTEXITCODE -ne 0) {
        throw "CherryStock typography post-processing failed."
    }

    Write-Host "[4/4] Enrich Semantic Passport with CherryStock agent execution detail..."
    & python scripts/enrich_archify_agent_harness.py $resolvedOutput $resolvedDetails
    if ($LASTEXITCODE -ne 0) {
        throw "CherryStock agent passport enrichment failed."
    }

    Write-Host "Rendered: $resolvedOutput"
    Write-Host "Agent passport: $resolvedDetails"
    Write-Host "Default title font: $SansFont"

    if (-not $NoOpen) {
        Start-Process $resolvedOutput
    }
}
finally {
    Pop-Location
}
