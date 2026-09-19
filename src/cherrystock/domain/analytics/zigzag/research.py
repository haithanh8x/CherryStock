from __future__ import annotations

from dataclasses import dataclass, replace
from statistics import median
from typing import Iterable

import numpy as np
import pandas as pd

from cherrystock.domain.analytics.zigzag.engine import calculate_zigzag
from cherrystock.domain.analytics.zigzag.models import ZigZagConfig, ZigZagPivot


DEFAULT_DEVIATION_GRID: tuple[float, ...] = (
    0.02,
    0.03,
    0.04,
    0.05,
    0.06,
    0.07,
    0.08,
    0.10,
    0.12,
)


@dataclass(frozen=True)
class SwingMetrics:
    source_bars: int
    pivot_count: int
    swing_count: int
    pivot_density_per_100_bars: float
    median_swing_bars: float
    median_abs_swing_pct: float
    short_swing_rate: float
    structural_valid: bool
    eligible: bool
    calibration_score: float


@dataclass(frozen=True)
class CalibrationSelection:
    ticker: str
    selected_deviation_pct: float
    selection_method: str
    calibration_version: str
    train_score: float
    validation_score: float
    test_score: float


def _config_with_deviation(config: ZigZagConfig, deviation_pct: float) -> ZigZagConfig:
    if not 0 < deviation_pct < 1:
        raise ValueError("deviation_pct must be between 0 and 1.")
    return replace(
        config,
        deviation_pct=float(deviation_pct),
        config_code=f"{config.config_code}_D{int(round(deviation_pct * 100)):02d}",
    )


def _structural_valid(pivots: list[ZigZagPivot]) -> bool:
    if not pivots:
        return False

    expected_seq = list(range(1, len(pivots) + 1))
    if [pivot.pivot_seq for pivot in pivots] != expected_seq:
        return False

    for index, pivot in enumerate(pivots):
        if pivot.pivot_date >= pivot.confirmed_at_date:
            return False
        if index == 0:
            continue
        previous = pivots[index - 1]
        if pivot.pivot_type == previous.pivot_type:
            return False
        if pivot.pivot_date <= previous.pivot_date:
            return False
    return True


def calculate_swing_metrics(
    frame: pd.DataFrame,
    pivots: list[ZigZagPivot],
    *,
    deviation_pct: float,
    minimum_swing_count: int = 5,
    minimum_median_swing_bars: float = 5.0,
    maximum_short_swing_rate: float = 0.10,
    minimum_amplitude_multiple: float = 1.5,
    short_swing_bars: int = 3,
) -> SwingMetrics:
    if frame.empty:
        return SwingMetrics(0, 0, 0, 0.0, 0.0, 0.0, 1.0, False, False, 0.0)

    dates = pd.to_datetime(frame["Date"]).dt.date.tolist()
    positions = {value: index for index, value in enumerate(dates)}

    swing_bars: list[int] = []
    swing_pct: list[float] = []

    for left, right in zip(pivots, pivots[1:]):
        left_index = positions.get(left.pivot_date)
        right_index = positions.get(right.pivot_date)
        if left_index is None or right_index is None or right_index <= left_index:
            continue
        swing_bars.append(right_index - left_index)
        swing_pct.append(abs(right.pivot_price / left.pivot_price - 1.0))

    source_bars = len(frame)
    pivot_count = len(pivots)
    swing_count = len(swing_bars)
    pivot_density = (pivot_count / source_bars * 100.0) if source_bars else 0.0
    median_bars = float(median(swing_bars)) if swing_bars else 0.0
    median_pct = float(median(swing_pct)) if swing_pct else 0.0
    short_rate = (
        sum(1 for bars in swing_bars if bars < short_swing_bars) / swing_count
        if swing_count
        else 1.0
    )

    structural_valid = _structural_valid(pivots)
    eligible = (
        structural_valid
        and swing_count >= minimum_swing_count
        and median_bars >= minimum_median_swing_bars
        and short_rate <= maximum_short_swing_rate
        and median_pct >= minimum_amplitude_multiple * deviation_pct
    )

    duration_quality = min(median_bars / 10.0, 1.0)
    amplitude_quality = min(
        median_pct / max(minimum_amplitude_multiple * deviation_pct, 1e-12),
        1.0,
    )
    noise_quality = 1.0 - min(short_rate / 0.25, 1.0)
    density_quality = 1.0 - min(max(pivot_density - 20.0, 0.0) / 20.0, 1.0)
    score = (
        0.30 * duration_quality
        + 0.30 * amplitude_quality
        + 0.30 * noise_quality
        + 0.10 * density_quality
    )
    if not structural_valid:
        score = 0.0

    return SwingMetrics(
        source_bars=source_bars,
        pivot_count=pivot_count,
        swing_count=swing_count,
        pivot_density_per_100_bars=float(pivot_density),
        median_swing_bars=median_bars,
        median_abs_swing_pct=median_pct,
        short_swing_rate=float(short_rate),
        structural_valid=structural_valid,
        eligible=eligible,
        calibration_score=float(score),
    )


