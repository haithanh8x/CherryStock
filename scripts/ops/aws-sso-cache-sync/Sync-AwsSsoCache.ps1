<#
.SYNOPSIS
    Downloads cache.zip from the Confluence "Notes" page (acli sign-in + existing Chrome
    profile) and overwrites C:\Users\ADMIN\.aws\sso\cache.

.DESCRIPTION
    Steps:
      1. Make sure Atlassian CLI (acli) is installed and signed in to haithanh8x.atlassian.net.
      2. Start (or reuse) Chrome with the real user profile "Default" (haithanh8x@gmail.com)
         and the DevTools protocol enabled, so the existing Atlassian session is reused.
      3. Open the Confluence page and download the cache.zip attachment.
      4. Extract the archive and copy every file over the AWS SSO cache folder
         (existing files are overwritten, a timestamped backup is kept).

    acli has no Confluence commands, so it is used for the Atlassian sign-in only; the
    attachment itself is downloaded through the authenticated Chrome session.

    If the Atlassian session has expired, the script waits for you to sign in inside the
    Chrome window that it opens (the Google account is already remembered in the profile).

.EXAMPLE
    .\Sync-AwsSsoCache.ps1

.EXAMPLE
    .\Sync-AwsSsoCache.ps1 -SkipAcli -NoBackup -CloseChromeAfter
#>
[CmdletBinding()]
param(
    [string]$PageUrl        = 'https://haithanh8x.atlassian.net/wiki/spaces/~5d08d9598b079d0bca82f91d/pages/22413313/Notes',
    [string]$Attachment     = 'cache.zip',
    [string]$TargetDir      = 'C:\Users\ADMIN\.aws\sso\cache',
    [string]$Site           = 'haithanh8x.atlassian.net',
    [string]$ChromeUserData = "$env:LOCALAPPDATA\Google\Chrome\User Data",
    [string]$ChromeProfile  = 'Default',
    [string]$ChromeExe      = 'C:\Program Files\Google\Chrome\Application\chrome.exe',
    [string]$CdpUrl         = 'http://127.0.0.1:9222',
    [int]$CdpPort           = 9222,
    [string]$WorkDir        = "$env:LOCALAPPDATA\aws-sso-cache-sync",
    [int]$LoginTimeoutMin   = 5,
    [int]$AcliTimeoutSec    = 120,
    [switch]$SkipAcli,
    [switch]$NoBackup,
    [switch]$NoCloseChrome,
    [switch]$CloseChromeAfter,
    [switch]$KeepTemp,
    [switch]$IncludeMacMetadata
)

$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'SilentlyContinue'

function Write-Step { param([string]$Message) Write-Host "`n=== $Message ===" -ForegroundColor Cyan }
function Write-Info { param([string]$Message) Write-Host "[info] $Message" -ForegroundColor Gray }
function Write-Ok   { param([string]$Message) Write-Host "[ok]   $Message" -ForegroundColor Green }
function Write-Warn { param([string]$Message) Write-Host "[warn] $Message" -ForegroundColor Yellow }

# ------------------------------------------------------------------ acli
function Resolve-Acli {
    $cmd = Get-Command acli -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    foreach ($candidate in @(
            "$env:LOCALAPPDATA\Programs\Atlassian\acli\acli.exe",
            "$env:ProgramFiles\Atlassian\acli\acli.exe")) {
        if (Test-Path $candidate) { return $candidate }
    }

    $wingetCopy = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter 'acli.exe' -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
    if ($wingetCopy) { return $wingetCopy }

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { return $null }
    Write-Info 'acli not found - installing Atlassian.AtlassianCLI with winget...'
    winget install --id Atlassian.AtlassianCLI -e --silent --accept-source-agreements --accept-package-agreements | Out-Host

    $cmd = Get-Command acli -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($candidate in @(
            "$env:LOCALAPPDATA\Programs\Atlassian\acli\acli.exe",
            "$env:ProgramFiles\Atlassian\acli\acli.exe")) {
        if (Test-Path $candidate) { return $candidate }
    }
    $wingetCopy = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter 'acli.exe' -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
    if ($wingetCopy) { return $wingetCopy }
    return $null
}

