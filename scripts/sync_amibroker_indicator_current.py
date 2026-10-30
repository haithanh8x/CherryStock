"""Replace the current (developing W/M) Indicator snapshot from AmiBroker APX.

Uses Export_Indicator.apx exactly as saved: ApplyTo=2, Daily periodicity,
Range=1 recent bar. Calculations run inside AmiBroker, not Python.

Validates the CSV BEFORE any persistent write. Then in one DuckDB transaction:
    VERIFY cal_indicator_current EXISTS;
    DELETE FROM cal_indicator_current;
    INSERT the validated latest-day W/M indicators.

This does NOT change cal_indicator_values or the APX/AFL originals. D values
belong to cal_indicator_values; the current V2 schema accepts W and M only.

Usage:
    python -m scripts.sync_amibroker_indicator_current --dry-run
    python -m scripts.sync_amibroker_indicator_current
    python -m scripts.sync_amibroker_indicator_current --csv C:/temp/export.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from cherrystock.config.settings import settings
from cherrystock.infrastructure.amibroker.windows_adapter import WindowsAmiBrokerAdapter
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory
from scripts.migrate_indicator_storage_v2 import CURRENT
from scripts.sync_amibroker_indicator_full import DEFAULT_AFL, SPECS

WM_SPECS = [s for s in SPECS if s.timeframe in ("W", "M")]
INDICATOR_COLUMNS = {s.csv_column for s in SPECS}
PRICE_COLUMNS = {f"{name}_{tf}" for name in ("OPEN", "HIGH", "LOW", "CLOSE")
                 for tf in ("D", "W", "M")}
CURRENT_COLUMNS = {"Ticker", "Date", "IndicatorName", "Timeframe", "Value", "UpdatedAt"}


def _q(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def validate_saved_apx(apx: Path) -> None:
    """The user's APX must export one latest daily bar; never modify it."""
    if not apx.is_file():
        raise FileNotFoundError(f"Missing AmiBroker APX: {apx}")
    root = ET.parse(apx).getroot()
    general = root.find("./General")
    backtest = root.find("./BacktestSettings")
    if general is None or backtest is None:
        raise ValueError("Export_Indicator.apx lacks General/BacktestSettings")
    checks = (
        (general.findtext("ApplyTo"), "2", "ApplyTo=2 (saved filter)"),
        (general.findtext("RangeType"), "2", "RangeType=2 (recent bars)"),
        (general.findtext("RangeAmount"), "1", "RangeAmount=1 (one recent bar)"),
        (backtest.findtext("Periodicity"), "0", "Periodicity=Daily"),
    )
    for actual, expected, label in checks:
        if (actual or "").strip() != expected:
            raise ValueError(f"Saved APX must use {label}, found {actual!r}: {apx}")
    declared = (general.findtext("FormulaPath") or "").replace("\\", "/").lower()
    if not declared.endswith("/export_indicator.afl"):
        raise ValueError(f"Saved APX points at a different formula: {declared}")
    embedded = general.findtext("FormulaContent") or ""
    if "CS_ExportIndicators" not in embedded:
        raise ValueError("APX FormulaContent does not contain the indicator exporter")


def run_apx(csv_path: Path) -> None:
    validate_saved_apx(DEFAULT_AFL.with_suffix(".apx"))
    WindowsAmiBrokerAdapter(
        database_path=settings.amibroker_database_path
    ).run_explore_export(
        formula_path=DEFAULT_AFL,
        export_path=csv_path,
        apply_to=2,
        range_mode=2,
        range_n=1,
        timeout_seconds=3600.0,
    )


