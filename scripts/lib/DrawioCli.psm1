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
    param([string]$DrawioExe)

    if (-not $DrawioExe) { $DrawioExe = Find-DrawioExecutable }
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
        [int]$TimeoutSeconds = 10,
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

                if ($stableReads -ge 2) { return $item }
            }
        }
        Start-Sleep -Milliseconds $PollMilliseconds
    }

    return $null
}

function Test-DrawioPngFile {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }

    $item = Get-Item -LiteralPath $Path -ErrorAction SilentlyContinue
    if (-not $item -or $item.Length -lt 8) { return $false }

    $expected = [byte[]](0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A)
    $buffer = New-Object byte[] 8
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
        $read = $stream.Read($buffer, 0, 8)
    }
    finally {
        $stream.Dispose()
    }

    if ($read -ne 8) { return $false }
    for ($i = 0; $i -lt 8; $i++) {
        if ($buffer[$i] -ne $expected[$i]) { return $false }
    }
    return $true
}

function Quote-DrawioNativeArgument {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ($Value.Contains('"')) {
        throw "Native argument contains an unsupported quote character: $Value"
    }

    if ($Value -match '\s') { return '"' + $Value + '"' }
    return $Value
}

function Invoke-DrawioNativeProcess {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$DrawioExe,
        [Parameter(Mandatory = $true)][string]$InputPath,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [int]$TimeoutSeconds = 30,
        [switch]$Transparent,
        [int]$Width = 0
    )

    if (Test-Path -LiteralPath $OutputPath) {
        Remove-Item -LiteralPath $OutputPath -Force
    }

    # IMPORTANT: draw.io Desktop 28.x uses commander with allowUnknownOption().
    # Unknown Electron flags can leak into program.args and become paths[0].
    # That makes valid input files fail with "input file/directory not found".
    # Therefore argv must contain ONLY draw.io options registered by 28.x.
    # Disable auto-update via environment instead of the unsupported CLI flag.
    $tokens = New-Object System.Collections.Generic.List[string]
    [void]$tokens.Add("--export")
    [void]$tokens.Add("--format")
    [void]$tokens.Add("png")
    [void]$tokens.Add("--output")
    [void]$tokens.Add((Quote-DrawioNativeArgument $OutputPath))

    if ($Transparent) { [void]$tokens.Add("--transparent") }
    if ($Width -gt 0) {
        [void]$tokens.Add("--width")
        [void]$tokens.Add([string]$Width)
    }

    [void]$tokens.Add((Quote-DrawioNativeArgument $InputPath))
    $argumentLine = $tokens -join ' '

    Write-Verbose ("Draw.io strategy: registered-cli-options")
    Write-Verbose ("Draw.io command: {0} {1}" -f $DrawioExe, $argumentLine)

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $DrawioExe
    $psi.Arguments = $argumentLine
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.EnvironmentVariables["DRAWIO_DISABLE_UPDATE"] = "true"

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    $startedAt = Get-Date

    try {
        if (-not $process.Start()) {
            throw "Draw.io process could not be started."
        }

        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()

        $finished = $process.WaitForExit([Math]::Max(1, $TimeoutSeconds) * 1000)
        if (-not $finished) {
            try { $process.Kill() } catch {}
            try { $process.WaitForExit() } catch {}
            throw "Draw.io process did not exit within ${TimeoutSeconds}s."
        }

        # Ensure async stdout/stderr readers are fully drained after process exit.
        $process.WaitForExit()
        $stdout = $stdoutTask.GetAwaiter().GetResult()
        $stderr = $stderrTask.GetAwaiter().GetResult()
        $exitCode = $process.ExitCode

        if ($stdout) { Write-Verbose ("Draw.io stdout: {0}" -f $stdout.Trim()) }
        if ($stderr) { Write-Verbose ("Draw.io stderr: {0}" -f $stderr.Trim()) }

        if ($exitCode -ne 0) {
            throw ("Draw.io exited with code {0}. stdout='{1}' stderr='{2}'" -f $exitCode, $stdout.Trim(), $stderr.Trim())
        }

        $output = Wait-DrawioOutputFile -Path $OutputPath -TimeoutSeconds 10
        if (-not $output) {
            throw ("Draw.io exited 0 but no stable output file was created. stdout='{0}' stderr='{1}'" -f $stdout.Trim(), $stderr.Trim())
        }

        if (-not (Test-DrawioPngFile -Path $OutputPath)) {
            throw "Draw.io created a file without a valid PNG signature: $OutputPath"
        }

        return [PSCustomObject]@{
            Strategy   = "registered-cli-options"
            Success    = $true
            ExitCode   = $exitCode
            OutputPath = $output.FullName
            Bytes      = $output.Length
            StdOut     = $stdout
            StdErr     = $stderr
            ElapsedMs  = [int]((Get-Date) - $startedAt).TotalMilliseconds
        }
    }
    finally {
        $process.Dispose()
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
        throw "Draw.io input file not found before launch: $InputPath"
    }

    $resolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
    if (-not $DrawioExe) { $DrawioExe = Find-DrawioExecutable }
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
    $resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)

    $result = Invoke-DrawioNativeProcess `
        -DrawioExe $DrawioExe `
        -InputPath $resolvedInput `
        -OutputPath $resolvedOutput `
        -TimeoutSeconds $TimeoutSeconds `
        -Transparent:$Transparent `
        -Width $Width `
        -Verbose:($VerbosePreference -ne [System.Management.Automation.ActionPreference]::SilentlyContinue)

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
        StdOut         = $result.StdOut
        StdErr         = $result.StdErr
    }
}

function Test-DrawioNativeExportCapability {
    [CmdletBinding()]
    param(
        [string]$DrawioExe,
        [int]$TimeoutSeconds = 30
    )

    if (-not $DrawioExe) { $DrawioExe = Find-DrawioExecutable }
    if (-not $DrawioExe) { throw "Draw.io Desktop CLI was not found." }

    $probeRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("cherrystock-drawio-probe-" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $probeRoot -Force | Out-Null
    $probeDrawio = Join-Path $probeRoot "probe.drawio"
    $probePng = Join-Path $probeRoot "probe.png"

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
        # Windows PowerShell 5.1 Set-Content -Encoding UTF8 writes a BOM.
        # Use UTF8 without BOM to keep the probe as close as possible to the
        # repository .drawio source and avoid parser differences.
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($probeDrawio, $probeXml, $utf8NoBom)

        $result = Invoke-DrawioPngExport `
            -InputPath $probeDrawio `
            -OutputPath $probePng `
            -DrawioExe $DrawioExe `
            -TimeoutSeconds $TimeoutSeconds `
            -Verbose:($VerbosePreference -ne [System.Management.Automation.ActionPreference]::SilentlyContinue)

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