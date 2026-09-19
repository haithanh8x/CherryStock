from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from cherrystock.domain.analytics.price_movement.classifier import classify_movement
from cherrystock.domain.analytics.price_movement.engine import (
    build_price_movement_profile,
    build_price_movement_swings,
    calculate_price_movement,
)
from cherrystock.domain.analytics.price_movement.models import (
    PriceMovementConfig,
    PriceMovementSwing,
)


def _config(
    *,
    lookback: int = 3,
    minimum: int = 3,
) -> PriceMovementConfig:
    return PriceMovementConfig(
        config_id=1,
        config_code="PM_ZZ_D_V2",
        model_version="V2.0",
        timeframe="D",
        zigzag_config_code="ZZ_D_5_MVP",
        profile_lookback_swings=lookback,
        minimum_profile_swings=minimum,
        trend_bias_threshold=0.20,
        range_bias_threshold=0.15,
        efficiency_threshold=0.30,
        atr_period=3,
    )


def _ohlc() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("2026-01-01", 101.0, 99.0, 100.0),
            ("2026-01-02", 103.0, 100.0, 102.0),
            ("2026-01-03", 105.0, 102.0, 104.0),
            ("2026-01-04", 107.0, 104.0, 106.0),
            ("2026-01-05", 109.0, 106.0, 108.0),
            ("2026-01-06", 110.0, 105.0, 106.0),
            ("2026-01-07", 108.0, 102.0, 103.0),
            ("2026-01-08", 105.0, 99.0, 100.0),
            ("2026-01-09", 103.0, 97.0, 98.0),
            ("2026-01-10", 106.0, 99.0, 105.0),
        ],
        columns=["Date", "High", "Low", "Close"],
    )


def _zigzag_one_up() -> pd.DataFrame:
    start_price = 99.0
    end_price = 107.0
    return pd.DataFrame(
        [
            {
                "ConfigId": 1,
                "ConfigCode": "ZZ_D_5_MVP",
                "Ticker": "MWG",
                "SwingSeq": 1,
                "Direction": "UP",
                "StartPivotSeq": 1,
                "StartDate": "2026-01-01",
                "StartPrice": start_price,
                "EndPivotSeq": 2,
                "EndDate": "2026-01-04",
                "EndPrice": end_price,
                "ConfirmedAtDate": "2026-01-05",
                "SwingPct": end_price / start_price - 1.0,
            }
        ]
    )


def _swing(
    seq: int,
    direction: str,
    swing_pct: float,
    *,
    efficiency: float = 0.5,
    persistence: float = 0.6,
) -> PriceMovementSwing:
    start_day = seq * 3 - 2
    end_day = seq * 3
    return PriceMovementSwing(
        price_movement_config_id=1,
        zigzag_config_id=1,
        zigzag_config_code="ZZ_D_5_MVP",
        ticker="MWG",
        swing_seq=seq,
        direction=direction,
        start_pivot_seq=seq,
        start_date=date(2026, 1, start_day),
        start_price=100.0,
        end_pivot_seq=seq + 1,
        end_date=date(2026, 1, end_day),
        end_price=100.0 * (1.0 + swing_pct),
        confirmed_at_date=date(2026, 1, end_day + 1),
        swing_pct=swing_pct,
        trading_bars=2,
        calendar_days=2,
        velocity_pct_per_bar=swing_pct / 2.0,
        avg_atr20_pct=0.02,
        atr_normalized_move=abs(swing_pct) / 0.02,
        path_efficiency=efficiency,
        directional_persistence_rate=persistence,
    )


def test_enriched_swing_preserves_zigzag_identity_and_formulas() -> None:
    source = _zigzag_one_up()

    swings = build_price_movement_swings(
        source,
        _ohlc(),
        config=_config(),
    )

    assert len(swings) == 1
    result = swings[0]
    assert result.zigzag_config_id == 1
    assert result.zigzag_config_code == "ZZ_D_5_MVP"
    assert result.swing_seq == 1
    assert result.direction == "UP"
    assert result.start_pivot_seq == 1
    assert result.end_pivot_seq == 2
    assert result.start_date == date(2026, 1, 1)
    assert result.end_date == date(2026, 1, 4)
    assert result.confirmed_at_date == date(2026, 1, 5)
    assert result.swing_pct == pytest.approx(107.0 / 99.0 - 1.0)
    assert result.trading_bars == 3
    assert result.velocity_pct_per_bar == pytest.approx(result.swing_pct / 3.0)
    assert 0 <= result.path_efficiency <= 1
    assert 0 <= result.directional_persistence_rate <= 1


