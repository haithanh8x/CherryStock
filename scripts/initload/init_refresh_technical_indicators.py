"""Initial full historical load for CherryStock Technical Indicator Engine.

This script runs ``refresh_technical_indicators`` for all active stock tickers
(`raw_lstTicker.status = 'Y'`) and all enabled indicator configs.

Important behavior:
- ``from_last_day=None`` => full historical refresh/backfill.
- ``tickers=None`` => no ticker filter; engine loads every active ticker that has
  data in ``raw_stock_eod``.
- Default onboarding validation remains enabled, so each active
  ``IndicatorCode + Parameters`` family must have D/W/M configs and active
  component metadata before calculation starts.
- The whole initialization runs inside one ``DuckDBUnitOfWork`` transaction.
  Any failure rolls back the write.

Usage from CherryStock repository root:
    .venv\\Scripts\\python.exe scripts\\initload\\init_refresh_technical_indicators.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from calcEngine.calcIndicators import refresh_technical_indicators  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


def _count_active_source_tickers(connection) -> int:
    """Return active tickers that actually have raw_stock_eod source data."""
    row = connection.execute(
        """
        SELECT COUNT(DISTINCT eod.Ticker)
        FROM "CherryMon"."main"."raw_stock_eod" AS eod
        INNER JOIN "CherryMon"."main"."raw_lstTicker" AS ticker
            ON ticker.Ticker = eod.Ticker
        WHERE ticker.status = 'Y'
        """
    ).fetchone()
    return int(row[0]) if row else 0


def _count_enabled_configs(connection) -> int:
    row = connection.execute(
        """
        SELECT COUNT(*)
        FROM "CherryMon"."main"."dim_indicator_config"
        WHERE IsEnabled = TRUE
        """
    ).fetchone()
    return int(row[0]) if row else 0


def main() -> int:
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)

    print("=" * 72)
    print("CherryStock Technical Indicator Engine - INITIAL FULL LOAD")
    print("Mode       : full historical")
    print("Tickers    : ALL active tickers (status='Y')")
    print("Timeframes : D / W / M")
    print("Configs    : ALL enabled configs")
    print("=" * 72)

    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None or uow.indicators is None:
            raise RuntimeError("UnitOfWork did not initialize indicator dependencies.")

        connection = uow.connection
        active_ticker_count = _count_active_source_tickers(connection)
        enabled_config_count = _count_enabled_configs(connection)

        if active_ticker_count == 0:
            raise RuntimeError(
                "Không có ticker active có dữ liệu trong raw_stock_eod. "
                "Kiểm tra raw_lstTicker.status='Y' và raw_stock_eod trước khi init load."
            )
        if enabled_config_count == 0:
            raise RuntimeError(
                "Không có config IsEnabled=TRUE trong dim_indicator_config."
            )

        print(f"Active source tickers : {active_ticker_count}")
        print(f"Enabled configs       : {enabled_config_count}")
        print("Starting full historical indicator refresh...")

        summary = refresh_technical_indicators(
            from_last_day=None,
            tickers=None,
            config_ids=None,
            timeframes=None,
            connection=connection,
            repository=uow.indicators,
        )

        output_tickers = int(
            connection.execute(
                """
                SELECT COUNT(DISTINCT Ticker)
                FROM "CherryMon"."main"."cal_indicator_values"
                """
            ).fetchone()[0]
        )
        output_rows = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM "CherryMon"."main"."cal_indicator_values"
                """
            ).fetchone()[0]
        )

        print("-" * 72)
        print("Initial load summary")
        print(f"Engine status         : {summary.get('status')}")
        print(f"Tickers processed     : {summary.get('tickers_processed')}")
        print(f"Indicators processed  : {summary.get('indicators_processed')}")
        print(f"Configs processed     : {summary.get('configs_processed')}")
        print(f"Records written       : {summary.get('records_upserted')}")
        print(f"Source start          : {summary.get('source_start')}")
        print(f"Source max date       : {summary.get('source_max_date')}")
        print(f"Output distinct ticker: {output_tickers}")
        print(f"Output total rows     : {output_rows}")
        print("-" * 72)

        if output_tickers < active_ticker_count:
            print(
                "WARNING: cal_indicator_values có ít ticker hơn source active. "
                "Một số ticker có thể chưa đủ historical bars để tạo indicator value."
            )

    print("Initial full indicator load committed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
