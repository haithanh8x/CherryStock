"""Find MCP server processes (python) under Code.exe 8784 or any Code.exe parent."""
import subprocess

r = subprocess.run(
    [
        "powershell", "-ExecutionPolicy", "Bypass", "-Command",
        "gwmi Win32_Process -Filter \"Name='python.exe'\" | "
        "select ProcessId,ParentProcessId,CommandLine | fl",
    ],
    capture_output=True,
    text=True,
)
print("== python ==")
print(r.stdout or "(none)")

# Also find any process (any name) whose CommandLine mentions duckdb_mcp
r2 = subprocess.run(
    [
        "powershell", "-ExecutionPolicy", "Bypass", "-Command",
        "gwmi Win32_Process | ? { $_.CommandLine -like '*duckdb_mcp*' -and $_.Name -ne 'powershell.exe' } | "
        "select ProcessId,Name,ParentProcessId,CommandLine | fl",
    ],
    capture_output=True,
    text=True,
)
print("== duckdb_mcp holders ==")
print(r2.stdout or "(none)")
if r2.stderr:
    print("ERR:", r2.stderr[:400])
