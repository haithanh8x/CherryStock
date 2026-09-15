from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class MovementConfig:
    config_id: int
    model_id: int
    model_code: str
    model_version: str
    timeframe: str
    atr_multiplier: float
    min_reversal_pct: float
    minimum_swing_bars: int
    min_historical_same_dir: int
    profile_max_swings: int
    magnitude_raw_weight: float
    magnitude_atr_weight: float
    persistence_er_weight: float
    persistence_r2_weight: float
    persistence_smoothness_weight: float
    persistence_directional_day_weight: float
    high_magnitude_threshold: float
    high_velocity_threshold: float
    high_persistence_threshold: float
    low_persistence_threshold: float
    mid_magnitude_threshold: float


@dataclass(frozen=True)
class SeedState:
    date: date
    direction: str
    current_swing_start_date: date
    candidate_end_date: date
    start_price: float
    candidate_end_price: float


@dataclass(frozen=True)
class SwingEvent:
    config_id: int
    ticker: str
    direction: str
    swing_seq: int
    pivot_start_date: date
    pivot_end_date: date
    confirmed_at_date: date
    start_price: float
    end_price: float
    swing_pct: float
    duration_bars: int
    duration_calendar_days: int
    velocity_log_per_bar: float
    velocity_pct_per_bar: float
    mean_atr: float | None
    atr_norm_magnitude: float | None
    efficiency_ratio: float
    regression_slope_per_bar: float | None
    regression_r2: float | None
    max_adverse_excursion_pct: float
    directional_day_ratio: float
    persistence_score: float
    threshold_pct: float
    threshold_source: str
    quality_status: str

    def to_record(self) -> dict[str, Any]:
        return {
            "ConfigId": self.config_id,
            "Ticker": self.ticker,
            "Direction": self.direction,
            "SwingSeq": self.swing_seq,
            "PivotStartDate": self.pivot_start_date,
            "PivotEndDate": self.pivot_end_date,
            "ConfirmedAtDate": self.confirmed_at_date,
            "StartPrice": self.start_price,
            "EndPrice": self.end_price,
            "SwingPct": self.swing_pct,
            "DurationBars": self.duration_bars,
            "DurationCalendarDays": self.duration_calendar_days,
            "VelocityLogPerBar": self.velocity_log_per_bar,
            "VelocityPctPerBar": self.velocity_pct_per_bar,
            "MeanATR": self.mean_atr,
            "ATRNormMagnitude": self.atr_norm_magnitude,
            "EfficiencyRatio": self.efficiency_ratio,
            "RegressionSlopePerBar": self.regression_slope_per_bar,
            "RegressionR2": self.regression_r2,
            "MaxAdverseExcursionPct": self.max_adverse_excursion_pct,
            "DirectionalDayRatio": self.directional_day_ratio,
            "PersistenceScore": self.persistence_score,
            "ThresholdPct": self.threshold_pct,
            "ThresholdSource": self.threshold_source,
            "QualityStatus": self.quality_status,
        }
