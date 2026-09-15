from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from cherrystock.domain.analytics.price_movement.engine import (
    calculate_leg_features,
    calculate_ticker_movement,
    classify_movement,
    score_against_history,
)
from cherrystock.domain.analytics.price_movement.models import (
    MovementConfig,
    SwingEvent,
)


def _config(*, min_history: int = 8) -> MovementConfig:
    return MovementConfig(
        config_id=1,
        model_id=1,
        model_code="PRICE_MOVEMENT_CHARACTER",
        model_version="V1",
        timeframe="D",
        atr_multiplier=2.0,
        min_reversal_pct=0.03,
        minimum_swing_bars=2,
        min_historical_same_dir=min_history,
        profile_max_swings=50,
        magnitude_raw_weight=0.60,
        magnitude_atr_weight=0.40,
        persistence_er_weight=0.35,
        persistence_r2_weight=0.35,
        persistence_smoothness_weight=0.20,
        persistence_directional_day_weight=0.10,
        high_magnitude_threshold=75.0,
        high_velocity_threshold=75.0,
        high_persistence_threshold=70.0,
        low_persistence_threshold=55.0,
        mid_magnitude_threshold=40.0,
    )


def _frame(closes: list[float], *, highs=None, lows=None, atr: float = 1.0) -> pd.DataFrame:
    start = pd.Timestamp("2026-01-01")
    highs = highs or [value + 1 for value in closes]
    lows = lows or [value - 1 for value in closes]
    return pd.DataFrame(
        {
            "Ticker": ["MWG"] * len(closes),
            "Date": [start + pd.Timedelta(days=index) for index in range(len(closes))],
            "Open": closes,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "ATR": [atr] * len(closes),
        }
    )


def _event(index: int, *, direction: str = "UP") -> SwingEvent:
    start = date(2025, 1, 1) + timedelta(days=index * 10)
    end = start + timedelta(days=4)
    confirmed = end + timedelta(days=2)
    magnitude = 0.05 + index * 0.01
    return SwingEvent(
        config_id=1,
        ticker="MWG",
        direction=direction,
        swing_seq=index + 1,
        pivot_start_date=start,
        pivot_end_date=end,
        confirmed_at_date=confirmed,
        start_price=100.0,
        end_price=100.0 * (1.0 + magnitude if direction == "UP" else 1.0 - magnitude),
        swing_pct=magnitude if direction == "UP" else -magnitude,
        duration_bars=4,
        duration_calendar_days=4,
        velocity_log_per_bar=0.01 + index * 0.001,
        velocity_pct_per_bar=1.0,
        mean_atr=2.0,
        atr_norm_magnitude=2.5 + index * 0.25,
        efficiency_ratio=0.8,
        regression_slope_per_bar=0.01,
        regression_r2=0.9,
        max_adverse_excursion_pct=0.01,
        directional_day_ratio=0.8,
        persistence_score=82.0,
        threshold_pct=0.03,
        threshold_source="ATR_PLUS_FLOOR",
        quality_status="OK",
    )


def test_confirmed_swing_keeps_pivot_date_separate_from_confirmation_date() -> None:
    frame = _frame(
        [100, 104, 108, 109, 107, 105],
        highs=[101, 105, 110, 112, 109, 107],
        lows=[99, 100, 103, 107, 105, 103],
        atr=1.0,
    )

    events, daily = calculate_ticker_movement(
        frame,
        ticker="MWG",
        config=_config(min_history=2),
    )

    assert events
    first = events[0]
    assert first.direction == "UP"
    assert first.pivot_end_date == date(2026, 1, 4)
    assert first.confirmed_at_date == date(2026, 1, 5)
    assert first.pivot_end_date < first.confirmed_at_date
    assert daily[-1]["SwingStatus"] == "PROVISIONAL"


def test_smooth_path_has_better_persistence_evidence_than_noisy_path() -> None:
    smooth = _frame([100, 104, 108, 112, 116, 120], atr=2.0)
    noisy = _frame([100, 115, 103, 118, 106, 120], atr=2.0)

    smooth_features = calculate_leg_features(
        smooth,
        direction="UP",
        start_price=100.0,
        endpoint_price=120.0,
    )
    noisy_features = calculate_leg_features(
        noisy,
        direction="UP",
        start_price=100.0,
        endpoint_price=120.0,
    )

    assert smooth_features["EfficiencyRatio"] > noisy_features["EfficiencyRatio"]
    assert smooth_features["RegressionR2"] > noisy_features["RegressionR2"]
    assert smooth_features["MaxAdverseExcursionPct"] < noisy_features["MaxAdverseExcursionPct"]


def test_same_direction_history_produces_separate_magnitude_and_velocity_scores() -> None:
    history = [_event(index, direction="UP") for index in range(8)]
    features = {
        "SwingPct": 0.11,
        "DurationBars": 4,
        "VelocityLogPerBar": 0.018,
        "VelocityPctPerBar": 1.8,
        "MeanATR": 2.0,
        "ATRNormMagnitude": 5.5,
        "EfficiencyRatio": 0.85,
        "RegressionSlopePerBar": 0.02,
        "RegressionR2": 0.92,
        "MaxAdverseExcursionPct": 0.01,
        "DirectionalDayRatio": 0.80,
        "SmoothnessComponent": 0.91,
    }

    score = score_against_history(
        direction="UP",
        as_of_date=date(2026, 1, 1),
        features=features,
        prior_swings=history,
        config=_config(),
    )

    assert score["HistoricalSameDirSwingCount"] == 8
    assert score["MagnitudeScore"] is not None
    assert score["VelocityScore"] is not None
    assert score["PersistenceScore"] is not None
    assert score["ScoreBasis"] == "RAW_PLUS_ATR"


def test_insufficient_history_is_explicit_not_zero_score() -> None:
    config = _config(min_history=8)
    label = classify_movement(
        "UP",
        magnitude_score=None,
        velocity_score=None,
        persistence_score_value=80.0,
        historical_count=3,
        config=config,
    )
    assert label == "INSUFFICIENT_HISTORY"