def stage_current(con, csv_path: Path, *, today: date, min_tickers: int,
                  max_age_days: int) -> dict:
    """Stage a *single latest trading date*; reject bad or incomplete exports."""
    if not csv_path.is_file() or csv_path.stat().st_size == 0:
        raise FileNotFoundError(f"Missing/empty APX export: {csv_path}")

    con.execute(
        "CREATE OR REPLACE TEMP TABLE _apx_current_csv AS "
        "SELECT * FROM read_csv(?, header=true, all_varchar=true, auto_detect=true)",
        [str(csv_path)],
    )
    columns = [row[1] for row in con.execute(
        "PRAGMA table_info('_apx_current_csv')"
    ).fetchall()]
    actual = set(columns)
    date_field = "Date" if "Date" in actual else "Date/Time"
    if "Ticker" not in actual or date_field not in actual:
        raise ValueError("APX CSV lacks Ticker and Date/Date/Time")
    missing = INDICATOR_COLUMNS - actual
    extra = actual - INDICATOR_COLUMNS - PRICE_COLUMNS - {"Ticker", date_field}
    if missing or extra:
        raise ValueError(
            f"APX CSV columns mismatch: missing={sorted(missing)[:12]}, "
            f"unexpected={sorted(extra)[:12]}; Timeframes must be ALL."
        )
    if len(columns) != len(actual):
        raise ValueError("APX CSV contains duplicate headers")

    raw_date = _q(date_field)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE _apx_current_source AS
        SELECT UPPER(TRIM(CAST("Ticker" AS VARCHAR))) AS Ticker,
               COALESCE(
                   TRY_CAST(CAST({raw_date} AS VARCHAR) AS DATE),
                   TRY_CAST(SUBSTR(CAST({raw_date} AS VARCHAR), 1, 10) AS DATE)
               ) AS Date
        FROM _apx_current_csv
    """)
    invalid = con.execute("""
        SELECT COUNT(*) FROM _apx_current_source
        WHERE Ticker IS NULL OR Ticker = '' OR Date IS NULL
    """).fetchone()[0]
    if invalid:
        raise ValueError(f"APX CSV has {invalid} invalid Ticker/Date rows")
    duplicate_source = con.execute("""
        SELECT Ticker, Date, COUNT(*) AS n
        FROM _apx_current_source GROUP BY Ticker, Date
        HAVING COUNT(*) > 1 LIMIT 1
    """).fetchone()
    if duplicate_source:
        raise ValueError(f"APX CSV repeats the same Ticker/Date: {duplicate_source}")

    source_tickers, latest_date = con.execute("""
        SELECT COUNT(DISTINCT Ticker), MAX(Date) FROM _apx_current_source
    """).fetchone()
    if source_tickers < min_tickers:
        raise ValueError(
            f"APX coverage too low: {source_tickers} tickers < {min_tickers}"
        )
    if latest_date is None or not (
        today - timedelta(days=max_age_days) <= latest_date <= today
    ):
        raise ValueError(
            f"Stale/future APX export: latest_date={latest_date}, today={today}, "
            f"max_age_days={max_age_days}"
        )

    # The APX's one recent bar is per symbol; some symbols may lag. Keep only
    # the most recent market date, never mix stale symbols into the snapshot.
    latest_tickers = con.execute("""
        SELECT COUNT(DISTINCT Ticker) FROM _apx_current_source WHERE Date=?
    """, [latest_date]).fetchone()[0]
    if latest_tickers < min_tickers:
        raise ValueError(
            f"Only {latest_tickers} tickers have the latest date {latest_date}; "
            f"min_tickers={min_tickers}. Refusing to replace current snapshot."
        )

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
        "CREATE OR REPLACE TEMP TABLE _apx_current_unpivot AS "
        f"UNPIVOT _apx_current_csv ON {quoted} "
        "INTO NAME CsvColumn VALUE RawValue"
    )
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE _apx_current_parsed AS
        SELECT UPPER(TRIM(CAST(u."Ticker" AS VARCHAR))) AS Ticker,
               COALESCE(
                   TRY_CAST(CAST(u.{raw_date} AS VARCHAR) AS DATE),
                   TRY_CAST(SUBSTR(CAST(u.{raw_date} AS VARCHAR), 1, 10) AS DATE)
               ) AS Date,
               m.IndicatorName, m.Timeframe,
               TRY_CAST(NULLIF(TRIM(CAST(u.RawValue AS VARCHAR)), '') AS DOUBLE) AS Value
        FROM _apx_current_unpivot u
        INNER JOIN _apx_current_map m ON u.CsvColumn=m.CsvColumn
        WHERE NULLIF(TRIM(CAST(u.RawValue AS VARCHAR)), '') IS NOT NULL
    """)
    invalid_values = con.execute("""
        SELECT COUNT(*) FROM _apx_current_parsed
        WHERE Ticker IS NULL OR Ticker='' OR Date IS NULL
           OR Value IS NULL OR NOT ISFINITE(Value)
    """).fetchone()[0]
    if invalid_values:
        raise ValueError(f"APX CSV contains {invalid_values} invalid W/M values")
    duplicate_values = con.execute("""
        SELECT Ticker, Date, IndicatorName, Timeframe, COUNT(*) AS n
        FROM _apx_current_parsed
        GROUP BY Ticker, Date, IndicatorName, Timeframe
        HAVING COUNT(*) > 1 LIMIT 1
    """).fetchone()
    if duplicate_values:
        raise ValueError(f"Duplicate Indicator rows in CSV: {duplicate_values}")

    con.execute("""
        CREATE OR REPLACE TEMP TABLE _apx_current_stage AS
        SELECT Ticker, Date, IndicatorName, Timeframe, Value
        FROM _apx_current_parsed
        WHERE Date=?
    """, [latest_date])
    total, weekly, monthly, week_tickers, month_tickers = con.execute("""
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE Timeframe='W'),
               COUNT(*) FILTER (WHERE Timeframe='M'),
               COUNT(DISTINCT Ticker) FILTER (WHERE Timeframe='W'),
               COUNT(DISTINCT Ticker) FILTER (WHERE Timeframe='M')
        FROM _apx_current_stage
    """).fetchone()
    if not total or week_tickers < min_tickers or month_tickers < min_tickers:
        raise ValueError(
            f"Incomplete latest-day W/M snapshot at {latest_date}: "
            f"W={week_tickers}, M={month_tickers} tickers "
            f"(required >= {min_tickers}). No data will be deleted."
        )
    return {
        "csv": str(csv_path), "latest_date": str(latest_date),
        "source_tickers": source_tickers, "latest_date_tickers": latest_tickers,
        "snapshot_rows": total, "weekly_rows": weekly, "monthly_rows": monthly,
        "weekly_tickers": week_tickers, "monthly_tickers": month_tickers,
        "ohlc_columns_ignored": len(actual & PRICE_COLUMNS),
    }


