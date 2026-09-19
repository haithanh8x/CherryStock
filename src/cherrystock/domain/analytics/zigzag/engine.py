from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

import numpy as np
import pandas as pd

from cherrystock.domain.analytics.zigzag.models import (
    ZigZagConfig,
    ZigZagCurrentLeg,
    ZigZagPivot,
)


@dataclass(frozen=True)
class ZigZagDiagnostics:
    source_rows: int
    usable_rows: int
    invalid_rows_dropped: int


@dataclass
class _Extreme:
    price: float
    date: date
    index: int


def _prepare_source(frame: pd.DataFrame) -> tuple[pd.DataFrame, ZigZagDiagnostics]:
    required = {"Date", "High", "Low", "Close"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"ZigZag source is missing columns: {sorted(missing)}")

    source_rows = len(frame)
    data = frame.loc[:, ["Date", "High", "Low", "Close"]].copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    for column in ("High", "Low", "Close"):
        data[column] = pd.to_numeric(data[column], errors="coerce")

    numeric = data[["High", "Low", "Close"]]
    finite = np.isfinite(numeric).all(axis=1)
    valid = (
        data["Date"].notna()
        & finite
        & (data["High"] > 0)
        & (data["Low"] > 0)
        & (data["Close"] > 0)
        & (data["High"] >= data["Low"])
        & (data["Close"] <= data["High"])
        & (data["Close"] >= data["Low"])
    )
    data = data.loc[valid].sort_values("Date").reset_index(drop=True)

    if data["Date"].duplicated().any():
        duplicates = data.loc[data["Date"].duplicated(keep=False), "Date"].dt.date.tolist()
        raise ValueError(f"ZigZag source contains duplicate dates: {duplicates[:5]}")

    return data, ZigZagDiagnostics(
        source_rows=source_rows,
        usable_rows=len(data),
        invalid_rows_dropped=source_rows - len(data),
    )


def _pivot(
    *,
    config: ZigZagConfig,
    ticker: str,
    seq: int,
    pivot_type: str,
    extreme: _Extreme,
    confirmed_at_date: date,
    confirmation_price: float,
) -> ZigZagPivot:
    return ZigZagPivot(
        config_id=config.config_id,
        ticker=ticker,
        pivot_seq=seq,
        pivot_type=pivot_type,
        pivot_date=extreme.date,
        pivot_price=float(extreme.price),
        confirmed_at_date=confirmed_at_date,
        confirmation_price=float(confirmation_price),
        deviation_pct=config.deviation_pct,
    )


def _choose_bootstrap(
    *,
    up_excursion: float,
    down_excursion: float,
    low_extreme: _Extreme,
    high_extreme: _Extreme,
    deviation_pct: float,
) -> str:
    up_excess = up_excursion - deviation_pct
    down_excess = down_excursion - deviation_pct
    if up_excess > down_excess:
        return "LOW"
    if down_excess > up_excess:
        return "HIGH"
    if low_extreme.date < high_extreme.date:
        return "LOW"
    if high_extreme.date < low_extreme.date:
        return "HIGH"
    return "LOW"


