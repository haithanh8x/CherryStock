param(
    [string]$InstallRoot = (Join-Path $HOME ".agents\skills\drawio-skill"),
    [string]$UpstreamRef = "7aa92f73819766eb914fffac66762cf2adb5d828",
    [switch]$SkipNativeExportProbe
)

$ErrorActionPreference = "Stop"

$repoUrl = "https://github.com/Agents365-ai/drawio-skill.git"
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("cherrystock-drawio-skill-" + [Guid]::NewGuid().ToString("N"))
$cloneRoot = Join-Path $tempRoot "repo"
$drawioModule = Join-Path $PSScriptRoot "lib\DrawioCli.psm1"

function Require-Command([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Required command '$Name' was not found in PATH."
    }
    return $cmd
}

if (-not (Test-Path -LiteralPath $drawioModule)) {
    throw "CherryStock Draw.io CLI helper not found: $drawioModule"
}
Import-Module $drawioModule -Force

Write-Host "CherryStock Draw.io Skill installer"
Write-Host "Upstream: $repoUrl"
Write-Host "Pinned ref: $UpstreamRef"
Write-Host "Install root: $InstallRoot"

Require-Command "git" | Out-Null

$python = Get-Command "python" -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command "py" -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "Python 3 is required but neither 'python' nor 'py' was found in PATH."
}

New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

try {
    & git clone --quiet --no-checkout $repoUrl $cloneRoot
    if ($LASTEXITCODE -ne 0) {
        throw "git clone failed with exit code $LASTEXITCODE"
    }

    Push-Location $cloneRoot
    try {
        & git sparse-checkout init --cone
        if ($LASTEXITCODE -ne 0) { throw "git sparse-checkout init failed" }

        & git sparse-checkout set skills/drawio-skill
        if ($LASTEXITCODE -ne 0) { throw "git sparse-checkout set failed" }

        & git checkout --quiet $UpstreamRef
        if ($LASTEXITCODE -ne 0) { throw "git checkout $UpstreamRef failed" }
    }
    finally {
        Pop-Location
    }

    $source = Join-Path $cloneRoot "skills\drawio-skill"
    if (-not (Test-Path (Join-Path $source "SKILL.md"))) {
        throw "Upstream skill payload was not found at $source"
    }

    if (Test-Path $InstallRoot) {
        Remove-Item $InstallRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
    Copy-Item -Path (Join-Path $source "*") -Destination $InstallRoot -Recurse -Force

    Set-Content -Path (Join-Path $InstallRoot ".cherrystock-upstream-ref") -Value $UpstreamRef -Encoding UTF8

    Write-Host "Installed upstream drawio-skill successfully."

    $diagramCtl = Join-Path $InstallRoot "scripts\diagramctl.py"
    if (Test-Path $diagramCtl) {
        Write-Host "Running diagramctl doctor..."
        if ($python.Name -eq "py.exe" -or $python.Name -eq "py") {
            & $python.Source -3 $diagramCtl doctor
        }
        else {
            & $python.Source $diagramCtl doctor
        }
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "diagramctl doctor returned exit code $LASTEXITCODE. Review the output above."
        }
    }

    $drawioExe = Find-DrawioExecutable

    if ($drawioExe) {
        Write-Host "Draw.io Desktop CLI detected: $drawioExe"
        try {
            & $drawioExe --version
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Draw.io Desktop '--version' returned exit code $LASTEXITCODE."
            }
        }
        catch {
            throw "Draw.io Desktop was found at '$drawioExe' but could not be executed: $($_.Exception.Message)"
        }

        if (-not $SkipNativeExportProbe) {
            Write-Host "Running isolated native PNG export probe..."
            $probe = Test-DrawioNativeExportCapability -DrawioExe $drawioExe -TimeoutSeconds 45
            Write-Host ("PASS: native PNG export probe ({0} bytes)" -f $probe.Bytes)
        }
        else {
            Write-Host "Native PNG export probe skipped by -SkipNativeExportProbe"
        }
    }
    else {
        Write-Warning "Draw.io Desktop CLI not detected. Core Python workflows still work; native PNG/SVG/PDF export will be skipped until Draw.io Desktop is installed."
    }
}
finally {
    if (Test-Path $tempRoot) {
        Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
