from __future__ import annotations

from collections.abc import Iterable


class ZigZagResearchRepository:
    """Persistence for manual ZigZag research workflows.

    Transaction ownership stays with the caller. This repository never commits.
    """

    def __init__(self, connection) -> None:
        self._connection = connection

    def replace_calibration(
        self,
        *,
        calibration_version: str,
        ticker: str,
        evaluations: Iterable[dict[str, object]],
        selection,
    ) -> None:
        self._connection.execute(
            """
            DELETE FROM "CherryMon"."main"."cal_zigzag_deviation_evaluation"
            WHERE CalibrationVersion = ? AND Ticker = ?
            """,
            [calibration_version, ticker],
        )
        self._connection.execute(
            """
            DELETE FROM "CherryMon"."main"."dim_zigzag_ticker_config"
            WHERE CalibrationVersion = ? AND Ticker = ? AND Timeframe = 'D'
            """,
            [calibration_version, ticker],
        )

        rows = list(evaluations)
        if rows:
            self._connection.executemany(
                """
                INSERT INTO "CherryMon"."main"."cal_zigzag_deviation_evaluation" (
                    CalibrationVersion,
                    Ticker,
                    SplitName,
                    DeviationPct,
                    SourceBars,
                    PivotCount,
                    SwingCount,
                    PivotDensityPer100Bars,
                    MedianSwingBars,
                    MedianAbsSwingPct,
                    ShortSwingRate,
                    StructuralValid,
                    IsEligible,
                    CalibrationScore
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row["CalibrationVersion"],
                        row["Ticker"],
                        row["SplitName"],
                        row["DeviationPct"],
                        row["SourceBars"],
                        row["PivotCount"],
                        row["SwingCount"],
                        row["PivotDensityPer100Bars"],
                        row["MedianSwingBars"],
                        row["MedianAbsSwingPct"],
                        row["ShortSwingRate"],
                        row["StructuralValid"],
                        row["IsEligible"],
                        row["CalibrationScore"],
                    )
                    for row in rows
                ],
            )

        self._connection.execute(
            """
            INSERT INTO "CherryMon"."main"."dim_zigzag_ticker_config" (
                CalibrationVersion,
                Ticker,
                Timeframe,
                BaseDeviationPct,
                SelectionMethod,
                TrainScore,
                ValidationScore,
                TestScore,
                Status,
                IsActive
            )
            VALUES (?, ?, 'D', ?, ?, ?, ?, ?, 'RECOMMENDED', FALSE)
            """,
            [
                calibration_version,
                ticker,
                selection.selected_deviation_pct,
                selection.selection_method,
                selection.train_score,
                selection.validation_score,
                selection.test_score,
            ],
        )

    def load_recommendations(
        self,
        *,
        calibration_version: str,
        tickers: Iterable[str],
    ) -> dict[str, float]:
        resolved = [ticker.strip().upper() for ticker in tickers if ticker.strip()]
        if not resolved:
            return {}

        placeholders = ",".join("?" for _ in resolved)
        rows = self._connection.execute(
            f"""
            SELECT Ticker, BaseDeviationPct
            FROM "CherryMon"."main"."dim_zigzag_ticker_config"
            WHERE CalibrationVersion = ?
              AND Timeframe = 'D'
              AND Ticker IN ({placeholders})
            """,
            [calibration_version, *resolved],
        ).fetchall()
        return {str(row[0]): float(row[1]) for row in rows}

    def replace_pilot(
        self,
        *,
        pilot_version: str,
        calibration_version: str,
        row: dict[str, object],
    ) -> None:
        ticker = str(row["Ticker"])
        self._connection.execute(
            """
            DELETE FROM "CherryMon"."main"."cal_zigzag_pilot_evaluation"
            WHERE PilotVersion = ? AND Ticker = ?
            """,
            [pilot_version, ticker],
        )
        self._connection.execute(
            """
            INSERT INTO "CherryMon"."main"."cal_zigzag_pilot_evaluation" (
                PilotVersion,
                CalibrationVersion,
                Ticker,
                BaselineDeviationPct,
                CalibratedDeviationPct,
                BaselineSwingCount,
                CalibratedSwingCount,
                BaselinePivotDensity,
                CalibratedPivotDensity,
                BaselineMedianSwingBars,
                CalibratedMedianSwingBars,
                BaselineMedianAbsSwingPct,
                CalibratedMedianAbsSwingPct,
                BaselineShortSwingRate,
                CalibratedShortSwingRate,
                BaselineStructuralValid,
                CalibratedStructuralValid,
                BaselineScore,
                CalibratedScore,
                Decision
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                pilot_version,
                calibration_version,
                ticker,
                row["BaselineDeviationPct"],
                row["CalibratedDeviationPct"],
                row["BaselineSwingCount"],
                row["CalibratedSwingCount"],
                row["BaselinePivotDensity"],
                row["CalibratedPivotDensity"],
                row["BaselineMedianSwingBars"],
                row["CalibratedMedianSwingBars"],
                row["BaselineMedianAbsSwingPct"],
                row["CalibratedMedianAbsSwingPct"],
                row["BaselineShortSwingRate"],
                row["CalibratedShortSwingRate"],
                row["BaselineStructuralValid"],
                row["CalibratedStructuralValid"],
                row["BaselineScore"],
                row["CalibratedScore"],
                row["Decision"],
            ],
        )

    def replace_regime(
        self,
        *,
        regime_version: str,
        calibration_version: str,
        row: dict[str, object],
    ) -> None:
        ticker = str(row["Ticker"])
        self._connection.execute(
            """
            DELETE FROM "CherryMon"."main"."cal_zigzag_regime_evaluation"
            WHERE RegimeVersion = ? AND Ticker = ?
            """,
            [regime_version, ticker],
        )
        self._connection.execute(
            """
            INSERT INTO "CherryMon"."main"."cal_zigzag_regime_evaluation" (
                RegimeVersion,
                CalibrationVersion,
                Ticker,
                BaseDeviationPct,
                StaticSwingCount,
                RegimeSwingCount,
                StaticShortSwingRate,
                RegimeShortSwingRate,
                StaticMedianSwingBars,
                RegimeMedianSwingBars,
                StaticMedianAbsSwingPct,
                RegimeMedianAbsSwingPct,
                StaticStructuralValid,
                RegimeStructuralValid,
                StaticScore,
                RegimeScore,
                LowVolBars,
                NormalBars,
                HighVolBars
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                regime_version,
                calibration_version,
                ticker,
                row["BaseDeviationPct"],
                row["StaticSwingCount"],
                row["RegimeSwingCount"],
                row["StaticShortSwingRate"],
                row["RegimeShortSwingRate"],
                row["StaticMedianSwingBars"],
                row["RegimeMedianSwingBars"],
                row["StaticMedianAbsSwingPct"],
                row["RegimeMedianAbsSwingPct"],
                row["StaticStructuralValid"],
                row["RegimeStructuralValid"],
                row["StaticScore"],
                row["RegimeScore"],
                row["LowVolBars"],
                row["NormalBars"],
                row["HighVolBars"],
            ],
        )
