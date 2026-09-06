"""Runbook runner: smart_money_v1_preflight.sql (read-only, statement-by-statement)."""

from pathlib import Path

from src.Ults.DuckLib import DuckDBManager

SQL_PATH = Path(__file__).resolve().parents[1] / "src" / "DuckDB" / "sql" / "smart_money_v1_preflight.sql"


def statements(script: str):
    """Split SQL on semicolons that terminate real statements.

    Semicolons inside '--' comments must not split, so comment prefixes are
    masked before splitting.
    """
    lines = script.splitlines()
    masked = []
    for line in lines:
        masked.append(" " * len(line) if line.strip().startswith("--") else line)
    parts = "\n".join(masked).split(";")
    # Re-split original text using masked split positions (equal lengths).
    result = []
    pos = 0
    for part in parts:
        length = len(part)
        result.append(script[pos : pos + length])
        pos += length + 1
    for stmt in result:
        body = "\n".join(
            line for line in stmt.splitlines() if not line.strip().startswith("--")
        ).strip()
        if body:
            yield body


def main() -> None:
    script = SQL_PATH.read_text(encoding="utf-8")
    manager = DuckDBManager(read_only=True)
    con = manager.get_connection(read_only=True)
    try:
        idx = 0
        for stmt in statements(script):
            idx += 1
            cur = con.execute(stmt)
            rows = cur.fetchall()
            print(f"-- statement {idx}: {len(rows)} row(s)")
            print(" | ".join(d[0] for d in cur.description))
            for row in rows[:40]:
                print(" | ".join("" if v is None else str(v) for v in row))
            if len(rows) > 40:
                print(f"... ({len(rows) - 40} more)")
    except Exception as exc:
        print(f"STOPPED at statement {idx}: {exc}")
    finally:
        manager.close_connection(con)


if __name__ == "__main__":
    main()
