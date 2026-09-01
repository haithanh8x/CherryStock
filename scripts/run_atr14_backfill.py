"""PHASE 2 + PHASE 3 runner for ATR14 onboarding.

PHASE 2 - Historical Backfill (TARGETED):
1. Smoke test on MWG with a bounded window (from_last_day=120).
2. Full targeted backfill for ATR14 ConfigIds only (from_last_day=None).

PHASE 3 - Validation:
Runs the mandatory validation queries from Indicator_Engine.md section 7
against ``cal_indicator_values`` for the ATR scope only.

Usage from CherryStock repository root:
    .venv\\Scripts\\python.exe scripts\\run_atr14_backfill.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from calcEngine.calcIndicators import refresh_technical_indicators  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402

INDICATOR_CODE = "ATR"
ATR_CONFIG_IDS = [37, 38, 39]
SMOKE_TICKER = "MWG"
SMOKE_FROM_LAST_DAY = 120


def _count_active_source_tickers(connection) -> int:
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


def phase2_smoke_test(config_ids: list[int]) -> None:
    """Targeted MWG smoke test with bounded checkpoint window."""
    print(f"[phase2] Smoke test: ticker={SMOKE_TICKER}, from_last_day={SMOKE_FROM_LAST_DAY}")
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None or uow.indicators is None:
            raise RuntimeError("UnitOfWork did not initialize indicator dependencies.")
        summary = refresh_technical_indicators(
            from_last_day=SMOKE_FROM_LAST_DAY,
            tickers=[SMOKE_TICKER],
            config_ids=config_ids,
            connection=uow.connection,
            repository=uow.indicators,
        )
    print(f"[phase2] Smoke summary: {summary}")
    if int(summary.get("records_upserted", 0)) <= 0:
        raise RuntimeError(
            "PHASE 2 FAIL: smoke test upserted 0 records. "
            "Check RequiredInputs, Parameters, WarmupBars, component mapping."
        )


def phase2_targeted_backfill(config_ids: list[int]) -> dict:
    """Full historical targeted backfill for ATR14 ConfigIds only."""
    print(f"[phase2] Targeted backfill: config_ids={config_ids}, from_last_day=None")
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None or uow.indicators is None:
            raise RuntimeError("UnitOfWork did not initialize indicator dependencies.")
        summary = refresh_technical_indicators(
            from_last_day=None,
            tickers=None,
            config_ids=config_ids,
            connection=uow.connection,
            repository=uow.indicators,
        )
    print(f"[phase2] Backfill summary: {summary}")
    if int(summary.get("records_upserted", 0)) <= 0:
        raise RuntimeError("PHASE 2 FAIL: targeted backfill upserted 0 records.")
    return summary


def phase3_validate(connection) -> bool:
    """Run mandatory PHASE 3 validation queries for the ATR scope."""
    passed = True

    print("-" * 72)
    print("[phase3] 7.2 Config/component coverage")
    rows = connection.execute(
        """
        SELECT c.ConfigCode, c.Timeframe, v.ComponentCode,
               COUNT(*) AS Records,
               COUNT(DISTINCT v.Ticker) AS Tickers,
               MIN(v.Date) AS MinDate,
               MAX(v.Date) AS MaxDate,
               SUM(CASE WHEN v.Value IS NULL THEN 1 ELSE 0 END) AS NullValues
        FROM "CherryMon"."main"."cal_indicator_values" v
        INNER JOIN "CherryMon"."main"."dim_indicator_config" c
            ON c.ConfigId = v.ConfigId
        WHERE c.IndicatorCode = 'ATR'
        GROUP BY c.ConfigCode, c.Timeframe, v.ComponentCode
        ORDER BY c.ConfigCode, v.ComponentCode
        """
    ).fetchall()
    for row in rows:
        print(f"  {row}")
    if not rows:
        print("  FAIL: no ATR output rows")
        passed = False
    elif len({row[1] for row in rows}) < 3:
        print("  FAIL: D/W/M family incomplete in output")
        passed = False

    print("-" * 72)
    print("[phase3] 7.3 Source vs output ticker coverage")
    active_tickers = _count_active_source_tickers(connection)
    row = connection.execute(
        """
        SELECT COUNT(DISTINCT v.Ticker)
        FROM "CherryMon"."main"."cal_indicator_values" v
        INNER JOIN "CherryMon"."main"."dim_indicator_config" c
            ON c.ConfigId = v.ConfigId
        WHERE c.IndicatorCode = 'ATR'
        """
    ).fetchone()
    output_tickers = int(row[0]) if row else 0
    print(f"  Active source tickers: {active_tickers}")
    print(f"  ATR output tickers   : {output_tickers}")
    if output_tickers < active_tickers * 0.9:
        print("  WARN: output ticker coverage below 90% of active source")
        passed = False

    print("-" * 72)
    print("[phase3] 7.4 Zero-output enabled configs")
    rows = connection.execute(
        """
        SELECT c.ConfigId, c.ConfigCode, c.Timeframe, COUNT(v.Ticker) AS OutputRows
        FROM "CherryMon"."main"."dim_indicator_config" c
        LEFT JOIN "CherryMon"."main"."cal_indicator_values" v
            ON v.ConfigId = c.ConfigId
        WHERE c.IndicatorCode = 'ATR'
          AND c.IsEnabled = TRUE
        GROUP BY c.ConfigId, c.ConfigCode, c.Timeframe
        ORDER BY c.ConfigCode
        """
    ).fetchall()
    for row in rows:
        print(f"  {row}")
        if int(row[3]) == 0:
            print("  FAIL: zero-output enabled config")
            passed = False

    print("-" * 72)
    print("[phase3] 7.5 Duplicate PK (mandatory 0 rows)")
    rows = connection.execute(
        """
        SELECT Ticker, Date, ConfigId, ComponentCode, COUNT(*) AS cnt
        FROM "CherryMon"."main"."cal_indicator_values"
        GROUP BY Ticker, Date, ConfigId, ComponentCode
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    print(f"  Duplicate rows: {len(rows)}")
    if rows:
        passed = False

    print("-" * 72)
    print("[phase3] 7.6 Unexpected components (mandatory 0 rows)")
    rows = connection.execute(
        """
        SELECT DISTINCT c.IndicatorCode, v.ComponentCode
        FROM "CherryMon"."main"."cal_indicator_values" v
        INNER JOIN "CherryMon"."main"."dim_indicator_config" c
            ON c.ConfigId = v.ConfigId
        LEFT JOIN "CherryMon"."main"."dim_indicator_component" comp
            ON comp.IndicatorCode = c.IndicatorCode
           AND comp.ComponentCode = v.ComponentCode
        WHERE c.IndicatorCode = 'ATR'
          AND comp.ComponentCode IS NULL
        """
    ).fetchall()
    print(f"  Unexpected components: {len(rows)}")
    if rows:
        passed = False

    print("-" * 72)
    print("[phase3] 7.7 Sample values (MWG, latest 12 per config)")
    rows = connection.execute(
        """
        SELECT v.Ticker, v.Date, c.ConfigCode, v.ComponentCode, v.Value
        FROM "CherryMon"."main"."cal_indicator_values" v
        INNER JOIN "CherryMon"."main"."dim_indicator_config" c
            ON c.ConfigId = v.ConfigId
        WHERE c.IndicatorCode = 'ATR'
          AND v.Ticker = 'MWG'
        QUALIFY ROW_NUMBER() OVER (PARTITION BY c.ConfigCode ORDER BY v.Date DESC) <= 12
        ORDER BY c.ConfigCode, v.Date DESC
        """
    ).fetchall()
    for row in rows:
        print(f"  {row}")
    if not rows:
        print("  FAIL: no sample rows for MWG")
        passed = False
    elif any(row[4] is None for row in rows):
        print("  FAIL: NULL values in latest samples")
        passed = False

    print("-" * 72)
    return passed


def main() -> int:
    phase2_smoke_test(ATR_CONFIG_IDS)
    phase2_targeted_backfill(ATR_CONFIG_IDS)

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None:
            raise RuntimeError("UnitOfWork did not initialize connection.")
        passed = phase3_validate(uow.connection)

    print("=" * 72)
    print(f"PHASE 3 STATUS: {'PASS' if passed else 'FAIL'}")
    print(f"FINAL STATUS: {'PRODUCTION_READY' if passed else 'NOT_READY'}")
    print("=" * 72)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
