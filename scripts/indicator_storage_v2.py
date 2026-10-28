"""AmiBroker APX -> DuckDB normalized indicator history + developing W/M.

No Python indicator calculations. Existing saved APX is the source of the
symbol filter (ApplyTo=2), Periodicity=Daily and its embedded AFL formula.
A temporary APX/AFL copy injects the exact incremental bar count and ALL
timeframes, leaving the user's saved project unmodified.

Run:
    python -m scripts.sync_amibroker_indicator_full --mode incremental --days 35
    python -m scripts.sync_amibroker_indicator_full --csv path/to/export.csv --mode incremental --days 10
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cherrystock.config.settings import settings
from cherrystock.infrastructure.amibroker.windows_adapter import WindowsAmiBrokerAdapter
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory
from scripts.migrate_indicator_storage_v2 import FACT, CURRENT, require_v2
from scripts.sync_amibroker_indicator_full import (
    DEFAULT_AFL, SPECS, _ensure_metadata, validate_apx,
)

ALL_COLUMNS = {spec.csv_column for spec in SPECS}
MAP_ROWS = sorted({
    (spec.csv_column, spec.csv_column.rsplit("_", 1)[0], spec.timeframe)
    for spec in SPECS
})


def _quote(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _runtime_formula(formula: str, *, days: int | None) -> str:
    """Force parameters in the temporary formula, not persisted AmiBroker params."""
    if days is None:
        mode = 'x_exportMode = "FULL";'
        count = 'x_exportDays = 10;'
    else:
        mode = 'x_exportMode = "INCREMENTAL";'
        count = f'x_exportDays = {days};'
    changes = (
        (r'x_exportMode = ParamList\( "Export mode", "FULL\|INCREMENTAL", 1 \);', mode),
        (r'x_exportDays = Param\( "Incremental trading bars", 10, 1, 365, 1 \);', count),
        (r'x_tfSelection = ParamList\( "Timeframes", "ALL\|D\|W\|M", 0 \);',
         'x_tfSelection = "ALL";'),
    )
    for pattern, replacement in changes:
        formula, matches = re.subn(pattern, lambda _: replacement, formula)
        if matches != 1:
            raise RuntimeError(f"APX embedded AFL is out of sync: {pattern}")
    return formula


def run_apx_export(destination: Path, *, days: int | None) -> None:
    original = DEFAULT_AFL.with_suffix(".apx")
    validate_apx(original, DEFAULT_AFL, incremental=days is not None)
    # The APX embeds its own AFL: editing the .afl on disk alone has no effect.
    with tempfile.TemporaryDirectory(prefix="cherrystock_indicator_") as td:
        temp = Path(td)
        runtime_afl = temp / "Export_Indicator_runtime.afl"
        runtime_apx = runtime_afl.with_suffix(".apx")
        tree = ET.parse(original)
        root = tree.getroot()
        formula_node = root.find("./General/FormulaContent")
        path_node = root.find("./General/FormulaPath")
        if formula_node is None or path_node is None or not formula_node.text:
            raise RuntimeError("APX FormulaContent/FormulaPath missing")
        # Saved APX contains literal backslash-r/backslash-n encoded lines.
        # Preserve the saved representation when injecting runtime parameters.
        embedded = formula_node.text
        formula_node.text = _runtime_formula(embedded, days=days)
        runtime_afl.write_text(
            _runtime_formula(DEFAULT_AFL.read_text(encoding="utf-8"), days=days),
            encoding="utf-8",
        )
        path_node.text = str(runtime_afl)
        # Use All quotations: AFL itself restricts output, but its indicators
        # still need complete OHLC history for OBV, AD, EMA and W/M.
        general = root.find("./General")
        backtest = root.find("./BacktestSettings")
        if general is not None and general.find("RangeType") is not None:
            general.find("RangeType").text = "0"
        if backtest is not None and backtest.find("RangeType") is not None:
            backtest.find("RangeType").text = "0"
        tree.write(runtime_apx, encoding="utf-8", xml_declaration=True)
        WindowsAmiBrokerAdapter(
            database_path=settings.amibroker_database_path
        ).run_explore_export(
            formula_path=runtime_afl,
            export_path=destination,
            apply_to=2,
            range_mode=0,
            range_n=0,
            timeout_seconds=3600.0,
        )


def stage_csv(connection, csv_path: Path, *, days: int | None, min_tickers: int) -> dict:
    if not csv_path.is_file() or csv_path.stat().st_size == 0:
        raise FileNotFoundError(f"Missing or empty AmiBroker export: {csv_path}")
    connection.execute(
        "CREATE OR REPLACE TEMP TABLE _indicator_csv AS "
        "SELECT * FROM read_csv(?, header=true, all_varchar=true, auto_detect=true)",
        [str(csv_path)],
    )
    columns = [r[1] for r in connection.execute("PRAGMA table_info('_indicator_csv')").fetchall()]
    date_column = "Date" if "Date" in columns else "Date/Time"
    if "Ticker" not in columns or date_column not in columns:
        raise ValueError("APX export missing Ticker/Date")
    if not ALL_COLUMNS.issubset(columns) or set(columns) - ALL_COLUMNS - {"Ticker", date_column}:
        raise ValueError(
            f"APX schema mismatch: missing={sorted(ALL_COLUMNS-set(columns))[:12]}, "
            f"unexpected={sorted(set(columns)-ALL_COLUMNS-{'Ticker',date_column})[:12]}. "
            "Ensure Timeframes=ALL and use the saved Export_Indicator APX."
        )
    connection.execute(
        "CREATE OR REPLACE TEMP TABLE _indicator_map "
        "(CsvColumn VARCHAR, IndicatorName VARCHAR, Timeframe VARCHAR)"
    )
    connection.executemany("INSERT INTO _indicator_map VALUES (?, ?, ?)", MAP_ROWS)
    quoted = ", ".join(_quote(s) for s in sorted(ALL_COLUMNS))
    connection.execute(
        f"CREATE OR REPLACE TEMP TABLE _indicator_unpivot AS "
        f"UNPIVOT _indicator_csv ON {quoted} "
        "INTO NAME CsvColumn VALUE RawValue"
    )
    connection.execute(f"""
        CREATE OR REPLACE TEMP TABLE _indicator_stage AS
        SELECT UPPER(TRIM(CAST(u."Ticker" AS VARCHAR))) AS Ticker,
               COALESCE(TRY_CAST(CAST(u.{_quote(date_column)} AS VARCHAR) AS DATE),
                        TRY_CAST(SUBSTR(CAST(u.{_quote(date_column)} AS VARCHAR),1,10) AS DATE)) AS Date,
               m.IndicatorName, m.Timeframe,
               TRY_CAST(TRIM(CAST(u.RawValue AS VARCHAR)) AS DOUBLE) AS Value,
               CAST(u.RawValue AS VARCHAR) AS RawValue
        FROM _indicator_unpivot u
        JOIN _indicator_map m ON m.CsvColumn = u.CsvColumn
        WHERE NULLIF(TRIM(CAST(u.RawValue AS VARCHAR)), '') IS NOT NULL
    """)
    invalid = connection.execute("""
        SELECT COUNT(*) FROM _indicator_stage
        WHERE Ticker = '' OR Date IS NULL OR Value IS NULL OR NOT ISFINITE(Value)
    """).fetchone()[0]
    if invalid:
        raise ValueError(f"Invalid AmiBroker numeric/ticker/date fields: {invalid}")
    duplicate = connection.execute("""
        SELECT Ticker, Date, IndicatorName, Timeframe, COUNT(*) AS n
        FROM _indicator_stage
        GROUP BY Ticker, Date, IndicatorName, Timeframe
        HAVING COUNT(*) > 1 LIMIT 1
    """).fetchone()
    if duplicate:
        raise ValueError(f"Duplicate indicator key in APX export: {duplicate}")
    ticker_count, date_count = connection.execute(
        "SELECT COUNT(DISTINCT Ticker), COUNT(DISTINCT Date) FROM _indicator_stage"
    ).fetchone()
    if ticker_count < min_tickers:
        raise ValueError(f"Export ticker coverage too low: {ticker_count} < {min_tickers}")
    if days is not None and date_count < days:
        raise ValueError(
            f"APX yielded {date_count} distinct dates, but --days={days}. "
            "Check AmiBroker price history and saved ticker filter."
        )
    if days is not None:
        connection.execute("""
            DELETE FROM _indicator_stage WHERE Date NOT IN (
                SELECT Date FROM (
                    SELECT DISTINCT Date FROM _indicator_stage
                    ORDER BY Date DESC LIMIT ?
                ) d
            )
        """, [days])
    # A stale APX/source snapshot must not revert newer committed history.
    last_history = connection.execute(
        f"SELECT MAX(Date) FROM {FACT} WHERE Timeframe = 'D'"
    ).fetchone()[0]
    last_export = connection.execute(
        "SELECT MAX(Date) FROM _indicator_stage WHERE Timeframe = 'D'"
    ).fetchone()[0]
    if last_history is not None and (last_export is None or last_export < last_history):
        raise ValueError(f"Stale export {last_export}; stored Daily is at {last_history}")

    summary = connection.execute("""
        SELECT COUNT(*), COUNT(DISTINCT Ticker), COUNT(DISTINCT Date),
               COUNT(*) FILTER (WHERE Timeframe='D'),
               COUNT(*) FILTER (WHERE Timeframe='W'),
               COUNT(*) FILTER (WHERE Timeframe='M'),
               MIN(Date), MAX(Date)
        FROM _indicator_stage
    """).fetchone()
    return dict(zip(
        ("rows", "tickers", "dates", "daily_values", "weekly_values",
         "monthly_values", "min_date", "max_date"),
        [str(v) if i in (6,7) and v is not None else v for i,v in enumerate(summary)],
    ))


def _split_current_and_history(con) -> None:
    con.execute("""
        CREATE OR REPLACE TEMP TABLE _indicator_history AS
        SELECT Ticker, Date, IndicatorName, Timeframe, Value
        FROM _indicator_stage
        WHERE Timeframe = 'D'
           OR (Timeframe = 'W' AND Date < CAST(DATE_TRUNC('week', CURRENT_DATE) AS DATE))
           OR (Timeframe = 'M' AND Date < CAST(DATE_TRUNC('month', CURRENT_DATE) AS DATE))
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE _indicator_current AS
        SELECT Ticker, Date, IndicatorName, Timeframe, Value
        FROM _indicator_stage
        WHERE (Timeframe = 'W' AND Date >= CAST(DATE_TRUNC('week', CURRENT_DATE) AS DATE))
           OR (Timeframe = 'M' AND Date >= CAST(DATE_TRUNC('month', CURRENT_DATE) AS DATE))
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY Ticker, IndicatorName, Timeframe ORDER BY Date DESC
        ) = 1
    """)


def commit_stage(con, summary: dict) -> dict:
    _split_current_and_history(con)
    count_history = con.execute("SELECT COUNT(*) FROM _indicator_history").fetchone()[0]
    count_current = con.execute("SELECT COUNT(*) FROM _indicator_current").fetchone()[0]
    con.execute("BEGIN TRANSACTION")
    try:
        # Keep legacy metadata for view consumers, not in either v2 table.
        _ensure_metadata(con)
        con.execute(f"""
            INSERT INTO {FACT} (Ticker,Date,IndicatorName,Timeframe,Value,UpdatedAt)
            SELECT Ticker,Date,IndicatorName,Timeframe,Value,CURRENT_TIMESTAMP
            FROM _indicator_history
            WHERE TRUE
            ON CONFLICT (Ticker,Date,IndicatorName,Timeframe)
            DO UPDATE SET Value=EXCLUDED.Value,UpdatedAt=EXCLUDED.UpdatedAt
        """)
        # Expire previous developing W/M when their calendar period rolls.
        # Closed results are taken only from the exported completed bar, not
        # from the prior provisional snapshot.
        con.execute(f"""
            DELETE FROM {CURRENT}
            WHERE (Timeframe='W' AND Date < CAST(DATE_TRUNC('week',CURRENT_DATE) AS DATE))
               OR (Timeframe='M' AND Date < CAST(DATE_TRUNC('month',CURRENT_DATE) AS DATE))
        """)
        con.execute(f"""
            INSERT INTO {CURRENT} (Ticker,Date,IndicatorName,Timeframe,Value,UpdatedAt)
            SELECT Ticker,Date,IndicatorName,Timeframe,Value,CURRENT_TIMESTAMP
            FROM _indicator_current
            WHERE TRUE
            ON CONFLICT (Ticker,IndicatorName,Timeframe)
            DO UPDATE SET Date=EXCLUDED.Date,Value=EXCLUDED.Value,
                          UpdatedAt=EXCLUDED.UpdatedAt
        """)
        con.execute("COMMIT")
    except BaseException:
        con.execute("ROLLBACK")
        raise
    return {"history_upserted": int(count_history),
            "current_upserted": int(count_current), "source_rows": summary["rows"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("full", "incremental"), default="incremental")
    parser.add_argument("--days", type=int, default=35)
    parser.add_argument("--csv", type=Path, help="Replay an existing APX CSV without AmiBroker")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--min-tickers", type=int, default=100)
    # Preserve CLI compatibility of old runbook; this is only relevant to full mode.
    parser.add_argument("--min-dates", type=int, default=200)
    parser.add_argument("--afl", type=Path, default=DEFAULT_AFL)
    args = parser.parse_args(argv)
    if args.days < 1 or args.min_tickers < 1:
        parser.error("--days and --min-tickers must be >= 1")
    if args.afl.resolve() != DEFAULT_AFL.resolve():
        parser.error("Only the canonical saved Export_Indicator.apx is supported")
    csv_path = args.csv.resolve() if args.csv else (
        settings.data_dir / f"tmp_Export_Indicator_{args.mode}.csv"
    )
    if args.csv is None:
        run_apx_export(csv_path, days=args.days if args.mode == "incremental" else None)
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with factory.writer() as con:
        require_v2(con)
        summary = stage_csv(
            con, csv_path, days=args.days if args.mode == "incremental" else None,
            min_tickers=args.min_tickers,
        )
        if args.mode == "full" and summary["dates"] < args.min_dates:
            raise ValueError("Full export lacks sufficient historical dates")
        print("[AFL INDICATORS] STAGED", json.dumps(summary, ensure_ascii=False))
        if args.dry_run:
            print("[AFL INDICATORS] DRY RUN: no writes")
            return 0
        result = commit_stage(con, summary)
        print("[AFL INDICATORS] COMMITTED", json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
