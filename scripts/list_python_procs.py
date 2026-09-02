"""Diagnose which python processes hold the CherryMon DuckDB file lock."""
import subprocess

result = subprocess.run(
    [
        "powershell", "-ExecutionPolicy", "Bypass", "-Command",
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Select-Object ProcessId, ParentProcessId, CommandLine | Format-List",
    ],
    capture_output=True,
    text=True,
)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[:800])
