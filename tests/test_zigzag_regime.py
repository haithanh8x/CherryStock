from __future__ import annotations

import pandas as pd

from cherrystock.domain.analytics.zigzag.engine import calculate_zigzag
from cherrystock.domain.analytics.zigzag.models import ZigZagConfig
from cherrystock.domain.analytics.zigzag.regime import (
    RegimeDeviationResolver,
    RegimePolicyConfig,
    build_regime_context,
)


def _config() -> ZigZagConfig:
    return ZigZagConfig(
        config_id=1,
        config_code="ZZ_D_5_MVP",
        model_version="MVP1",
        timeframe="D",
        deviation_pct=0.05,
        pivot_price_source="HIGH_LOW",
        confirmation_price_source="CLOSE",
        minimum_swing_bars=1,
    )


def _frame() -> pd.DataFrame:
    rows = [
        ("2026-01-01", 100, 98, 99),
        ("2026-01-02", 99, 95, 96),
        ("2026-01-03", 97, 92, 93),
        ("2026-01-04", 96, 90, 91),
        ("2026-01-05", 100, 94, 96),
        ("2026-01-06", 104, 98, 103),
        ("2026-01-07", 110, 102, 109),
        ("2026-01-08", 109, 101, 103),
        ("2026-01-09", 104, 100, 102),
        ("2026-01-10", 108, 102, 107),
    ]
    return pd.DataFrame(rows, columns=["Date", "High", "Low", "Close"])


def test_static_engine_is_backward_compatible_with_identity_resolver() -> None:
    frame = _frame()

    expected, _, _ = calculate_zigzag(frame, ticker="MWG", config=_config())
    actual, _, _ = calculate_zigzag(
        frame,
        ticker="MWG",
        config=_config(),
        deviation_resolver=lambda confirmed_date, index, base: base,
    )

    assert expected == actual


def test_regime_context_does_not_change_past_when_future_changes() -> None:
    dates = pd.date_range("2025-01-01", periods=120, freq="D")
    base = pd.DataFrame(
        {
            "Date": dates,
            "High": [102.0 + i * 0.1 for i in range(120)],
            "Low": [98.0 + i * 0.1 for i in range(120)],
            "Close": [100.0 + i * 0.1 for i in range(120)],
        }
    )
    changed = base.copy()
    changed.loc[100:, "High"] = changed.loc[100:, "High"] * 2
    changed.loc[100:, "Low"] = changed.loc[100:, "Low"] * 0.5

    left = build_regime_context(base)
    right = build_regime_context(changed)

    pd.testing.assert_series_equal(
        left.loc[:99, "ATRPercentile"],
        right.loc[:99, "ATRPercentile"],
        check_names=False,
    )
    pd.testing.assert_series_equal(
        left.loc[:99, "Regime"],
        right.loc[:99, "Regime"],
        check_names=False,
    )


def test_regime_resolver_applies_multipliers_and_clamps() -> None:
    context = pd.DataFrame(
        {
            "Regime": ["LOW_VOL", "NORMAL", "HIGH_VOL"],
        }
    )
    policy = RegimePolicyConfig(
        low_multiplier=0.8,
        normal_multiplier=1.0,
        high_multiplier=1.3,
        minimum_deviation_pct=0.02,
        maximum_deviation_pct=0.15,
    )
    resolver = RegimeDeviationResolver(context, policy=policy)

    assert resolver.deviation_at(0, 0.05) == 0.04
    assert resolver.deviation_at(1, 0.05) == 0.05
    assert resolver.deviation_at(2, 0.05) == 0.065
    assert resolver.deviation_at(0, 0.02) == 0.02
    assert resolver.deviation_at(2, 0.20) == 0.15


def test_resolver_is_called_only_after_confirmed_pivots() -> None:
    calls: list[tuple[int, float]] = []

    def resolver(confirmed_date, index, base):
        calls.append((index, base))
        return base

    pivots, _, _ = calculate_zigzag(
        _frame(),
        ticker="MWG",
        config=_config(),
        deviation_resolver=resolver,
    )

    assert len(calls) == len(pivots)
    assert all(base == 0.05 for _, base in calls)
