from __future__ import annotations

from datetime import date
from math import exp, log
from typing import Iterable

import numpy as np
import pandas as pd

from .models import MovementConfig, SeedState, SwingEvent


def _finite(value) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def reversal_threshold(atr: float | None, reference_price: float, config: MovementConfig) -> tuple[float, str]:
    reference = max(abs(float(reference_price)), 1e-12)
    atr_value = _finite(atr)
    if atr_value is None or atr_value <= 0:
        return float(config.min_reversal_pct), "PCT_FALLBACK"
    return max(float(config.min_reversal_pct), float(config.atr_multiplier) * atr_value / reference), "ATR_PLUS_FLOOR"


def _path_slice(frame: pd.DataFrame, start_date: date, end_date: date) -> pd.DataFrame:
    mask = (frame["Date"].dt.date >= start_date) & (frame["Date"].dt.date <= end_date)
    return frame.loc[mask].sort_values("Date").copy()


def calculate_leg_features(
    path: pd.DataFrame,
    *,
    direction: str,
    start_price: float,
    endpoint_price: float,
) -> dict[str, float | int | None]:
    if path.empty:
        raise ValueError("Price movement feature path cannot be empty.")

    start_price = float(start_price)
    endpoint_price = float(endpoint_price)
    duration_bars = max(int(len(path) - 1), 0)
    swing_pct = endpoint_price / start_price - 1.0
    velocity_log_per_bar = log(endpoint_price / start_price) / max(duration_bars, 1)
    velocity_pct_per_bar = (exp(velocity_log_per_bar) - 1.0) * 100.0

    atr_source = path["ATR"] if "ATR" in path.columns else pd.Series(index=path.index, dtype=float)
    atr = pd.to_numeric(atr_source, errors="coerce")
    valid_atr = atr[(atr > 0) & atr.notna()]
    mean_atr = float(valid_atr.mean()) if not valid_atr.empty else None
    atr_norm_magnitude = (
        abs(endpoint_price - start_price) / mean_atr
        if mean_atr is not None and mean_atr > 0
        else None
    )

    close = pd.to_numeric(path["Close"], errors="coerce").dropna().astype(float)
    if len(close) >= 2:
        diffs = close.diff().dropna()
        travelled = float(diffs.abs().sum())
        efficiency_ratio = abs(float(close.iloc[-1] - close.iloc[0])) / travelled if travelled > 0 else 0.0

        x = np.arange(len(close), dtype=float)
        y = np.log(close.to_numpy(dtype=float))
        slope, intercept = np.polyfit(x, y, 1)
        predicted = slope * x + intercept
        ss_res = float(np.sum((y - predicted) ** 2))
        ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
        regression_r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-15 else 1.0
        regression_r2 = float(np.clip(regression_r2, 0.0, 1.0))

        if direction == "UP":
            running = close.cummax()
            adverse = (close / running) - 1.0
            max_adverse = abs(float(adverse.min()))
            directional_ratio = float((diffs > 0).mean())
        else:
            running = close.cummin()
            adverse = (close / running) - 1.0
            max_adverse = max(float(adverse.max()), 0.0)
            directional_ratio = float((diffs < 0).mean())
        regression_slope = float(slope)
    else:
        efficiency_ratio = 0.0
        regression_slope = None
        regression_r2 = None
        max_adverse = 0.0
        directional_ratio = 0.0

    adverse_ratio = min(1.0, max_adverse / max(abs(swing_pct), 1e-12))
    smoothness = 1.0 - adverse_ratio

    return {
        "SwingPct": float(swing_pct),
        "DurationBars": duration_bars,
        "VelocityLogPerBar": float(velocity_log_per_bar),
        "VelocityPctPerBar": float(velocity_pct_per_bar),
        "MeanATR": mean_atr,
        "ATRNormMagnitude": float(atr_norm_magnitude) if atr_norm_magnitude is not None else None,
        "EfficiencyRatio": float(np.clip(efficiency_ratio, 0.0, 1.0)),
        "RegressionSlopePerBar": regression_slope,
        "RegressionR2": regression_r2,
        "MaxAdverseExcursionPct": float(max_adverse),
        "DirectionalDayRatio": float(np.clip(directional_ratio, 0.0, 1.0)),
        "SmoothnessComponent": float(np.clip(smoothness, 0.0, 1.0)),
    }


