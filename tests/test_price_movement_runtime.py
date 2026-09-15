from __future__ import annotations

import pandas as pd

from cherrystock.domain.analytics.price_movement.engine import calculate_ticker_movement
from cherrystock.domain.analytics.price_movement.models import MovementConfig
from cherrystock.domain.analytics.price_movement.runtime import calculate_ticker_movement_fast
from cherrystock.domain.analytics.price_movement.source_quality import (
    inspect_price_source_quality,
)


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


def test_runtime_drops_nonpositive_calculation_bar_without_crashing() -> None:
    frame = _frame()
    bad_date = pd.Timestamp(frame.loc[2, "Date"]).date()
    frame.loc[2, "Low"] = 0.0

    diagnostics = inspect_price_source_quality(frame)
    events, daily = calculate_ticker_movement_fast(
        frame,
        ticker="MWG",
        config=_config(),
    )

    assert diagnostics.invalid_ohlc_rows == 1
    assert diagnostics.invalid_calculation_rows == 1
    assert diagnostics.open_only_invalid_rows == 0
    assert diagnostics.usable_rows == len(frame) - 1
    assert all(row["Date"] != bad_date for row in daily)
    assert all(row["QualityStatus"] == "PARTIAL" for row in daily)
    assert all(event.quality_status == "PARTIAL" for event in events)
    assert all(event.start_price > 0 and event.end_price > 0 for event in events)


def test_runtime_retains_open_only_zero_but_marks_source_partial() -> None:
    frame = _frame()
    frame.loc[2, "Open"] = 0.0

    diagnostics = inspect_price_source_quality(frame)
    events, daily = calculate_ticker_movement_fast(
        frame,
        ticker="MWG",
        config=_config(),
    )

    assert diagnostics.invalid_ohlc_rows == 1
    assert diagnostics.invalid_calculation_rows == 0
    assert diagnostics.open_only_invalid_rows == 1
    assert diagnostics.usable_rows == len(frame)
    assert len(daily) == len(frame)
    assert all(row["QualityStatus"] == "PARTIAL" for row in daily)
    assert all(event.quality_status == "PARTIAL" for event in events)
