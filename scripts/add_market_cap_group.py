"""Add MarketCap_Group to CherryMon.main.vw_Ticker_Info (idempotent)."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from src.cherrystock.config.settings import settings
from src.cherrystock.infrastructure.database.connection import DuckDBConnectionFactory

VIEW = '"CherryMon"."main"."vw_Ticker_Info"'
COLUMN = "MarketCap_Group"

# MarketCap is expected to be in VND. Thresholds are VND, not billions.
THRESHOLDS = (50_000_000_000_000, 10_000_000_000_000, 1_000_000_000_000)


def update(db_path: Path, *, dry_run: bool = False) -> None:
    if not db_path.is_file():
        raise FileNotFoundError(f"DuckDB database not found: {db_path}")
    factory = DuckDBConnectionFactory(db_path=db_path, duckdb_env="local")
    with factory.writer() as con:
        matches = con.execute(
            """
            SELECT database_name, sql FROM duckdb_views()
            WHERE schema_name = 'main' AND view_name = 'vw_Ticker_Info'
              AND NOT internal
            """
        ).fetchall()
        if len(matches) != 1:
            raise RuntimeError(
                f"Expected one vw_Ticker_Info view; found {len(matches)}. "
                f"Candidates: {[row[0] for row in matches]}"
            )
        catalog, original_sql = matches[0]
        resolved_view = f'"{catalog.replace(chr(34), chr(34) * 2)}"."main"."vw_Ticker_Info"'
        cols = [row[0] for row in con.execute(
            f"DESCRIBE SELECT * FROM {resolved_view}"
        ).fetchall()]
        if "MarketCap" not in cols:
            raise RuntimeError("MarketCap column is missing from the source view")
        if COLUMN in cols:
            print(f"[MarketCap] SKIP: {COLUMN} already exists in {resolved_view}")
            return

        # Extract original SELECT from CREATE VIEW and preserve the current columns.
        original_sql = original_sql.strip().rstrip(";")
        match = re.search(r"\bAS\s+(?=SELECT\b|WITH\b|\()", original_sql, re.IGNORECASE)
        if match is None:
            raise RuntimeError("Could not parse CREATE VIEW statement from duckdb_views()")
        original_query = original_sql[match.end():]
        projection = (
            "CASE "
            "WHEN TRY_CAST(\"MarketCap\" AS DOUBLE) IS NULL "
            "  OR TRY_CAST(\"MarketCap\" AS DOUBLE) <= 0 THEN 'Unknown' "
            f"WHEN TRY_CAST(\"MarketCap\" AS DOUBLE) >= {THRESHOLDS[0]} THEN 'Large Cap' "
            f"WHEN TRY_CAST(\"MarketCap\" AS DOUBLE) >= {THRESHOLDS[1]} THEN 'Mid Cap' "
            f"WHEN TRY_CAST(\"MarketCap\" AS DOUBLE) >= {THRESHOLDS[2]} THEN 'Small Cap' "
            "ELSE 'Micro Cap' END"
        )
        ddl = (
            f"CREATE OR REPLACE VIEW {resolved_view} AS "
            f"SELECT base.*, {projection} AS \"{COLUMN}\" "
            f"FROM ({original_query}) AS base"
        )
        if dry_run:
            print(ddl)
            return
        con.execute("BEGIN TRANSACTION")
        try:
            con.execute(ddl)
            con.execute(
                f"COMMENT ON COLUMN {resolved_view}.\"{COLUMN}\" IS "
                "'Market capitalization class using MarketCap in VND: "
                "Large >= 50,000 billion; Mid >= 10,000 billion; "
                "Small >= 1,000 billion; Micro below 1,000 billion; "
                "Unknown for missing/nonpositive values.'"
            )
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        print(f"[MarketCap] UPDATED {resolved_view} | column={COLUMN}")
        for row in con.execute(
            f'SELECT "{COLUMN}", COUNT(*) FROM {resolved_view} GROUP BY 1 ORDER BY 1'
        ).fetchall():
            print(f"  {row[0]}: {row[1]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, default=settings.local_db_path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    update(args.db_path.expanduser(), dry_run=args.dry_run)


if __name__ == "__main__":
    main()
