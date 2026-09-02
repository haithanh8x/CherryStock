"""Snapshot test: check write access to DuckDB, and identify which VS Code MCP child holds it."""
import subprocess

# 1. List ALL python-like processes with parent process ids (short output, no quoting issues)
r1 = subprocess.run(
    [
        "powershell", "-ExecutionPolicy", "Bypass", "-Command",
        "gwmi Win32_Process -Filter \"Name='python.exe'\" | select ProcessId,ParentProcessId | ft -auto",
    ],
    capture_output=True,
    text=True,
)
print("== python processes ==")
print(r1.stdout or "(none)")
if r1.stderr:
    print("ERR1:", r1.stderr[:400])

# 2. Try a write connection
import duckdb

try:
    con = duckdb.connect("C:/OneDrive/Working/Datafile/CherryMon.duckdb", read_only=False)
    print("WRITE OK")
    con.close()
except Exception as exc:
    print("WRITE FAIL:", exc)
