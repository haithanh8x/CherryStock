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

Write-Host "[1/3] Structural validation"
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
    Write-Host "[2/3] Native CLI probe skipped by -SkipExport"
    Write-Host "[3/3] Demo export skipped by -SkipExport"
    exit 0
}

$drawioExe = Find-DrawioExecutable
if (-not $drawioExe) {
    Write-Warning "Draw.io Desktop CLI was not found. Validation passed; native export checks skipped."
    Write-Host "Open the editable source manually: $diagramPath"
    exit 0
}

$drawioInfo = Get-DrawioExecutableInfo -DrawioExe $drawioExe
Write-Host "Draw.io CLI: $drawioExe"
if ($drawioInfo) {
    Write-Host ("File version:    {0}" -f $drawioInfo.FileVersion)
    Write-Host ("Product version: {0}" -f $drawioInfo.ProductVersion)
}

$runningDrawio = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -in @("draw.io", "drawio") })
if ($runningDrawio.Count -gt 0) {
    Write-Host ("Detected {0} running Draw.io process(es). The helper will avoid relying on the normal GUI instance." -f $runningDrawio.Count)
}
else {
    Write-Host "No running Draw.io GUI process detected. The helper will try the documented CLI path first."
}

Write-Host "[2/3] Native CLI export probe"
$probe = Test-DrawioNativeExportCapability -DrawioExe $drawioExe -TimeoutSeconds 30 -Verbose
Write-Host ("PASS: native CLI probe ({0} bytes, strategy={1}, elapsed={2}ms)" -f $probe.Bytes, $probe.Strategy, $probe.ElapsedMs)

New-Item -ItemType Directory -Path $generatedDir -Force | Out-Null

Write-Host "[3/3] Demo native PNG export"
Write-Host "Output: $pngPath"
$result = Invoke-DrawioPngExport -InputPath $diagramPath -OutputPath $pngPath -DrawioExe $drawioExe -Width 2000 -TimeoutSeconds 30 -Verbose

if (-not (Test-Path -LiteralPath $pngPath -PathType Leaf)) {
    throw "Native export returned but final PNG does not exist: $pngPath"
}
if (-not (Test-DrawioPngFile -Path $pngPath)) {
    throw "Final file exists but is not a valid PNG: $pngPath"
}

Write-Host "PASS: demo native PNG export"
Write-Host ("Strategy:        {0}" -f $result.Strategy)
Write-Host ("PNG bytes:       {0}" -f $result.Bytes)
Write-Host ("Elapsed:         {0} ms" -f $result.ElapsedMs)
Write-Host "Editable source: $diagramPath"
Write-Host "Draft PNG:       $pngPath"