def persistence_score(features: dict[str, float | int | None], config: MovementConfig) -> float:
    er = float(features.get("EfficiencyRatio") or 0.0)
    r2 = float(features.get("RegressionR2") or 0.0)
    smoothness = float(features.get("SmoothnessComponent") or 0.0)
    directional = float(features.get("DirectionalDayRatio") or 0.0)
    score = 100.0 * (
        config.persistence_er_weight * er
        + config.persistence_r2_weight * r2
        + config.persistence_smoothness_weight * smoothness
        + config.persistence_directional_day_weight * directional
    )
    return float(np.clip(score, 0.0, 100.0))


def percentile_rank(values: Iterable[float | None], value: float | None) -> float | None:
    candidate = _finite(value)
    if candidate is None:
        return None
    clean = np.asarray([float(v) for v in values if _finite(v) is not None], dtype=float)
    if clean.size == 0:
        return None
    less = float(np.sum(clean < candidate))
    equal = float(np.sum(np.isclose(clean, candidate, rtol=1e-10, atol=1e-12)))
    return (less + 0.5 * equal) / float(clean.size)


def score_against_history(
    *,
    direction: str,
    as_of_date: date,
    features: dict[str, float | int | None],
    prior_swings: list[SwingEvent],
    config: MovementConfig,
) -> dict[str, float | int | str | None]:
    eligible = [
        item
        for item in prior_swings
        if item.direction == direction and item.confirmed_at_date < as_of_date
    ][-config.profile_max_swings :]
    count = len(eligible)
    direct_persistence = persistence_score(features, config)
    if count < config.min_historical_same_dir:
        return {
            "HistoricalSameDirSwingCount": count,
            "MagnitudePercentile": None,
            "ATRNormMagnitudePercentile": None,
            "VelocityPercentile": None,
            "PersistencePercentile": percentile_rank(
                [item.persistence_score for item in eligible], direct_persistence
            ),
            "MagnitudeScore": None,
            "VelocityScore": None,
            "PersistenceScore": direct_persistence,
            "ScoreBasis": "INSUFFICIENT_HISTORY",
        }

    raw_pct = percentile_rank([abs(item.swing_pct) for item in eligible], abs(float(features["SwingPct"])))
    atr_pct = percentile_rank(
        [item.atr_norm_magnitude for item in eligible],
        features.get("ATRNormMagnitude"),
    )
    velocity_pct = percentile_rank(
        [abs(item.velocity_log_per_bar) for item in eligible],
        abs(float(features["VelocityLogPerBar"])),
    )
    persistence_pct = percentile_rank(
        [item.persistence_score for item in eligible],
        direct_persistence,
    )

    if raw_pct is None:
        magnitude_score = None
        score_basis = "NONE"
    elif atr_pct is None:
        magnitude_score = 100.0 * raw_pct
        score_basis = "RAW_ONLY"
    else:
        magnitude_score = 100.0 * (
            config.magnitude_raw_weight * raw_pct
            + config.magnitude_atr_weight * atr_pct
        )
        score_basis = "RAW_PLUS_ATR"

    return {
        "HistoricalSameDirSwingCount": count,
        "MagnitudePercentile": None if raw_pct is None else 100.0 * raw_pct,
        "ATRNormMagnitudePercentile": None if atr_pct is None else 100.0 * atr_pct,
        "VelocityPercentile": None if velocity_pct is None else 100.0 * velocity_pct,
        "PersistencePercentile": None if persistence_pct is None else 100.0 * persistence_pct,
        "MagnitudeScore": magnitude_score,
        "VelocityScore": None if velocity_pct is None else 100.0 * velocity_pct,
        "PersistenceScore": direct_persistence,
        "ScoreBasis": score_basis,
    }


