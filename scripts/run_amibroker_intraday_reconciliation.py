"""Runbook runner: tests/test_amibroker_intraday_reconciliation.md

Read-only execution of the four AmiBroker Intraday smoke SQL scripts, in order:
  00 schema preflight, 01 overview, 02 data quality, 03 reconcile EOD.
Each result set is printed. No mutation is performed.
"""

from pathlib import Path

from src.Ults.DuckLib import DuckDBManager

SQL_DIR = Path(__file__).resolve().parents[1] / "src" / "DuckDB" / "sql"
FILES = [
    "amibroker_intraday_00_schema_preflight.sql",
    "amibroker_intraday_01_overview.sql",
    "amibroker_intraday_02_data_quality.sql",
    "amibroker_intraday_03_reconcile_eod.sql",
]


def statements(script: str, filename: str):
    """Split a SQL script into executable statements, dropping comment-only chunks.

    The reconcile script defines one WITH/CTE chain followed by standalone
    SELECT statements. Each later SELECT needs the CTE block re-attached to be
    runnable on its own, so the first chunk is kept as a prefix there.
    """
    chunks = [
        "\n".join(
            line for line in chunk.splitlines() if not line.strip().startswith("--")
        ).strip()
        for chunk in script.split(";")
    ]
    chunks = [c for c in chunks if c]
    prefix = chunks[0] if filename.endswith("03_reconcile_eod.sql") else ""
    for i, chunk in enumerate(chunks):
        if prefix and i > 0 and chunk.lstrip().upper().startswith("SELECT"):
            # Statement 1 is "WITH ... classified AS (...) SELECT ... FROM
            # classified ... ORDER BY source". To run later SELECTs standalone,
            # reuse the full CTE chain (WITH stock_i ... classified) directly.
            # The chain begins at the script's leading WITH and ends right
            # before statement 1's final SELECT line.
            body = prefix
            # Cut everything after the closing of the CTE chain: find the last
            # "FROM classified" (statement 1's main SELECT) and take what
            # precedes it, minus its trailing "SELECT ... " header line.
            pos = body.rfind("FROM classified")
            head = body[:pos]
            # head now ends with "... classified AS (\n<full select list>\n)\n\nSELECT\n source,\n ... FROM classified" minus that FROM; strip back to the end of the classified CTE.
            sel_pos = head.rfind("\nSELECT")
            cte_chain = head[:sel_pos]
            yield cte_chain + " " + chunk
        else:
            yield chunk


def main() -> None:
    manager = DuckDBManager(read_only=True)
    con = manager.get_connection(read_only=True)
    try:
        for filename in FILES:
            script = (SQL_DIR / filename).read_text(encoding="utf-8")
            print(f"\n=== {filename} ===")
            for idx, stmt in enumerate(statements(script, filename), start=1):
                try:
                    cur = con.execute(stmt)
                    rows = cur.fetchall()
                except Exception as exc:  # surface the failing statement clearly
                    print(f"[statement {idx}] ERROR: {exc}")
                    continue
                cols = [d[0] for d in cur.description]
                print(f"\n-- statement {idx}: {len(rows)} row(s)")
                print(" | ".join(cols))
                for row in rows[:300]:
                    print(" | ".join("" if v is None else str(v) for v in row))
                if len(rows) > 300:
                    print(f"... ({len(rows) - 300} more rows truncated)")
    finally:
        manager.close_connection(con)


if __name__ == "__main__":
    main()
