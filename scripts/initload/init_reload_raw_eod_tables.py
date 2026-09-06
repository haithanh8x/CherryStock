from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from CrawlStock.readAmi import syncAmibroker_EOD  # noqa: E402
from Ults.DuckLib import executeDuckSQL  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402

VIEW_NAME = '"CherryMon"."main"."vw_Ticker_OHLC_D"'
VIEW_SQL = PROJECT_ROOT / "src" / "DuckDB" / "sql" / "vw_Ticker_OHLC_D.sql"


def _drop_daily_view() -> None:
    factory = DuckDBConnectionFactory()
    with factory.writer() as connection:
        connection.execute(f"DROP VIEW IF EXISTS {VIEW_NAME};")


def _recreate_daily_view() -> None:
    factory = DuckDBConnectionFactory()
    with factory.writer() as connection:
        prerequisite_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE lower(table_catalog) = 'cherrymon'
              AND lower(table_schema) = 'main'
              AND lower(table_name) IN ('raw_stock_eod', 'raw_stock_intraday')
            """
        ).fetchone()[0]
        if int(prerequisite_count) < 2:
            print(
                "Skip vw_Ticker_OHLC_D rebuild: raw_stock_eod and "
                "raw_stock_intraday are not both available yet."
            )
            return

        executeDuckSQL(
            con=connection,
            sql_file_path=str(VIEW_SQL),
            sql_description="Rebuild vw_Ticker_OHLC_D",
        )



def main() -> None:
    """
    Full reload all configured AmiBroker EOD sources.

    syncAmibroker_EOD(from_last_day=None) follows the existing EOD contract:
    each configured target is rebuilt from the complete source folder.
    """
    _drop_daily_view()
    syncAmibroker_EOD(from_last_day=None)
    _recreate_daily_view()


if __name__ == "__main__":
    main()
