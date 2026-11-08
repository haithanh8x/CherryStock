param(
    [string]$GitExe,
    [switch]$PreflightOnly
)

$ErrorActionPreference = "Stop"

$RepoPath = Split-Path -Parent $PSScriptRoot
$Branch = "main"
$Remote = "origin"

Set-Location $RepoPath

function Resolve-GitExecutable {
    if ($GitExe) {
        if (-not (Test-Path -LiteralPath $GitExe -PathType Leaf)) {
            throw "Specified Git executable does not exist: $GitExe"
        }
        & $GitExe --version | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Specified Git executable could not run: $GitExe" }
        return (Get-Item -LiteralPath $GitExe).FullName
    }

    $candidates = @()
    foreach ($root in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if ($root) { $candidates += Join-Path $root 'Git\cmd\git.exe' }
    }
    # SSH sessions can have different access to Scoop's current junction.
    # Use physical version directories, never the shim or current link.
    $scoopRoot = if ($env:SCOOP) { $env:SCOOP } else { Join-Path $env:USERPROFILE 'scoop' }
    $versions = @(Get-ChildItem -LiteralPath (Join-Path $scoopRoot 'apps\git') -Directory -ErrorAction SilentlyContinue |
        Where-Object { -not ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) } |
        Sort-Object LastWriteTime -Descending)
    foreach ($version in $versions) {
        $candidates += Join-Path $version.FullName 'cmd\git.exe'
    }
    $candidates += @(Get-Command git.exe -CommandType Application -All -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -notmatch '[\\/]scoop[\\/]shims[\\/]|[\\/]current[\\/]' } |
        Select-Object -ExpandProperty Source)

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            & $candidate --version | Out-Null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        }
    }
    throw 'No runnable Git executable found. In this SSH session, check access to the physical Git installation or specify -GitExe. No sync was performed.'
}

Write-Host "========================================"
Write-Host "CherryStock Git Auto Sync"
Write-Host "========================================"
Write-Host "Repository: $RepoPath"
Write-Host "Branch:     $Branch"
Write-Host "Remote:     $Remote"
Write-Host ""

function Test-GitPathExists {
    param([Parameter(Mandatory = $true)][string]$GitPathName)

    $ResolvedGitPath = & $script:GitExecutable rev-parse --git-path $GitPathName 2>$null
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
        & $script:GitExecutable status
        Write-Host ""

        $Unmerged = & $script:GitExecutable diff --name-only --diff-filter=U
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
    $script:GitExecutable = Resolve-GitExecutable
    Write-Host "Git executable: $script:GitExecutable"
    Write-Host "[0/6] Preflight Git state"
    & $script:GitExecutable rev-parse --is-inside-work-tree | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Not inside a Git work tree" }

    Assert-NoInProgressGitOperation

    $CurrentBranch = & $script:GitExecutable branch --show-current
    if ($LASTEXITCODE -ne 0) { throw "Unable to determine current branch" }
    if ($CurrentBranch -ne $Branch) {
        throw "Current branch is '$CurrentBranch', expected '$Branch'. Switch to '$Branch' before auto-sync."
    }

    Write-Host "Git preflight passed."
    if ($PreflightOnly) {
        Write-Host 'Preflight-only: no add, commit, fetch, rebase or push performed.'
        return
    }

    Write-Host ""
    Write-Host "[1/6] Git status"
    & $script:GitExecutable status
    if ($LASTEXITCODE -ne 0) { throw "git status failed" }

    Write-Host ""
    Write-Host "[2/6] Commit local changes if any"
    $Changes = & $script:GitExecutable status --porcelain
    if ($LASTEXITCODE -ne 0) { throw "git status --porcelain failed" }

    if ($Changes) {
        & $script:GitExecutable add .
        if ($LASTEXITCODE -ne 0) { throw "git add failed" }

        $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        & $script:GitExecutable commit -m "auto-sync: $Timestamp"
        if ($LASTEXITCODE -ne 0) { throw "git commit failed" }
    }
    else {
        Write-Host "No local changes to commit."
    }

    Write-Host ""
    Write-Host "[3/6] Fetch remote"
    & $script:GitExecutable fetch $Remote
    if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }

    Write-Host ""
    Write-Host "[4/6] Rebase local branch onto $Remote/$Branch"
    & $script:GitExecutable rebase "$Remote/$Branch"
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Rebase did not complete. Inspect with: git status" -ForegroundColor Yellow
        Write-Host "After resolving conflicts: git add <files>; git rebase --continue" -ForegroundColor Yellow
        Write-Host "To cancel: git rebase --abort" -ForegroundColor Yellow
        throw "git rebase $Remote/$Branch failed"
    }

    Write-Host ""
    Write-Host "[5/6] Push local branch"
    & $script:GitExecutable push $Remote $Branch
    if ($LASTEXITCODE -ne 0) { throw "git push failed" }

    Write-Host ""
    Write-Host "[6/6] Final status"
    & $script:GitExecutable status --short --branch
    if ($LASTEXITCODE -ne 0) { throw "final git status failed" }

    Write-Host ""
    Write-Host "Git auto sync completed successfully."
}
catch {
    Write-Error "Git auto sync failed: $($_.Exception.Message)" -ErrorAction Continue
    exit 1
}
