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

function Get-DrawioExecutableInfo {
    [CmdletBinding()]
    param(
        [string]$DrawioExe
    )

    if (-not $DrawioExe) {
        $DrawioExe = Find-DrawioExecutable
    }
    if (-not $DrawioExe -or -not (Test-Path -LiteralPath $DrawioExe -PathType Leaf)) {
        return $null
    }

    $resolved = (Resolve-Path -LiteralPath $DrawioExe).Path
    $item = Get-Item -LiteralPath $resolved

    return [PSCustomObject]@{
        Path           = $resolved
        FileVersion    = $item.VersionInfo.FileVersion
        ProductVersion = $item.VersionInfo.ProductVersion
    }
}

function Wait-DrawioOutputFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$TimeoutSeconds = 5,
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

function Quote-DrawioNativeArgument {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ($Value.Contains('"')) {
        throw "Native argument contains an unsupported quote character: $Value"
    }

    if ($Value -match '\s') {
        return '"' + $Value + '"'
    }

    return $Value
}

function Invoke-DrawioProcessAttempt {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$DrawioExe,
        [Parameter(Mandatory = $true)][string]$InputPath,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [Parameter(Mandatory = $true)][string]$Strategy,
        [int]$TimeoutSeconds = 30,
        [switch]$Transparent,
        [int]$Width = 0,
        [switch]$UseIsolatedProfile,
        [switch]$DisableGpu
    )

    if (Test-Path -LiteralPath $OutputPath) {
        Remove-Item -LiteralPath $OutputPath -Force
    }

    $profileDir = $null
    if ($UseIsolatedProfile) {
        $profileDir = Join-Path ([System.IO.Path]::GetTempPath()) ("cherrystock-drawio-profile-" + [Guid]::NewGuid().ToString("N"))
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }

    $tokens = New-Object System.Collections.Generic.List[string]

    if ($UseIsolatedProfile) {
        [void]$tokens.Add(("--user-data-dir={0}" -f (Quote-DrawioNativeArgument $profileDir)))
    }
    if ($DisableGpu) {
        [void]$tokens.Add("--disable-gpu")
    }

    [void]$tokens.Add("--disable-update")
    [void]$tokens.Add("--export")
    [void]$tokens.Add("--format")
    [void]$tokens.Add("png")
    [void]$tokens.Add("--output")
    [void]$tokens.Add((Quote-DrawioNativeArgument $OutputPath))

    if ($Transparent) {
        [void]$tokens.Add("--transparent")
    }
    if ($Width -gt 0) {
        [void]$tokens.Add("--width")
        [void]$tokens.Add([string]$Width)
    }

    [void]$tokens.Add((Quote-DrawioNativeArgument $InputPath))
    $argumentLine = $tokens -join ' '

    $process = $null
    $startedAt = Get-Date

    try {
        Write-Verbose ("Draw.io strategy: {0}" -f $Strategy)
        Write-Verbose ("Draw.io command: {0} {1}" -f $DrawioExe, $argumentLine)

        # draw.io.exe is a Windows GUI/Electron executable. The PowerShell call
        # operator can return before a GUI process finishes. Start-Process plus
        # WaitForExit binds validation to the actual native process lifecycle.
        $process = Start-Process -FilePath $DrawioExe -ArgumentList $argumentLine -PassThru

        $finished = $process.WaitForExit([Math]::Max(1, $TimeoutSeconds) * 1000)
        if (-not $finished) {
            try {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
            catch {
                # Best-effort cleanup only.
            }

            return [PSCustomObject]@{
                Strategy   = $Strategy
                Success    = $false
                ExitCode   = $null
                TimedOut   = $true
                OutputPath = $OutputPath
                ProfileDir = $profileDir
                Error      = "Draw.io process did not exit within ${TimeoutSeconds}s."
                ElapsedMs  = [int]((Get-Date) - $startedAt).TotalMilliseconds
            }
        }

        $process.Refresh()
        $exitCode = $process.ExitCode

        if ($exitCode -ne 0) {
            return [PSCustomObject]@{
                Strategy   = $Strategy
                Success    = $false
                ExitCode   = $exitCode
                TimedOut   = $false
                OutputPath = $OutputPath
                ProfileDir = $profileDir
                Error      = "Draw.io process exited with code $exitCode."
                ElapsedMs  = [int]((Get-Date) - $startedAt).TotalMilliseconds
            }
        }

        $output = Wait-DrawioOutputFile -Path $OutputPath -TimeoutSeconds 5
        if (-not $output) {
            return [PSCustomObject]@{
                Strategy   = $Strategy
                Success    = $false
                ExitCode   = $exitCode
                TimedOut   = $false
                OutputPath = $OutputPath
                ProfileDir = $profileDir
                Error      = "Draw.io exited 0 but did not create a stable output file."
                ElapsedMs  = [int]((Get-Date) - $startedAt).TotalMilliseconds
            }
        }

        if (-not (Test-DrawioPngFile -Path $OutputPath)) {
            return [PSCustomObject]@{
                Strategy   = $Strategy
                Success    = $false
                ExitCode   = $exitCode
                TimedOut   = $false
                OutputPath = $OutputPath
                ProfileDir = $profileDir
                Error      = "Draw.io created a file without a valid PNG signature."
                ElapsedMs  = [int]((Get-Date) - $startedAt).TotalMilliseconds
            }
        }

        return [PSCustomObject]@{
            Strategy   = $Strategy
            Success    = $true
            ExitCode   = $exitCode
            TimedOut   = $false
            OutputPath = $output.FullName
            ProfileDir = $profileDir
            Bytes      = $output.Length
            Error      = $null
            ElapsedMs  = [int]((Get-Date) - $startedAt).TotalMilliseconds
        }
    }
    finally {
        if ($process) {
            $process.Dispose()
        }
        if ($profileDir -and (Test-Path -LiteralPath $profileDir)) {
            Remove-Item -LiteralPath $profileDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
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

    $runningDrawio = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -in @("draw.io", "drawio") })
    $attempts = @()

    if ($runningDrawio.Count -eq 0) {
        $attempts += [PSCustomObject]@{ Name = "documented-cli"; Isolated = $false; DisableGpu = $false }
    }

    $attempts += [PSCustomObject]@{ Name = "isolated-profile"; Isolated = $true; DisableGpu = $false }
    $attempts += [PSCustomObject]@{ Name = "isolated-profile-disable-gpu"; Isolated = $true; DisableGpu = $true }

    $diagnostics = New-Object System.Collections.Generic.List[object]
    $showVerbose = ($VerbosePreference -ne [System.Management.Automation.ActionPreference]::SilentlyContinue)

    foreach ($attempt in $attempts) {
        $result = Invoke-DrawioProcessAttempt `
            -DrawioExe $DrawioExe `
            -InputPath $resolvedInput `
            -OutputPath $OutputPath `
            -Strategy $attempt.Name `
            -TimeoutSeconds $TimeoutSeconds `
            -Transparent:$Transparent `
            -Width $Width `
            -UseIsolatedProfile:$attempt.Isolated `
            -DisableGpu:$attempt.DisableGpu `
            -Verbose:$showVerbose

        [void]$diagnostics.Add($result)

        if ($result.Success) {
            $info = Get-DrawioExecutableInfo -DrawioExe $DrawioExe
            return [PSCustomObject]@{
                Path           = $result.OutputPath
                Bytes          = $result.Bytes
                ExitCode       = $result.ExitCode
                DrawioExe      = $DrawioExe
                FileVersion    = if ($info) { $info.FileVersion } else { $null }
                ProductVersion = if ($info) { $info.ProductVersion } else { $null }
                InputPath      = $resolvedInput
                Strategy       = $result.Strategy
                ElapsedMs      = $result.ElapsedMs
                PngValid       = $true
            }
        }
    }

    $info = Get-DrawioExecutableInfo -DrawioExe $DrawioExe
    $summary = ($diagnostics | ForEach-Object {
        "[{0}] exit={1}; timeout={2}; elapsedMs={3}; error={4}" -f $_.Strategy, $_.ExitCode, $_.TimedOut, $_.ElapsedMs, $_.Error
    }) -join " | "

    $versionText = if ($info) { "fileVersion='$($info.FileVersion)', productVersion='$($info.ProductVersion)'" } else { "version=unknown" }
    $runningText = if ($runningDrawio.Count -gt 0) { "$($runningDrawio.Count) draw.io process(es) were already running" } else { "no draw.io GUI process was detected before export" }

    throw ("Draw.io native PNG export failed after all deterministic strategies. Executable='{0}', {1}, {2}, input='{3}', output='{4}'. Diagnostics: {5}" -f $DrawioExe, $versionText, $runningText, $resolvedInput, $OutputPath, $summary)
}

