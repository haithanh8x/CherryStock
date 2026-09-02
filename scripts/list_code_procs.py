"""List all Code.exe processes to find the second VS Code instance (PID 8784)."""
import subprocess

r = subprocess.run(
    [
        "powershell", "-ExecutionPolicy", "Bypass", "-Command",
        "gwmi Win32_Process -Filter \"Name='Code.exe'\" | "
        "select ProcessId,ParentProcessId,CreationDate | sort ProcessId | ft -auto",
    ],
    capture_output=True,
    text=True,
)
print(r.stdout or "(none)")
if r.stderr:
    print("ERR:", r.stderr[:400])
