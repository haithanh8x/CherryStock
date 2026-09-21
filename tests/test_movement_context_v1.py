from __future__ import annotations

from pathlib import Path

import duckdb
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_SQL = PROJECT_ROOT / "src" / "DuckDB" / "sql" / "movement_context_v1_schema.sql"


def _connection():
    connection = duckdb.connect()
    connection.execute("ATTACH ':memory:' AS CherryMon")
    connection.execute("CREATE SCHEMA IF NOT EXISTS CherryMon.main")

    connection.execute(
        """
        CREATE TABLE "CherryMon"."main"."vw_Ticker_Movement_Profile" (
            PriceMovementConfigCode VARCHAR,
            PriceMovementModelVersion VARCHAR,
            Timeframe VARCHAR,
            PriceMovementConfigId BIGINT,
            ZigZagConfigId BIGINT,
            ZigZagConfigCode VARCHAR,
            Ticker VARCHAR,
            AsOfConfirmedAtDate DATE,
            ProfileLookbackSwings INTEGER,
            ConfirmedSwingCount INTEGER,
            LastSwingSeq BIGINT,
            LastSwingDirection VARCHAR,
            LastSwingPct DOUBLE,
            MedianUpSwingPct DOUBLE,
            MedianDownSwingAbsPct DOUBLE,
            MedianAbsSwingPct DOUBLE,
            MedianTradingBars DOUBLE,
            MedianAbsVelocityPctPerBar DOUBLE,
            MedianATRNormalizedMove DOUBLE,
            MedianPathEfficiency DOUBLE,
            MedianDirectionalPersistenceRate DOUBLE,
            DirectionalBias DOUBLE,
            MovementCharacter VARCHAR,
            CalculatedAt TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE "CherryMon"."main"."vw_Ticker_ZigZag_Current" (
            ConfigId BIGINT,
            ConfigCode VARCHAR,
            ModelVersion VARCHAR,
            Timeframe VARCHAR,
            DeviationPct DOUBLE,
            Ticker VARCHAR,
            AsOfDate DATE,
            Direction VARCHAR,
            StartPivotSeq BIGINT,
            StartPivotDate DATE,
            StartPivotPrice DOUBLE,
            CandidatePivotType VARCHAR,
            CandidatePivotDate DATE,
            CandidatePivotPrice DOUBLE,
            LastClose DOUBLE,
            CurrentMovePct DOUBLE,
            ReversalFromCandidatePct DOUBLE,
            Status VARCHAR,
            CalculatedAt TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE "CherryMon"."main"."vw_Ticker_OHLC_D" (
            Ticker VARCHAR,
            Date DATE
        )
        """
    )

    connection.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
    return connection


def _insert_profile(
    connection,
    *,
    movement_character: str = "MIXED",
    confirmed_swing_count: int = 20,
) -> None:
    connection.execute(
        """
        INSERT INTO "CherryMon"."main"."vw_Ticker_Movement_Profile" (
            PriceMovementConfigCode,
            PriceMovementModelVersion,
            Timeframe,
            PriceMovementConfigId,
            ZigZagConfigId,
            ZigZagConfigCode,
            Ticker,
            AsOfConfirmedAtDate,
            ProfileLookbackSwings,
            ConfirmedSwingCount,
            LastSwingSeq,
            LastSwingDirection,
            LastSwingPct,
            MedianUpSwingPct,
            MedianDownSwingAbsPct,
            MedianAbsSwingPct,
            MedianTradingBars,
            MedianAbsVelocityPctPerBar,
            MedianATRNormalizedMove,
            MedianPathEfficiency,
            MedianDirectionalPersistenceRate,
            DirectionalBias,
            MovementCharacter,
            CalculatedAt
        )
        VALUES (
            'PM_ZZ_D_V2',
            'V2.0',
            'D',
            1,
            1,
            'ZZ_D_5_MVP',
            'MWG',
            DATE '2026-09-17',
            20,
            ?,
            278,
            'DOWN',
            -0.09617918313570506,
            0.12767589005701185,
            0.09857262644061404,
            0.11420421510256817,
            8.0,
            0.015733630956432567,
            4.0236928476562674,
            0.45809816569240036,
            0.6594202898550725,
            0.029368732320127895,
            ?,
            CURRENT_TIMESTAMP
        )
        """,
        [confirmed_swing_count, movement_character],
    )


