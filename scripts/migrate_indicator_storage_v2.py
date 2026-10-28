"""One-time, transactional migration to the simple AmiBroker indicator storage model.

Use on the local DuckDB after a filesystem backup:
    python -m scripts.migrate_indicator_storage_v2

A complete pre-migration copy is preserved as cal_indicator_values_legacy_backup.
Existing public vw_Ticker_indicators consumers retain their ConfigId/ComponentCode
projection via a compatibility VIEW, while v2 facts have only a logical name.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from cherrystock.config.settings import settings
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory

SCHEMA = '"CherryMon"."main"'
FACT = f'{SCHEMA}."cal_indicator_values"'
CURRENT = f'{SCHEMA}."cal_indicator_current"'
LEGACY = f'{SCHEMA}."cal_indicator_values_legacy_backup"'
PUBLIC = f'{SCHEMA}."vw_Ticker_indicators"'
CONFIGS = f'{SCHEMA}."dim_indicator_config"'
COMPONENTS = f'{SCHEMA}."dim_indicator_component"'


def _columns(con, table: str) -> set[str]:
    return {r[0] for r in con.execute(
        """SELECT column_name FROM information_schema.columns
           WHERE table_catalog = 'CherryMon'
             AND table_schema = 'main' AND table_name = ?""",
        [table],
    ).fetchall()}


def _create_fact(con) -> None:
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {FACT} (
            Ticker VARCHAR NOT NULL,
            Date DATE NOT NULL,
            IndicatorName VARCHAR NOT NULL,
            Timeframe VARCHAR NOT NULL CHECK (Timeframe IN ('D', 'W', 'M')),
            Value DOUBLE,
            UpdatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (Ticker, Date, IndicatorName, Timeframe)
        )
    """)