def classify_movement(
    direction: str | None,
    *,
    magnitude_score: float | None,
    velocity_score: float | None,
    persistence_score_value: float | None,
    historical_count: int,
    config: MovementConfig,
) -> str:
    if direction not in {"UP", "DOWN"}:
        return "TRANSITION"
    if historical_count < config.min_historical_same_dir or magnitude_score is None:
        return "INSUFFICIENT_HISTORY"

    mag = float(magnitude_score)
    vel = float(velocity_score or 0.0)
    per = float(persistence_score_value or 0.0)
    suffix = "UP" if direction == "UP" else "DOWN"

    if mag >= config.high_magnitude_threshold and per >= config.high_persistence_threshold:
        return f"STRONG_PERSISTENT_{suffix}"
    if (
        mag >= config.high_magnitude_threshold
        and vel >= config.high_velocity_threshold
        and per < config.low_persistence_threshold
    ):
        return f"EXPLOSIVE_VOLATILE_{suffix}"
    if per >= config.high_persistence_threshold and mag >= config.mid_magnitude_threshold:
        return f"STEADY_{suffix}"
    if per >= config.high_persistence_threshold and mag < config.mid_magnitude_threshold:
        return f"SLOW_GRIND_{suffix}"
    return f"NORMAL_{suffix}"


def _event_from_features(
    *,
    config: MovementConfig,
    ticker: str,
    direction: str,
    swing_seq: int,
    pivot_start_date: date,
    pivot_end_date: date,
    confirmed_at_date: date,
    start_price: float,
    end_price: float,
    threshold_pct: float,
    threshold_source: str,
    features: dict[str, float | int | None],
) -> SwingEvent:
    quality = "OK" if features.get("ATRNormMagnitude") is not None and threshold_source == "ATR_PLUS_FLOOR" else "PARTIAL"
    return SwingEvent(
        config_id=config.config_id,
        ticker=ticker,
        direction=direction,
        swing_seq=swing_seq,
        pivot_start_date=pivot_start_date,
        pivot_end_date=pivot_end_date,
        confirmed_at_date=confirmed_at_date,
        start_price=float(start_price),
        end_price=float(end_price),
        swing_pct=float(features["SwingPct"]),
        duration_bars=int(features["DurationBars"]),
        duration_calendar_days=(pivot_end_date - pivot_start_date).days,
        velocity_log_per_bar=float(features["VelocityLogPerBar"]),
        velocity_pct_per_bar=float(features["VelocityPctPerBar"]),
        mean_atr=_finite(features.get("MeanATR")),
        atr_norm_magnitude=_finite(features.get("ATRNormMagnitude")),
        efficiency_ratio=float(features["EfficiencyRatio"]),
        regression_slope_per_bar=_finite(features.get("RegressionSlopePerBar")),
        regression_r2=_finite(features.get("RegressionR2")),
        max_adverse_excursion_pct=float(features["MaxAdverseExcursionPct"]),
        directional_day_ratio=float(features["DirectionalDayRatio"]),
        persistence_score=persistence_score(features, config),
        threshold_pct=float(threshold_pct),
        threshold_source=threshold_source,
        quality_status=quality,
    )


