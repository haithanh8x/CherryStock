"""List all python.exe + Code.exe child processes (MCP servers run as VS Code children)."""
import subprocess

result = subprocess.run(
    [
        "powershell", "-ExecutionPolicy", "Bypass", "-Command",
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -in @('python.exe','pythonw.exe') } | "
        "Select-Object ProcessId, ParentProcessId, CreationDate, Name, CommandLine | Format-List",
    ],
    capture_output=True,
    text=True,
)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[:800])
