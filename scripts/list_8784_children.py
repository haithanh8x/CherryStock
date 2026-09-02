"""Check if PID 8784 (Code.exe) itself has the DB file open - likely via an MCP server
running in-process or a worker. List children of 8784 with any name."""
import subprocess

r = subprocess.run(
    [
        "powershell", "-ExecutionPolicy", "Bypass", "-Command",
        "gwmi Win32_Process -Filter \"ParentProcessId=8784\" | "
        "select ProcessId,Name,CommandLine | fl",
    ],
    capture_output=True,
    text=True,
)
print(r.stdout or "(none)")
