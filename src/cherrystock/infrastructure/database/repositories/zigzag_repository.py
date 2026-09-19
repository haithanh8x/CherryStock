from __future__ import annotations

from cherrystock.domain.analytics.zigzag.models import (
    ZigZagConfig,
    ZigZagCurrentLeg,
    ZigZagPivot,
)


class ZigZagRepository:
    """DuckDB persistence for the ZigZag MWG MVP.

    Transaction ownership stays with the caller. This repository never commits.
    """

    def __init__(self, connection) -> None:
        self._connection = connection

    def load_mvp_config(self) -> ZigZagConfig:
        row = self._connection.execute(
            """
            SELECT
                ConfigId,
                ConfigCode,
                ModelVersion,
                Timeframe,
                DeviationPct,
                PivotPriceSource,
                ConfirmationPriceSource,
                MinimumSwingBars
            FROM "CherryMon"."main"."dim_zigzag_config"
            WHERE ConfigCode = 'ZZ_D_5_MVP'
              AND IsEnabled = TRUE
            ORDER BY ConfigId DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            raise RuntimeError("Enabled ZigZag MVP config ZZ_D_5_MVP was not found.")

        return ZigZagConfig(
            config_id=int(row[0]),
            config_code=str(row[1]),
            model_version=str(row[2]),
            timeframe=str(row[3]),
            deviation_pct=float(row[4]),
            pivot_price_source=str(row[5]),
            confirmation_price_source=str(row[6]),
            minimum_swing_bars=int(row[7]),
        )

    def replace_ticker(
        self,
        *,
        config_id: int,
        ticker: str,
        pivots: list[ZigZagPivot],
        current: ZigZagCurrentLeg | None,
    ) -> dict[str, int]:
        self._connection.execute(
            """
            DELETE FROM "CherryMon"."main"."cal_zigzag_current_leg"
            WHERE ConfigId = ? AND Ticker = ?
            """,
            [config_id, ticker],
        )
        self._connection.execute(
            """
            DELETE FROM "CherryMon"."main"."cal_zigzag_pivot"
            WHERE ConfigId = ? AND Ticker = ?
            """,
            [config_id, ticker],
        )

        if pivots:
            self._connection.executemany(
                """
                INSERT INTO "CherryMon"."main"."cal_zigzag_pivot" (
                    ConfigId,
                    Ticker,
                    PivotSeq,
                    PivotType,
                    PivotDate,
                    PivotPrice,
                    ConfirmedAtDate,
                    ConfirmationPrice,
                    DeviationPct
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [pivot.to_record() for pivot in pivots],
            )

        current_rows = 0
        if current is not None:
            self._connection.execute(
                """
                INSERT INTO "CherryMon"."main"."cal_zigzag_current_leg" (
                    ConfigId,
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
                    Status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                current.to_record(),
            )
            current_rows = 1

        return {
            "pivot_rows_inserted": len(pivots),
            "current_rows_inserted": current_rows,
        }
