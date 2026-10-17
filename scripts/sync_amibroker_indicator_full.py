"""Full-history AmiBroker AFL indicator refresh into CherryMon.cal_indicator_values.

The .apx is the executable source of truth for all indicator formulae; this
script is deliberately NOT a Python indicator calculation engine.

Workflow:
  1. Verify APX: All Symbols + All Quotes + Daily base periodicity.
  2. Run New Analysis / Explore via the existing Windows AmiBroker adapter.
  3. Stage and validate the entire wide CSV in DuckDB (no production writes).
  4. In ONE transaction, register minimal compatibility metadata automatically,
     DELETE old fact rows, INSERT every valid AFL result and verify row counts.

The legacy public views (vw_Ticker_indicators, vw_Indicator_config) still use
ConfigId metadata joins. Small dim rows are therefore maintained automatically,
never configured manually by daily operators. Production table/view schemas
and existing ConfigIds remain intact. No manual dim seeding is required.

Use --csv PATH for offline validation/replay of a previously exported full CSV.
Use --dry-run to validate without touching production tables.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.amibroker.windows_adapter import (  # noqa: E402
    WindowsAmiBrokerAdapter,
)
from cherrystock.infrastructure.database.connection import (  # noqa: E402
    DuckDBConnectionFactory,
)

SCHEMA = '"CherryMon"."main"'
FACT = f'{SCHEMA}."cal_indicator_values"'
INDICATORS = f'{SCHEMA}."dim_indicator"'
COMPONENTS = f'{SCHEMA}."dim_indicator_component"'
CONFIGS = f'{SCHEMA}."dim_indicator_config"'
DEFAULT_AFL = PROJECT_ROOT / "src" / "Amibroker" / "Formulas" / "CherryMon" / "Export_Indicator.afl"
SUFFIXES = ("D", "W", "M")

# These are output contracts, not user-maintained dimension configurations.
# Key is the exact AFL base column name; value is (indicator code, components).
FAMILIES = {
    "MA20": ("MA", ("VALUE",)),
    "MA50": ("MA", ("VALUE",)),
    "MA100": ("MA", ("VALUE",)),
    "MA200": ("MA", ("VALUE",)),
    "BB20_2": ("BB", ("LOWER", "MIDDLE", "UPPER", "WIDTH", "PERCENT")),
    "ATR14": ("ATR", ("VALUE",)),
    "RSI14": ("RSI", ("VALUE",)),
    "OBV": ("OBV", ("VALUE",)),
    "AD": ("AD", ("VALUE",)),
    "MACD12_26_9": ("MACD", ("LINE", "SIGNAL", "HIST")),
    "EMA9": ("EMA", ("VALUE",)),
    "EMA21": ("EMA", ("VALUE",)),
    "EMA50": ("EMA", ("VALUE",)),
    "EMA200": ("EMA", ("VALUE",)),
    "ADX14": ("ADX", ("ADX", "PLUS_DI", "MINUS_DI")),
    "ROC5": ("ROC", ("VALUE",)),
    "ROC10": ("ROC", ("VALUE",)),
    "ROC20": ("ROC", ("VALUE",)),
    "VOL_MA20": ("VOL_MA", ("VALUE",)),
    "VOL_MA50": ("VOL_MA", ("VALUE",)),
    "VOL_RATIO20": ("VOL_RATIO", ("VALUE",)),
    "HIGH52W": ("HIGH52W", ("VALUE",)),
    "LOW52W": ("LOW52W", ("VALUE",)),
    "STOCH14_3_3": ("STOCH", ("K", "D")),
    "MFI14": ("MFI", ("VALUE",)),
    "CMF20": ("CMF", ("VALUE",)),
    "VWAP20": ("VWAP", ("VALUE",)),
}
# Indicator code -> (category, library name, RequiredInputs).
DEFINITIONS = {
    "MA": ("TREND", "sma", ["Close"]),
    "BB": ("VOLATILITY", "bbands", ["Close"]),
    "ATR": ("VOLATILITY", "atr", ["High", "Low", "Close"]),
    "RSI": ("MOMENTUM", "rsi", ["Close"]),
    "OBV": ("VOLUME", "obv", ["Close", "Volume"]),
    "AD": ("VOLUME", "ad", ["High", "Low", "Close", "Volume"]),
    "MACD": ("MOMENTUM", "macd", ["Close"]),
    "EMA": ("TREND", "ema", ["Close"]),
    "ADX": ("TREND", "adx", ["High", "Low", "Close"]),
    "ROC": ("MOMENTUM", "roc", ["Close"]),
    "VOL_MA": ("VOLUME", "sma", ["Volume"]),
    "VOL_RATIO": ("VOLUME", "volume_ratio", ["Volume"]),
    "HIGH52W": ("STRUCTURE", "hhv", ["High"]),
    "LOW52W": ("STRUCTURE", "llv", ["Low"]),
    "STOCH": ("MOMENTUM", "stoch", ["High", "Low", "Close"]),
    "MFI": ("VOLUME", "mfi", ["High", "Low", "Close", "Volume"]),
    "CMF": ("VOLUME", "cmf", ["High", "Low", "Close", "Volume"]),
    "VWAP": ("VOLUME", "vwap", ["High", "Low", "Close", "Volume"]),
}
PRIMARY_COMPONENTS = {"BB": "UPPER", "MACD": "LINE", "ADX": "ADX", "STOCH": "K"}
SEMANTICS = {
    ("MA", "VALUE"): ("PRICE_LEVEL", "PRICE"),
    ("EMA", "VALUE"): ("PRICE_LEVEL", "PRICE"),
    ("BB", "LOWER"): ("PRICE_LEVEL", "PRICE"),
    ("BB", "MIDDLE"): ("PRICE_LEVEL", "PRICE"),
    ("BB", "UPPER"): ("PRICE_LEVEL", "PRICE"),
    ("BB", "WIDTH"): ("VOLATILITY", "PERCENT"),
    ("BB", "PERCENT"): ("RATIO", "RATIO"),
    ("ATR", "VALUE"): ("VOLATILITY_DISTANCE", "PRICE"),
    ("RSI", "VALUE"): ("OSCILLATOR", "INDEX"),
    ("OBV", "VALUE"): ("CUMULATIVE_FLOW", "VOLUME"),
    ("AD", "VALUE"): ("CUMULATIVE_FLOW", "VOLUME"),
}
EXPECTED_COLUMNS = {
    f"{base}_{component}_{tf}" if component != "VALUE" else f"{base}_{tf}"
    for base, (_, components) in FAMILIES.items()
    for component in components
    for tf in SUFFIXES
}


@dataclass(frozen=True)
class ColumnSpec:
    csv_column: str
    config_code: str
    indicator_code: str
    timeframe: str
    component: str
    parameters: str
    warmup_bars: int


def _column_specs() -> list[ColumnSpec]:
    result = []
    for base, (indicator_code, components) in FAMILIES.items():
        numeric = [int(v) for v in re.findall(r"\d+", base)]
        for tf in SUFFIXES:
            parameters: dict[str, int | float] = {}
            if base == "BB20_2":
                parameters = {"length": 20, "std": 2.0}
            elif base == "MACD12_26_9":
                parameters = {"fast": 12, "slow": 26, "signal": 9}
            elif base == "STOCH14_3_3":
                parameters = {"k": 14, "smooth_k": 3, "d": 3}
            elif numeric:
                parameters = {"length": numeric[0]}
            if base in ("HIGH52W", "LOW52W"):
                parameters = {"length": {"D": 252, "W": 52, "M": 12}[tf]}
            if base in ("OBV", "AD"):
                parameters = {}
            warmup = max(parameters.get("length", 1), parameters.get("slow", 1), 1)
            for comp in components:
                csv_column = f"{base}_{tf}" if comp == "VALUE" else f"{base}_{comp}_{tf}"
                result.append(
                    ColumnSpec(
                        csv_column=csv_column,
                        config_code=f"{base}_{tf}",
                        indicator_code=indicator_code,
                        timeframe=tf,
                        component=comp,
                        parameters=json.dumps(parameters, sort_keys=True),
                        warmup_bars=int(warmup),
                    )
                )
    return result


SPECS = _column_specs()
assert {item.csv_column for item in SPECS} == EXPECTED_COLUMNS


def validate_apx(apx: Path, afl: Path, *, incremental: bool = False) -> None:
    """Refuse partial-range or unrelated APX projects before any destructive write."""
    if not apx.is_file() or not afl.is_file():
        raise FileNotFoundError(f"Missing AFL/APX: {afl} | {apx}")
    root = ET.parse(apx).getroot()
    general = root.find("./General")
    backtest = root.find("./BacktestSettings")
    if general is None or backtest is None:
        raise ValueError("APX missing General or BacktestSettings section.")
    settings_to_check = (
        (general.findtext("RangeType"), "0", "Range: All quotations"),
        (backtest.findtext("Periodicity"), "0", "Periodicity: Daily"),
    )
    if incremental:
        # The saved APX may use N recent bars; the importer restricts the
        # actual fact changes to the latest N distinct trading dates.
        settings_to_check = settings_to_check[1:]
    for actual, expected, name in settings_to_check:
        if (actual or "").strip() != expected:
            raise ValueError(f"APX must use {name}; got {actual!r}. Save the project in AmiBroker.")
    # ApplyTo=2 is AmiBroker's saved "Filter" selection. The user's APX
    # deliberately selects the intended ticker universe via that filter.
    # Do not rewrite it to All symbols; CSV coverage checks protect the
    # full-table replacement from an unexpectedly narrow filter.
    apply_to = (general.findtext("ApplyTo") or "").strip()
    if apply_to not in {"0", "2"}:
        raise ValueError(
            f"APX ApplyTo must be 0 (All symbols) or 2 (Filter); got {apply_to!r}."
        )
    declared = (general.findtext("FormulaPath") or "").replace("\\", "/").lower()
    if not declared.endswith("/export_indicator.afl"):
        raise ValueError(f"Wrong APX formula: {declared!r}")
    embedded = general.findtext("FormulaContent") or ""
    if "CS_ExportIndicators" not in embedded:
        raise ValueError("APX has old/missing embedded indicator formula. Re-save current AFL in New Analysis.")


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def prepare_stage(
    connection, csv_path: Path, *, min_dates: int, min_tickers: int = 100,
    compare_existing: bool = True,
) -> dict[str, object]:
    """Stage full CSV and reject missing columns, parse errors or duplicates."""
    if not csv_path.is_file() or csv_path.stat().st_size == 0:
        raise FileNotFoundError(f"Missing/empty full exploration CSV: {csv_path}")

    connection.execute(
        "CREATE TEMP TABLE _afl_csv AS "
        "SELECT * FROM read_csv(?, header=true, all_varchar=true, auto_detect=true)",
        [str(csv_path)],
    )
    columns = [row[1] for row in connection.execute("PRAGMA table_info('_afl_csv')").fetchall()]
    date_column = "Date" if "Date" in columns else "Date/Time"
    if "Ticker" not in columns or date_column not in columns:
        raise ValueError(f"CSV missing Ticker or Date: {columns[:8]}")
    if len(columns) != len(set(columns)):
        raise ValueError("CSV has duplicate/renamed column headers.")
    missing = sorted(EXPECTED_COLUMNS - set(columns))
    unrecognized = sorted(
        c for c in columns if c not in EXPECTED_COLUMNS and c not in {"Ticker", date_column}
    )
    if missing or unrecognized:
        raise ValueError(
            f"CSV must contain all 108 D/W/M indicator columns. "
            f"missing={missing[:12]}, extra={unrecognized[:12]}; "
            "re-save APX with Timeframes=ALL."
        )

    connection.execute(
        "CREATE TEMP TABLE _afl_map "
        "(CsvColumn VARCHAR, ConfigCode VARCHAR, IndicatorCode VARCHAR, "
        "Timeframe VARCHAR, ComponentCode VARCHAR, Parameters VARCHAR, WarmupBars INTEGER)"
    )
    connection.executemany(
        "INSERT INTO _afl_map VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                s.csv_column,
                s.config_code,
                s.indicator_code,
                s.timeframe,
                s.component,
                s.parameters,
                s.warmup_bars,
            )
            for s in SPECS
        ],
    )
    # DuckDB UNPIVOT discards nulls and avoids keeping a huge Pandas melt.
    quoted = ", ".join(_quote(s.csv_column) for s in SPECS)
    connection.execute(
        f"CREATE TEMP TABLE _afl_unpivot AS "
        f"UNPIVOT _afl_csv ON {quoted} "
        "INTO NAME CsvColumn VALUE RawValue"
    )
    connection.execute(
        f"""
        CREATE TEMP TABLE _afl_stage AS
        SELECT
            UPPER(TRIM(CAST(u."Ticker" AS VARCHAR))) AS Ticker,
            COALESCE(
                TRY_CAST(CAST(u.{_quote(date_column)} AS VARCHAR) AS DATE),
                TRY_CAST(SUBSTR(CAST(u.{_quote(date_column)} AS VARCHAR), 1, 10) AS DATE)
            ) AS Date,
            m.ConfigCode,
            m.IndicatorCode,
            m.Timeframe,
            m.ComponentCode,
            NULLIF(TRIM(CAST(u.RawValue AS VARCHAR)), '') AS RawValue,
            TRY_CAST(NULLIF(TRIM(CAST(u.RawValue AS VARCHAR)), '') AS DOUBLE) AS Value
        FROM _afl_unpivot u
        INNER JOIN _afl_map m ON m.CsvColumn = u.CsvColumn
        WHERE NULLIF(TRIM(CAST(u.RawValue AS VARCHAR)), '') IS NOT NULL
        """
    )
    counts = connection.execute(
        """
        SELECT COUNT(*),
               COUNT(DISTINCT Ticker),
               COUNT(DISTINCT Date),
               MIN(Date), MAX(Date),
               COUNT(*) FILTER (WHERE Ticker = '' OR Date IS NULL OR Value IS NULL OR NOT isfinite(Value))
        FROM _afl_stage
        """
    ).fetchone()
    total, tickers, dates, date_min, date_max, invalid = counts
    if invalid:
        raise ValueError(f"AFL CSV contains {invalid} invalid ticker/date/numeric values")
    if not total or tickers < min_tickers or dates < min_dates:
        raise ValueError(
            f"Full historical export appears incomplete: rows={total} "
            f"tickers={tickers} (minimum {min_tickers}), "
            f"distinct_dates={dates} (minimum {min_dates})"
        )
    repeated = connection.execute(
        """
        SELECT Ticker, Date, ConfigCode, ComponentCode, COUNT(*) AS n
        FROM _afl_stage
        GROUP BY Ticker, Date, ConfigCode, ComponentCode
        HAVING COUNT(*) > 1 LIMIT 1
        """
    ).fetchone()
    if repeated is not None:
        raise ValueError(f"Duplicate indicator fact key in AFL export: {repeated}")
    present = {
        r[0] for r in connection.execute(
            "SELECT DISTINCT Timeframe FROM _afl_stage"
        ).fetchall()
    }
    if present != set(SUFFIXES):
        raise ValueError(f"Missing D/W/M values: actual={present}")

    previous = connection.execute(
        f"SELECT COUNT(*), COUNT(DISTINCT Ticker), MIN(Date), MAX(Date) FROM {FACT}"
    ).fetchone()
    if compare_existing and previous[1] >= 20 and tickers < 0.8 * previous[1]:
        raise ValueError(
            f"Ticker coverage decreased from {previous[1]} to {tickers}; "
            "refusing full replacement."
        )
    if compare_existing and previous[2] is not None and date_min > previous[2]:
        raise ValueError(
            f"Oldest indicator Date regressed from {previous[2]} to {date_min}; "
            "refusing partial historical overwrite."
        )
    if compare_existing and previous[3] is not None and date_max < previous[3]:
        raise ValueError(
            f"Latest indicator Date regressed from {previous[3]} to {date_max}; "
            "refusing stale AFL export."
        )
    if compare_existing and previous[0] >= 10000 and total < 0.8 * previous[0]:
        raise ValueError(
            f"Row coverage collapsed from {previous[0]} to {total}; "
            "refusing full replacement."
        )
    return {
        "rows": int(total),
        "tickers": int(tickers),
        "distinct_dates": int(dates),
        "min_date": str(date_min),
        "max_date": str(date_max),
        "old_rows": int(previous[0]),
        "old_tickers": int(previous[1]),
    }


def prepare_incremental_stage(
    connection, csv_path: Path, *, days: int = 10, min_tickers: int = 100
) -> dict[str, object]:
    """Validate the APX export then retain only the latest N distinct trading dates.

    Unlike full refresh, no historical min/max comparison is made against the
    entire existing fact. No missing (null) component is used as a deletion
    signal: incremental mode is strictly a key-based UPSERT.
    """
    if days < 1:
        raise ValueError("days must be >= 1")
    summary = prepare_stage_incremental(connection, csv_path, min_tickers=min_tickers)
    date_count = connection.execute(
        "SELECT COUNT(DISTINCT Date) FROM _afl_stage"
    ).fetchone()[0]
    if date_count < days:
        raise ValueError(
            f"Incremental APX exported only {date_count} distinct dates; "
            f"requested {days}. Set Range to at least {days} recent bars."
        )
    connection.execute(
        """
        DELETE FROM _afl_stage
        WHERE Date NOT IN (
            SELECT Date FROM (
                SELECT DISTINCT Date FROM _afl_stage
                ORDER BY Date DESC LIMIT ?
            )
        )
        """,
        [days],
    )
    dates = connection.execute(
        "SELECT MIN(Date), MAX(Date), COUNT(DISTINCT Date), COUNT(*) FROM _afl_stage"
    ).fetchone()
    summary.update(
        {"min_date": str(dates[0]), "max_date": str(dates[1]),
         "distinct_dates": int(dates[2]), "rows": int(dates[3]), "mode": "incremental"}
    )
    return summary


def prepare_stage_incremental(
    connection, csv_path: Path, *, min_tickers: int = 100
) -> dict[str, object]:
    """Use the shared full CSV parser but bypass full-history comparison guards.

    The previous fact is not deleted by this staging operation.
    """
    # Full staging validates all indicator columns and uniqueness, but its
    # historical comparison is not applicable to incremental updates.
    return prepare_stage(
        connection, csv_path, min_dates=1, min_tickers=min_tickers,
        compare_existing=False,
    )


def upsert_incremental(connection, stage_summary: dict[str, object]) -> dict[str, object]:
    """Atomic key-based MERGE; never truncate or delete historical fact rows."""
    connection.execute("BEGIN TRANSACTION")
    try:
        _ensure_metadata(connection)
        connection.execute(
            f"""
            MERGE INTO {FACT} AS dst
            USING (
                SELECT s.Ticker, s.Date, c.ConfigId,
                       s.ComponentCode, s.Value
                FROM _afl_stage s
                JOIN {CONFIGS} c ON c.ConfigCode = s.ConfigCode
            ) AS src
            ON dst.Ticker = src.Ticker
               AND dst.Date = src.Date
               AND dst.ConfigId = src.ConfigId
               AND dst.ComponentCode = src.ComponentCode
            WHEN MATCHED THEN
                UPDATE SET Value = src.Value, CalculatedAt = CURRENT_TIMESTAMP
            WHEN NOT MATCHED THEN
                INSERT (Ticker, Date, ConfigId, ComponentCode, Value, CalculatedAt)
                VALUES (src.Ticker, src.Date, src.ConfigId, src.ComponentCode,
                        src.Value, CURRENT_TIMESTAMP)
            """
        )
        affected = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM _afl_stage s
            JOIN {CONFIGS} c ON c.ConfigCode = s.ConfigCode
            JOIN {FACT} v ON v.Ticker = s.Ticker
                         AND v.Date = s.Date
                         AND v.ConfigId = c.ConfigId
                         AND v.ComponentCode = s.ComponentCode
            """
        ).fetchone()[0]
        if affected != stage_summary["rows"]:
            raise RuntimeError(
                f"Incremental verification failed: staged={stage_summary['rows']} "
                f"present={affected}"
            )
        connection.execute("COMMIT")
    except BaseException:
        connection.execute("ROLLBACK")
        raise
    return {"upserted": int(affected)}


