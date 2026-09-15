from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd

from cherrystock.domain.analytics.price_movement.models import (
    MovementConfig,
    SeedState,
    SwingEvent,
)


class PriceMovementRepository:
    """DuckDB repository for Price Movement Character metadata and persistence."""

    DAILY_TABLE = '"CherryMon"."main"."cal_price_movement_daily"'
    SWING_TABLE = '"CherryMon"."main"."cal_price_movement_swing"'

    def __init__(self, connection) -> None:
        self._connection = connection

    def load_enabled_config(self, as_of_date: date | None = None) -> MovementConfig:
        resolved_date = as_of_date or date.today()
        row = self._connection.execute(
            """
            SELECT
                c.ConfigId,
                c.ModelId,
                m.ModelCode,
                m.ModelVersion,
                c.Timeframe,
                c.ATRMultiplier,
                c.MinReversalPct,
                c.MinimumSwingBars,
                c.MinHistoricalSameDir,
                c.ProfileMaxSwings,
                c.MagnitudeRawWeight,
                c.MagnitudeATRWeight,
                c.PersistenceERWeight,
                c.PersistenceR2Weight,
                c.PersistenceSmoothnessWeight,
                c.PersistenceDirectionalDayWeight,
                c.HighMagnitudeThreshold,
                c.HighVelocityThreshold,
                c.HighPersistenceThreshold,
                c.LowPersistenceThreshold,
                c.MidMagnitudeThreshold
            FROM "CherryMon"."main"."dim_price_movement_config" AS c
            INNER JOIN "CherryMon"."main"."dim_price_movement_model" AS m
                ON m.ModelId = c.ModelId
            WHERE c.IsEnabled = TRUE
              AND m.IsEnabled = TRUE
              AND c.EffectiveFrom <= ?
              AND (c.EffectiveTo IS NULL OR c.EffectiveTo >= ?)
              AND m.EffectiveFrom <= ?
              AND (m.EffectiveTo IS NULL OR m.EffectiveTo >= ?)
              AND c.Timeframe = 'D'
            ORDER BY c.EffectiveFrom DESC, c.ConfigId DESC
            LIMIT 1
            """,
            [resolved_date, resolved_date, resolved_date, resolved_date],
        ).fetchone()
        if row is None:
            raise RuntimeError("No enabled daily Price Movement Character config is available.")

        return MovementConfig(
            config_id=int(row[0]),
            model_id=int(row[1]),
            model_code=str(row[2]),
            model_version=str(row[3]),
            timeframe=str(row[4]),
            atr_multiplier=float(row[5]),
            min_reversal_pct=float(row[6]),
            minimum_swing_bars=int(row[7]),
            min_historical_same_dir=int(row[8]),
            profile_max_swings=int(row[9]),
            magnitude_raw_weight=float(row[10]),
            magnitude_atr_weight=float(row[11]),
            persistence_er_weight=float(row[12]),
            persistence_r2_weight=float(row[13]),
            persistence_smoothness_weight=float(row[14]),
            persistence_directional_day_weight=float(row[15]),
            high_magnitude_threshold=float(row[16]),
            high_velocity_threshold=float(row[17]),
            high_persistence_threshold=float(row[18]),
            low_persistence_threshold=float(row[19]),
            mid_magnitude_threshold=float(row[20]),
        )

    @staticmethod
    def _ticker_filter(tickers: Iterable[str] | None, alias: str = "") -> tuple[str, list[object]]:
        normalized = sorted(
            {str(value).strip().upper() for value in (tickers or []) if str(value).strip()}
        )
        if not normalized:
            return "", []
        prefix = f"{alias}." if alias else ""
        placeholders = ", ".join("?" for _ in normalized)
        return f" AND {prefix}Ticker IN ({placeholders})", normalized

    def load_latest_daily_states(
        self,
        *,
        config_id: int,
        tickers: Iterable[str] | None = None,
    ) -> dict[str, SeedState]:
        ticker_filter, params = self._ticker_filter(tickers, alias="d")
        rows = self._connection.execute(
            f"""
            WITH ranked AS (
                SELECT
                    d.Ticker,
                    d.Date,
                    d.Direction,
                    d.CurrentSwingStartDate,
                    d.CandidateEndDate,
                    d.StartPrice,
                    d.CandidateEndPrice,
                    ROW_NUMBER() OVER (
                        PARTITION BY d.Ticker
                        ORDER BY d.Date DESC
                    ) AS rn
                FROM {self.DAILY_TABLE} AS d
                WHERE d.ConfigId = ?
                  {ticker_filter}
            )
            SELECT
                Ticker,
                Date,
                Direction,
                CurrentSwingStartDate,
                CandidateEndDate,
                StartPrice,
                CandidateEndPrice
            FROM ranked
            WHERE rn = 1
            """,
            [int(config_id), *params],
        ).fetchall()

        result: dict[str, SeedState] = {}
        for row in rows:
            if (
                row[2] not in {"UP", "DOWN"}
                or row[3] is None
                or row[4] is None
                or row[5] is None
                or row[6] is None
            ):
                continue
            result[str(row[0])] = SeedState(
                date=row[1],
                direction=str(row[2]),
                current_swing_start_date=row[3],
                candidate_end_date=row[4],
                start_price=float(row[5]),
                candidate_end_price=float(row[6]),
            )
        return result

    def load_latest_daily_dates(
        self,
        *,
        config_id: int,
        tickers: Iterable[str] | None = None,
    ) -> dict[str, date]:
        ticker_filter, params = self._ticker_filter(tickers)
        rows = self._connection.execute(
            f"""
            SELECT Ticker, MAX(Date) AS MaxDate
            FROM {self.DAILY_TABLE}
            WHERE ConfigId = ?
              {ticker_filter}
            GROUP BY Ticker
            """,
            [int(config_id), *params],
        ).fetchall()
        return {str(ticker): max_date for ticker, max_date in rows if max_date is not None}

    def load_confirmed_swings(
        self,
        *,
        config_id: int,
        tickers: Iterable[str] | None = None,
    ) -> dict[str, list[SwingEvent]]:
        ticker_filter, params = self._ticker_filter(tickers)
        rows = self._connection.execute(
            f"""
            SELECT
                ConfigId,
                Ticker,
                Direction,
                SwingSeq,
                PivotStartDate,
                PivotEndDate,
                ConfirmedAtDate,
                StartPrice,
                EndPrice,
                SwingPct,
                DurationBars,
                DurationCalendarDays,
                VelocityLogPerBar,
                VelocityPctPerBar,
                MeanATR,
                ATRNormMagnitude,
                EfficiencyRatio,
                RegressionSlopePerBar,
                RegressionR2,
                MaxAdverseExcursionPct,
                DirectionalDayRatio,
                PersistenceScore,
                ThresholdPct,
                ThresholdSource,
                QualityStatus
            FROM {self.SWING_TABLE}
            WHERE ConfigId = ?
              {ticker_filter}
            ORDER BY Ticker, SwingSeq
            """,
            [int(config_id), *params],
        ).fetchall()

        result: dict[str, list[SwingEvent]] = {}
        for row in rows:
            event = SwingEvent(
                config_id=int(row[0]),
                ticker=str(row[1]),
                direction=str(row[2]),
                swing_seq=int(row[3]),
                pivot_start_date=row[4],
                pivot_end_date=row[5],
                confirmed_at_date=row[6],
                start_price=float(row[7]),
                end_price=float(row[8]),
                swing_pct=float(row[9]),
                duration_bars=int(row[10]),
                duration_calendar_days=int(row[11]),
                velocity_log_per_bar=float(row[12]),
                velocity_pct_per_bar=float(row[13]),
                mean_atr=None if row[14] is None else float(row[14]),
                atr_norm_magnitude=None if row[15] is None else float(row[15]),
                efficiency_ratio=float(row[16]),
                regression_slope_per_bar=None if row[17] is None else float(row[17]),
                regression_r2=None if row[18] is None else float(row[18]),
                max_adverse_excursion_pct=float(row[19]),
                directional_day_ratio=float(row[20]),
                persistence_score=float(row[21]),
                threshold_pct=float(row[22]),
                threshold_source=str(row[23]),
                quality_status=str(row[24]),
            )
            result.setdefault(event.ticker, []).append(event)
        return result

    def replace_checkpoint(
        self,
        *,
        config_id: int,
        tickers: Iterable[str],
        swing_rows: pd.DataFrame,
        daily_rows: pd.DataFrame,
        full_replace: bool,
    ) -> tuple[int, int]:
        normalized = sorted({str(value).strip().upper() for value in tickers if str(value).strip()})
        if not normalized:
            return 0, 0

        cleanup_registered = False
        swing_registered = False
        daily_registered = False
        try:
            if full_replace:
                cleanup = pd.DataFrame(
                    [{"ConfigId": int(config_id), "Ticker": ticker} for ticker in normalized]
                )
                self._connection.register("df_price_movement_cleanup", cleanup)
                cleanup_registered = True
                self._connection.execute(
                    f"""
                    DELETE FROM {self.SWING_TABLE} AS target
                    WHERE EXISTS (
                        SELECT 1
                        FROM df_price_movement_cleanup AS cleanup
                        WHERE cleanup.ConfigId = target.ConfigId
                          AND cleanup.Ticker = target.Ticker
                    )
                    """
                )
                self._connection.execute(
                    f"""
                    DELETE FROM {self.DAILY_TABLE} AS target
                    WHERE EXISTS (
                        SELECT 1
                        FROM df_price_movement_cleanup AS cleanup
                        WHERE cleanup.ConfigId = target.ConfigId
                          AND cleanup.Ticker = target.Ticker
                    )
                    """
                )

            swing_count = 0
            if swing_rows is not None and not swing_rows.empty:
                self._connection.register("df_price_movement_swings", swing_rows)
                swing_registered = True
                self._connection.execute(
                    f"""
                    INSERT INTO {self.SWING_TABLE} (
                        ConfigId, Ticker, Direction, SwingSeq,
                        PivotStartDate, PivotEndDate, ConfirmedAtDate,
                        StartPrice, EndPrice, SwingPct,
                        DurationBars, DurationCalendarDays,
                        VelocityLogPerBar, VelocityPctPerBar,
                        MeanATR, ATRNormMagnitude,
                        EfficiencyRatio, RegressionSlopePerBar, RegressionR2,
                        MaxAdverseExcursionPct, DirectionalDayRatio, PersistenceScore,
                        ThresholdPct, ThresholdSource, QualityStatus, CalculatedAt
                    )
                    SELECT
                        ConfigId, Ticker, Direction, SwingSeq,
                        PivotStartDate, PivotEndDate, ConfirmedAtDate,
                        StartPrice, EndPrice, SwingPct,
                        DurationBars, DurationCalendarDays,
                        VelocityLogPerBar, VelocityPctPerBar,
                        MeanATR, ATRNormMagnitude,
                        EfficiencyRatio, RegressionSlopePerBar, RegressionR2,
                        MaxAdverseExcursionPct, DirectionalDayRatio, PersistenceScore,
                        ThresholdPct, ThresholdSource, QualityStatus, CURRENT_TIMESTAMP
                    FROM df_price_movement_swings
                    ON CONFLICT (ConfigId, Ticker, PivotStartDate, Direction) DO UPDATE SET
                        SwingSeq = EXCLUDED.SwingSeq,
                        PivotEndDate = EXCLUDED.PivotEndDate,
                        ConfirmedAtDate = EXCLUDED.ConfirmedAtDate,
                        StartPrice = EXCLUDED.StartPrice,
                        EndPrice = EXCLUDED.EndPrice,
                        SwingPct = EXCLUDED.SwingPct,
                        DurationBars = EXCLUDED.DurationBars,
                        DurationCalendarDays = EXCLUDED.DurationCalendarDays,
                        VelocityLogPerBar = EXCLUDED.VelocityLogPerBar,
                        VelocityPctPerBar = EXCLUDED.VelocityPctPerBar,
                        MeanATR = EXCLUDED.MeanATR,
                        ATRNormMagnitude = EXCLUDED.ATRNormMagnitude,
                        EfficiencyRatio = EXCLUDED.EfficiencyRatio,
                        RegressionSlopePerBar = EXCLUDED.RegressionSlopePerBar,
                        RegressionR2 = EXCLUDED.RegressionR2,
                        MaxAdverseExcursionPct = EXCLUDED.MaxAdverseExcursionPct,
                        DirectionalDayRatio = EXCLUDED.DirectionalDayRatio,
                        PersistenceScore = EXCLUDED.PersistenceScore,
                        ThresholdPct = EXCLUDED.ThresholdPct,
                        ThresholdSource = EXCLUDED.ThresholdSource,
                        QualityStatus = EXCLUDED.QualityStatus,
                        CalculatedAt = EXCLUDED.CalculatedAt
                    """
                )
                swing_count = len(swing_rows)

            daily_count = 0
            if daily_rows is not None and not daily_rows.empty:
                self._connection.register("df_price_movement_daily", daily_rows)
                daily_registered = True
                self._connection.execute(
                    f"""
                    INSERT INTO {self.DAILY_TABLE} (
                        ConfigId, Ticker, Date, Direction, SwingStatus,
                        CurrentSwingStartDate, CandidateEndDate, StartPrice, CandidateEndPrice,
                        CurrentSwingPct, DurationBars, VelocityLogPerBar, VelocityPctPerBar,
                        ATRNormMagnitude, EfficiencyRatio, RegressionSlopePerBar, RegressionR2,
                        MaxAdverseExcursionPct, DirectionalDayRatio,
                        HistoricalSameDirSwingCount,
                        MagnitudePercentile, ATRNormMagnitudePercentile,
                        VelocityPercentile, PersistencePercentile,
                        MagnitudeScore, VelocityScore, PersistenceScore,
                        MovementCharacter, ScoreBasis,
                        ThresholdPct, ThresholdSource, QualityStatus, CalculatedAt
                    )
                    SELECT
                        ConfigId, Ticker, Date, Direction, SwingStatus,
                        CurrentSwingStartDate, CandidateEndDate, StartPrice, CandidateEndPrice,
                        CurrentSwingPct, DurationBars, VelocityLogPerBar, VelocityPctPerBar,
                        ATRNormMagnitude, EfficiencyRatio, RegressionSlopePerBar, RegressionR2,
                        MaxAdverseExcursionPct, DirectionalDayRatio,
                        HistoricalSameDirSwingCount,
                        MagnitudePercentile, ATRNormMagnitudePercentile,
                        VelocityPercentile, PersistencePercentile,
                        MagnitudeScore, VelocityScore, PersistenceScore,
                        MovementCharacter, ScoreBasis,
                        ThresholdPct, ThresholdSource, QualityStatus, CURRENT_TIMESTAMP
                    FROM df_price_movement_daily
                    ON CONFLICT (ConfigId, Ticker, Date) DO UPDATE SET
                        Direction = EXCLUDED.Direction,
                        SwingStatus = EXCLUDED.SwingStatus,
                        CurrentSwingStartDate = EXCLUDED.CurrentSwingStartDate,
                        CandidateEndDate = EXCLUDED.CandidateEndDate,
                        StartPrice = EXCLUDED.StartPrice,
                        CandidateEndPrice = EXCLUDED.CandidateEndPrice,
                        CurrentSwingPct = EXCLUDED.CurrentSwingPct,
                        DurationBars = EXCLUDED.DurationBars,
                        VelocityLogPerBar = EXCLUDED.VelocityLogPerBar,
                        VelocityPctPerBar = EXCLUDED.VelocityPctPerBar,
                        ATRNormMagnitude = EXCLUDED.ATRNormMagnitude,
                        EfficiencyRatio = EXCLUDED.EfficiencyRatio,
                        RegressionSlopePerBar = EXCLUDED.RegressionSlopePerBar,
                        RegressionR2 = EXCLUDED.RegressionR2,
                        MaxAdverseExcursionPct = EXCLUDED.MaxAdverseExcursionPct,
                        DirectionalDayRatio = EXCLUDED.DirectionalDayRatio,
                        HistoricalSameDirSwingCount = EXCLUDED.HistoricalSameDirSwingCount,
                        MagnitudePercentile = EXCLUDED.MagnitudePercentile,
                        ATRNormMagnitudePercentile = EXCLUDED.ATRNormMagnitudePercentile,
                        VelocityPercentile = EXCLUDED.VelocityPercentile,
                        PersistencePercentile = EXCLUDED.PersistencePercentile,
                        MagnitudeScore = EXCLUDED.MagnitudeScore,
                        VelocityScore = EXCLUDED.VelocityScore,
                        PersistenceScore = EXCLUDED.PersistenceScore,
                        MovementCharacter = EXCLUDED.MovementCharacter,
                        ScoreBasis = EXCLUDED.ScoreBasis,
                        ThresholdPct = EXCLUDED.ThresholdPct,
                        ThresholdSource = EXCLUDED.ThresholdSource,
                        QualityStatus = EXCLUDED.QualityStatus,
                        CalculatedAt = EXCLUDED.CalculatedAt
                    """
                )
                daily_count = len(daily_rows)

            return swing_count, daily_count
        finally:
            if daily_registered:
                self._connection.unregister("df_price_movement_daily")
            if swing_registered:
                self._connection.unregister("df_price_movement_swings")
            if cleanup_registered:
                self._connection.unregister("df_price_movement_cleanup")
