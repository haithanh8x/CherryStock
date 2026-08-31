$ErrorActionPreference = "Stop"

$RepoPath = "C:\Github\CherryStock"
$Branch = "main"
$Remote = "origin"

Set-Location $RepoPath

Write-Host "========================================"
Write-Host "CherryStock Git Auto Sync"
Write-Host "========================================"
Write-Host "Repository: $RepoPath"
Write-Host "Branch:     $Branch"
Write-Host "Remote:     $Remote"
Write-Host ""

try {
    Write-Host "[1/5] Git status"
    git status
    if ($LASTEXITCODE -ne 0) { throw "git status failed" }

    Write-Host ""
    Write-Host "[2/5] Commit local changes if any"
    $Changes = git status --porcelain

    if ($Changes) {
        git add .
        if ($LASTEXITCODE -ne 0) { throw "git add failed" }

        $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        git commit -m "auto-sync: $Timestamp"
        if ($LASTEXITCODE -ne 0) { throw "git commit failed" }
    }
    else {
        Write-Host "No local changes to commit."
    }

    Write-Host ""
    Write-Host "[3/5] Fetch remote"
    git fetch $Remote $Branch
    if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }

    Write-Host ""
    Write-Host "[4/5] Pull with rebase"
    git pull --rebase $Remote $Branch
    if ($LASTEXITCODE -ne 0) { throw "git pull --rebase failed" }

    Write-Host ""
    Write-Host "[5/5] Push local branch"
    git push $Remote $Branch
    if ($LASTEXITCODE -ne 0) { throw "git push failed" }

    Write-Host ""
    Write-Host "Git auto sync completed successfully."
}
catch {
    Write-Error "Git auto sync failed: $($_.Exception.Message)"
    exit 1
}