def calculate_ticker_movement(
    frame: pd.DataFrame,
    *,
    ticker: str,
    config: MovementConfig,
    prior_swings: list[SwingEvent] | None = None,
    seed_state: SeedState | None = None,
) -> tuple[list[SwingEvent], list[dict[str, object]]]:
    if frame.empty:
        return [], []

    data = frame.sort_values("Date").copy()
    data["Date"] = pd.to_datetime(data["Date"])
    history = list(prior_swings or [])
    emitted: list[SwingEvent] = []
    daily: list[dict[str, object]] = []
    next_seq = max((item.swing_seq for item in history), default=0) + 1

    direction: str | None = None
    start_date: date | None = None
    start_price: float | None = None
    candidate_date: date | None = None
    candidate_price: float | None = None
    seed_date: date | None = None

    seeking_high_date: date | None = None
    seeking_high: float | None = None
    seeking_low_date: date | None = None
    seeking_low: float | None = None

    if seed_state is not None:
        direction = seed_state.direction
        start_date = seed_state.current_swing_start_date
        start_price = float(seed_state.start_price)
        candidate_date = seed_state.candidate_end_date
        candidate_price = float(seed_state.candidate_end_price)
        seed_date = seed_state.date

    for row in data.itertuples(index=False):
        current_date = pd.Timestamp(row.Date).date()
        if seed_date is not None and current_date <= seed_date:
            continue

        high = float(row.High)
        low = float(row.Low)
        close = float(row.Close)
        atr = _finite(getattr(row, "ATR", None))

        if direction is None:
            if seeking_high is None or high > seeking_high:
                seeking_high = high
                seeking_high_date = current_date
            if seeking_low is None or low < seeking_low:
                seeking_low = low
                seeking_low_date = current_date

            up_threshold, _ = reversal_threshold(atr, seeking_low or close, config)
            down_threshold, _ = reversal_threshold(atr, seeking_high or close, config)
            up_move = close / max(float(seeking_low or close), 1e-12) - 1.0
            down_move = 1.0 - close / max(float(seeking_high or close), 1e-12)

            if up_move >= up_threshold and up_move >= down_move:
                direction = "UP"
                start_date = seeking_low_date or current_date
                start_price = float(seeking_low or close)
                candidate_date = current_date
                candidate_price = high
            elif down_move >= down_threshold:
                direction = "DOWN"
                start_date = seeking_high_date or current_date
                start_price = float(seeking_high or close)
                candidate_date = current_date
                candidate_price = low

        if direction == "UP":
            if candidate_price is None or high >= candidate_price:
                candidate_price = high
                candidate_date = current_date

            threshold_pct, threshold_source = reversal_threshold(atr, candidate_price, config)
            path_to_candidate = _path_slice(data, start_date, candidate_date)
            swing_bars = max(len(path_to_candidate) - 1, 0)
            if (
                swing_bars >= config.minimum_swing_bars
                and close <= candidate_price * (1.0 - threshold_pct)
            ):
                features = calculate_leg_features(
                    path_to_candidate,
                    direction="UP",
                    start_price=start_price,
                    endpoint_price=candidate_price,
                )
                event = _event_from_features(
                    config=config,
                    ticker=ticker,
                    direction="UP",
                    swing_seq=next_seq,
                    pivot_start_date=start_date,
                    pivot_end_date=candidate_date,
                    confirmed_at_date=current_date,
                    start_price=start_price,
                    end_price=candidate_price,
                    threshold_pct=threshold_pct,
                    threshold_source=threshold_source,
                    features=features,
                )
                emitted.append(event)
                history.append(event)
                next_seq += 1

                direction = "DOWN"
                start_date = candidate_date
                start_price = candidate_price
                candidate_date = current_date
                candidate_price = low

        elif direction == "DOWN":
            if candidate_price is None or low <= candidate_price:
                candidate_price = low
                candidate_date = current_date

            threshold_pct, threshold_source = reversal_threshold(atr, candidate_price, config)
            path_to_candidate = _path_slice(data, start_date, candidate_date)
            swing_bars = max(len(path_to_candidate) - 1, 0)
            if (
                swing_bars >= config.minimum_swing_bars
                and close >= candidate_price * (1.0 + threshold_pct)
            ):
                features = calculate_leg_features(
                    path_to_candidate,
                    direction="DOWN",
                    start_price=start_price,
                    endpoint_price=candidate_price,
                )
                event = _event_from_features(
                    config=config,
                    ticker=ticker,
                    direction="DOWN",
                    swing_seq=next_seq,
                    pivot_start_date=start_date,
                    pivot_end_date=candidate_date,
                    confirmed_at_date=current_date,
                    start_price=start_price,
                    end_price=candidate_price,
                    threshold_pct=threshold_pct,
                    threshold_source=threshold_source,
                    features=features,
                )
                emitted.append(event)
                history.append(event)
                next_seq += 1

                direction = "UP"
                start_date = candidate_date
                start_price = candidate_price
                candidate_date = current_date
                candidate_price = high

        if direction not in {"UP", "DOWN"} or start_date is None or candidate_date is None:
            daily.append(
                {
                    "ConfigId": config.config_id,
                    "Ticker": ticker,
                    "Date": current_date,
                    "Direction": None,
                    "SwingStatus": "TRANSITION",
                    "CurrentSwingStartDate": None,
                    "CandidateEndDate": None,
                    "StartPrice": None,
                    "CandidateEndPrice": None,
                    "CurrentSwingPct": None,
                    "DurationBars": None,
                    "VelocityLogPerBar": None,
                    "VelocityPctPerBar": None,
                    "ATRNormMagnitude": None,
                    "EfficiencyRatio": None,
                    "RegressionSlopePerBar": None,
                    "RegressionR2": None,
                    "MaxAdverseExcursionPct": None,
                    "DirectionalDayRatio": None,
                    "HistoricalSameDirSwingCount": 0,
                    "MagnitudePercentile": None,
                    "ATRNormMagnitudePercentile": None,
                    "VelocityPercentile": None,
                    "PersistencePercentile": None,
                    "MagnitudeScore": None,
                    "VelocityScore": None,
                    "PersistenceScore": None,
                    "MovementCharacter": "TRANSITION",
                    "ScoreBasis": "NONE",
                    "ThresholdPct": None,
                    "ThresholdSource": None,
                    "QualityStatus": "PARTIAL",
                }
            )
            continue

        path_to_now = _path_slice(data, start_date, current_date)
        features = calculate_leg_features(
            path_to_now,
            direction=direction,
            start_price=float(start_price),
            endpoint_price=float(candidate_price),
        )
        score = score_against_history(
            direction=direction,
            as_of_date=current_date,
            features=features,
            prior_swings=history,
            config=config,
        )
        threshold_pct, threshold_source = reversal_threshold(atr, float(candidate_price), config)
        movement_character = classify_movement(
            direction,
            magnitude_score=_finite(score["MagnitudeScore"]),
            velocity_score=_finite(score["VelocityScore"]),
            persistence_score_value=_finite(score["PersistenceScore"]),
            historical_count=int(score["HistoricalSameDirSwingCount"]),
            config=config,
        )
        quality = "OK"
        if threshold_source != "ATR_PLUS_FLOOR" or score["ScoreBasis"] in {"RAW_ONLY", "INSUFFICIENT_HISTORY", "NONE"}:
            quality = "PARTIAL"

        daily.append(
            {
                "ConfigId": config.config_id,
                "Ticker": ticker,
                "Date": current_date,
                "Direction": direction,
                "SwingStatus": "PROVISIONAL",
                "CurrentSwingStartDate": start_date,
                "CandidateEndDate": candidate_date,
                "StartPrice": float(start_price),
                "CandidateEndPrice": float(candidate_price),
                "CurrentSwingPct": float(features["SwingPct"]),
                "DurationBars": int(features["DurationBars"]),
                "VelocityLogPerBar": float(features["VelocityLogPerBar"]),
                "VelocityPctPerBar": float(features["VelocityPctPerBar"]),
                "ATRNormMagnitude": _finite(features.get("ATRNormMagnitude")),
                "EfficiencyRatio": float(features["EfficiencyRatio"]),
                "RegressionSlopePerBar": _finite(features.get("RegressionSlopePerBar")),
                "RegressionR2": _finite(features.get("RegressionR2")),
                "MaxAdverseExcursionPct": float(features["MaxAdverseExcursionPct"]),
                "DirectionalDayRatio": float(features["DirectionalDayRatio"]),
                **score,
                "MovementCharacter": movement_character,
                "ThresholdPct": float(threshold_pct),
                "ThresholdSource": threshold_source,
                "QualityStatus": quality,
            }
        )

    return emitted, daily