def _create_current(con) -> None:
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {CURRENT} (
            Ticker VARCHAR NOT NULL,
            Date DATE NOT NULL,
            IndicatorName VARCHAR NOT NULL,
            Timeframe VARCHAR NOT NULL CHECK (Timeframe IN ('W', 'M')),
            Value DOUBLE,
            UpdatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (Ticker, IndicatorName, Timeframe)
        )
    """)


def _create_compatibility_view(con) -> None:
    # Legacy R/S and SmartMoney still resolve ConfigId and ComponentCode.
    # These IDs are a read projection only; neither ID is stored in v2 facts.
    con.execute(f"""
        CREATE OR REPLACE VIEW {PUBLIC} AS
        WITH all_values AS (
            SELECT Ticker, Date, IndicatorName, Timeframe, Value, UpdatedAt
            FROM {FACT}
            UNION ALL
            SELECT Ticker, Date, IndicatorName, Timeframe, Value, UpdatedAt
            FROM {CURRENT}
        )
        SELECT
            v.Ticker, v.Date, cfg.ConfigId, comp.ComponentCode,
            v.Value, v.UpdatedAt AS CalculatedAt,
            cfg.IndicatorCode, v.Timeframe
        FROM all_values v
        JOIN {CONFIGS} cfg ON cfg.Timeframe = v.Timeframe
        JOIN {COMPONENTS} comp ON comp.IndicatorCode = cfg.IndicatorCode
        WHERE v.IndicatorName = CASE
            WHEN comp.ComponentCode = 'VALUE'
                THEN REGEXP_REPLACE(cfg.ConfigCode, '_[DWM]$', '')
            ELSE REGEXP_REPLACE(cfg.ConfigCode, '_[DWM]$', '')
                 || '_' || comp.ComponentCode
        END
    """)


def migrate(con) -> dict[str, int | str]:
    """Safe rerun: no alteration if already migrated; no drop of legacy rows."""
    columns = _columns(con, "cal_indicator_values")
    if columns and "IndicatorName" not in columns and "ConfigId" not in columns:
        raise RuntimeError(f"Unknown cal_indicator_values schema: {sorted(columns)}")
    if "ConfigId" in columns and _columns(con, "cal_indicator_values_legacy_backup"):
        raise RuntimeError(
            "Legacy backup already exists while old fact is still active. "
            "Resolve the previous migration attempt before proceeding."
        )
    con.execute("BEGIN TRANSACTION")
    try:
        legacy_rows = 0
        if "ConfigId" in columns:
            # DuckDB generally disallows ALTER TABLE RENAME on indexed/PK
            # tables. Preserve the original as a physical CTAS backup before
            # dropping the legacy fact and creating the new PK contract.
            con.execute(f"CREATE TABLE {LEGACY} AS SELECT * FROM {FACT}")
            legacy_rows = int(con.execute(f"SELECT COUNT(*) FROM {LEGACY}").fetchone()[0])
            original_count = int(con.execute(f"SELECT COUNT(*) FROM {FACT}").fetchone()[0])
            if legacy_rows != original_count:
                raise RuntimeError("Legacy backup row count differs from source; aborting migration")
            # A view that still depends on the old fact may block DROP TABLE.
            # The transaction will roll back; never use DROP CASCADE.
            con.execute(f"DROP VIEW IF EXISTS {PUBLIC}")
            con.execute(f"DROP TABLE {FACT}")
        _create_fact(con)
        _create_current(con)

        if legacy_rows:
            # Map legacy ConfigId + ComponentCode to a human-readable AFL name.
            # Rows for open W/M periods are developing and belong to CURRENT.
            source = f"""
                SELECT v.Ticker, v.Date,
                    CASE WHEN v.ComponentCode = 'VALUE'
                        THEN REGEXP_REPLACE(cfg.ConfigCode, '_[DWM]$', '')
                        ELSE REGEXP_REPLACE(cfg.ConfigCode, '_[DWM]$', '')
                             || '_' || v.ComponentCode
                    END AS IndicatorName,
                    cfg.Timeframe, v.Value, v.CalculatedAt
                FROM {LEGACY} v
                JOIN {CONFIGS} cfg ON cfg.ConfigId = v.ConfigId
                WHERE v.Value IS NOT NULL AND ISFINITE(v.Value)
                  AND cfg.Timeframe IN ('D','W','M')
            """
            con.execute(f"""
                INSERT INTO {FACT} (Ticker, Date, IndicatorName, Timeframe, Value, UpdatedAt)
                SELECT Ticker, Date, IndicatorName, Timeframe, Value, CalculatedAt
                FROM ({source}) s
                WHERE Timeframe = 'D'
                   OR (Timeframe = 'W' AND Date < CAST(DATE_TRUNC('week', CURRENT_DATE) AS DATE))
                   OR (Timeframe = 'M' AND Date < CAST(DATE_TRUNC('month', CURRENT_DATE) AS DATE))
                ON CONFLICT (Ticker, Date, IndicatorName, Timeframe) DO UPDATE
                    SET Value = EXCLUDED.Value, UpdatedAt = EXCLUDED.UpdatedAt
            """)
            con.execute(f"""
                INSERT INTO {CURRENT} (Ticker, Date, IndicatorName, Timeframe, Value, UpdatedAt)
                SELECT Ticker, Date, IndicatorName, Timeframe, Value, CalculatedAt
                FROM ({source}) s
                WHERE (Timeframe = 'W' AND Date >= CAST(DATE_TRUNC('week', CURRENT_DATE) AS DATE))
                   OR (Timeframe = 'M' AND Date >= CAST(DATE_TRUNC('month', CURRENT_DATE) AS DATE))
                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY Ticker, IndicatorName, Timeframe
                    ORDER BY Date DESC, CalculatedAt DESC
                ) = 1
                ON CONFLICT (Ticker, IndicatorName, Timeframe) DO UPDATE
                    SET Date = EXCLUDED.Date, Value = EXCLUDED.Value,
                        UpdatedAt = EXCLUDED.UpdatedAt
            """)

        _create_compatibility_view(con)
        summary = {
            "legacy_backup_rows": legacy_rows,
            "history_rows": int(con.execute(f"SELECT COUNT(*) FROM {FACT}").fetchone()[0]),
            "current_rows": int(con.execute(f"SELECT COUNT(*) FROM {CURRENT}").fetchone()[0]),
            "schema": "v2",
        }
        con.execute("COMMIT")
        return summary
    except BaseException:
        con.execute("ROLLBACK")
        raise


def require_v2(con) -> None:
    if not {"IndicatorName", "Timeframe", "UpdatedAt"}.issubset(
        _columns(con, "cal_indicator_values")
    ) or not _columns(con, "cal_indicator_current"):
        raise RuntimeError(
            "Indicator v2 schema is not migrated. Run "
            "'python -m scripts.migrate_indicator_storage_v2' after backing up DuckDB."
        )


def main() -> None:
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with factory.writer() as con:
        print("[INDICATOR MIGRATION]", migrate(con))


if __name__ == "__main__":
    main()