def _ensure_metadata(connection) -> None:
    """Minimal, idempotent view-compatibility bridge; AFL owns calculations."""
    for indicator_code in sorted({s.indicator_code for s in SPECS}):
        category, function_name, required_inputs = DEFINITIONS[indicator_code]
        connection.execute(
            f"""
            INSERT INTO {INDICATORS}
                (IndicatorCode, IndicatorName, Category, Engine, FunctionName,
                 RequiredInputs, ParameterSchema, Description, IsActive)
            SELECT ?, ?, ?, 'AFL', ?, ?::JSON, NULL, 'AmiBroker AFL full export', TRUE
            WHERE NOT EXISTS (
                SELECT 1 FROM {INDICATORS} WHERE IndicatorCode = ?
            )
            """,
            [indicator_code, indicator_code, category, function_name,
             json.dumps(required_inputs), indicator_code],
        )
        connection.execute(
            f"UPDATE {INDICATORS} SET IsActive = TRUE WHERE IndicatorCode = ?",
            [indicator_code],
        )

    components = {
        (spec.indicator_code, spec.component)
        for spec in SPECS
    }
    for indicator_code, component in sorted(components):
        semantic, unit = SEMANTICS.get((indicator_code, component), (None, None))
        primary = component == PRIMARY_COMPONENTS.get(indicator_code, "VALUE")
        connection.execute(
            f"""
            INSERT INTO {COMPONENTS}
                (IndicatorCode, ComponentCode, ComponentName, OutputPrefix,
                 SortOrder, ValueSemantic, Unit, IsPrimary, IsActive)
            SELECT ?, ?, ?, NULL, 1, ?, ?, ?, TRUE
            WHERE NOT EXISTS (
                SELECT 1 FROM {COMPONENTS}
                WHERE IndicatorCode = ? AND ComponentCode = ?
            )
            """,
            [indicator_code, component, component, semantic, unit, primary,
             indicator_code, component],
        )
        connection.execute(
            f"""UPDATE {COMPONENTS} SET IsActive = TRUE
                WHERE IndicatorCode = ? AND ComponentCode = ?""",
            [indicator_code, component],
        )

    configs = {(s.config_code, s.indicator_code, s.timeframe, s.parameters, s.warmup_bars)
               for s in SPECS}
    for config_code, indicator_code, tf, parameters, warmup in sorted(configs):
        connection.execute(
            f"""
            INSERT INTO {CONFIGS}
                (ConfigCode, IndicatorCode, Timeframe, Parameters,
                 WarmupBars, IsEnabled, Description)
            SELECT ?, ?, ?, ?::JSON, ?, TRUE, 'AmiBroker AFL full-history export'
            WHERE NOT EXISTS (
                SELECT 1 FROM {CONFIGS} WHERE ConfigCode = ?
            )
            """,
            [config_code, indicator_code, tf, parameters, warmup, config_code],
        )
        connection.execute(
            f"UPDATE {CONFIGS} SET IsEnabled = TRUE WHERE ConfigCode = ?",
            [config_code],
        )