function Invoke-AcliLogin {
    # acli writes normal status output to stderr; do not let that abort the script.
    $ErrorActionPreference = 'Continue'

    if (Test-Cdp) {
        Write-Warn "Chrome is already running with the automation profile on $CdpUrl, so acli cannot open a browser."
        Write-Warn "Skipping the acli sign-in step (the download still uses the Chrome session)."
        return
    }

    $acli = Resolve-Acli
    if (-not $acli) {
        Write-Warn 'acli is not available - skipping the acli sign-in step.'
        return
    }

    Write-Info "acli: $acli"
    & $acli --version 2>&1 | Out-Host

    $status = & $acli jira auth status 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0) {
        Write-Ok 'acli is already signed in.'
        $status.Trim() | Out-Host
        return
    }

    Write-Info "Signing in to $Site - a browser window will open (choose the haithanh8x@gmail.com profile)."
    $proc = Start-Process -FilePath $acli -ArgumentList @('jira', 'auth', 'login', '--web', '--site', $Site) -PassThru -WindowStyle Hidden
    if (-not $proc.WaitForExit($AcliTimeoutSec * 1000)) {
        Write-Warn "acli sign-in did not finish within $AcliTimeoutSec s - stopping it."
        try { $proc.Kill() } catch { }
        Start-Sleep -Seconds 1
    }

    $status = & $acli jira auth status 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0) {
        Write-Ok 'acli sign-in completed.'
        $status.Trim() | Out-Host
    }
    else {
        Write-Warn 'acli is still not signed in; continuing because the download uses the Chrome session.'
        Write-Warn "Run 'acli jira auth login --web' manually once, or use -SkipAcli."
    }
}

# ------------------------------------------------------------------ chrome / CDP
function Test-Cdp {
    try {
        $null = Invoke-WebRequest -Uri "$CdpUrl/json/version" -UseBasicParsing -TimeoutSec 3
        return $true
    }
    catch { return $false }
}

function Stop-ChromeGracefully {
    $procs = Get-Process chrome -ErrorAction SilentlyContinue
    if (-not $procs) { return }
    Write-Info 'Closing Chrome so the profile can be reused with the DevTools protocol...'
    $procs | ForEach-Object { $null = $_.CloseMainWindow() }
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 500
        if (-not (Get-Process chrome -ErrorAction SilentlyContinue)) { return }
    }
    Write-Warn 'Chrome did not close in time - forcing it to stop.'
    Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

