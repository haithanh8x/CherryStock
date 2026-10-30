"""Create/refresh vw_Ticker_Indicator_Current without changing Indicator facts.

Run after cal_indicator_current and indicator dimensions exist:
    python -m scripts.create_vw_ticker_indicator_current

The CREATE OR REPLACE VIEW and validation run in one transaction. The process
fails/rolls back if any current row is unmapped or metadata causes row fan-out.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from cherrystock.config.settings import settings
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory

SCHEMA = '"CherryMon"."main"'
FACT = f'{SCHEMA}."cal_indicator_current"'
VIEW = f'{SCHEMA}."vw_Ticker_Indicator_Current"'
SQL_PATH = ROOT / "src" / "DuckDB" / "sql" / "vw_Ticker_Indicator_Current.sql"


def apply_view(con) -> dict[str, object]:
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute(SQL_PATH.read_text(encoding="utf-8"))
        fact_rows = con.execute(f"SELECT COUNT(*) FROM {FACT}").fetchone()[0]
        view_rows = con.execute(f"SELECT COUNT(*) FROM {VIEW}").fetchone()[0]
        missing = con.execute(
            f"SELECT COUNT(*) FROM {VIEW} "
            "WHERE ConfigId IS NULL OR ComponentCode IS NULL"
        ).fetchone()[0]
        duplicate_keys = con.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT Ticker, Date, IndicatorName, Timeframe
                FROM {VIEW}
                GROUP BY Ticker, Date, IndicatorName, Timeframe
                HAVING COUNT(*) > 1
            ) AS duplicates
        """).fetchone()[0]
        if missing or duplicate_keys or fact_rows != view_rows:
            unmapped = con.execute(f"""
                SELECT DISTINCT IndicatorName, Timeframe
                FROM {VIEW}
                WHERE ConfigId IS NULL OR ComponentCode IS NULL
                ORDER BY IndicatorName, Timeframe LIMIT 10
            """).fetchall()
            raise RuntimeError(
                "vw_Ticker_Indicator_Current mapping validation failed: "
                f"fact_rows={fact_rows}, view_rows={view_rows}, "
                f"unmapped_rows={missing}, duplicate_keys={duplicate_keys}, "
                f"unmapped_examples={unmapped}"
            )
        result = {
            "view": "CherryMon.main.vw_Ticker_Indicator_Current",
            "fact_rows": int(fact_rows),
            "view_rows": int(view_rows),
            "unmapped_rows": int(missing),
            "duplicate_keys": int(duplicate_keys),
        }
        con.execute("COMMIT")
        return result
    except BaseException:
        con.execute("ROLLBACK")
        raise


def main() -> None:
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with factory.writer() as con:
        print("[INDICATOR CURRENT VIEW]", json.dumps(
            apply_view(con), ensure_ascii=False,
        ))


if __name__ == "__main__":
    main()