def replace_full_history(connection, stage_summary: dict[str, object]) -> dict[str, object]:
    """Atomically replace the entire legacy fact while preserving consumer IDs."""
    connection.execute("BEGIN TRANSACTION")
    try:
        _ensure_metadata(connection)
        missing_config = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM _afl_map m
            LEFT JOIN {CONFIGS} c ON c.ConfigCode = m.ConfigCode
            WHERE c.ConfigId IS NULL
            """
        ).fetchone()[0]
        if missing_config:
            raise RuntimeError(f"{missing_config} AFL ConfigCodes have no ConfigId mapping")

        # DELETE rather than an externally visible TRUNCATE: transaction ensures
        # the previous fact survives any insert, validation, or commit failure.
        connection.execute(f"DELETE FROM {FACT}")
        connection.execute(
            f"""
            INSERT INTO {FACT}
                (Ticker, Date, ConfigId, ComponentCode, Value, CalculatedAt)
            SELECT s.Ticker, s.Date, c.ConfigId, s.ComponentCode,
                   s.Value, CURRENT_TIMESTAMP
            FROM _afl_stage s
            INNER JOIN {CONFIGS} c ON c.ConfigCode = s.ConfigCode
            """
        )
        new_rows = int(connection.execute(f"SELECT COUNT(*) FROM {FACT}").fetchone()[0])
        if new_rows != stage_summary["rows"]:
            raise RuntimeError(
                f"Replacement row mismatch stage={stage_summary['rows']} fact={new_rows}"
            )
        public_rows = int(
            connection.execute(
                f'SELECT COUNT(*) FROM {SCHEMA}."vw_Ticker_indicators"'
            ).fetchone()[0]
        )
        if public_rows != new_rows:
            raise RuntimeError(
                f"Public view loses rows: fact={new_rows}, vw_Ticker_indicators={public_rows}"
            )
        connection.execute("COMMIT")
    except BaseException:
        connection.execute("ROLLBACK")
        raise
    return {"inserted": new_rows, "public_view_rows": public_rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--afl", type=Path, default=DEFAULT_AFL)
    parser.add_argument(
        "--csv", type=Path,
        help="Use an existing full-history CSV; bypass AmiBroker automation",
    )
    parser.add_argument("--dry-run", action="store_true", help="Stage/validate; no writes")
    parser.add_argument(
        "--min-tickers", type=int, default=100,
        help="Minimum distinct tickers for full-universe export (default 100)",
    )
    parser.add_argument(
        "--min-dates", type=int, default=200,
        help="Minimum distinct source dates proving All quotations export (default 200)",
    )
    args = parser.parse_args(argv)

    if args.min_dates < 1 or args.min_tickers < 1:
        parser.error("--min-dates and --min-tickers must be >= 1")

    if args.csv is None:
        validate_apx(args.afl.with_suffix(".apx"), args.afl)
        csv_path = settings.data_dir / "tmp_Export_Indicator_full.csv"
        WindowsAmiBrokerAdapter(
            database_path=settings.amibroker_database_path
        ).run_explore_export(
            formula_path=args.afl,
            export_path=csv_path,
            apply_to=2,  # Saved APX controls ApplyTo; adapter does not override it.
            range_mode=0,
            range_n=0,
            timeout_seconds=3600.0,
        )
    else:
        csv_path = args.csv.resolve()

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    # Stage and validate before starting any write transaction.
    with factory.writer() as connection:
        summary = prepare_stage(
            connection, csv_path,
            min_dates=args.min_dates, min_tickers=args.min_tickers,
        )
        print("[AFL Indicators] STAGED", json.dumps(summary, ensure_ascii=False))
        if args.dry_run:
            print("[AFL Indicators] DRY RUN: cal_indicator_values unchanged")
            return 0
        results = replace_full_history(connection, summary)
        print("[AFL Indicators] COMMITTED", json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
