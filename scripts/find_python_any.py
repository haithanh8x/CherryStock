"""Find every process whose command line OR loaded path mentions python (incl. Code.exe children)."""
import subprocess

r = subprocess.run(
    [
        "powershell", "-ExecutionPolicy", "Bypass", "-Command",
        "gwmi Win32_Process | "
        "? { $_.CommandLine -like '*python*' -and $_.ProcessId -ne $PID } | "
        "select ProcessId,ParentProcessId,Name,CommandLine | fl",
    ],
    capture_output=True,
    text=True,
)
print(r.stdout or "(none)")
