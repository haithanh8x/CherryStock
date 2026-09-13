from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

# Production modules still use top-level imports such as Ults.* internally,
# so direct script execution needs src/ on sys.path in addition to repo root.
from CrawlStock.readYahooFinance import (  # noqa: E402
    YAHOO_OTHER_TICKERS,
    _normalize_yf_eod,
    syncYahooFinance_EOD,
)
from Ults.DuckLib import DuckDBManager  # noqa: E402

TARGET_TABLE = '"CherryMon"."main"."raw_other_eod"'


def _print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def _ticker_sql_list() -> str:
    return ", ".join("'" + ticker.replace("'", "''") + "'" for ticker in YAHOO_OTHER_TICKERS)


def check_database() -> bool:
    """Check whether Yahoo EOD rows exist and are current enough to diagnose ingestion."""
    _print_section("DuckDB target")
    ticker_values = _ticker_sql_list()

    try:
        with DuckDBManager(read_only=True) as con:
            table_exists = con.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'main'
                  AND table_name = 'raw_other_eod'
                """
            ).fetchone()[0]

            if not table_exists:
                print(f"FAIL: target table does not exist: {TARGET_TABLE}")
                return False

            summary = con.execute(
                f"""
                SELECT
                    Ticker,
                    MIN(Date) AS min_date,
                    MAX(Date) AS max_date,
                    COUNT(*) AS row_count,
                    COUNT(DISTINCT Date) AS trading_days
                FROM {TARGET_TABLE}
                WHERE Ticker IN ({ticker_values})
                GROUP BY Ticker
                ORDER BY Ticker
                """
            ).df()

            if summary.empty:
                print("FAIL: raw_other_eod contains no rows for configured Yahoo tickers.")
                print("Configured tickers:", ", ".join(YAHOO_OTHER_TICKERS))
                return False

            print(summary.to_string(index=False))

            present = set(summary["Ticker"].astype(str))
            missing = [ticker for ticker in YAHOO_OTHER_TICKERS if ticker not in present]
            if missing:
                print("WARN: configured tickers missing from DuckDB:", ", ".join(missing))

            latest = con.execute(
                f"""
                SELECT MAX(Date)
                FROM {TARGET_TABLE}
                WHERE Ticker IN ({ticker_values})
                """
            ).fetchone()[0]
            print(f"Latest Yahoo date in DuckDB: {latest}")

            duplicate_count = con.execute(
                f"""
                SELECT COUNT(*)
                FROM (
                    SELECT Ticker, Date, COUNT(*) AS n
                    FROM {TARGET_TABLE}
                    WHERE Ticker IN ({ticker_values})
                    GROUP BY Ticker, Date
                    HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0]
            print(f"Duplicate Ticker+Date groups: {duplicate_count}")

            if duplicate_count:
                print("FAIL: duplicate Yahoo logical keys detected.")
                return False

            return not missing
    except Exception as exc:
        print(f"FAIL: DuckDB check error: {type(exc).__name__}: {exc}")
        return False


def probe_yahoo(period: str) -> bool:
    """Probe Yahoo and run the production normalizer without writing to DuckDB."""
    _print_section(f"Yahoo source probe | period={period}")
    all_ok = True

    for ticker in YAHOO_OTHER_TICKERS:
        try:
            raw = yf.download(
                ticker,
                period=period,
                interval="1d",
                auto_adjust=True,
                progress=False,
            )
            normalized = _normalize_yf_eod(raw, ticker)

            if normalized.empty:
                print(f"FAIL {ticker}: Yahoo returned no usable normalized EOD rows.")
                all_ok = False
                continue

            min_date = normalized["Date"].min()
            max_date = normalized["Date"].max()
            print(
                f"PASS {ticker}: rows={len(normalized)} "
                f"range={min_date}..{max_date} close={normalized['Close'].iloc[-1]}"
            )
        except Exception as exc:
            print(f"FAIL {ticker}: {type(exc).__name__}: {exc}")
            all_ok = False

    return all_ok


def run_sync(days: int) -> bool:
    """Run the production Yahoo EOD sync explicitly when the operator requests it."""
    _print_section(f"Production Yahoo sync | days={days}")
    try:
        syncYahooFinance_EOD(from_last_day=days)
        print("Sync call completed. Rechecking DuckDB...")
        return check_database()
    except Exception as exc:
        print(f"FAIL: syncYahooFinance_EOD raised {type(exc).__name__}: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnose missing CherryStock Yahoo Finance EOD data. Read-only unless --sync is used."
    )
    parser.add_argument(
        "--period",
        default="10d",
        help="Yahoo probe period accepted by yfinance, default: 10d.",
    )
    parser.add_argument(
        "--db-only",
        action="store_true",
        help="Check DuckDB only; do not call Yahoo.",
    )
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="Probe Yahoo only; do not inspect DuckDB.",
    )
    parser.add_argument(
        "--sync",
        type=int,
        metavar="DAYS",
        help="Explicitly run production syncYahooFinance_EOD for DAYS, then verify DuckDB.",
    )
    args = parser.parse_args()

    if args.db_only and args.source_only:
        parser.error("--db-only and --source-only cannot be used together")

    print("CherryStock Yahoo EOD diagnostic")
    print("Date:", date.today().isoformat())
    print("Tickers:", ", ".join(YAHOO_OTHER_TICKERS))
    print("Target:", TARGET_TABLE)

    results: list[bool] = []

    if args.sync is not None:
        if args.sync < 1:
            parser.error("--sync DAYS must be >= 1")
        results.append(run_sync(args.sync))
    else:
        if not args.source_only:
            results.append(check_database())
        if not args.db_only:
            results.append(probe_yahoo(args.period))

    passed = bool(results) and all(results)
    _print_section("Verdict")
    print("PASS" if passed else "FAIL")
    print(
        "Action:",
        "STOP"
        if passed
        else "Use docs/runbook/Yahoo_EOD_Diagnostic.md and STOP after the matching branch.",
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
