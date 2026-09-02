"""Diagnose which processes have a handle on CherryMon.duckdb (via handle or nsight)."""
import subprocess

# Try listing ALL processes whose command line mentions duckdb or mcp
result = subprocess.run(
    [
        "powershell", "-ExecutionPolicy", "Bypass", "-Command",
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match 'duckdb|mcp_server' } | "
        "Select-Object ProcessId, ParentProcessId, Name, CommandLine | Format-List",
    ],
    capture_output=True,
    text=True,
)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[:800])
