Set-StrictMode -Version Latest

function Find-DrawioExecutable {
    [CmdletBinding()]
    param()

    $candidates = New-Object System.Collections.Generic.List[string]

    $cmd = Get-Command "drawio" -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
        [void]$candidates.Add([string]$cmd.Source)
    }

    [void]$candidates.Add("C:\Program Files\draw.io\draw.io.exe")

    if ($env:LOCALAPPDATA) {
        [void]$candidates.Add((Join-Path $env:LOCALAPPDATA "Programs\draw.io\draw.io.exe"))
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    return $null
}

function Wait-DrawioOutputFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$TimeoutSeconds = 30,
        [int]$PollMilliseconds = 250
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $lastLength = -1L
    $stableReads = 0

    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-Path -LiteralPath $Path -PathType Leaf) {
            $item = Get-Item -LiteralPath $Path -ErrorAction SilentlyContinue
            if ($item -and $item.Length -gt 0) {
                if ($item.Length -eq $lastLength) {
                    $stableReads++
                }
                else {
                    $lastLength = $item.Length
                    $stableReads = 0
                }

                # Require two consecutive stable reads so we do not consume a file
                # while Electron is still flushing it to disk.
                if ($stableReads -ge 2) {
                    return $item
                }
            }
        }

        Start-Sleep -Milliseconds $PollMilliseconds
    }

    return $null
}

function Test-DrawioPngFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $false
    }

    $item = Get-Item -LiteralPath $Path -ErrorAction SilentlyContinue
    if (-not $item -or $item.Length -lt 8) {
        return $false
    }

    $expected = [byte[]](0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A)
    $buffer = New-Object byte[] 8
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
        $read = $stream.Read($buffer, 0, 8)
    }
    finally {
        $stream.Dispose()
    }

    if ($read -ne 8) {
        return $false
    }

    for ($i = 0; $i -lt 8; $i++) {
        if ($buffer[$i] -ne $expected[$i]) {
            return $false
        }
    }

    return $true
}

function Invoke-DrawioPngExport {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$InputPath,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [string]$DrawioExe,
        [int]$TimeoutSeconds = 30,
        [switch]$Transparent,
        [int]$Width = 0
    )

    if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) {
        throw "Draw.io input file not found: $InputPath"
    }

    $resolvedInput = (Resolve-Path -LiteralPath $InputPath).Path

    if (-not $DrawioExe) {
        $DrawioExe = Find-DrawioExecutable
    }
    if (-not $DrawioExe -or -not (Test-Path -LiteralPath $DrawioExe -PathType Leaf)) {
        throw "Draw.io Desktop CLI was not found."
    }
    $DrawioExe = (Resolve-Path -LiteralPath $DrawioExe).Path

    $outputDirectory = Split-Path -Parent $OutputPath
    if (-not $outputDirectory) {
        $outputDirectory = (Get-Location).Path
        $OutputPath = Join-Path $outputDirectory $OutputPath
    }
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

    if (Test-Path -LiteralPath $OutputPath) {
        Remove-Item -LiteralPath $OutputPath -Force
    }

    # draw.io Desktop is an Electron single-instance application. Its source
    # calls app.requestSingleInstanceLock() and a second instance exits cleanly
    # without performing CLI export. A unique Chromium user-data-dir gives this
    # export process its own singleton namespace and makes CLI export reliable
    # even while the normal draw.io GUI is already open.
    $profileDir = Join-Path ([System.IO.Path]::GetTempPath()) ("cherrystock-drawio-profile-" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null

    $args = New-Object System.Collections.Generic.List[string]
    [void]$args.Add("--user-data-dir=$profileDir")
    [void]$args.Add("--export")
    [void]$args.Add("--format")
    [void]$args.Add("png")
    [void]$args.Add("--output")
    [void]$args.Add($OutputPath)

    if ($Transparent) {
        [void]$args.Add("--transparent")
    }
    if ($Width -gt 0) {
        [void]$args.Add("--width")
        [void]$args.Add([string]$Width)
    }

    [void]$args.Add($resolvedInput)

    try {
        $runningDrawio = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -in @("draw.io", "drawio") })
        if ($runningDrawio.Count -gt 0) {
            Write-Verbose ("Detected {0} existing draw.io process(es); isolated user-data-dir will avoid the single-instance lock." -f $runningDrawio.Count)
        }

        Write-Verbose ("Draw.io executable: {0}" -f $DrawioExe)
        Write-Verbose ("Draw.io isolated profile: {0}" -f $profileDir)
        Write-Verbose ("Draw.io output: {0}" -f $OutputPath)

        & $DrawioExe @args
        $exitCode = $LASTEXITCODE

        if ($exitCode -ne 0) {
            throw "Draw.io export failed with exit code $exitCode"
        }

        $output = Wait-DrawioOutputFile -Path $OutputPath -TimeoutSeconds $TimeoutSeconds
        if (-not $output) {
            $message = ("Draw.io returned exit code 0 but no stable PNG was created within {0}s. The export was isolated from any running GUI instance via --user-data-dir. Executable='{1}', input='{2}', output='{3}', profile='{4}'." -f $TimeoutSeconds, $DrawioExe, $resolvedInput, $OutputPath, $profileDir)
            throw $message
        }

        if (-not (Test-DrawioPngFile -Path $OutputPath)) {
            throw "Draw.io created an output file, but it does not have a valid PNG signature: $OutputPath"
        }

        return [PSCustomObject]@{
            Path       = $output.FullName
            Bytes      = $output.Length
            ExitCode   = $exitCode
            DrawioExe  = $DrawioExe
            InputPath  = $resolvedInput
            ProfileDir = $profileDir
            PngValid   = $true
        }
    }
    finally {
        # Remove only the dedicated temporary profile created by this function.
        if (Test-Path -LiteralPath $profileDir) {
            Remove-Item -LiteralPath $profileDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

Export-ModuleMember -Function Find-DrawioExecutable, Wait-DrawioOutputFile, Test-DrawioPngFile, Invoke-DrawioPngExport