def replace_current(con, *, latest_date: date, expected_rows: int) -> dict:
    """All-or-nothing replace. DELETE and INSERT share one transaction."""
    con.execute("BEGIN TRANSACTION")
    try:
        kind = con.execute("""
            SELECT table_type FROM information_schema.tables
            WHERE table_catalog='CherryMon' AND table_schema='main'
              AND table_name='cal_indicator_current'
        """).fetchone()
        if kind and kind[0] != "BASE TABLE":
            raise RuntimeError("cal_indicator_current exists but is not a table")
        # The table must exist. Schema creation is managed separately.
        try:
            con.execute(f"SELECT * FROM {CURRENT} LIMIT 0")
        except Exception as exc:
            raise RuntimeError(
                "Missing or inaccessible CherryMon.main.cal_indicator_current. "
                "Create it separately before running this script. "
                "No current indicator data has been deleted."
            ) from exc
        columns = {item[0] for item in con.description}
        if not CURRENT_COLUMNS.issubset(columns):
            raise RuntimeError(
                f"cal_indicator_current schema is incompatible: {sorted(columns)}"
            )

        previous_date = con.execute(
            f"SELECT MAX(Date) FROM {CURRENT}"
        ).fetchone()[0]
        if previous_date is not None and latest_date < previous_date:
            raise ValueError(
                f"APX latest date {latest_date} is older than current table "
                f"date {previous_date}; refusing destructive replacement."
            )
        old_rows = int(con.execute(
            f"SELECT COUNT(*) FROM {CURRENT}"
        ).fetchone()[0])
        con.execute(f"DELETE FROM {CURRENT}")
        con.execute(f"""
            INSERT INTO {CURRENT}
                (Ticker,Date,IndicatorName,Timeframe,Value,UpdatedAt)
            SELECT Ticker,Date,IndicatorName,Timeframe,Value,CURRENT_TIMESTAMP
            FROM _apx_current_stage
        """)
        new_rows, new_dates, actual_date = con.execute(f"""
            SELECT COUNT(*), COUNT(DISTINCT Date), MAX(Date) FROM {CURRENT}
        """).fetchone()
        if new_rows != expected_rows or new_dates != 1 or actual_date != latest_date:
            raise RuntimeError(
                f"Snapshot verification failed: expected={expected_rows} "
                f"actual={new_rows}, dates={new_dates}, maxdate={actual_date}"
            )
        con.execute("COMMIT")
    except BaseException:
        con.execute("ROLLBACK")
        raise
    return {
        "previous_rows_deleted": old_rows,
        "inserted": new_rows,
        "latest_date": str(latest_date),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path,
                        help="Replay an AmiBroker CSV instead of running APX")
    parser.add_argument("--dry-run", action="store_true",
                        help="Export and validate, without persistent DB writes")
    parser.add_argument("--min-tickers", type=int, default=100)
    parser.add_argument("--max-age-days", type=int, default=14,
                        help="Maximum allowed age of latest trading date")
    args = parser.parse_args(argv)
    if args.min_tickers < 1 or args.max_age_days < 0:
        parser.error("--min-tickers must be >= 1 and --max-age-days >= 0")

    csv_path = args.csv.resolve() if args.csv else (
        settings.data_dir / "tmp_Export_Indicator_current.csv"
    )
    if args.csv is None:
        run_apx(csv_path)

    today = datetime.now(timezone(timedelta(hours=7))).date()
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with factory.writer() as con:
        staged = stage_current(
            con, csv_path, today=today,
            min_tickers=args.min_tickers, max_age_days=args.max_age_days,
        )
        print("[APX CURRENT] STAGED", json.dumps(staged, ensure_ascii=False))
        if args.dry_run:
            print("[APX CURRENT] DRY RUN: cal_indicator_current unchanged")
            return 0
        committed = replace_current(
            con,
            latest_date=date.fromisoformat(staged["latest_date"]),
            expected_rows=staged["snapshot_rows"],
        )
        print("[APX CURRENT] COMMITTED", json.dumps(committed, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
