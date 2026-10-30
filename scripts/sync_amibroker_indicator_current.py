"""Refresh current developing W/M indicators from the saved AmiBroker APX.

This is deliberately standalone: it does not require Indicator V2 fact migration,
does not alter cal_indicator_values or indicator metadata, and never modifies the
saved Export_Indicator.apx/.afl. AmiBroker AFL remains the calculation engine.

Usage (Windows, AmiBroker configured):
    python -m scripts.sync_amibroker_indicator_current --dry-run
    python -m scripts.sync_amibroker_indicator_current
    python -m scripts.sync_amibroker_indicator_current --days 45
    python -m scripts.sync_amibroker_indicator_current --csv C:/temp/export.csv

cal_indicator_current follows the V2 contract: *developing W and M only*.
Daily indicators continue to belong to cal_indicator_values.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from cherrystock.config.settings import settings
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory
from scripts.indicator_storage_v2 import run_apx_export
from scripts.migrate_indicator_storage_v2 import CURRENT, _columns, _create_current
from scripts.sync_amibroker_indicator_full import SPECS

WM_SPECS = [s for s in SPECS if s.timeframe in ("W", "M")]
INDICATOR_COLUMNS = {s.csv_column for s in SPECS}
PRICE_COLUMNS = {f"{prefix}_{tf}" for prefix in ("OPEN", "HIGH", "LOW", "CLOSE")
                 for tf in ("D", "W", "M")}
CURRENT_COLUMNS = {"Ticker", "Date", "IndicatorName", "Timeframe", "Value", "UpdatedAt"}


def _q(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def stage_current(con, csv_path: Path, *, as_of: date, min_tickers: int,
                  max_age_days: int) -> dict:
    """Validate the APX output and stage latest W/M within the current periods."""
    if not csv_path.is_file() or csv_path.stat().st_size == 0:
        raise FileNotFoundError(f"Missing/empty AmiBroker export: {csv_path}")

    con.execute(
        "CREATE OR REPLACE TEMP TABLE _apx_current_csv AS "
        "SELECT * FROM read_csv(?, header=true, all_varchar=true, auto_detect=true)",
        [str(csv_path)],
    )
    columns = [r[1] for r in con.execute(
        "PRAGMA table_info('_apx_current_csv')"
    ).fetchall()]
    column_set = set(columns)
    date_field = "Date" if "Date" in column_set else "Date/Time"
    if "Ticker" not in column_set or date_field not in column_set:
        raise ValueError("APX CSV is missing Ticker or Date/DateTime")
    missing = INDICATOR_COLUMNS - column_set
    extra = column_set - INDICATOR_COLUMNS - PRICE_COLUMNS - {"Ticker", date_field}
    if missing or extra:
        raise ValueError(
            f"APX indicator columns mismatch: missing={sorted(missing)[:15]}, "
            f"unexpected={sorted(extra)[:15]}"
        )

    parsed_date = (
        f"COALESCE(TRY_CAST(CAST({_q(date_field)} AS VARCHAR) AS DATE), "
        f"TRY_CAST(SUBSTR(CAST({_q(date_field)} AS VARCHAR),1,10) AS DATE))"
    )
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE _apx_current_source AS
        SELECT UPPER(TRIM(CAST("Ticker" AS VARCHAR))) AS Ticker,
               {parsed_date} AS Date
        FROM _apx_current_csv
    """)
    invalid_source = con.execute("""
        SELECT COUNT(*) FROM _apx_current_source WHERE Ticker = '' OR Ticker IS NULL OR Date IS NULL
    """).fetchone()[0]
    if invalid_source:
        raise ValueError(f"APX has {invalid_source} invalid ticker/date rows")
    duplicate_source = con.execute("""
        SELECT Ticker, Date, COUNT(*) AS n FROM _apx_current_source
        GROUP BY Ticker, Date HAVING COUNT(*) > 1 LIMIT 1
    """).fetchone()
    if duplicate_source:
        raise ValueError(f"Duplicate APX Ticker/Date: {duplicate_source}")
    csv_rows, source_tickers, source_max_date = con.execute("""
        SELECT COUNT(*), COUNT(DISTINCT Ticker), MAX(Date)
        FROM _apx_current_source
    """).fetchone()
    if source_tickers < min_tickers:
        raise ValueError(f"APX ticker coverage too low: {source_tickers} < {min_tickers}")
    if source_max_date is None or not (as_of - timedelta(days=max_age_days) <= source_max_date <= as_of):
        raise ValueError(
            f"Stale/future APX export: source={source_max_date}, as_of={as_of}; "
            f"max_age_days={max_age_days}. Check AmiBroker data or --as-of."
        )

    # CSV is wide. UNPIVOT discards blanks; W/M are point-in-time observations
    # only on the last observed daily bar of a week/month (no forward-fill).
    con.execute(
        "CREATE OR REPLACE TEMP TABLE _apx_current_map "
        "(CsvColumn VARCHAR, IndicatorName VARCHAR, Timeframe VARCHAR)"
    )
    con.executemany(
        "INSERT INTO _apx_current_map VALUES (?,?,?)",
        [(s.csv_column, s.csv_column.rsplit("_", 1)[0], s.timeframe)
         for s in WM_SPECS],
    )
    quoted = ", ".join(_q(s.csv_column) for s in WM_SPECS)
    con.execute(
        f"CREATE OR REPLACE TEMP TABLE _apx_current_unpivot AS "
        f"UNPIVOT _apx_current_csv ON {quoted} "
        "INTO NAME CsvColumn VALUE RawValue"
    )
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE _apx_current_parsed AS
        SELECT UPPER(TRIM(CAST(u."Ticker" AS VARCHAR))) AS Ticker,
               COALESCE(TRY_CAST(CAST(u.{_q(date_field)} AS VARCHAR) AS DATE),
                        TRY_CAST(SUBSTR(CAST(u.{_q(date_field)} AS VARCHAR),1,10) AS DATE)) AS Date,
               m.IndicatorName, m.Timeframe,
               TRY_CAST(NULLIF(TRIM(CAST(u.RawValue AS VARCHAR)), '') AS DOUBLE) AS Value,
               CAST(u.RawValue AS VARCHAR) AS RawValue
        FROM _apx_current_unpivot u
        JOIN _apx_current_map m ON m.CsvColumn=u.CsvColumn
        WHERE NULLIF(TRIM(CAST(u.RawValue AS VARCHAR)), '') IS NOT NULL
    """)
    invalid_numeric = con.execute("""
        SELECT COUNT(*) FROM _apx_current_parsed
        WHERE Date IS NULL OR Ticker IS NULL OR Ticker='' OR
              Value IS NULL OR NOT ISFINITE(Value)
    """).fetchone()[0]
    if invalid_numeric:
        raise ValueError(f"APX has {invalid_numeric} invalid W/M observations")
    duplicate = con.execute("""
        SELECT Ticker, Date, IndicatorName, Timeframe, COUNT(*) AS n
        FROM _apx_current_parsed
        GROUP BY Ticker, Date, IndicatorName, Timeframe
        HAVING COUNT(*) > 1 LIMIT 1
    """).fetchone()
    if duplicate:
        raise ValueError(f"Duplicate W/M indicator observation: {duplicate}")

    week_start = as_of - timedelta(days=as_of.weekday())
    month_start = as_of.replace(day=1)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE _apx_current_stage AS
        SELECT Ticker, Date, IndicatorName, Timeframe, Value
        FROM _apx_current_parsed
        WHERE (Timeframe='W' AND Date >= ? AND Date <= ?)
           OR (Timeframe='M' AND Date >= ? AND Date <= ?)
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY Ticker, IndicatorName, Timeframe
            ORDER BY Date DESC
        ) = 1
    """, [week_start, as_of, month_start, as_of])
    rows, week_rows, month_rows, current_tickers = con.execute("""
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE Timeframe='W'),
               COUNT(*) FILTER (WHERE Timeframe='M'),
               COUNT(DISTINCT Ticker)
        FROM _apx_current_stage
    """).fetchone()
    if rows == 0:
        raise ValueError(
            "No developing W/M values in the current calendar periods. "
            "Check APX Timeframes=ALL, date, and most recent AmiBroker quotes."
        )
    if current_tickers < min_tickers:
        raise ValueError(
            f"Current W/M ticker coverage too low: {current_tickers} < {min_tickers}"
        )
    return {
        "csv": str(csv_path),
        "csv_rows": csv_rows, "source_tickers": source_tickers,
        "source_max_date": str(source_max_date),
        "as_of": str(as_of), "week_start": str(week_start),
        "month_start": str(month_start), "current_tickers": current_tickers,
        "upsert_candidates": rows, "weekly_values": week_rows,
        "monthly_values": month_rows,
        "price_columns_ignored": len(PRICE_COLUMNS & column_set),
    }


