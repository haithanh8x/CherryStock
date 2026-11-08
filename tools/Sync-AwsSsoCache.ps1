#Requires -Version 5.1
<#
.SYNOPSIS
Download cache.zip with Confluence CLI and refresh the current user's AWS SSO cache.
.DESCRIPTION
Uses CherryVault/ConfluenceApiToken, or an existing CONFLUENCE_API_TOKEN when
-UseEnvironmentToken is supplied. No Chrome, acli, credentials file or token logging.
All JSON files are validated before mutation. Existing files absent from the ZIP
are preserved. Backups contain credentials: keep them private and remove when unneeded.
.EXAMPLE
Unlock-SecretStore
.\tools\Sync-AwsSsoCache.ps1
.EXAMPLE
.\tools\Sync-AwsSsoCache.ps1 -ArchivePath C:\path\cache.zip -TargetDir C:\path\test-cache
#>
[CmdletBinding()]
param(
    [string]$Domain = 'haithanh8x.atlassian.net',
    [string]$Email = 'haithanh8x@gmail.com',
    [ValidatePattern('^\d+$')][string]$PageId = '22413313',
    [string]$Vault = 'CherryVault',
    [string]$SecretName = 'ConfluenceApiToken',
    [string]$TargetDir = (Join-Path $env:USERPROFILE '.aws\sso\cache'),
    [string]$WorkDir = (Join-Path $env:LOCALAPPDATA 'aws-sso-cache-sync'),
    [string]$ArchivePath,
    [switch]$UseEnvironmentToken
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$runDir = $null
$zip = $null
$savedEnvironment = @{}
$environmentNames = @('CONFLUENCE_DOMAIN', 'CONFLUENCE_EMAIL', 'CONFLUENCE_API_TOKEN')

try {
    if ($Domain -notmatch '^[a-zA-Z0-9-]+\.atlassian\.net$') {
        throw 'Domain must be an Atlassian Cloud hostname without protocol or path.'
    }
    $TargetDir = [IO.Path]::GetFullPath($TargetDir)
    $WorkDir = [IO.Path]::GetFullPath($WorkDir)
    if (Test-Path -LiteralPath $TargetDir) {
        if (-not (Test-Path -LiteralPath $TargetDir -PathType Container)) {
            throw 'TargetDir must be a directory.'
        }
        if ((Get-Item -LiteralPath $TargetDir).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'TargetDir must not be a junction or symbolic link.'
        }
    }
    New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
    $runDir = Join-Path $WorkDir ('run-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $runDir | Out-Null

    if ($ArchivePath) {
        $zipPath = (Resolve-Path -LiteralPath $ArchivePath).ProviderPath
    }
    else {
        $cli = Get-Command confluence.cmd -ErrorAction SilentlyContinue
        if (-not $cli) { throw 'confluence-cli is missing. Install with: npm install -g confluence-cli' }
        foreach ($name in $environmentNames) {
            $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        }
        try {
            if ($UseEnvironmentToken) {
                if ([string]::IsNullOrWhiteSpace($env:CONFLUENCE_API_TOKEN)) {
                    throw 'CONFLUENCE_API_TOKEN is empty.'
                }
            }
            else {
                Import-Module Microsoft.PowerShell.SecretManagement -ErrorAction Stop
                try {
                    # No automatic prompt in background sessions; unlock interactively first.
                    $token = Get-Secret -Vault $Vault -Name $SecretName -AsPlainText -ErrorAction Stop
                }
                catch {
                    throw "Cannot read secret '$SecretName' in '$Vault'. Run Unlock-SecretStore in this PowerShell session first."
                }
                if ($token -isnot [string] -or [string]::IsNullOrWhiteSpace($token)) {
                    throw 'The token secret must be a non-empty string or SecureString.'
                }
                $env:CONFLUENCE_API_TOKEN = $token
                $token = $null
            }
            $env:CONFLUENCE_DOMAIN = $Domain
            $env:CONFLUENCE_EMAIL = $Email
            Write-Host "Downloading cache.zip from Confluence page $PageId..."
            # Suppress raw CLI output so credentials/API response bodies cannot enter logs.
            & $cli.Source attachments $PageId -p cache.zip -d --dest $runDir *> $null
            if ($LASTEXITCODE -ne 0) { throw "Confluence download failed (exit $LASTEXITCODE)." }
        }
        finally {
            foreach ($name in $environmentNames) {
                [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process')
            }
            $token = $null
        }
        $zipPath = Join-Path $runDir 'cache.zip'
    }

    if (-not (Test-Path -LiteralPath $zipPath -PathType Leaf)) { throw 'cache.zip was not downloaded.' }
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($zipPath)
    $files = @()
    $seen = @{}
    $totalBytes = 0L
    foreach ($entry in $zip.Entries) {
        $name = $entry.FullName.Replace('\', '/')
        if ($name.StartsWith('/') -or $name -match '(^|/)\.\.(/|$)' -or $name.Contains(':')) {
            throw 'Unsafe path found in ZIP.'
        }
        if ($name.EndsWith('/')) { continue }
        if ($name -match '(^|/)__MACOSX(/|$)|(^|/)\.DS_Store$|(^|/)\._') { continue }
        # Accept flat JSON files or exactly one cache/ wrapper; never write nested paths.
        $fileName = $name -replace '^cache/', ''
        if ($fileName -notmatch '^[a-zA-Z0-9_-]+\.json$') { throw 'ZIP contains an unsupported file or directory layout.' }
        if ($seen.ContainsKey($fileName)) { throw 'ZIP contains duplicate destination filenames.' }
        $seen[$fileName] = $true
        $totalBytes += $entry.Length
        if ($entry.Length -gt 1MB -or $totalBytes -gt 10MB -or $seen.Count -gt 100) {
            throw 'ZIP exceeds cache size limits (1 MB/file, 10 MB total, 100 files).'
        }
        $staged = Join-Path $runDir $fileName
        [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $staged, $false)
        try { $null = Get-Content -LiteralPath $staged -Raw | ConvertFrom-Json -ErrorAction Stop }
        catch { throw 'ZIP contains invalid JSON; target cache was not modified.' }
        $files += [pscustomobject]@{ Name = $fileName; Staged = $staged }
    }
    $zip.Dispose()
    $zip = $null
    if ($files.Count -eq 0) { throw 'ZIP contains no cache JSON files.' }

    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    $backupDir = Join-Path $WorkDir ('backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $backupDir | Out-Null
    foreach ($file in $files) {
        $destination = Join-Path $TargetDir $file.Name
        if (Test-Path -LiteralPath $destination) {
            $item = Get-Item -LiteralPath $destination
            if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                throw 'A destination file is a directory or link; cache was not modified.'
            }
            Copy-Item -LiteralPath $destination -Destination (Join-Path $backupDir $file.Name)
        }
    }
    $written = @()
    try {
        foreach ($file in $files) {
            $destination = Join-Path $TargetDir $file.Name
            $written += $file.Name
            Copy-Item -LiteralPath $file.Staged -Destination $destination -Force
            if ((Get-FileHash -LiteralPath $file.Staged).Hash -ne (Get-FileHash -LiteralPath $destination).Hash) {
                throw 'Post-copy hash verification failed.'
            }
        }
    }
    catch {
        foreach ($name in $written) {
            $backup = Join-Path $backupDir $name
            $destination = Join-Path $TargetDir $name
            if (Test-Path -LiteralPath $backup) { Copy-Item -LiteralPath $backup -Destination $destination -Force }
            else { Remove-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue }
        }
        throw
    }
    Write-Host "Synced $($files.Count) JSON file(s) to $TargetDir (SHA256 verified)."
    Write-Host "Backup: $backupDir. Files absent from the ZIP were preserved."
    Write-Host 'Copy verification does not confirm that the SSO tokens are unexpired or valid on this machine.'
}
finally {
    if ($null -ne $zip) { $zip.Dispose() }
    if ($runDir -and (Test-Path -LiteralPath $runDir)) {
        Remove-Item -LiteralPath $runDir -Recurse -Force
    }
}
