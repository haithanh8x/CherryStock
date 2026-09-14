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
    $ioRoot = Join-Path $tempRoot "path with spaces"
    New-Item -ItemType Directory -Path $ioRoot -Force | Out-Null
    $inputDrawio = Join-Path $ioRoot "input diagram.drawio"
    $outputPng = Join-Path $ioRoot "output image.png"

    $source = @'
using System;
using System.IO;
using System.Threading;

public static class FakeDrawioExporter
{
    [STAThread]
    public static int Main(string[] args)
    {
        if (!String.Equals(Environment.GetEnvironmentVariable("DRAWIO_DISABLE_UPDATE"), "true", StringComparison.OrdinalIgnoreCase))
        {
            Console.Error.WriteLine("DRAWIO_DISABLE_UPDATE environment contract missing");
            return 8;
        }

        string output = null;
        string input = null;

        for (int i = 0; i < args.Length; i++)
        {
            // Regression guard for draw.io Desktop 28.x: these are not
            // commander-registered draw.io options and must not be passed in argv.
            if (args[i] == "--disable-update" ||
                args[i] == "--disable-gpu" ||
                args[i].StartsWith("--user-data-dir", StringComparison.OrdinalIgnoreCase))
            {
                Console.Error.WriteLine("unsupported argv token: " + args[i]);
                return 9;
            }

            if (args[i] == "--output" && i + 1 < args.Length)
            {
                output = args[++i];
            }
            else if (!args[i].StartsWith("-", StringComparison.Ordinal))
            {
                input = args[i];
            }
        }

        if (String.IsNullOrWhiteSpace(output) || String.IsNullOrWhiteSpace(input) || !File.Exists(input))
        {
            Console.Error.WriteLine("input/output contract invalid");
            return 2;
        }

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
        Console.WriteLine(input + " -> " + output);
        return 0;
    }
}
'@

    Add-Type -TypeDefinition $source -OutputAssembly $fakeExe -OutputType ConsoleApplication

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText(
        $inputDrawio,
        '<mxfile><diagram id="test"><mxGraphModel shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel></diagram></mxfile>',
        $utf8NoBom
    )

    $started = Get-Date
    $result = Invoke-DrawioPngExport `
        -InputPath $inputDrawio `
        -OutputPath $outputPng `
        -DrawioExe $fakeExe `
        -TimeoutSeconds 10 `
        -Verbose
    $elapsed = [int]((Get-Date) - $started).TotalMilliseconds

    if (-not (Test-Path -LiteralPath $outputPng -PathType Leaf)) {
        throw "FAIL: helper returned but fake exporter output does not exist."
    }
    if (-not (Test-DrawioPngFile -Path $outputPng)) {
        throw "FAIL: helper returned an output that does not pass PNG signature validation."
    }
    if ($elapsed -lt 1000) {
        throw "FAIL: helper returned too early (${elapsed}ms); expected it to wait for delayed process completion."
    }
    if (-not $result.PngValid) {
        throw "FAIL: helper did not mark PNG as valid."
    }
    if ($result.Strategy -ne "registered-cli-options") {
        throw "FAIL: unexpected CLI strategy '$($result.Strategy)'."
    }
    if ($result.StdOut -notmatch "input diagram\.drawio") {
        throw "FAIL: quoted input path with spaces was not preserved by native argv. stdout='$($result.StdOut)'"
    }

    Write-Host "PASS: DrawioCli waits for delayed process completion"
    Write-Host "PASS: DrawioCli argv contains only draw.io-registered options"
    Write-Host "PASS: DRAWIO_DISABLE_UPDATE is supplied through environment"
    Write-Host "PASS: native input/output paths with spaces are preserved"
    Write-Host ("Strategy:  {0}" -f $result.Strategy)
    Write-Host ("Elapsed:   {0} ms" -f $elapsed)
    Write-Host ("PNG bytes: {0}" -f $result.Bytes)
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}