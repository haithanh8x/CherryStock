from __future__ import annotations

import pandas as pd

from cherrystock.domain.analytics.price_movement.models import (
    PriceMovementConfig,
    PriceMovementProfile,
    PriceMovementSwing,
)


class PriceMovementRepository:
    """DuckDB persistence for REQ-0031 Price Movement V2.

    Transaction ownership stays with the caller. This repository never commits.
    """

    def __init__(self, connection) -> None:
        self._connection = connection

    def load_config(self, config_code: str = "PM_ZZ_D_V2") -> PriceMovementConfig:
        row = self._connection.execute(
            """
            SELECT
                ConfigId,
                ConfigCode,
                ModelVersion,
                Timeframe,
                ZigZagConfigCode,
                ProfileLookbackSwings,
                MinimumProfileSwings,
                TrendBiasThreshold,
                RangeBiasThreshold,
                EfficiencyThreshold,
                ATRPeriod
            FROM "CherryMon"."main"."dim_price_movement_config"
            WHERE ConfigCode = ?
              AND IsEnabled = TRUE
            ORDER BY ConfigId DESC
            LIMIT 1
            """,
            [config_code],
        ).fetchone()

        if row is None:
            raise RuntimeError(
                f"Enabled Price Movement config '{config_code}' was not found."
            )

        return PriceMovementConfig(
            config_id=int(row[0]),
            config_code=str(row[1]),
            model_version=str(row[2]),
            timeframe=str(row[3]),
            zigzag_config_code=str(row[4]),
            profile_lookback_swings=int(row[5]),
            minimum_profile_swings=int(row[6]),
            trend_bias_threshold=float(row[7]),
            range_bias_threshold=float(row[8]),
            efficiency_threshold=float(row[9]),
            atr_period=int(row[10]),
        )

    def load_zigzag_swings(
        self,
        *,
        ticker: str,
        zigzag_config_code: str,
    ) -> pd.DataFrame:
        frame = self._connection.execute(
            """
            SELECT
                ConfigId,
                ConfigCode,
                ModelVersion,
                Timeframe,
                DeviationPct,
                Ticker,
                SwingSeq,
                Direction,
                StartPivotSeq,
                StartPivotType,
                StartDate,
                StartPrice,
                EndPivotSeq,
                EndPivotType,
                EndDate,
                EndPrice,
                ConfirmedAtDate,
                SwingPct,
                CalendarDays
            FROM "CherryMon"."main"."vw_Ticker_ZigZag_Swings"
            WHERE Ticker = ?
              AND ConfigCode = ?
            ORDER BY SwingSeq
            """,
            [ticker, zigzag_config_code],
        ).df()

        for column in ("StartDate", "EndDate", "ConfirmedAtDate"):
            if column in frame.columns:
                frame[column] = pd.to_datetime(frame[column])
        return frame

    def load_ohlc(self, *, ticker: str) -> pd.DataFrame:
        frame = self._connection.execute(
            """
            SELECT
                Ticker,
                Date,
                High,
                Low,
                Close
            FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
            WHERE Ticker = ?
            ORDER BY Date
            """,
            [ticker],
        ).df()
        if not frame.empty:
            frame["Date"] = pd.to_datetime(frame["Date"])
        return frame

    def replace_ticker(
        self,
        *,
        price_movement_config_id: int,
        ticker: str,
        swings: list[PriceMovementSwing],
        profile: PriceMovementProfile | None,
    ) -> dict[str, int]:
        self._connection.execute(
            """
            DELETE FROM "CherryMon"."main"."cal_price_movement_profile"
            WHERE PriceMovementConfigId = ?
              AND Ticker = ?
            """,
            [price_movement_config_id, ticker],
        )
        self._connection.execute(
            """
            DELETE FROM "CherryMon"."main"."cal_price_movement_swing"
            WHERE PriceMovementConfigId = ?
              AND Ticker = ?
            """,
            [price_movement_config_id, ticker],
        )

        if swings:
            self._connection.executemany(
                """
                INSERT INTO "CherryMon"."main"."cal_price_movement_swing" (
                    PriceMovementConfigId,
                    ZigZagConfigId,
                    ZigZagConfigCode,
                    Ticker,
                    SwingSeq,
                    Direction,
                    StartPivotSeq,
                    StartDate,
                    StartPrice,
                    EndPivotSeq,
                    EndDate,
                    EndPrice,
                    ConfirmedAtDate,
                    SwingPct,
                    TradingBars,
                    CalendarDays,
                    VelocityPctPerBar,
                    AvgATRPct,
                    ATRNormalizedMove,
                    PathEfficiency,
                    DirectionalPersistenceRate
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                [item.to_record() for item in swings],
            )

        profile_rows = 0
        if profile is not None:
            self._connection.execute(
                """
                INSERT INTO "CherryMon"."main"."cal_price_movement_profile" (
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
                    MovementCharacter
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                profile.to_record(),
            )
            profile_rows = 1

        return {
            "swing_rows_inserted": len(swings),
            "profile_rows_inserted": profile_rows,
        }
