"""Backfill historical MA breadth inputs from legacy indicator facts.

The AmiBroker cal_indicator_history source currently starts in 2025.
Preserve ALL AmiBroker observations and insert only earlier missing MA20,
MA50, MA100, MA200 D/W/M values. Restrict to tickers represented by the
existing AmiBroker history to maintain the same market universe.

Usage:
  python -m scripts.backfill_market_breadth_ma_history --dry-run
  python -m scripts.backfill_market_breadth_ma_history
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from cherrystock.config.settings import settings
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory

HISTORY = '"CherryMon"."main"."cal_indicator_history"'
LEGACY = '"CherryMon"."main"."cal_indicator_values"'
CONFIG = '"CherryMon"."main"."dim_indicator_config"'
EOD = '"CherryMon"."main"."raw_stock_eod"'

def run(dry_run: bool = False) -> dict[str, object]:
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with factory.writer() as con:
        min_date, latest_date, tickers = con.execute(
            f"SELECT MIN(Date), MAX(Date), COUNT(DISTINCT Ticker) FROM {HISTORY}"
        ).fetchone()
        if min_date is None or latest_date is None or tickers < 1:
            raise RuntimeError("AmiBroker history must be initialized before MA backfill")
        two_year_start = con.execute(
            "SELECT CAST(?::DATE - INTERVAL '2 years' AS DATE)", [latest_date]
        ).fetchone()[0]
        if two_year_start >= min_date:
            return {"status": "already_covers_window", "earliest": str(min_date),
                    "start": str(two_year_start), "inserted": 0}
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE _breadth_ma_backfill AS
            SELECT DISTINCT v.Ticker, v.Date,
                REGEXP_REPLACE(cfg.ConfigCode, '_[DWM]$', '') AS IndicatorName,
                cfg.Timeframe, CAST(v.Value AS DOUBLE) AS Value
            FROM {LEGACY} v
            JOIN {CONFIG} cfg ON cfg.ConfigId = v.ConfigId
            JOIN (SELECT DISTINCT Ticker FROM {HISTORY}) t
                ON t.Ticker = v.Ticker
            JOIN {EOD} e ON e.Ticker = v.Ticker AND e.Date = v.Date
            WHERE v.Date >= ? AND v.Date < ?
              AND cfg.ConfigCode IN (
                'MA20_D','MA50_D','MA100_D','MA200_D',
                'MA20_W','MA50_W','MA100_W','MA200_W',
                'MA20_M','MA50_M','MA100_M','MA200_M'
              )
              AND v.ComponentCode = 'VALUE'
              AND v.Value IS NOT NULL AND isfinite(v.Value)
              AND e.Close IS NOT NULL AND e.Close > 0
        """, [two_year_start, min_date])
        duplicate_keys = con.execute("""
            SELECT COUNT(*) FROM (
                SELECT Ticker,Date,IndicatorName,Timeframe
                FROM _breadth_ma_backfill GROUP BY ALL HAVING COUNT(*)>1
            )
        """).fetchone()[0]
        if duplicate_keys:
            raise ValueError(f"Duplicate legacy MA keys detected: {duplicate_keys}")
        count, earliest, latest = con.execute(
            "SELECT COUNT(*), MIN(Date), MAX(Date) FROM _breadth_ma_backfill"
        ).fetchone()
        if count == 0 or earliest > two_year_start:
            raise ValueError(
                f"Insufficient legacy MA coverage: rows={count}, earliest={earliest}, "
                f"requested_start={two_year_start}"
            )
        result = {"start": str(two_year_start), "legacy_earliest": str(earliest),
                  "legacy_latest": str(latest), "staged": count, "dry_run": dry_run}
        if dry_run:
            return result
        con.execute("BEGIN TRANSACTION")
        try:
            con.execute(f"""
                INSERT INTO {HISTORY}
                    (Ticker,Date,IndicatorName,Timeframe,Value,UpdatedAt)
                SELECT Ticker,Date,IndicatorName,Timeframe,Value,CURRENT_TIMESTAMP
                FROM _breadth_ma_backfill
                ON CONFLICT (Ticker,Date,IndicatorName,Timeframe) DO NOTHING
            """)
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
        before = min_date
        after, total = con.execute(
            f"SELECT MIN(Date), COUNT(*) FROM {HISTORY}"
        ).fetchone()
        if after > two_year_start:
            raise RuntimeError("History backfill did not reach the two-year start")
        result.update({"inserted_or_retained": count, "earliest_before": str(before),
                       "earliest_after": str(after), "total_rows": total})
        return result

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.dry_run), ensure_ascii=False, default=str), flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