def _insert_current_leg(connection) -> None:
    connection.execute(
        """
        INSERT INTO "CherryMon"."main"."vw_Ticker_ZigZag_Current" (
            ConfigId,
            ConfigCode,
            ModelVersion,
            Timeframe,
            DeviationPct,
            Ticker,
            AsOfDate,
            Direction,
            StartPivotSeq,
            StartPivotDate,
            StartPivotPrice,
            CandidatePivotType,
            CandidatePivotDate,
            CandidatePivotPrice,
            LastClose,
            CurrentMovePct,
            ReversalFromCandidatePct,
            Status,
            CalculatedAt
        )
        VALUES (
            1,
            'ZZ_D_5_MVP',
            'MVP1',
            'D',
            0.05,
            'MWG',
            DATE '2026-09-21',
            'UP',
            279,
            DATE '2026-09-17',
            70.0,
            'HIGH',
            DATE '2026-09-21',
            73.5,
            73.5,
            0.05,
            0.01,
            'PROVISIONAL',
            CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        INSERT INTO "CherryMon"."main"."vw_Ticker_OHLC_D" (Ticker, Date)
        VALUES
            ('MWG', DATE '2026-09-17'),
            ('MWG', DATE '2026-09-18'),
            ('MWG', DATE '2026-09-21')
        """
    )


def test_mwg_like_context_interprets_profile_and_current_leg() -> None:
    connection = _connection()
    try:
        _insert_profile(connection)
        _insert_current_leg(connection)

        row = connection.execute(
            """
            SELECT
                ContextStatus,
                TrendRegime,
                TrendQuality,
                LastSwingTypicalPct,
                LastSwingExtentRatio,
                LastSwingState,
                CurrentTradingBars,
                CurrentMoveSpeedPctPerBar,
                CurrentMoveSpeedRatio,
                CurrentMoveSpeedState
            FROM "CherryMon"."main"."vw_Ticker_Movement_Context"
            WHERE Ticker = 'MWG'
            """
        ).fetchone()

        assert row is not None
        assert row[0] == "PROFILE_PLUS_CURRENT"
        assert row[1] == "MIXED"
        assert row[2] == "MODERATE_HIGH"
        assert row[3] == pytest.approx(0.09857262644061404)
        assert row[4] == pytest.approx(
            0.09617918313570506 / 0.09857262644061404
        )
        assert row[5] == "TYPICAL_DOWN_SWING"
        assert row[6] == 2
        assert row[7] == pytest.approx(0.025)
        assert row[8] == pytest.approx(0.025 / 0.015733630956432567)
        assert row[9] == "FAST"
    finally:
        connection.close()


def test_context_remains_profile_only_without_current_leg() -> None:
    connection = _connection()
    try:
        _insert_profile(connection)

        row = connection.execute(
            """
            SELECT
                ContextStatus,
                CurrentLegDirection,
                CurrentTradingBars,
                CurrentMoveSpeedPctPerBar,
                CurrentMoveSpeedRatio,
                CurrentMoveSpeedState
            FROM "CherryMon"."main"."vw_Ticker_Movement_Context"
            WHERE Ticker = 'MWG'
            """
        ).fetchone()

        assert row is not None
        assert row[0] == "PROFILE_ONLY"
        assert row[1] is None
        assert row[2] == 0
        assert row[3] is None
        assert row[4] is None
        assert row[5] == "UNKNOWN"
    finally:
        connection.close()


def test_insufficient_history_is_preserved_as_context_status() -> None:
    connection = _connection()
    try:
        _insert_profile(
            connection,
            movement_character="INSUFFICIENT_HISTORY",
            confirmed_swing_count=4,
        )

        row = connection.execute(
            """
            SELECT ContextStatus, TrendRegime, TrendQuality
            FROM "CherryMon"."main"."vw_Ticker_Movement_Context"
            WHERE Ticker = 'MWG'
            """
        ).fetchone()

        assert row == (
            "INSUFFICIENT_HISTORY",
            "INSUFFICIENT_HISTORY",
            "INSUFFICIENT_HISTORY",
        )
    finally:
        connection.close()


def test_movement_context_schema_has_no_rs_or_smartmoney_dependency() -> None:
    sql = SCHEMA_SQL.read_text(encoding="utf-8").lower()

    assert "vw_ticker_smartmoney" not in sql
    assert "vw_rs_" not in sql
    assert "levelladder" not in sql
