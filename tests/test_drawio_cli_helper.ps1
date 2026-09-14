$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$modulePath = Join-Path $repoRoot "scripts\lib\DrawioCli.psm1"

if (-not (Test-Path -LiteralPath $modulePath -PathType Leaf)) {
    throw "DrawioCli helper not found: $modulePath"
}

Import-Module $modulePath -Force

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("cherrystock-test-drawio-cli-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

try {
    $fakeExe = Join-Path $tempRoot "fake-drawio-exporter.exe"
    $inputDrawio = Join-Path $tempRoot "input.drawio"
    $outputPng = Join-Path $tempRoot "output.png"

    $source = @'
using System;
using System.IO;
using System.Threading;

public static class FakeDrawioExporter
{
    [STAThread]
    public static int Main(string[] args)
    {
        string output = null;

        for (int i = 0; i < args.Length; i++)
        {
            if (args[i] == "--output" && i + 1 < args.Length)
            {
                output = args[++i];
            }
        }

        if (String.IsNullOrWhiteSpace(output))
        {
            return 2;
        }

        // Deliberately behave like a GUI application that completes later.
        Thread.Sleep(1200);

        string dir = Path.GetDirectoryName(output);
        if (!String.IsNullOrEmpty(dir))
        {
            Directory.CreateDirectory(dir);
        }

        byte[] png = new byte[]
        {
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x00
        };

        File.WriteAllBytes(output, png);
        return 0;
    }
}
'@

    Add-Type -TypeDefinition $source -OutputAssembly $fakeExe -OutputType ConsoleApplication
    Set-Content -LiteralPath $inputDrawio -Value '<mxfile><diagram id="test"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel></diagram></mxfile>' -Encoding UTF8

    $started = Get-Date
    $result = Invoke-DrawioPngExport `
        -InputPath $inputDrawio `
        -OutputPath $outputPng `
        -DrawioExe $fakeExe `
        -TimeoutSeconds 10
    $elapsed = [int]((Get-Date) - $started).TotalMilliseconds

    if (-not (Test-Path -LiteralPath $outputPng -PathType Leaf)) {
        throw "FAIL: helper returned but fake exporter output does not exist."
    }

    if (-not (Test-DrawioPngFile -Path $outputPng)) {
        throw "FAIL: helper returned an output that does not pass PNG signature validation."
    }

    if ($elapsed -lt 1000) {
        throw "FAIL: helper returned too early (${elapsed}ms); expected it to wait for the delayed GUI exporter."
    }

    if (-not $result.PngValid) {
        throw "FAIL: helper did not mark PNG as valid."
    }

    Write-Host "PASS: DrawioCli helper waits for delayed GUI process completion"
    Write-Host ("Strategy:  {0}" -f $result.Strategy)
    Write-Host ("Elapsed:   {0} ms" -f $elapsed)
    Write-Host ("PNG bytes: {0}" -f $result.Bytes)
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
