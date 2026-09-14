param(
    [string]$SkillRoot = (Join-Path $HOME ".agents\skills\drawio-skill"),
    [string]$Diagram = "docs\architecture\diagrams\agent-harness-five-components.drawio",
    [switch]$SkipExport
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$diagramPath = Join-Path $repoRoot $Diagram
$generatedDir = Join-Path $repoRoot "docs\architecture\generated"
$pngPath = Join-Path $generatedDir "Agent_Harness_Five_Components.png"
$validator = Join-Path $SkillRoot "scripts\validate.py"
$drawioModule = Join-Path $PSScriptRoot "lib\DrawioCli.psm1"

if (-not (Test-Path -LiteralPath $diagramPath)) {
    throw "Demo diagram not found: $diagramPath"
}
if (-not (Test-Path -LiteralPath $validator)) {
    throw "drawio-skill validator not found at $validator. Run .\scripts\install_drawio_skill.ps1 first."
}
if (-not (Test-Path -LiteralPath $drawioModule)) {
    throw "CherryStock Draw.io CLI helper not found: $drawioModule"
}

Import-Module $drawioModule -Force

$python = Get-Command "python" -ErrorAction SilentlyContinue
$usePyLauncher = $false
if (-not $python) {
    $python = Get-Command "py" -ErrorAction SilentlyContinue
    $usePyLauncher = $true
}
if (-not $python) {
    throw "Python 3 was not found in PATH."
}

Write-Host "[1/2] Structural validation"
if ($usePyLauncher) {
    & $python.Source -3 $validator $diagramPath --score
}
else {
    & $python.Source $validator $diagramPath --score
}
if ($LASTEXITCODE -ne 0) {
    throw "drawio-skill structural validation failed with exit code $LASTEXITCODE"
}
Write-Host "PASS: structural validation"

if ($SkipExport) {
    Write-Host "[2/2] Export skipped by -SkipExport"
    exit 0
}

$drawioExe = Find-DrawioExecutable
if (-not $drawioExe) {
    Write-Warning "Draw.io Desktop CLI was not found. Validation passed; PNG export skipped."
    Write-Host "Open the editable source manually: $diagramPath"
    exit 0
}

New-Item -ItemType Directory -Path $generatedDir -Force | Out-Null

$runningDrawio = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -in @("draw.io", "drawio") })
if ($runningDrawio.Count -gt 0) {
    Write-Host ("Detected {0} running Draw.io process(es). Export will use an isolated Electron user-data-dir so the existing GUI does not block the CLI." -f $runningDrawio.Count)
}

Write-Host "[2/2] Native PNG export"
Write-Host "Draw.io CLI: $drawioExe"
Write-Host "Output:      $pngPath"

$result = Invoke-DrawioPngExport -InputPath $diagramPath -OutputPath $pngPath -DrawioExe $drawioExe -Width 2000 -TimeoutSeconds 45 -Verbose

if (-not (Test-Path -LiteralPath $pngPath -PathType Leaf)) {
    throw "Native export returned but final PNG does not exist: $pngPath"
}
if (-not (Test-DrawioPngFile -Path $pngPath)) {
    throw "Final file exists but is not a valid PNG: $pngPath"
}

Write-Host "PASS: native PNG export"
Write-Host ("PNG bytes:       {0}" -f $result.Bytes)
Write-Host "Editable source: $diagramPath"
Write-Host "Draft PNG:       $pngPath"
