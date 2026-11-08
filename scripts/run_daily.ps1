$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
$entryPoint = Join-Path $repoRoot 'run.py'

if (-not (Test-Path -LiteralPath $entryPoint -PathType Leaf)) {
    throw "Cannot find run.py at $entryPoint"
}

if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    $python = $venvPython
} else {
    $python = @(Get-Command python -CommandType Application -ErrorAction Stop)[0].Source
    Write-Warning "Repository .venv not found; using $python"
}

Push-Location -LiteralPath $repoRoot
try {
    & $python $entryPoint
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

exit $exitCode
