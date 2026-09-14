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

# draw.io Desktop CLI behavior for -o differs across Windows builds. To avoid
# relying on whether -o is interpreted as a file path or a directory, always
# export into a temporary directory, then detect the actual PNG and move/rename
# it to CherryStock's deterministic generated-artifact path.
$tempExportDir = Join-Path ([System.IO.Path]::GetTempPath()) ("cherrystock-drawio-export-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempExportDir -Force | Out-Null

try {
    Write-Host "[2/2] Exporting draft PNG with $drawioExe"
    Write-Host "Temporary export directory: $tempExportDir"

    & $drawioExe -x -f png --width 2000 -o $tempExportDir $diagramPath
    $drawioExitCode = $LASTEXITCODE

    if ($drawioExitCode -ne 0) {
        throw "Draw.io export failed with exit code $drawioExitCode"
    }

    $exportedPngs = @(Get-ChildItem -Path $tempExportDir -File -Filter "*.png" -Recurse -ErrorAction SilentlyContinue)

    if ($exportedPngs.Count -eq 0) {
        # Some Windows builds may still place the generated PNG beside the
        # source despite -o. Check the source directory as a compatibility
        # fallback and only consider files newer than the start of this run.
        $sourceDir = Split-Path -Parent $diagramPath
        $sourceStem = [System.IO.Path]::GetFileNameWithoutExtension($diagramPath)
        $fallbackCandidates = @(
            (Join-Path $sourceDir ($sourceStem + ".png")),
            (Join-Path $sourceDir ($sourceStem + ".drawio.png"))
        ) | Where-Object { Test-Path $_ }

        foreach ($candidate in $fallbackCandidates) {
            $exportedPngs += Get-Item $candidate
        }
    }

    if ($exportedPngs.Count -eq 0) {
        throw "Draw.io returned success but no PNG was found in '$tempExportDir' or beside the source diagram. Run '& `"$drawioExe`" --help' locally to inspect this installed CLI's export syntax."
    }

    if ($exportedPngs.Count -gt 1) {
        $names = ($exportedPngs | ForEach-Object { $_.FullName }) -join "; "
        Write-Warning "Multiple PNG candidates were produced; using the newest one. Candidates: $names"
    }

    $actualPng = $exportedPngs | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1

    if (Test-Path $pngPath) {
        Remove-Item $pngPath -Force
    }

    Move-Item -Path $actualPng.FullName -Destination $pngPath -Force

    if (-not (Test-Path $pngPath)) {
        throw "PNG candidate was detected but could not be moved to: $pngPath"
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