def calculate_zigzag(
    frame: pd.DataFrame,
    *,
    ticker: str,
    config: ZigZagConfig,
) -> tuple[list[ZigZagPivot], ZigZagCurrentLeg | None, ZigZagDiagnostics]:
    """Calculate a confirmed percentage-reversal ZigZag in one forward scan.

    Candidate extrema use High/Low. Reversal confirmation uses Close.
    Confirmed pivots expose the extreme date separately from the confirmation date.
    """

    if not 0 < config.deviation_pct < 1:
        raise ValueError("deviation_pct must be between 0 and 1.")
    if config.minimum_swing_bars < 1:
        raise ValueError("minimum_swing_bars must be >= 1.")

    data, diagnostics = _prepare_source(frame)
    if data.empty:
        return [], None, diagnostics

    rows = list(data.itertuples(index=False))
    first = rows[0]
    first_date = first.Date.date()

    bootstrap_low = _Extreme(float(first.Low), first_date, 0)
    bootstrap_high = _Extreme(float(first.High), first_date, 0)
    high_after_low = _Extreme(float(first.High), first_date, 0)
    low_after_high = _Extreme(float(first.Low), first_date, 0)

    state: str | None = None
    candidate: _Extreme | None = None
    opposite: _Extreme | None = None
    last_pivot_index: int | None = None
    pivots: list[ZigZagPivot] = []

    for i, row in enumerate(rows):
        bar_date = row.Date.date()
        high = float(row.High)
        low = float(row.Low)
        close = float(row.Close)

        if state is None:
            if low < bootstrap_low.price:
                bootstrap_low = _Extreme(low, bar_date, i)
                high_after_low = _Extreme(high, bar_date, i)
            elif high > high_after_low.price:
                high_after_low = _Extreme(high, bar_date, i)

            if high > bootstrap_high.price:
                bootstrap_high = _Extreme(high, bar_date, i)
                low_after_high = _Extreme(low, bar_date, i)
            elif low < low_after_high.price:
                low_after_high = _Extreme(low, bar_date, i)

            up_excursion = close / bootstrap_low.price - 1.0
            down_excursion = 1.0 - close / bootstrap_high.price

            up_ready = (
                up_excursion >= config.deviation_pct
                and i - bootstrap_low.index >= config.minimum_swing_bars
            )
            down_ready = (
                down_excursion >= config.deviation_pct
                and i - bootstrap_high.index >= config.minimum_swing_bars
            )
            if not up_ready and not down_ready:
                continue

            if up_ready and down_ready:
                first_type = _choose_bootstrap(
                    up_excursion=up_excursion,
                    down_excursion=down_excursion,
                    low_extreme=bootstrap_low,
                    high_extreme=bootstrap_high,
                    deviation_pct=config.deviation_pct,
                )
            elif up_ready:
                first_type = "LOW"
            else:
                first_type = "HIGH"

            if first_type == "LOW":
                pivots.append(
                    _pivot(
                        config=config,
                        ticker=ticker,
                        seq=1,
                        pivot_type="LOW",
                        extreme=bootstrap_low,
                        confirmed_at_date=bar_date,
                        confirmation_price=close,
                    )
                )
                state = "UP"
                last_pivot_index = bootstrap_low.index
                candidate = high_after_low
                opposite = _Extreme(low, bar_date, i)
            else:
                pivots.append(
                    _pivot(
                        config=config,
                        ticker=ticker,
                        seq=1,
                        pivot_type="HIGH",
                        extreme=bootstrap_high,
                        confirmed_at_date=bar_date,
                        confirmation_price=close,
                    )
                )
                state = "DOWN"
                last_pivot_index = bootstrap_high.index
                candidate = low_after_high
                opposite = _Extreme(high, bar_date, i)
            continue

        if state == "UP":
            assert candidate is not None
            assert last_pivot_index is not None

            if high > candidate.price:
                candidate = _Extreme(high, bar_date, i)
                opposite = _Extreme(low, bar_date, i)
            elif opposite is None or low < opposite.price:
                opposite = _Extreme(low, bar_date, i)

            reversal = (candidate.price - close) / candidate.price
            enough_bars = i - last_pivot_index >= config.minimum_swing_bars
            if reversal >= config.deviation_pct and enough_bars:
                pivots.append(
                    _pivot(
                        config=config,
                        ticker=ticker,
                        seq=len(pivots) + 1,
                        pivot_type="HIGH",
                        extreme=candidate,
                        confirmed_at_date=bar_date,
                        confirmation_price=close,
                    )
                )
                last_pivot_index = candidate.index
                state = "DOWN"
                candidate = opposite or _Extreme(low, bar_date, i)
                opposite = _Extreme(high, bar_date, i)
            continue

        assert state == "DOWN"
        assert candidate is not None
        assert last_pivot_index is not None

        if low < candidate.price:
            candidate = _Extreme(low, bar_date, i)
            opposite = _Extreme(high, bar_date, i)
        elif opposite is None or high > opposite.price:
            opposite = _Extreme(high, bar_date, i)

        reversal = close / candidate.price - 1.0
        enough_bars = i - last_pivot_index >= config.minimum_swing_bars
        if reversal >= config.deviation_pct and enough_bars:
            pivots.append(
                _pivot(
                    config=config,
                    ticker=ticker,
                    seq=len(pivots) + 1,
                    pivot_type="LOW",
                    extreme=candidate,
                    confirmed_at_date=bar_date,
                    confirmation_price=close,
                )
            )
            last_pivot_index = candidate.index
            state = "UP"
            candidate = opposite or _Extreme(high, bar_date, i)
            opposite = _Extreme(low, bar_date, i)

    last_row = rows[-1]
    last_date = last_row.Date.date()
    last_close = float(last_row.Close)

    # Whipsaw dedupe: a reversal confirmed against a candidate seeded from the
    # just-confirmed pivot bar can re-emit the same extreme. Keep the first
    # confirmation per (PivotDate, PivotType) and resequence so PivotSeq stays
    # contiguous and pivot keys stay unique.
    deduped: list[ZigZagPivot] = []
    seen_keys: set[tuple[date, str]] = set()
    for pivot in pivots:
        key = (pivot.pivot_date, pivot.pivot_type)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(
            pivot
            if pivot.pivot_seq == len(deduped) + 1
            else replace(pivot, pivot_seq=len(deduped) + 1)
        )
    pivots = deduped

    if state is None or not pivots or candidate is None:
        current = ZigZagCurrentLeg(
            config_id=config.config_id,
            ticker=ticker,
            as_of_date=last_date,
            direction=None,
            start_pivot_seq=None,
            start_pivot_date=None,
            start_pivot_price=None,
            candidate_pivot_type=None,
            candidate_pivot_date=None,
            candidate_pivot_price=None,
            last_close=last_close,
            current_move_pct=None,
            reversal_from_candidate_pct=None,
            status="TRANSITION",
        )
        return pivots, current, diagnostics

    start = pivots[-1]
    if state == "UP":
        current_move = candidate.price / start.pivot_price - 1.0
        reversal = (candidate.price - last_close) / candidate.price
        candidate_type = "HIGH"
    else:
        current_move = candidate.price / start.pivot_price - 1.0
        reversal = last_close / candidate.price - 1.0
        candidate_type = "LOW"

    current = ZigZagCurrentLeg(
        config_id=config.config_id,
        ticker=ticker,
        as_of_date=last_date,
        direction=state,
        start_pivot_seq=start.pivot_seq,
        start_pivot_date=start.pivot_date,
        start_pivot_price=start.pivot_price,
        candidate_pivot_type=candidate_type,
        candidate_pivot_date=candidate.date,
        candidate_pivot_price=candidate.price,
        last_close=last_close,
        current_move_pct=float(current_move),
        reversal_from_candidate_pct=float(reversal),
        status="PROVISIONAL",
    )
    return pivots, current, diagnostics
