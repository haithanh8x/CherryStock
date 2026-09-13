from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from CrawlStock.readAmi import syncAmibroker_EOD  # noqa: E402
from CrawlStock.readYahooFinance import syncYahooFinance_EOD  # noqa: E402
from Ults.DuckLib import executeDuckSQL  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402

YAHOO_HISTORY_START = "2024-04-01"

DEPENDENT_VIEWS = (
    (
        '"CherryMon"."main"."vw_Ticker_OHLC_D"',
        PROJECT_ROOT / "src" / "DuckDB" / "sql" / "vw_Ticker_OHLC_D.sql",
        ("raw_stock_eod", "raw_stock_intraday"),
    ),
    (
        '"CherryMon"."main"."vw_raw_stock_eod"',
        PROJECT_ROOT / "src" / "DuckDB" / "sql" / "vw_raw_stock_eod.sql",
        ("raw_stock_eod", "raw_stock_intraday", "raw_stock_fa"),
    ),
)


def _drop_daily_views() -> None:
    factory = DuckDBConnectionFactory()
    with factory.writer() as connection:
        for view_name, _, _ in DEPENDENT_VIEWS:
            connection.execute(f"DROP VIEW IF EXISTS {view_name};")


def _recreate_daily_views() -> None:
    factory = DuckDBConnectionFactory()
    with factory.writer() as connection:
        available = {
            str(row[0]).lower()
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE lower(table_catalog) = 'cherrymon'
                  AND lower(table_schema) = 'main'
                """
            ).fetchall()
        }

        for view_name, sql_path, prerequisites in DEPENDENT_VIEWS:
            missing = [name for name in prerequisites if name.lower() not in available]
            if missing:
                print(f"Skip {view_name} rebuild: missing prerequisites {missing}.")
                continue
            executeDuckSQL(
                con=connection,
                sql_file_path=str(sql_path),
                sql_description=f"Rebuild {view_name}",
            )


def main() -> None:
    """Full reload AmiBroker EOD, then restore Yahoo history in shared raw_other_eod."""
    _drop_daily_views()

    print("[1/2] Full reload AmiBroker EOD...")
    syncAmibroker_EOD(from_last_day=None)

    # raw_other_eod is shared by AmiBroker EOD/other and Yahoo Finance. AmiBroker
    # full-load mode rebuilds the table, so Yahoo history must be restored after it.
    print(f"[2/2] Upsert Yahoo EOD history from {YAHOO_HISTORY_START}...")
    syncYahooFinance_EOD(start_date=YAHOO_HISTORY_START)

    _recreate_daily_views()


if __name__ == "__main__":
    main()
