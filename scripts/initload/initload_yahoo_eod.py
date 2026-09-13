from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from CrawlStock.readYahooFinance import (  # noqa: E402
    YAHOO_OTHER_TICKERS,
    syncYahooFinance_EOD,
)
from Ults.DuckLib import DuckDBManager  # noqa: E402

DEFAULT_START_DATE = "2024-04-01"
TARGET_TABLE = '"CherryMon"."main"."raw_other_eod"'


def _ticker_sql_list() -> str:
    return ", ".join("'" + ticker.replace("'", "''") + "'" for ticker in YAHOO_OTHER_TICKERS)


def _parse_iso_date(value: str, name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {name}: {value!r}. Expected YYYY-MM-DD.") from exc


def _verify(start_date: str, end_date: str | None) -> bool:
    start = _parse_iso_date(start_date, "start_date")
    end = _parse_iso_date(end_date, "end_date") if end_date else None
    ticker_values = _ticker_sql_list()

    with DuckDBManager(read_only=True) as con:
        params: list[object] = [start]
        end_filter = ""
        if end is not None:
            end_filter = "AND Date < ?"
            params.append(end)

        summary = con.execute(
            f"""
            SELECT
                Ticker,
                MIN(Date) AS min_date,
                MAX(Date) AS max_date,
                COUNT(*) AS row_count
            FROM {TARGET_TABLE}
            WHERE Ticker IN ({ticker_values})
              AND Date >= ?
              {end_filter}
            GROUP BY Ticker
            ORDER BY Ticker
            """,
            params,
        ).df()

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

    print("\n=== Historical Yahoo rows in DuckDB ===")
    if summary.empty:
        print("FAIL: no Yahoo rows found in requested historical window.")
        return False

    print(summary.to_string(index=False))
    print(f"Duplicate Ticker+Date groups: {duplicate_count}")

    present = set(summary["Ticker"].astype(str))
    missing = [ticker for ticker in YAHOO_OTHER_TICKERS if ticker not in present]
    if missing:
        print("FAIL: missing configured Yahoo tickers:", ", ".join(missing))
        return False

    # A mixed-calendar source may not trade exactly on the requested start date.
    latest_allowed_first_date = start + timedelta(days=7)
    late_tickers = []
    for row in summary.itertuples(index=False):
        if row.min_date is None or row.min_date > latest_allowed_first_date:
            late_tickers.append(str(row.Ticker))

    if late_tickers:
        print(
            "FAIL: no rows close enough to requested start date for:",
            ", ".join(late_tickers),
        )
        return False

    if duplicate_count:
        print("FAIL: duplicate Yahoo logical keys detected.")
        return False

    print("PASS: historical Yahoo EOD window is present and logical keys are unique.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Idempotently backfill CherryStock Yahoo EOD into raw_other_eod. "
            "Default start date: 2024-04-01."
        )
    )
    parser.add_argument(
        "--start",
        default=DEFAULT_START_DATE,
        help=f"Inclusive Yahoo start date, default: {DEFAULT_START_DATE}.",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="Optional exclusive Yahoo end date (YYYY-MM-DD). Default: latest available.",
    )
    args = parser.parse_args()

    start = _parse_iso_date(args.start, "start_date")
    end = _parse_iso_date(args.end, "end_date") if args.end else None
    if end is not None and end <= start:
        parser.error("--end must be later than --start")

    print("=" * 72)
    print("CherryStock - YAHOO EOD HISTORICAL INITLOAD")
    print("=" * 72)
    print("Target:", TARGET_TABLE)
    print("Tickers:", ", ".join(YAHOO_OTHER_TICKERS))
    print("Start (inclusive):", start.isoformat())
    print("End (exclusive):", end.isoformat() if end else "latest available")
    print("Write mode: INSERT ... ON CONFLICT (Ticker, Date) DO UPDATE")

    syncYahooFinance_EOD(
        start_date=start.isoformat(),
        end_date=end.isoformat() if end else None,
    )

    passed = _verify(
        start_date=start.isoformat(),
        end_date=end.isoformat() if end else None,
    )

    print("\n=== Verdict ===")
    print("PASS" if passed else "FAIL")
    print("Action:", "KEEP + STOP" if passed else "STOP and keep the exact output.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
