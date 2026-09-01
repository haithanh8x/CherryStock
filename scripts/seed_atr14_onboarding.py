"""Onboard ATR14 (ACTIVATE scenario) into CherryStock Indicator Engine metadata.

Scenario: ACTIVATE
- ``dim_indicator.ATR`` exists but IsActive=FALSE and ParameterSchema=NULL.
- No components, no configs.

This script performs PHASE 1 (Config Metadata) of the mandatory three-phase
state machine in ``.github/agents/Instructions/Indicator_Engine.md``:

1. Upsert ``dim_indicator`` (activate ATR, set ParameterSchema).
2. Upsert ``dim_indicator_component`` (single-output VALUE contract).
3. Upsert ``dim_indicator_config`` complete D/W/M family ATR14_D/W/M.

All writes are idempotent upserts inside one transaction. Rerunning does not
create duplicates. No ``cal_indicator_values`` rows are touched.

Usage from CherryStock repository root:
    .venv\\Scripts\\python.exe scripts\\seed_atr14_onboarding.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from Ults.DuckLib import DuckDBManager  # noqa: E402

DIM_INDICATOR = '"CherryMon"."main"."dim_indicator"'
DIM_COMPONENT = '"CherryMon"."main"."dim_indicator_component"'
DIM_CONFIG = '"CherryMon"."main"."dim_indicator_config"'

INDICATOR_CODE = "ATR"
PARAMETERS_JSON = '{"length": 14}'
WARMUP_BARS = 14
TIMEFRAMES = ("D", "W", "M")


def upsert_dim_indicator() -> None:
    """Activate ATR master definition with full runtime contract."""
    con = DuckDBManager.get_connection(read_only=False)
    try:
        con.execute(
            f"""
            INSERT INTO {DIM_INDICATOR} (
                IndicatorCode, IndicatorName, Category, Engine, FunctionName,
                RequiredInputs, ParameterSchema, Description, IsActive, UpdatedAt
            )
            VALUES (
                'ATR',
                'Average True Range',
                'VOLATILITY',
                'PANDAS_TA_CLASSIC',
                'atr',
                '["High","Low","Close"]'::JSON,
                '{{"length":{{"type":"integer","min":2,"required":true}}}}'::JSON,
                'Average True Range - volatility measure based on true range',
                TRUE,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (IndicatorCode) DO UPDATE SET
                IndicatorName = EXCLUDED.IndicatorName,
                Category = EXCLUDED.Category,
                Engine = EXCLUDED.Engine,
                FunctionName = EXCLUDED.FunctionName,
                RequiredInputs = EXCLUDED.RequiredInputs,
                ParameterSchema = EXCLUDED.ParameterSchema,
                Description = EXCLUDED.Description,
                IsActive = EXCLUDED.IsActive,
                UpdatedAt = CURRENT_TIMESTAMP
            """
        )
        con.commit()
        row = con.execute(
            f"""
            SELECT IndicatorCode, Engine, FunctionName, RequiredInputs,
                   ParameterSchema, IsActive
            FROM {DIM_INDICATOR}
            WHERE IndicatorCode = 'ATR'
            """
        ).fetchone()
        print(f"[seed_atr14] dim_indicator upserted: {row}")
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass
        raise
    finally:
        DuckDBManager.close_connection(con)


def upsert_dim_indicator_component() -> None:
    """Upsert single-output VALUE component contract for ATR."""
    con = DuckDBManager.get_connection(read_only=False)
    try:
        con.execute(
            f"""
            INSERT INTO {DIM_COMPONENT} (
                IndicatorCode, ComponentCode, ComponentName,
                OutputPrefix, SortOrder, IsPrimary, IsActive
            )
            VALUES (
                'ATR', 'VALUE', 'Average True Range', NULL, 1, TRUE, TRUE
            )
            ON CONFLICT (IndicatorCode, ComponentCode) DO UPDATE SET
                ComponentName = EXCLUDED.ComponentName,
                OutputPrefix = EXCLUDED.OutputPrefix,
                SortOrder = EXCLUDED.SortOrder,
                IsPrimary = EXCLUDED.IsPrimary,
                IsActive = TRUE
            """
        )
        con.commit()
        row = con.execute(
            f"""
            SELECT IndicatorCode, ComponentCode, OutputPrefix, IsPrimary, IsActive
            FROM {DIM_COMPONENT}
            WHERE IndicatorCode = 'ATR'
            """
        ).fetchall()
        print(f"[seed_atr14] dim_indicator_component upserted: {row}")
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass
        raise
    finally:
        DuckDBManager.close_connection(con)


def upsert_dim_indicator_config() -> None:
    """Upsert complete ATR14 D/W/M config family."""
    con = DuckDBManager.get_connection(read_only=False)
    try:
        con.executemany(
            f"""
            INSERT INTO {DIM_CONFIG} (
                ConfigCode, IndicatorCode, Timeframe,
                Parameters, WarmupBars, IsEnabled
            )
            VALUES (?, 'ATR', ?, ?::JSON, ?, TRUE)
            ON CONFLICT (ConfigCode) DO UPDATE SET
                IndicatorCode = EXCLUDED.IndicatorCode,
                Timeframe = EXCLUDED.Timeframe,
                Parameters = EXCLUDED.Parameters,
                WarmupBars = EXCLUDED.WarmupBars,
                IsEnabled = TRUE,
                UpdatedAt = CURRENT_TIMESTAMP
            """,
            [
                (f"ATR14_{tf}", INDICATOR_CODE, tf, PARAMETERS_JSON, WARMUP_BARS)
                for tf in TIMEFRAMES
            ],
        )
        con.commit()
        rows = con.execute(
            f"""
            SELECT ConfigId, ConfigCode, Timeframe, Parameters, WarmupBars, IsEnabled
            FROM {DIM_CONFIG}
            WHERE IndicatorCode = 'ATR'
            ORDER BY Timeframe
            """
        ).fetchall()
        print(f"[seed_atr14] dim_indicator_config upserted: {rows}")
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass
        raise
    finally:
        DuckDBManager.close_connection(con)


def main() -> int:
    print("[seed_atr14] PHASE 1 - Config Metadata onboarding start")
    upsert_dim_indicator()
    upsert_dim_indicator_component()
    upsert_dim_indicator_config()
    print("[seed_atr14] PHASE 1 complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
