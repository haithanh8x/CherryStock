from __future__ import annotations

from datetime import date

import pandas as pd

from cherrystock.domain.analytics.zigzag.models import ZigZagConfig, ZigZagPivot
from cherrystock.domain.analytics.zigzag.research import (
    SwingMetrics,
    calculate_swing_metrics,
    chronological_split,
    compare_static_variants,
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


def test_chronological_split_is_ordered_and_disjoint() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.date_range("2026-01-01", periods=100, freq="D"),
            "High": range(100, 200),
            "Low": range(99, 199),
            "Close": range(99, 199),
        }
    )

    splits = chronological_split(frame)

    assert len(splits["TRAIN"]) == 60
    assert len(splits["VALIDATION"]) == 20
    assert len(splits["TEST"]) == 20
    assert splits["TRAIN"]["Date"].max() < splits["VALIDATION"]["Date"].min()
    assert splits["VALIDATION"]["Date"].max() < splits["TEST"]["Date"].min()


def test_swing_metrics_use_bar_distance_and_absolute_magnitude() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.date_range("2026-01-01", periods=16, freq="D"),
            "High": [110.0] * 16,
            "Low": [90.0] * 16,
            "Close": [100.0] * 16,
        }
    )
    pivots = [
        ZigZagPivot(1, "MWG", 1, "LOW", date(2026, 1, 1), 90.0, date(2026, 1, 2), 96.0, 0.05),
        ZigZagPivot(1, "MWG", 2, "HIGH", date(2026, 1, 6), 105.0, date(2026, 1, 7), 99.0, 0.05),
        ZigZagPivot(1, "MWG", 3, "LOW", date(2026, 1, 11), 92.0, date(2026, 1, 12), 98.0, 0.05),
        ZigZagPivot(1, "MWG", 4, "HIGH", date(2026, 1, 16), 108.0, date(2026, 1, 17), 101.0, 0.05),
    ]

    metrics = calculate_swing_metrics(frame, pivots, deviation_pct=0.05)

    assert metrics.structural_valid is True
    assert metrics.swing_count == 3
    assert metrics.median_swing_bars == 5
    assert metrics.short_swing_rate == 0


def test_multi_ticker_pilot_promotes_only_material_improvement(monkeypatch) -> None:
    baseline = SwingMetrics(
        source_bars=200,
        pivot_count=40,
        swing_count=39,
        pivot_density_per_100_bars=20,
        median_swing_bars=6,
        median_abs_swing_pct=0.08,
        short_swing_rate=0.20,
        structural_valid=True,
        eligible=False,
        calibration_score=0.60,
    )
    calibrated = SwingMetrics(
        source_bars=200,
        pivot_count=30,
        swing_count=29,
        pivot_density_per_100_bars=15,
        median_swing_bars=8,
        median_abs_swing_pct=0.10,
        short_swing_rate=0.10,
        structural_valid=True,
        eligible=True,
        calibration_score=0.80,
    )

    def fake_evaluate(frame, *, ticker, base_config, deviation_pct):
        return baseline if deviation_pct == 0.05 else calibrated

    monkeypatch.setattr(
        "cherrystock.domain.analytics.zigzag.research.evaluate_deviation",
        fake_evaluate,
    )

    row = compare_static_variants(
        pd.DataFrame({"Date": [pd.Timestamp("2026-01-01")]}),
        ticker="DIG",
        base_config=_config(),
        calibrated_deviation_pct=0.07,
    )

    assert row["Decision"] == "PROMOTE_CALIBRATED"


def test_pilot_keeps_five_percent_when_calibration_equals_baseline(monkeypatch) -> None:
    metric = SwingMetrics(
        source_bars=200,
        pivot_count=20,
        swing_count=19,
        pivot_density_per_100_bars=10,
        median_swing_bars=8,
        median_abs_swing_pct=0.10,
        short_swing_rate=0.05,
        structural_valid=True,
        eligible=True,
        calibration_score=0.90,
    )
    monkeypatch.setattr(
        "cherrystock.domain.analytics.zigzag.research.evaluate_deviation",
        lambda *args, **kwargs: metric,
    )

    row = compare_static_variants(
        pd.DataFrame({"Date": [pd.Timestamp("2026-01-01")]}),
        ticker="MWG",
        base_config=_config(),
        calibrated_deviation_pct=0.05,
    )

    assert row["Decision"] == "BASELINE_SUFFICIENT"
