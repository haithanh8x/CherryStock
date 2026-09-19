from __future__ import annotations

from dataclasses import dataclass
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


def _seed_opposite_after_candidate(
    rows: list[object],
    *,
    candidate: _Extreme,
    state: str,
    end_index: int,
) -> _Extreme | None:
    """Seed the opposite extreme strictly after candidate.PivotDate.

    This helper is used only once during bootstrap. Normal runtime maintains the
    same information incrementally, so total engine complexity stays O(n).
    """

    opposite: _Extreme | None = None
    for index in range(candidate.index + 1, end_index + 1):
        row = rows[index]
        bar_date = row.Date.date()

        if state == "UP":
            price = float(row.Low)
            if opposite is None or price < opposite.price:
                opposite = _Extreme(price, bar_date, index)
        else:
            price = float(row.High)
            if opposite is None or price > opposite.price:
                opposite = _Extreme(price, bar_date, index)

    return opposite


def calculate_zigzag(
    frame: pd.DataFrame,
    *,
    ticker: str,
    config: ZigZagConfig,
) -> tuple[list[ZigZagPivot], ZigZagCurrentLeg | None, ZigZagDiagnostics]:
    """Calculate a confirmed percentage-reversal ZigZag in one forward scan.

    Daily OHLC cannot reveal the intraday order of High and Low. The MVP
    therefore enforces one pivot per trading date: once a pivot is located on a
    bar, the next pivot candidate must come from a strictly later bar.

    Candidate extrema use High/Low. Reversal confirmation uses Close.
    PivotDate and ConfirmedAtDate remain separate for point-in-time safety.
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
    high_after_low: _Extreme | None = None
    low_after_high: _Extreme | None = None

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
                high_after_low = None
            elif i > bootstrap_low.index and (
                high_after_low is None or high > high_after_low.price
            ):
                high_after_low = _Extreme(high, bar_date, i)

            if high > bootstrap_high.price:
                bootstrap_high = _Extreme(high, bar_date, i)
                low_after_high = None
            elif i > bootstrap_high.index and (
                low_after_high is None or low < low_after_high.price
            ):
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
                candidate = (
                    high_after_low
                    if high_after_low is not None
                    and high_after_low.index > bootstrap_low.index
                    else None
                )
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
                candidate = (
                    low_after_high
                    if low_after_high is not None
                    and low_after_high.index > bootstrap_high.index
                    else None
                )

            opposite = (
                _seed_opposite_after_candidate(
                    rows,
                    candidate=candidate,
                    state=state,
                    end_index=i,
                )
                if candidate is not None
                else None
            )
            continue

        assert last_pivot_index is not None

        if state == "UP":
            if candidate is None:
                candidate = _Extreme(high, bar_date, i)
                opposite = None
                continue

            if high > candidate.price:
                candidate = _Extreme(high, bar_date, i)
                # Same-day Low cannot be ordered after the new High.
                opposite = None
                continue

            if i > candidate.index and (opposite is None or low < opposite.price):
                opposite = _Extreme(low, bar_date, i)

            reversal = (candidate.price - close) / candidate.price
            enough_bars = (
                candidate.index - last_pivot_index >= config.minimum_swing_bars
            )
            if (
                i > candidate.index
                and reversal >= config.deviation_pct
                and enough_bars
            ):
                confirmed = candidate
                pivots.append(
                    _pivot(
                        config=config,
                        ticker=ticker,
                        seq=len(pivots) + 1,
                        pivot_type="HIGH",
                        extreme=confirmed,
                        confirmed_at_date=bar_date,
                        confirmation_price=close,
                    )
                )
                last_pivot_index = confirmed.index
                state = "DOWN"

                # Carry only an opposite extreme from a strictly later bar.
                candidate = (
                    opposite
                    if opposite is not None and opposite.index > confirmed.index
                    else None
                )
                # Do not pre-build another leg from bars before this confirmation.
                opposite = None
            continue

        assert state == "DOWN"

        if candidate is None:
            candidate = _Extreme(low, bar_date, i)
            opposite = None
            continue

        if low < candidate.price:
            candidate = _Extreme(low, bar_date, i)
            # Same-day High cannot be ordered after the new Low.
            opposite = None
            continue

        if i > candidate.index and (opposite is None or high > opposite.price):
            opposite = _Extreme(high, bar_date, i)

        reversal = close / candidate.price - 1.0
        enough_bars = candidate.index - last_pivot_index >= config.minimum_swing_bars
        if (
            i > candidate.index
            and reversal >= config.deviation_pct
            and enough_bars
        ):
            confirmed = candidate
            pivots.append(
                _pivot(
                    config=config,
                    ticker=ticker,
                    seq=len(pivots) + 1,
                    pivot_type="LOW",
                    extreme=confirmed,
                    confirmed_at_date=bar_date,
                    confirmation_price=close,
                )
            )
            last_pivot_index = confirmed.index
            state = "UP"

            candidate = (
                opposite
                if opposite is not None and opposite.index > confirmed.index
                else None
            )
            opposite = None

    last_row = rows[-1]
    last_date = last_row.Date.date()
    last_close = float(last_row.Close)

    if state is None or not pivots:
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
    if candidate is None:
        current = ZigZagCurrentLeg(
            config_id=config.config_id,
            ticker=ticker,
            as_of_date=last_date,
            direction=state,
            start_pivot_seq=start.pivot_seq,
            start_pivot_date=start.pivot_date,
            start_pivot_price=start.pivot_price,
            candidate_pivot_type="HIGH" if state == "UP" else "LOW",
            candidate_pivot_date=None,
            candidate_pivot_price=None,
            last_close=last_close,
            current_move_pct=None,
            reversal_from_candidate_pct=None,
            status="PROVISIONAL",
        )
        return pivots, current, diagnostics

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
