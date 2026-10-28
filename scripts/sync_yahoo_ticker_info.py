"""Yahoo Finance ticker metadata registry and refresh job.

Run: python -m scripts.sync_yahoo_ticker_info
     python -m scripts.sync_yahoo_ticker_info --ticker AAPL --ticker ^GSPC
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import yfinance as yf
from CrawlStock.readYahooFinance import YAHOO_OTHER_TICKERS
from Ults.DuckLib import DuckDBManager

TABLE = '"CherryMon"."main"."raw_yahoo_ticker_info"'
FIELDS = {
    "shortName": "ShortName", "longName": "Name",
    "longBusinessSummary": "Description", "quoteType": "AssetType",
    "exchange": "Exchange", "fullExchangeName": "ExchangeName",
    "currency": "Currency", "exchangeTimezoneName": "Timezone",
    "sector": "Sector", "industry": "Industry", "marketCap": "MarketCap",
}
DEFAULT_TICKERS = tuple(YAHOO_OTHER_TICKERS)


def ensure_table(con):
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            Ticker VARCHAR PRIMARY KEY,
            Name VARCHAR, ShortName VARCHAR, Description VARCHAR,
            AssetType VARCHAR, Exchange VARCHAR, ExchangeName VARCHAR,
            Currency VARCHAR, Timezone VARCHAR, Sector VARCHAR,
            Industry VARCHAR, MarketCap DOUBLE,
            Status VARCHAR NOT NULL DEFAULT 'Y'
                CHECK (Status IN ('Y', 'N')),
            UpdatedAt TIMESTAMPTZ,
            LastError VARCHAR
        )
    """)


def sync_ticker_info(tickers=None, connection=None):
    """Seed new symbols; refresh metadata without overwriting manual Y/N flags."""
    if connection is None:
        with DuckDBManager() as con:
            return sync_ticker_info(tickers=tickers, connection=con)

    con = connection
    ensure_table(con)
    tickers = list(dict.fromkeys(t.strip() for t in
        (DEFAULT_TICKERS if tickers is None else tickers) if t and t.strip()))
    results = {"updated": 0, "failed": 0}
    for ticker in tickers:
        con.execute(f"INSERT INTO {TABLE} (Ticker, Status) VALUES (?, 'Y') ON CONFLICT (Ticker) DO NOTHING", [ticker])
        try:
            info = yf.Ticker(ticker).info or {}
            if not info or not any(info.get(k) for k in ("shortName", "longName", "quoteType")):
                raise ValueError("Yahoo returned no usable metadata")
            values = [info.get(k) for k in FIELDS]
            columns = list(FIELDS.values())
            assignments = ", ".join(f'"{c}" = ?' for c in columns)
            con.execute(
                f"UPDATE {TABLE} SET {assignments}, UpdatedAt = ?, LastError = NULL WHERE Ticker = ?",
                [*values, datetime.now(timezone.utc), ticker],
            )
            results["updated"] += 1
            # Keep successful ticker updates quiet; run.py prints the aggregate summary.
        except Exception as exc:
            con.execute(f"UPDATE {TABLE} SET LastError = ? WHERE Ticker = ?", [str(exc)[:1000], ticker])
            results["failed"] += 1
            print(f"[Yahoo INFO] FAIL {ticker}: {exc}")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", action="append", help="Repeat to add/refresh symbols")
    args = parser.parse_args()
    result = sync_ticker_info(tickers=args.ticker)
    print(result)
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
