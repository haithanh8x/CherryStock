"""Initial-load or upsert AmiBroker incremental indicator history (D/W/M)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
from cherrystock.config.settings import settings
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory
from scripts.indicator_apx_runner import export_incremental
from scripts.sync_amibroker_indicator_full import SPECS
from scripts.migrate_indicator_storage_v2 import SCHEMA

HISTORY = f'{SCHEMA}."cal_indicator_history"'
KEY = ("Ticker", "Date", "IndicatorName", "Timeframe")

def stage(con, csv: Path) -> int:
    if not csv.is_file() or not csv.stat().st_size:
        raise ValueError(f"Empty or missing export: {csv}")
    con.execute("CREATE OR REPLACE TEMP TABLE _history_csv AS SELECT * FROM read_csv(?, header=true, all_varchar=true)", [str(csv)])
    cols = {r[1] for r in con.execute("PRAGMA table_info('_history_csv')").fetchall()}
    date_col = "Date" if "Date" in cols else "Date/Time"
    required = {"Ticker", date_col} | {s.csv_column for s in SPECS}
    if required - cols:
        raise ValueError(f"Missing CSV columns: {sorted(required-cols)[:20]}")
    con.execute("""CREATE OR REPLACE TEMP TABLE _history_stage
        (Ticker VARCHAR, Date DATE, IndicatorName VARCHAR, Timeframe VARCHAR, Value DOUBLE)""")
    for spec in SPECS:
        name = spec.csv_column.rsplit("_", 1)[0].replace("'", "''")
        tf = spec.timeframe
        column = '"' + spec.csv_column.replace('"', '""') + '"'
        con.execute(f"""INSERT INTO _history_stage
            SELECT UPPER(TRIM("Ticker")), TRY_CAST(LEFT("{date_col}",10) AS DATE),
                   '{name}', '{tf}', TRY_CAST({column} AS DOUBLE)
            FROM _history_csv WHERE TRY_CAST({column} AS DOUBLE) IS NOT NULL""")
    invalid = con.execute("""SELECT COUNT(*) FROM _history_stage
        WHERE Ticker IS NULL OR Ticker='' OR Date IS NULL OR NOT isfinite(Value)""").fetchone()[0]
    if invalid:
        raise ValueError(f"Invalid history rows: {invalid}")
    duplicates = con.execute("""SELECT COUNT(*) FROM (
        SELECT Ticker, Date, IndicatorName, Timeframe FROM _history_stage
        GROUP BY ALL HAVING COUNT(*)>1)""").fetchone()[0]
    if duplicates:
        raise ValueError(f"Duplicate history keys: {duplicates}")
    count, tickers = con.execute("SELECT COUNT(*), COUNT(DISTINCT Ticker) FROM _history_stage").fetchone()
    if count == 0 or tickers < 1:
        raise ValueError("No valid history indicators")
    return count

def main(mode: str, argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, help="Use an existing CSV without running AmiBroker")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    bars = 600 if mode == "initial" else 10
    csv = args.csv or settings.data_dir / f"tmp_Export_Indicator_history_{mode}.csv"
    if args.csv is None:
        export_incremental(csv, bars)
    with DuckDBConnectionFactory(db_path=settings.local_db_path).writer() as con:
        count = stage(con, csv)
        print("[HISTORY] STAGED", json.dumps({"mode":mode,"bars":bars,"rows":count}))
        if args.dry_run:
            return 0
        con.execute("BEGIN TRANSACTION")
        try:
            con.execute(f"""CREATE TABLE IF NOT EXISTS {HISTORY} (
                Ticker VARCHAR NOT NULL, Date DATE NOT NULL,
                IndicatorName VARCHAR NOT NULL, Timeframe VARCHAR NOT NULL
                CHECK(Timeframe IN ('D','W','M')),
                Value DOUBLE, UpdatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (Ticker,Date,IndicatorName,Timeframe))""")
            if mode == "initial":
                existing = con.execute(f"SELECT COUNT(*) FROM {HISTORY}").fetchone()[0]
                if existing:
                    raise RuntimeError(f"History already has {existing} rows; initial load refused")
            # Older installations may have created the history table without a key.
            # Require the same primary key as the current history contract.
            has_pk = con.execute("""SELECT COUNT(*) FROM duckdb_constraints()
                WHERE table_name='cal_indicator_history' AND constraint_type='PRIMARY KEY'""").fetchone()[0]
            if not has_pk:
                con.execute(f"ALTER TABLE {HISTORY} ADD PRIMARY KEY (Ticker,Date,IndicatorName,Timeframe)")
            con.execute(f"""INSERT INTO {HISTORY}
                (Ticker,Date,IndicatorName,Timeframe,Value,UpdatedAt)
                SELECT Ticker,Date,IndicatorName,Timeframe,Value,CURRENT_TIMESTAMP
                FROM _history_stage
                ON CONFLICT (Ticker,Date,IndicatorName,Timeframe)
                DO UPDATE SET Value=excluded.Value,UpdatedAt=excluded.UpdatedAt""")
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
        print("[HISTORY] COMMITTED", json.dumps({"mode":mode,"staged_rows":count}))
    return 0
