from __future__ import annotations

import pandas as pd

from cherrystock.domain.analytics.price_movement.engine import calculate_ticker_movement
from cherrystock.domain.analytics.price_movement.models import MovementConfig
from cherrystock.domain.analytics.price_movement.runtime import calculate_ticker_movement_fast


def _config() -> MovementConfig:
    return MovementConfig(
        config_id=1,
        model_id=1,
        model_code="PRICE_MOVEMENT_CHARACTER",
        model_version="V1",
        timeframe="D",
        atr_multiplier=2.0,
        min_reversal_pct=0.03,
        minimum_swing_bars=2,
        min_historical_same_dir=2,
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


def _frame() -> pd.DataFrame:
    closes = [100, 104, 108, 109, 107, 104, 101, 103, 106, 110, 108]
    highs = [101, 105, 110, 112, 109, 106, 103, 105, 108, 112, 110]
    lows = [99, 100, 103, 107, 105, 102, 99, 101, 104, 108, 106]
    return pd.DataFrame(
        {
            "Ticker": ["MWG"] * len(closes),
            "Date": pd.date_range("2026-01-01", periods=len(closes), freq="D"),
            "Open": closes,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "ATR": [1.0] * len(closes),
        }
    )


def test_fast_runtime_matches_reference_state_machine() -> None:
    frame = _frame()
    config = _config()

    reference_events, reference_daily = calculate_ticker_movement(
        frame,
        ticker="MWG",
        config=config,
    )
    fast_events, fast_daily = calculate_ticker_movement_fast(
        frame,
        ticker="MWG",
        config=config,
    )

    assert [event.to_record() for event in fast_events] == [
        event.to_record() for event in reference_events
    ]
    assert fast_daily == reference_daily
