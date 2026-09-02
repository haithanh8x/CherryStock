"""Check ALL Code.exe processes for open handles on CherryMon.duckdb via openfiles is not
available without admin; instead use PowerShell + handle-free heuristic: test write lock
repeatedly and report. Also list ALL processes named Code.exe with start dates and the
workspace they host by checking for CherryStock command lines."""
import subprocess

r = subprocess.run(
    [
        "powershell", "-ExecutionPolicy", "Bypass", "-Command",
        "gwmi Win32_Process -Filter \"Name='Code.exe'\" | "
        "? { $_.CommandLine -like '*CherryStock*' } | "
        "select ProcessId,ParentProcessId,CommandLine | fl",
    ],
    capture_output=True,
    text=True,
)
print(r.stdout or "(no Code.exe with CherryStock cmdline)")