def commit_current(con, *, as_of: date) -> dict:
    """Create only the current table if absent; atomically UPSERT W/M snapshots."""
    week_start = as_of - timedelta(days=as_of.weekday())
    month_start = as_of.replace(day=1)
    con.execute("BEGIN TRANSACTION")
    try:
        kind = con.execute("""
            SELECT table_type FROM information_schema.tables
            WHERE table_catalog='CherryMon' AND table_schema='main'
              AND table_name='cal_indicator_current'
        """).fetchone()
        if kind and kind[0] != "BASE TABLE":
            raise RuntimeError("cal_indicator_current exists but is not a base table")
        _create_current(con)
        existing_columns = _columns(con, "cal_indicator_current")
        if not CURRENT_COLUMNS.issubset(existing_columns):
            raise RuntimeError(
                f"Existing cal_indicator_current has incompatible columns: "
                f"{sorted(existing_columns)}"
            )
        # Reject stale data rather than overwriting a newer per-ticker snapshot.
        older = con.execute(f"""
            SELECT COUNT(*)
            FROM _apx_current_stage s
            JOIN {CURRENT} c USING(Ticker, IndicatorName, Timeframe)
            WHERE s.Date < c.Date
        """).fetchone()[0]
        if older:
            raise ValueError(
                f"{older} APX rows older than saved current snapshots; aborting"
            )
        expired = con.execute(f"""
            SELECT COUNT(*) FROM {CURRENT}
            WHERE (Timeframe='W' AND Date < ?)
               OR (Timeframe='M' AND Date < ?)
        """, [week_start, month_start]).fetchone()[0]
        con.execute(f"""
            DELETE FROM {CURRENT}
            WHERE (Timeframe='W' AND Date < ?)
               OR (Timeframe='M' AND Date < ?)
        """, [week_start, month_start])
        con.execute(f"""
            INSERT INTO {CURRENT}
                (Ticker, Date, IndicatorName, Timeframe, Value, UpdatedAt)
            SELECT Ticker, Date, IndicatorName, Timeframe, Value, CURRENT_TIMESTAMP
            FROM _apx_current_stage
            WHERE TRUE
            ON CONFLICT (Ticker,IndicatorName,Timeframe) DO UPDATE SET
                Date=EXCLUDED.Date, Value=EXCLUDED.Value,
                UpdatedAt=EXCLUDED.UpdatedAt
        """)
        total, week_total, month_total = con.execute(f"""
            SELECT COUNT(*),
                   COUNT(*) FILTER (WHERE Timeframe='W'),
                   COUNT(*) FILTER (WHERE Timeframe='M')
            FROM {CURRENT}
        """).fetchone()
        con.execute("COMMIT")
        return {
            "expired_period_rows": expired,
            "total_current": total,
            "weekly_current": week_total,
            "monthly_current": month_total,
        }
    except BaseException:
        con.execute("ROLLBACK")
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=35,
                        help="Latest N AmiBroker trading bars (default: 35)")
    parser.add_argument("--csv", type=Path,
                        help="Replay an exported CSV without calling AmiBroker")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate/stage without creating or modifying tables")
    parser.add_argument("--min-tickers", type=int, default=100)
    parser.add_argument("--max-age-days", type=int, default=14,
                        help="Maximum age of newest exported quote (default: 14 days)")
    parser.add_argument("--as-of", type=date.fromisoformat,
                        default=datetime.now(timezone(timedelta(hours=7))).date(),
                        help="Calendar date for W/M period classification (YYYY-MM-DD)")
    args = parser.parse_args(argv)
    if args.days < 1 or args.min_tickers < 1 or args.max_age_days < 0:
        parser.error("--days and --min-tickers must be positive; --max-age-days >= 0")
    csv_path = args.csv.resolve() if args.csv else (
        settings.data_dir / "tmp_Export_Indicator_current.csv"
    )
    if args.csv is None:
        run_apx_export(csv_path, days=args.days)
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with factory.writer() as con:
        staged = stage_current(
            con, csv_path, as_of=args.as_of,
            min_tickers=args.min_tickers, max_age_days=args.max_age_days,
        )
        print("[APX CURRENT] STAGED", json.dumps(staged, ensure_ascii=False))
        if args.dry_run:
            print("[APX CURRENT] DRY RUN: no persistent DB changes")
            return 0
        committed = commit_current(con, as_of=args.as_of)
        print("[APX CURRENT] COMMITTED", json.dumps(committed, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
