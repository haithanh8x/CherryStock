param(
    [string]$Html = "docs/architecture/generated/CherryStock_High_Level.html",
    [string]$DefaultFont = "Inter",
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot
try {
    if (-not (Test-Path $Html)) {
        throw "CherryStock Archify HTML not found: $Html"
    }

    & python scripts/customize_archify_typography.py $Html --sans-font $DefaultFont
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to inject CherryStock font picker."
    }

    $resolvedHtml = (Resolve-Path $Html).Path
    Write-Host "Updated: $resolvedHtml"
    Write-Host "Font picker: Inter / Segoe UI / IBM Plex Sans / Arial / system-ui / JetBrains Mono"
    Write-Host "Selection is persisted in localStorage."

    if (-not $NoOpen) {
        Start-Process $resolvedHtml
    }
}
finally {
    Pop-Location
}
