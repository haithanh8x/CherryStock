param(
    [string]$SansFont = "Inter",
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$renderer = Join-Path $PSScriptRoot "render_archify_cherrystock.ps1"

if (-not (Test-Path $renderer -PathType Leaf)) {
    throw "CherryStock Archify renderer not found: $renderer"
}

$inputPath = "docs/architecture/diagrams/cherrystock-analytics-calculation-engines.architecture.json"
$outputPath = "docs/architecture/generated/CherryStock_Analytics_Calculation_Engines.html"

Push-Location $repoRoot
try {
    & $renderer `
        -InputPath $inputPath `
        -OutputPath $outputPath `
        -SansFont $SansFont `
        -NoOpen:$NoOpen

    if ($LASTEXITCODE -ne 0) {
        throw "Analytics Archify render failed with exit code $LASTEXITCODE."
    }

    Write-Host "Analytics drill-down artifact ready: $outputPath"
}
finally {
    Pop-Location
}