def evaluate_deviation(
    frame: pd.DataFrame,
    *,
    ticker: str,
    base_config: ZigZagConfig,
    deviation_pct: float,
) -> SwingMetrics:
    config = _config_with_deviation(base_config, deviation_pct)
    pivots, _, _ = calculate_zigzag(frame, ticker=ticker, config=config)
    return calculate_swing_metrics(frame, pivots, deviation_pct=deviation_pct)


def chronological_split(
    frame: pd.DataFrame,
    *,
    train_ratio: float = 0.60,
    validation_ratio: float = 0.20,
) -> dict[str, pd.DataFrame]:
    if frame.empty:
        raise ValueError("cannot split an empty frame.")
    if not 0 < train_ratio < 1:
        raise ValueError("train_ratio must be between 0 and 1.")
    if not 0 < validation_ratio < 1:
        raise ValueError("validation_ratio must be between 0 and 1.")
    if train_ratio + validation_ratio >= 1:
        raise ValueError("TRAIN + VALIDATION ratios must leave a TEST holdout.")

    ordered = frame.sort_values("Date").reset_index(drop=True)
    if len(ordered) < 30:
        raise ValueError("at least 30 rows are required for calibration.")

    train_end = max(1, int(len(ordered) * train_ratio))
    validation_end = max(train_end + 1, int(len(ordered) * (train_ratio + validation_ratio)))
    validation_end = min(validation_end, len(ordered) - 1)

    return {
        "TRAIN": ordered.iloc[:train_end].reset_index(drop=True),
        "VALIDATION": ordered.iloc[train_end:validation_end].reset_index(drop=True),
        "TEST": ordered.iloc[validation_end:].reset_index(drop=True),
    }


