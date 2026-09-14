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

if (-not (Test-Path $diagramPath)) {
    throw "Demo diagram not found: $diagramPath"
}
if (-not (Test-Path $validator)) {
    throw "drawio-skill validator not found at $validator. Run .\scripts\install_drawio_skill.ps1 first."
}

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

$drawioCandidates = @()
$cmd = Get-Command "drawio" -ErrorAction SilentlyContinue
if ($cmd) { $drawioCandidates += $cmd.Source }
$drawioCandidates += "C:\Program Files\draw.io\draw.io.exe"
if ($env:LOCALAPPDATA) {
    $drawioCandidates += (Join-Path $env:LOCALAPPDATA "Programs\draw.io\draw.io.exe")
}
$drawioExe = $drawioCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if (-not $drawioExe) {
    Write-Warning "Draw.io Desktop CLI was not found. Validation passed; PNG export skipped."
    Write-Host "Open the editable source manually: $diagramPath"
    exit 0
}

New-Item -ItemType Directory -Path $generatedDir -Force | Out-Null
$tempExportDir = Join-Path ([System.IO.Path]::GetTempPath()) ("cherrystock-drawio-export-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempExportDir -Force | Out-Null
$tempPng = Join-Path $tempExportDir "agent-harness-five-components.png"

Write-Host "[2/2] Exporting draft PNG with $drawioExe"
Write-Host "Temporary PNG target: $tempPng"

try {
    # Use explicit long-form CLI switches and an output FILE, not an output directory.
    # This is the most consistent syntax across recent draw.io Desktop Windows builds.
    & $drawioExe --export --format png --output $tempPng $diagramPath
    $exportExitCode = $LASTEXITCODE

    if ($exportExitCode -ne 0) {
        throw "Draw.io export failed with exit code $exportExitCode"
    }

    if (-not (Test-Path $tempPng)) {
        $nearSource = [System.IO.Path]::ChangeExtension($diagramPath, ".png")
        $nearSourceDrawioPng = "$diagramPath.png"

        if (Test-Path $nearSource) {
            $tempPng = $nearSource
        }
        elseif (Test-Path $nearSourceDrawioPng) {
            $tempPng = $nearSourceDrawioPng
        }
        else {
            throw "Draw.io returned exit code 0 but did not create the requested PNG '$tempPng'. Run '& `"$drawioExe`" --help' and '& `"$drawioExe`" --version' locally and capture their output if this persists."
        }
    }

    Copy-Item -Path $tempPng -Destination $pngPath -Force

    if (-not (Test-Path $pngPath)) {
        throw "PNG existed after export but could not be copied to: $pngPath"
    }

    Write-Host "PASS: PNG generated"
    Write-Host "Editable source: $diagramPath"
    Write-Host "Draft PNG:      $pngPath"
}
finally {
    if (Test-Path $tempExportDir) {
        Remove-Item $tempExportDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
