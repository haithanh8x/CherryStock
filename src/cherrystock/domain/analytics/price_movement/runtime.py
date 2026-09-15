from __future__ import annotations

from datetime import date

import pandas as pd

from .engine import (
    _event_from_features,
    _finite,
    calculate_leg_features,
    classify_movement,
    reversal_threshold,
    score_against_history,
)
from .models import MovementConfig, SeedState, SwingEvent


def _bar_slice(frame: pd.DataFrame, start_index: int, end_index: int) -> pd.DataFrame:
    """Return one inclusive leg slice without rescanning the whole ticker history."""
    return frame.iloc[start_index : end_index + 1]


def calculate_ticker_movement_fast(
    frame: pd.DataFrame,
    *,
    ticker: str,
    config: MovementConfig,
    prior_swings: list[SwingEvent] | None = None,
    seed_state: SeedState | None = None,
) -> tuple[list[SwingEvent], list[dict[str, object]]]:
    """Point-in-time swing state machine optimized for historical/runtime refresh.

    Semantics match ``engine.calculate_ticker_movement``. The difference is
    implementation only: leg paths are sliced by bar position so each daily
    feature calculation does not filter the entire ticker history.
    """
    if frame.empty:
        return [], []

    data = frame.sort_values("Date").reset_index(drop=True).copy()
    data["Date"] = pd.to_datetime(data["Date"])
    bar_dates = [timestamp.date() for timestamp in data["Date"]]
    date_to_index = {bar_date: index for index, bar_date in enumerate(bar_dates)}

    history = list(prior_swings or [])
    emitted: list[SwingEvent] = []
    daily: list[dict[str, object]] = []
    next_seq = max((item.swing_seq for item in history), default=0) + 1

    direction: str | None = None
    start_date: date | None = None
    start_index: int | None = None
    start_price: float | None = None
    candidate_date: date | None = None
    candidate_index: int | None = None
    candidate_price: float | None = None
    seed_date: date | None = None

    seeking_high_date: date | None = None
    seeking_high_index: int | None = None
    seeking_high: float | None = None
    seeking_low_date: date | None = None
    seeking_low_index: int | None = None
    seeking_low: float | None = None

    if seed_state is not None:
        direction = seed_state.direction
        start_date = seed_state.current_swing_start_date
        candidate_date = seed_state.candidate_end_date
        start_index = date_to_index.get(start_date)
        candidate_index = date_to_index.get(candidate_date)
        if start_index is None or candidate_index is None:
            raise RuntimeError(
                f"Cannot resume {ticker}: persisted provisional dates are outside loaded source "
                f"(start={start_date}, candidate={candidate_date}). Run a targeted full rebuild."
            )
        start_price = float(seed_state.start_price)
        candidate_price = float(seed_state.candidate_end_price)
        seed_date = seed_state.date

    for current_index, row in enumerate(data.itertuples(index=False)):
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
                seeking_high_index = current_index
            if seeking_low is None or low < seeking_low:
                seeking_low = low
                seeking_low_date = current_date
                seeking_low_index = current_index

            up_threshold, _ = reversal_threshold(atr, seeking_low or close, config)
            down_threshold, _ = reversal_threshold(atr, seeking_high or close, config)
            up_move = close / max(float(seeking_low or close), 1e-12) - 1.0
            down_move = 1.0 - close / max(float(seeking_high or close), 1e-12)

            if up_move >= up_threshold and up_move >= down_move:
                direction = "UP"
                start_date = seeking_low_date or current_date
                start_index = seeking_low_index if seeking_low_index is not None else current_index
                start_price = float(seeking_low or close)
                candidate_date = current_date
                candidate_index = current_index
                candidate_price = high
            elif down_move >= down_threshold:
                direction = "DOWN"
                start_date = seeking_high_date or current_date
                start_index = seeking_high_index if seeking_high_index is not None else current_index
                start_price = float(seeking_high or close)
                candidate_date = current_date
                candidate_index = current_index
                candidate_price = low

        if direction == "UP":
            if candidate_price is None or high >= candidate_price:
                candidate_price = high
                candidate_date = current_date
                candidate_index = current_index

            assert start_index is not None
            assert candidate_index is not None
            assert start_date is not None
            assert candidate_date is not None
            assert start_price is not None
            assert candidate_price is not None

            threshold_pct, threshold_source = reversal_threshold(atr, candidate_price, config)
            path_to_candidate = _bar_slice(data, start_index, candidate_index)
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
                start_index = candidate_index
                start_price = candidate_price
                candidate_date = current_date
                candidate_index = current_index
                candidate_price = low

        elif direction == "DOWN":
            if candidate_price is None or low <= candidate_price:
                candidate_price = low
                candidate_date = current_date
                candidate_index = current_index

            assert start_index is not None
            assert candidate_index is not None
            assert start_date is not None
            assert candidate_date is not None
            assert start_price is not None
            assert candidate_price is not None

            threshold_pct, threshold_source = reversal_threshold(atr, candidate_price, config)
            path_to_candidate = _bar_slice(data, start_index, candidate_index)
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
                start_index = candidate_index
                start_price = candidate_price
                candidate_date = current_date
                candidate_index = current_index
                candidate_price = high

        if (
            direction not in {"UP", "DOWN"}
            or start_date is None
            or start_index is None
            or candidate_date is None
            or candidate_index is None
            or start_price is None
            or candidate_price is None
        ):
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

        path_to_now = _bar_slice(data, start_index, current_index)
        features = calculate_leg_features(
            path_to_now,
            direction=direction,
            start_price=start_price,
            endpoint_price=candidate_price,
        )
        score = score_against_history(
            direction=direction,
            as_of_date=current_date,
            features=features,
            prior_swings=history,
            config=config,
        )
        threshold_pct, threshold_source = reversal_threshold(atr, candidate_price, config)
        movement_character = classify_movement(
            direction,
            magnitude_score=_finite(score["MagnitudeScore"]),
            velocity_score=_finite(score["VelocityScore"]),
            persistence_score_value=_finite(score["PersistenceScore"]),
            historical_count=int(score["HistoricalSameDirSwingCount"]),
            config=config,
        )
        quality = "OK"
        if threshold_source != "ATR_PLUS_FLOOR" or score["ScoreBasis"] in {
            "RAW_ONLY",
            "INSUFFICIENT_HISTORY",
            "NONE",
        }:
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
