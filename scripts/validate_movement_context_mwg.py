from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402


TICKER = "MWG"
CONTEXT_CONFIG_CODE = "MC_PM_ZZ_D_V1"
SCHEMA_SQL = PROJECT_ROOT / "src" / "DuckDB" / "sql" / "movement_context_v1_schema.sql"


def validate() -> int:
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    failures: list[str] = []

    with factory.reader() as connection:
        context = connection.execute(
            """
            SELECT
                MovementContextConfigCode,
                PriceMovementConfigCode,
                ZigZagConfigCode,
                Ticker,
                ContextAsOfDate,
                ProfileAsOfConfirmedAtDate,
                CurrentLegAsOfDate,
                ContextStatus,
                TrendRegime,
                TrendQuality,
                TypicalSwingPct,
                TypicalSwingBars,
                TypicalMoveSpeedPctPerBar,
                MedianPathEfficiency,
                MedianDirectionalPersistenceRate,
                DirectionalBias,
                LastSwingDirection,
                LastSwingPct,
                LastSwingTypicalPct,
                LastSwingExtentRatio,
                LastSwingState,
                CurrentLegDirection,
                CurrentMovePct,
                CurrentTradingBars,
                CurrentMoveSpeedPctPerBar,
                CurrentMoveSpeedRatio,
                CurrentMoveSpeedState,
                CurrentLegStatus,
                CurrentStartPivotDate
            FROM "CherryMon"."main"."vw_Ticker_Movement_Context"
            WHERE Ticker = ?
              AND MovementContextConfigCode = ?
            """,
            [TICKER, CONTEXT_CONFIG_CODE],
        ).df()

        if len(context) != 1:
            failures.append(f"expected one MWG context row, got {len(context)}")
            profile = pd.DataFrame()
            current = pd.DataFrame()
            ohlc = pd.DataFrame()
        else:
            row = context.iloc[0]
            profile = connection.execute(
                """
                SELECT
                    AsOfConfirmedAtDate,
                    LastSwingDirection,
                    LastSwingPct,
                    MedianUpSwingPct,
                    MedianDownSwingAbsPct,
                    MedianAbsSwingPct,
                    MedianTradingBars,
                    MedianAbsVelocityPctPerBar,
                    MedianPathEfficiency,
                    MedianDirectionalPersistenceRate,
                    DirectionalBias,
                    MovementCharacter
                FROM "CherryMon"."main"."vw_Ticker_Movement_Profile"
                WHERE Ticker = ?
                  AND PriceMovementConfigCode = ?
                  AND ZigZagConfigCode = ?
                """,
                [
                    TICKER,
                    str(row["PriceMovementConfigCode"]),
                    str(row["ZigZagConfigCode"]),
                ],
            ).df()

            current = connection.execute(
                """
                SELECT
                    AsOfDate,
                    Direction,
                    StartPivotDate,
                    CurrentMovePct,
                    Status
                FROM "CherryMon"."main"."vw_Ticker_ZigZag_Current"
                WHERE Ticker = ?
                  AND ConfigCode = ?
                """,
                [TICKER, str(row["ZigZagConfigCode"])],
            ).df()

            ohlc = connection.execute(
                """
                SELECT Date
                FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
                WHERE Ticker = ?
                ORDER BY Date
                """,
                [TICKER],
            ).df()

    if len(context) == 1 and len(profile) != 1:
        failures.append(f"expected one upstream movement profile, got {len(profile)}")

    if len(context) == 1 and len(profile) == 1:
        c = context.iloc[0]
        p = profile.iloc[0]

        if str(c["TrendRegime"]) != str(p["MovementCharacter"]):
            failures.append("TrendRegime must equal MovementCharacter")

        if not np.isclose(
            float(c["TypicalSwingPct"]),
            float(p["MedianAbsSwingPct"]),
            rtol=1e-9,
            atol=1e-9,
        ):
            failures.append("TypicalSwingPct mismatch")

        if not np.isclose(
            float(c["TypicalSwingBars"]),
            float(p["MedianTradingBars"]),
            rtol=1e-9,
            atol=1e-9,
        ):
            failures.append("TypicalSwingBars mismatch")

        if not np.isclose(
            float(c["TypicalMoveSpeedPctPerBar"]),
            float(p["MedianAbsVelocityPctPerBar"]),
            rtol=1e-9,
            atol=1e-9,
        ):
            failures.append("TypicalMoveSpeedPctPerBar mismatch")

        same_direction = (
            float(p["MedianUpSwingPct"])
            if str(p["LastSwingDirection"]) == "UP"
            else float(p["MedianDownSwingAbsPct"])
        )
        expected_extent = abs(float(p["LastSwingPct"])) / same_direction

        if not np.isclose(
            float(c["LastSwingTypicalPct"]),
            same_direction,
            rtol=1e-9,
            atol=1e-9,
        ):
            failures.append("LastSwingTypicalPct mismatch")

        if not np.isclose(
            float(c["LastSwingExtentRatio"]),
            expected_extent,
            rtol=1e-9,
            atol=1e-9,
        ):
            failures.append("LastSwingExtentRatio mismatch")

        allowed_trend_quality = {
            "INSUFFICIENT_HISTORY",
            "LOW",
            "MODERATE",
            "MODERATE_HIGH",
            "HIGH",
        }
        if str(c["TrendQuality"]) not in allowed_trend_quality:
            failures.append("unsupported TrendQuality")

        allowed_last_swing_prefix = {
            "UNKNOWN",
            "SHALLOW_UP_SWING",
            "SHALLOW_DOWN_SWING",
            "BELOW_TYPICAL_UP_SWING",
            "BELOW_TYPICAL_DOWN_SWING",
            "TYPICAL_UP_SWING",
            "TYPICAL_DOWN_SWING",
            "EXTENDED_UP_SWING",
            "EXTENDED_DOWN_SWING",
            "EXTREME_UP_SWING",
            "EXTREME_DOWN_SWING",
        }
        if str(c["LastSwingState"]) not in allowed_last_swing_prefix:
            failures.append("unsupported LastSwingState")

        if len(current) == 1 and pd.notna(current.iloc[0]["StartPivotDate"]):
            start_date = pd.Timestamp(current.iloc[0]["StartPivotDate"])
            as_of_date = pd.Timestamp(current.iloc[0]["AsOfDate"])
            ohlc_dates = pd.to_datetime(ohlc["Date"])
            expected_bars = int(
                ((ohlc_dates >= start_date) & (ohlc_dates <= as_of_date)).sum() - 1
            )
            expected_bars = max(expected_bars, 0)

            if int(c["CurrentTradingBars"]) != expected_bars:
                failures.append(
                    "CurrentTradingBars mismatch: "
                    f"stored={int(c['CurrentTradingBars'])} expected={expected_bars}"
                )

            if expected_bars >= 1 and pd.notna(current.iloc[0]["CurrentMovePct"]):
                expected_speed = float(current.iloc[0]["CurrentMovePct"]) / expected_bars
                expected_ratio = abs(expected_speed) / float(
                    p["MedianAbsVelocityPctPerBar"]
                )

                if not np.isclose(
                    float(c["CurrentMoveSpeedPctPerBar"]),
                    expected_speed,
                    rtol=1e-9,
                    atol=1e-9,
                ):
                    failures.append("CurrentMoveSpeedPctPerBar mismatch")

                if not np.isclose(
                    float(c["CurrentMoveSpeedRatio"]),
                    expected_ratio,
                    rtol=1e-9,
                    atol=1e-9,
                ):
                    failures.append("CurrentMoveSpeedRatio mismatch")

    schema_text = SCHEMA_SQL.read_text(encoding="utf-8").lower()
    for forbidden in ("vw_ticker_smartmoney", "vw_rs_", "levelladder"):
        if forbidden in schema_text:
            failures.append(f"forbidden cross-domain dependency: {forbidden}")

    print("=== MovementContext V1 MWG validation ===")
    print(f"context_rows: {len(context)}")
    print(f"profile_rows: {len(profile)}")
    print(f"current_rows: {len(current)}")
    print(f"structural_errors: {len(failures)}")

    if not context.empty:
        print("\n--- MWG MovementContext ---")
        print(context.to_string(index=False))

    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nMOVEMENT CONTEXT VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(validate())