function Test-DrawioNativeExportCapability {
    [CmdletBinding()]
    param(
        [string]$DrawioExe,
        [int]$TimeoutSeconds = 30
    )

    if (-not $DrawioExe) {
        $DrawioExe = Find-DrawioExecutable
    }
    if (-not $DrawioExe) {
        throw "Draw.io Desktop CLI was not found."
    }

    $probeRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("cherrystock-drawio-probe-" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $probeRoot -Force | Out-Null
    $probeDrawio = Join-Path $probeRoot "probe.drawio"
    $probePng = Join-Path $probeRoot "probe.png"

    # shadow=0 is deliberate. draw.io Desktop has a documented Windows CLI bug
    # where mxGraphModel shadow=1 can exit 0 without producing PNG output.
    $probeXml = @'
<mxfile host="app.diagrams.net">
  <diagram id="probe" name="Page-1">
    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="probe-box" value="CherryStock Draw.io CLI Probe" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="1">
          <mxGeometry x="80" y="80" width="260" height="80" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
'@

    try {
        Set-Content -LiteralPath $probeDrawio -Value $probeXml -Encoding UTF8
        $showVerbose = ($VerbosePreference -ne [System.Management.Automation.ActionPreference]::SilentlyContinue)
        $result = Invoke-DrawioPngExport -InputPath $probeDrawio -OutputPath $probePng -DrawioExe $DrawioExe -TimeoutSeconds $TimeoutSeconds -Verbose:$showVerbose

        if (-not (Test-DrawioPngFile -Path $probePng)) {
            throw "Native export probe produced an invalid PNG: $probePng"
        }

        return [PSCustomObject]@{
            Status         = "PASS"
            DrawioExe      = $result.DrawioExe
            FileVersion    = $result.FileVersion
            ProductVersion = $result.ProductVersion
            Strategy       = $result.Strategy
            ElapsedMs      = $result.ElapsedMs
            Bytes          = $result.Bytes
        }
    }
    finally {
        if (Test-Path -LiteralPath $probeRoot) {
            Remove-Item -LiteralPath $probeRoot -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

Export-ModuleMember -Function Find-DrawioExecutable, Get-DrawioExecutableInfo, Wait-DrawioOutputFile, Test-DrawioPngFile, Invoke-DrawioPngExport, Test-DrawioNativeExportCapability