function Start-CdpChrome {
    if (Test-Cdp) {
        Write-Ok "Reusing the Chrome instance already listening on $CdpUrl"
        return $false
    }

    if (Get-Process chrome -ErrorAction SilentlyContinue) {
        if ($NoCloseChrome) {
            throw "Chrome is running without the DevTools protocol on $CdpUrl. Close Chrome and run again, or drop -NoCloseChrome."
        }
        Stop-ChromeGracefully
    }

    if (-not (Test-Path $ChromeExe)) {
        $ChromeExe = @(
            "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
            "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
            "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
        ) | Where-Object { Test-Path $_ } | Select-Object -First 1
        if (-not $ChromeExe) { throw 'chrome.exe not found.' }
    }

    # Chrome 136+ refuses --remote-debugging-port on the default user-data-dir.
    # A directory junction gives it a non-default path while keeping the same profile.
    $link = Join-Path $env:LOCALAPPDATA 'chrome-cdp-profile'
    if (-not (Test-Path $link)) {
        Write-Info "Creating profile junction $link -> $ChromeUserData"
        cmd /c mklink /J "$link" "$ChromeUserData" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Could not create the junction $link" }
    }

    Write-Info "Starting Chrome with profile '$ChromeProfile' and DevTools on port $CdpPort..."
    Start-Process -FilePath $ChromeExe -ArgumentList @(
        "--user-data-dir=`"$link`"",
        "--profile-directory=$ChromeProfile",
        "--remote-debugging-port=$CdpPort",
        '--no-first-run',
        '--no-default-browser-check',
        'about:blank'
    ) | Out-Null

    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 500
        if (Test-Cdp) { Write-Ok 'Chrome is ready.'; return $true }
    }
    throw "Chrome did not expose the DevTools protocol on $CdpUrl"
}

# ------------------------------------------------------------------ helpers
function Install-NodeDeps {
    param([string]$ScriptDir)
    if (Test-Path (Join-Path $ScriptDir 'node_modules\playwright-core')) { return }
    Write-Info 'Installing playwright-core (no browser download - uses the installed Chrome)...'
    Push-Location $ScriptDir
    try {
        npm install --no-audit --no-fund --silent | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'npm install failed' }
    }
    finally { Pop-Location }
    Write-Ok 'playwright-core installed.'
}

function Get-FileHashSafe {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $null }
    (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
}

# ------------------------------------------------------------------ main
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null

Write-Step 'Step 1/5 - Atlassian sign-in (acli)'
if ($SkipAcli) { Write-Info 'Skipped (-SkipAcli).' } else { Invoke-AcliLogin }

Write-Step 'Step 2/5 - Prepare Chrome with the existing profile'
$startedChrome = Start-CdpChrome

Write-Step 'Step 3/5 - Download the attachment'
Install-NodeDeps -ScriptDir $scriptDir

$zipPath = Join-Path $WorkDir $Attachment
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

& node (Join-Path $scriptDir 'download-attachment.mjs') `
    --page-url $PageUrl `
    --attachment $Attachment `
    --out $zipPath `
    --cdp $CdpUrl `
    --timeout-min "$LoginTimeoutMin"

if ($LASTEXITCODE -ne 0) { throw "Attachment download failed (exit code $LASTEXITCODE)." }
if (-not (Test-Path $zipPath)) { throw "Downloaded file not found: $zipPath" }
Write-Ok ("Downloaded {0} ({1:N0} bytes)" -f $zipPath, (Get-Item $zipPath).Length)

Write-Step 'Step 4/5 - Extract and overwrite the AWS SSO cache'
$extractDir = Join-Path $WorkDir 'extract'
if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir -Force
Write-Info "Extracted to $extractDir"

# The archive usually wraps everything in a single "cache" folder - use it as the source root.
$sourceRoot = $extractDir
$rootItems = @(Get-ChildItem -LiteralPath $extractDir -Force)
$rootDirs  = @($rootItems | Where-Object PSIsContainer)
$rootFiles = @($rootItems | Where-Object { -not $_.PSIsContainer })
if ($rootFiles.Count -eq 0 -and $rootDirs.Count -eq 1) {
    $sourceRoot = $rootDirs[0].FullName
    Write-Info "Using the archive subfolder '$($rootDirs[0].Name)' as the source root"
}

if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
    Write-Info "Created target directory $TargetDir"
}

if (-not $NoBackup) {
    $backupDir = Join-Path $WorkDir ("backup-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    Copy-Item -Path (Join-Path $TargetDir '*') -Destination $backupDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Info "Backup of the previous cache: $backupDir"
}

$copied = 0
$changed = 0
Get-ChildItem -LiteralPath $sourceRoot -Recurse -File | Where-Object {
    if ($IncludeMacMetadata) { return $true }
    $_.FullName -notmatch '\\__MACOSX\\' -and $_.Name -ne '.DS_Store' -and -not $_.Name.StartsWith('._')
} | ForEach-Object {
    $relative    = $_.FullName.Substring($sourceRoot.Length).TrimStart('\', '/')
    $destination = Join-Path $TargetDir $relative
    $destDir     = Split-Path -Parent $destination
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Force -Path $destDir | Out-Null }

    $before = Get-FileHashSafe -Path $destination
    $after  = Get-FileHashSafe -Path $_.FullName
    Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
    $copied++
    if ($before -ne $after) { $changed++; Write-Verbose "updated $relative" }
    else { Write-Verbose "unchanged $relative" }
}

if ($copied -eq 0) { throw "The archive $Attachment contained no files." }
Write-Ok ("Copied {0} file(s) into {1} ({2} changed)" -f $copied, $TargetDir, $changed)

Write-Step 'Step 5/5 - Verify'
Get-ChildItem -LiteralPath $TargetDir -File | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize | Out-Host
$jsonCount = (Get-ChildItem -LiteralPath $TargetDir -Filter '*.json' -File).Count
Write-Ok ("Target folder now contains {0} json file(s)." -f $jsonCount)

if (-not $KeepTemp) {
    Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
}

if ($CloseChromeAfter -and $startedChrome) {
    Write-Info 'Closing the Chrome instance started by this script...'
    Stop-ChromeGracefully
}

Write-Host "`nDone. AWS SSO cache refreshed from $PageUrl" -ForegroundColor Green
if ($startedChrome -and -not $CloseChromeAfter) {
    Write-Info "Chrome is left running on port $CdpPort so the next run can reuse the session."
}
exit 0