def calibrate_static_deviation(
    frame: pd.DataFrame,
    *,
    ticker: str,
    base_config: ZigZagConfig,
    calibration_version: str = "V1.1",
    deviations: Iterable[float] = DEFAULT_DEVIATION_GRID,
) -> tuple[list[dict[str, object]], CalibrationSelection]:
    splits = chronological_split(frame)
    candidates = sorted({float(value) for value in deviations})
    if not candidates:
        raise ValueError("deviation grid must not be empty.")

    evaluations: list[dict[str, object]] = []
    metrics_by_key: dict[tuple[str, float], SwingMetrics] = {}

    for split_name, split_frame in splits.items():
        for deviation in candidates:
            metrics = evaluate_deviation(
                split_frame,
                ticker=ticker,
                base_config=base_config,
                deviation_pct=deviation,
            )
            metrics_by_key[(split_name, deviation)] = metrics
            evaluations.append(
                {
                    "CalibrationVersion": calibration_version,
                    "Ticker": ticker,
                    "SplitName": split_name,
                    "DeviationPct": deviation,
                    "SourceBars": metrics.source_bars,
                    "PivotCount": metrics.pivot_count,
                    "SwingCount": metrics.swing_count,
                    "PivotDensityPer100Bars": metrics.pivot_density_per_100_bars,
                    "MedianSwingBars": metrics.median_swing_bars,
                    "MedianAbsSwingPct": metrics.median_abs_swing_pct,
                    "ShortSwingRate": metrics.short_swing_rate,
                    "StructuralValid": metrics.structural_valid,
                    "IsEligible": metrics.eligible,
                    "CalibrationScore": metrics.calibration_score,
                }
            )

    eligible = [
        deviation
        for deviation in candidates
        if metrics_by_key[("TRAIN", deviation)].eligible
        and metrics_by_key[("VALIDATION", deviation)].eligible
    ]

    if eligible:
        selected = min(eligible)
        method = "SMALLEST_ELIGIBLE"
    else:
        structurally_valid = [
            deviation
            for deviation in candidates
            if metrics_by_key[("TRAIN", deviation)].structural_valid
            and metrics_by_key[("VALIDATION", deviation)].structural_valid
        ]
        if not structurally_valid:
            raise RuntimeError(
                f"No structurally valid ZigZag deviation candidate for {ticker}."
            )
        selected = max(
            structurally_valid,
            key=lambda deviation: (
                (
                    metrics_by_key[("TRAIN", deviation)].calibration_score
                    + metrics_by_key[("VALIDATION", deviation)].calibration_score
                )
                / 2.0,
                -deviation,
            ),
        )
        method = "FALLBACK_SCORE"

    selection = CalibrationSelection(
        ticker=ticker,
        selected_deviation_pct=selected,
        selection_method=method,
        calibration_version=calibration_version,
        train_score=metrics_by_key[("TRAIN", selected)].calibration_score,
        validation_score=metrics_by_key[("VALIDATION", selected)].calibration_score,
        test_score=metrics_by_key[("TEST", selected)].calibration_score,
    )
    return evaluations, selection


def compare_static_variants(
    frame: pd.DataFrame,
    *,
    ticker: str,
    base_config: ZigZagConfig,
    calibrated_deviation_pct: float,
    baseline_deviation_pct: float = 0.05,
) -> dict[str, object]:
    baseline = evaluate_deviation(
        frame,
        ticker=ticker,
        base_config=base_config,
        deviation_pct=baseline_deviation_pct,
    )
    calibrated = evaluate_deviation(
        frame,
        ticker=ticker,
        base_config=base_config,
        deviation_pct=calibrated_deviation_pct,
    )

    if np.isclose(calibrated_deviation_pct, baseline_deviation_pct):
        decision = "BASELINE_SUFFICIENT"
    else:
        short_rate_improved = (
            calibrated.short_swing_rate
            <= baseline.short_swing_rate * 0.80
        )
        duration_not_oversmoothed = (
            calibrated.median_swing_bars
            <= max(baseline.median_swing_bars * 2.0, 1.0)
        )
        minimum_swings = max(5.0, baseline.swing_count * 0.50)
        swing_coverage_ok = calibrated.swing_count >= minimum_swings
        if (
            baseline.structural_valid
            and calibrated.structural_valid
            and short_rate_improved
            and duration_not_oversmoothed
            and swing_coverage_ok
        ):
            decision = "PROMOTE_CALIBRATED"
        else:
            decision = "KEEP_5_BASELINE"

    return {
        "Ticker": ticker,
        "BaselineDeviationPct": baseline_deviation_pct,
        "CalibratedDeviationPct": calibrated_deviation_pct,
        "BaselineSwingCount": baseline.swing_count,
        "CalibratedSwingCount": calibrated.swing_count,
        "BaselinePivotDensity": baseline.pivot_density_per_100_bars,
        "CalibratedPivotDensity": calibrated.pivot_density_per_100_bars,
        "BaselineMedianSwingBars": baseline.median_swing_bars,
        "CalibratedMedianSwingBars": calibrated.median_swing_bars,
        "BaselineMedianAbsSwingPct": baseline.median_abs_swing_pct,
        "CalibratedMedianAbsSwingPct": calibrated.median_abs_swing_pct,
        "BaselineShortSwingRate": baseline.short_swing_rate,
        "CalibratedShortSwingRate": calibrated.short_swing_rate,
        "BaselineStructuralValid": baseline.structural_valid,
        "CalibratedStructuralValid": calibrated.structural_valid,
        "BaselineScore": baseline.calibration_score,
        "CalibratedScore": calibrated.calibration_score,
        "Decision": decision,
    }
