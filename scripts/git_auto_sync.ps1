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

function Test-GitPathExists {
    param([Parameter(Mandatory = $true)][string]$GitPathName)

    $ResolvedGitPath = git rev-parse --git-path $GitPathName 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $ResolvedGitPath) {
        return $false
    }

    return Test-Path $ResolvedGitPath
}

function Assert-NoInProgressGitOperation {
    $RebaseMerge = Test-GitPathExists "rebase-merge"
    $RebaseApply = Test-GitPathExists "rebase-apply"
    $MergeHead = Test-GitPathExists "MERGE_HEAD"
    $CherryPickHead = Test-GitPathExists "CHERRY_PICK_HEAD"
    $RevertHead = Test-GitPathExists "REVERT_HEAD"

    if ($RebaseMerge -or $RebaseApply) {
        Write-Host ""
        Write-Host "An existing rebase is already in progress." -ForegroundColor Yellow
        git status
        Write-Host ""

        $Unmerged = git diff --name-only --diff-filter=U
        if ($Unmerged) {
            Write-Host "Resolve these conflicted files first:" -ForegroundColor Yellow
            $Unmerged | ForEach-Object { Write-Host "  $_" }
            Write-Host "Then run:" -ForegroundColor Yellow
            Write-Host "  git add <resolved-files>"
            Write-Host "  git rebase --continue"
        }
        else {
            Write-Host "No unresolved conflicts were detected." -ForegroundColor Yellow
            Write-Host "Complete or cancel the existing rebase before auto-sync:" -ForegroundColor Yellow
            Write-Host "  git rebase --continue"
            Write-Host "or"
            Write-Host "  git rebase --abort"
        }

        throw "Existing rebase detected. Auto-sync will not start a nested rebase."
    }

    if ($MergeHead) {
        throw "A merge is in progress. Complete it with git commit, or cancel it with git merge --abort, then rerun auto-sync."
    }

    if ($CherryPickHead) {
        throw "A cherry-pick is in progress. Complete it with git cherry-pick --continue, or cancel it with git cherry-pick --abort, then rerun auto-sync."
    }

    if ($RevertHead) {
        throw "A revert is in progress. Complete it with git revert --continue, or cancel it with git revert --abort, then rerun auto-sync."
    }
}

try {
    Write-Host "[0/6] Preflight Git state"
    git rev-parse --is-inside-work-tree | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Not inside a Git work tree" }

    Assert-NoInProgressGitOperation

    $CurrentBranch = git branch --show-current
    if ($LASTEXITCODE -ne 0) { throw "Unable to determine current branch" }
    if ($CurrentBranch -ne $Branch) {
        throw "Current branch is '$CurrentBranch', expected '$Branch'. Switch to '$Branch' before auto-sync."
    }

    Write-Host "Git preflight passed."

    Write-Host ""
    Write-Host "[1/6] Git status"
    git status
    if ($LASTEXITCODE -ne 0) { throw "git status failed" }

    Write-Host ""
    Write-Host "[2/6] Commit local changes if any"
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
    Write-Host "[3/6] Fetch remote"
    git fetch $Remote
    if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }

    Write-Host ""
    Write-Host "[4/6] Rebase local branch onto $Remote/$Branch"
    git rebase "$Remote/$Branch"
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Rebase did not complete. Inspect with: git status" -ForegroundColor Yellow
        Write-Host "After resolving conflicts: git add <files>; git rebase --continue" -ForegroundColor Yellow
        Write-Host "To cancel: git rebase --abort" -ForegroundColor Yellow
        throw "git rebase $Remote/$Branch failed"
    }

    Write-Host ""
    Write-Host "[5/6] Push local branch"
    git push $Remote $Branch
    if ($LASTEXITCODE -ne 0) { throw "git push failed" }

    Write-Host ""
    Write-Host "[6/6] Final status"
    git status --short --branch
    if ($LASTEXITCODE -ne 0) { throw "final git status failed" }

    Write-Host ""
    Write-Host "Git auto sync completed successfully."
}
catch {
    Write-Error "Git auto sync failed: $($_.Exception.Message)"
    exit 1
}
