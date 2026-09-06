"""Targeted full historical initload for OBV and AD Line indicator values.

Prerequisite:
    Apply src/DuckDB/sql/indicator_obv_ad_activate.sql through the approved
    CherryMon indicator-metadata workflow before running this script.

This PHASE 2 wrapper resolves ConfigId values dynamically, runs an MWG smoke
refresh, then performs a full historical backfill for only OBV_D/W/M and
AD_D/W/M. Other indicator ConfigIds are untouched.

Usage:
    .\\.venv\\Scripts\\python.exe scripts\\initload\\init_reload_cal_indicator_values_obv_ad.py
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

EXPECTED_CONFIG_CODES = (
    "OBV_D",
    "OBV_W",
    "OBV_M",
    "AD_D",
    "AD_W",
    "AD_M",
)
SMOKE_TICKER = "MWG"


def _resolve_config_ids(connection) -> list[int]:
    rows = connection.execute(
        """
        SELECT
            cfg.ConfigId,
            cfg.ConfigCode,
            cfg.IsEnabled,
            ind.IsActive
        FROM "CherryMon"."main"."dim_indicator_config" AS cfg
        INNER JOIN "CherryMon"."main"."dim_indicator" AS ind
            ON ind.IndicatorCode = cfg.IndicatorCode
        WHERE cfg.ConfigCode IN (?, ?, ?, ?, ?, ?)
        ORDER BY cfg.ConfigCode
        """,
        list(EXPECTED_CONFIG_CODES),
    ).fetchall()

    found = {str(row[1]): row for row in rows}
    missing = sorted(set(EXPECTED_CONFIG_CODES) - set(found))
    if missing:
        raise RuntimeError(
            "Missing OBV/AD configs: "
            f"{missing}. Apply src/DuckDB/sql/indicator_obv_ad_activate.sql first."
        )

    inactive = [
        code
        for code, row in found.items()
        if not bool(row[2]) or not bool(row[3])
    ]
    if inactive:
        raise RuntimeError(f"OBV/AD configs are not fully active/enabled: {sorted(inactive)}")

    return [int(found[code][0]) for code in EXPECTED_CONFIG_CODES]


def _print_output_coverage(connection) -> None:
    rows = connection.execute(
        """
        SELECT
            cfg.ConfigCode,
            cfg.Timeframe,
            COUNT(val.Ticker) AS Records,
            COUNT(DISTINCT val.Ticker) AS Tickers,
            MIN(val.Date) AS MinDate,
            MAX(val.Date) AS MaxDate,
            SUM(CASE WHEN val.Value IS NULL THEN 1 ELSE 0 END) AS NullValues
        FROM "CherryMon"."main"."dim_indicator_config" AS cfg
        LEFT JOIN "CherryMon"."main"."cal_indicator_values" AS val
            ON val.ConfigId = cfg.ConfigId
        WHERE cfg.ConfigCode IN (?, ?, ?, ?, ?, ?)
        GROUP BY cfg.ConfigCode, cfg.Timeframe
        ORDER BY cfg.ConfigCode
        """,
        list(EXPECTED_CONFIG_CODES),
    ).fetchall()

    print("-" * 88)
    print("OBV / AD output coverage")
    for row in rows:
        print(row)
    print("-" * 88)

    zero_output = [str(row[0]) for row in rows if int(row[2] or 0) == 0]
    if zero_output:
        raise RuntimeError(f"Enabled OBV/AD configs with zero output: {zero_output}")


def main() -> int:
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)

    print("=" * 88)
    print("CherryStock Indicator Engine - OBV + AD TARGETED INITIAL LOAD")
    print("Configs : OBV_D/W/M + AD_D/W/M")
    print("Mode    : MWG smoke -> full historical targeted backfill")
    print("=" * 88)

    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None or uow.indicators is None:
            raise RuntimeError("UnitOfWork did not initialize indicator dependencies.")

        connection = uow.connection
        config_ids = _resolve_config_ids(connection)
        print(f"Resolved ConfigIds: {config_ids}")

        smoke = refresh_technical_indicators(
            from_last_day=120,
            tickers=[SMOKE_TICKER],
            config_ids=config_ids,
            timeframes=None,
            connection=connection,
            repository=uow.indicators,
        )
        print(f"Smoke summary: {smoke}")
        if int(smoke.get("records_upserted", 0)) <= 0:
            raise RuntimeError("OBV/AD smoke refresh produced zero records.")

        backfill = refresh_technical_indicators(
            from_last_day=None,
            tickers=None,
            config_ids=config_ids,
            timeframes=None,
            connection=connection,
            repository=uow.indicators,
        )
        print(f"Backfill summary: {backfill}")
        if int(backfill.get("records_upserted", 0)) <= 0:
            raise RuntimeError("OBV/AD historical backfill produced zero records.")

        _print_output_coverage(connection)

    print("OBV + AD targeted historical initload committed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