def test_ohlc_after_end_date_does_not_change_confirmed_swing_features() -> None:
    left = _ohlc()
    right = _ohlc().copy()
    right.loc[right["Date"] >= "2026-01-05", ["High", "Low", "Close"]] = [
        [300.0, 200.0, 250.0],
        [320.0, 210.0, 300.0],
        [330.0, 220.0, 250.0],
        [340.0, 230.0, 300.0],
        [350.0, 240.0, 250.0],
        [360.0, 250.0, 300.0],
    ]

    first = build_price_movement_swings(
        _zigzag_one_up(),
        left,
        config=_config(),
    )[0]
    second = build_price_movement_swings(
        _zigzag_one_up(),
        right,
        config=_config(),
    )[0]

    assert first == second


def test_direction_sign_mismatch_is_rejected() -> None:
    source = _zigzag_one_up()
    source.loc[0, "Direction"] = "DOWN"

    with pytest.raises(ValueError, match="DOWN swing is not negative"):
        build_price_movement_swings(
            source,
            _ohlc(),
            config=_config(),
        )


def test_upstream_swing_pct_mismatch_is_rejected() -> None:
    source = _zigzag_one_up()
    source.loc[0, "SwingPct"] = 0.99

    with pytest.raises(ValueError, match="ZigZag SwingPct mismatch"):
        build_price_movement_swings(
            source,
            _ohlc(),
            config=_config(),
        )


def test_classifier_has_deterministic_boundaries() -> None:
    config = _config(minimum=3)

    assert classify_movement(
        confirmed_swing_count=2,
        directional_bias=0.9,
        median_path_efficiency=0.9,
        config=config,
    ) == "INSUFFICIENT_HISTORY"

    assert classify_movement(
        confirmed_swing_count=3,
        directional_bias=0.25,
        median_path_efficiency=0.40,
        config=config,
    ) == "TRENDING_UP"

    assert classify_movement(
        confirmed_swing_count=3,
        directional_bias=-0.25,
        median_path_efficiency=0.40,
        config=config,
    ) == "TRENDING_DOWN"

    assert classify_movement(
        confirmed_swing_count=3,
        directional_bias=0.10,
        median_path_efficiency=0.20,
        config=config,
    ) == "RANGE_BOUND"

    assert classify_movement(
        confirmed_swing_count=3,
        directional_bias=0.18,
        median_path_efficiency=0.40,
        config=config,
    ) == "MIXED"


def test_profile_uses_only_configured_recent_lookback() -> None:
    swings = [
        _swing(1, "DOWN", -0.50, efficiency=0.9),
        _swing(2, "UP", 0.05, efficiency=0.5),
        _swing(3, "DOWN", -0.04, efficiency=0.5),
        _swing(4, "UP", 0.06, efficiency=0.5),
    ]
    config = _config(lookback=3, minimum=3)

    profile = build_price_movement_profile(swings, config=config)

    assert profile is not None
    assert profile.confirmed_swing_count == 3
    assert profile.last_swing_seq == 4
    expected_bias = (0.05 - 0.04 + 0.06) / (0.05 + 0.04 + 0.06)
    assert profile.directional_bias == pytest.approx(expected_bias)
    assert profile.movement_character == "TRENDING_UP"


def test_calculate_price_movement_returns_profile() -> None:
    swings, profile = calculate_price_movement(
        _zigzag_one_up(),
        _ohlc(),
        config=_config(lookback=3, minimum=3),
    )

    assert len(swings) == 1
    assert profile is not None
    assert profile.confirmed_swing_count == 1
    assert profile.movement_character == "INSUFFICIENT_HISTORY"
