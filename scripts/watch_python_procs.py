"""Find python PIDs that are VS Code MCP children, repeatedly (lock holder respawn loop)."""
import subprocess
import time

for attempt in range(3):
    r = subprocess.run(
        [
            "powershell", "-ExecutionPolicy", "Bypass", "-Command",
            "gwmi Win32_Process -Filter \"Name='python.exe'\" | "
            "select ProcessId,ParentProcessId,CommandLine | fl",
        ],
        capture_output=True,
        text=True,
    )
    print(f"== attempt {attempt + 1} ==")
    print(r.stdout or "(none)")
    time.sleep(2)
