from __future__ import annotations

import pandas as pd

from cherrystock.domain.analytics.zigzag.engine import calculate_zigzag
from cherrystock.domain.analytics.zigzag.models import ZigZagConfig


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


def _frame(rows: list[tuple[str, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["Date", "High", "Low", "Close"])


BASE_PATH = [
    ("2026-07-01", 100, 98, 99),
    ("2026-07-02", 99, 95, 96),
    ("2026-07-03", 97, 92, 93),
    ("2026-07-04", 96, 90, 91),
    ("2026-07-05", 100, 94, 96),
    ("2026-07-06", 104, 98, 103),
    ("2026-07-07", 110, 102, 109),
    ("2026-07-08", 109, 101, 103),
    ("2026-07-09", 104, 100, 102),
    ("2026-07-10", 108, 102, 107),
]


def test_low_pivot_is_actual_trough_not_confirmation_bar() -> None:
    frame = _frame(BASE_PATH[:6])

    pivots, current, diagnostics = calculate_zigzag(frame, ticker="MWG", config=_config())

    assert diagnostics.invalid_rows_dropped == 0
    assert [pivot.pivot_type for pivot in pivots] == ["HIGH", "LOW"]

    trough = pivots[1]
    assert str(trough.pivot_date) == "2026-07-04"
    assert trough.pivot_price == 90
    assert str(trough.confirmed_at_date) == "2026-07-05"
    assert trough.pivot_date < trough.confirmed_at_date

    assert current is not None
    assert current.direction == "UP"
    assert current.status == "PROVISIONAL"


def test_high_pivot_is_actual_peak_and_confirmed_later() -> None:
    frame = _frame(BASE_PATH[:8])

    pivots, current, _ = calculate_zigzag(frame, ticker="MWG", config=_config())

    assert [pivot.pivot_type for pivot in pivots] == ["HIGH", "LOW", "HIGH"]

    peak = pivots[2]
    assert str(peak.pivot_date) == "2026-07-07"
    assert peak.pivot_price == 110
    assert str(peak.confirmed_at_date) == "2026-07-08"
    assert peak.pivot_date < peak.confirmed_at_date

    assert current is not None
    assert current.direction == "DOWN"


def test_pivots_alternate_and_current_leg_follows_last_pivot() -> None:
    frame = _frame(BASE_PATH)

    pivots, current, _ = calculate_zigzag(frame, ticker="MWG", config=_config())

    assert [pivot.pivot_type for pivot in pivots] == ["HIGH", "LOW", "HIGH", "LOW"]
    assert [pivot.pivot_seq for pivot in pivots] == [1, 2, 3, 4]

    trough = pivots[3]
    assert str(trough.pivot_date) == "2026-07-09"
    assert trough.pivot_price == 100
    assert str(trough.confirmed_at_date) == "2026-07-10"

    assert current is not None
    assert current.direction == "UP"
    assert current.start_pivot_seq == 4


def test_invalid_price_row_is_dropped_explicitly() -> None:
    frame = _frame(
        [
            ("2026-07-01", 100, 98, 99),
            ("2026-07-02", 0, 0, 0),
            ("2026-07-03", 106, 100, 105),
        ]
    )

    _, _, diagnostics = calculate_zigzag(frame, ticker="MWG", config=_config())

    assert diagnostics.source_rows == 3
    assert diagnostics.usable_rows == 2
    assert diagnostics.invalid_rows_dropped == 1


def test_reversal_after_confirmed_pivot_does_not_stall() -> None:
    """Regression for the MWG 2014 freeze.

    The next LOW candidate is allowed to form before the HIGH confirmation date,
    but it must be on a strictly later trading bar than the HIGH PivotDate. The
    engine must still confirm that LOW when a later Close reverses by 5%.
    """

    # Bootstrap HIGH on 01-01, confirm it on 01-02. The candidate LOW is the
    # 01-02 Low (strictly after the HIGH PivotDate), then 01-03 confirms it.
    rows = [
        ("2026-01-01", 10.0, 9.0, 9.5),   # bootstrap high 10.0, low 9.0
        ("2026-01-02", 9.2, 8.4, 8.6),    # drop >5% from high -> bootstrap HIGH confirmed
        ("2026-01-03", 9.5, 8.9, 9.3),    # close 9.3 vs candidate low 8.4 = +10.7% -> LOW pivot
        ("2026-01-04", 10.5, 9.8, 10.2),  # rally continues
        ("2026-01-05", 12.0, 11.2, 11.5),
        ("2026-01-06", 14.0, 13.1, 13.5),
    ]
    frame = _frame(rows)

    pivots, current, _ = calculate_zigzag(frame, ticker="MWG", config=_config())

    types = [pivot.pivot_type for pivot in pivots]
    assert types == ["HIGH", "LOW"], f"expected stalled leg resolved, got {types}"

    low_pivot = pivots[1]
    assert str(low_pivot.pivot_date) == "2026-01-02"
    assert low_pivot.pivot_price == 8.4
    assert str(low_pivot.confirmed_at_date) == "2026-01-03"

    assert current is not None
    assert current.direction == "UP"
    assert current.status == "PROVISIONAL"


def test_same_day_whipsaw_does_not_emit_multiple_pivots_on_one_date() -> None:
    """Daily OHLC has no intraday High/Low ordering, so one bar may own one pivot."""

    frame = _frame(
        [
            ("2026-02-01", 10.0, 9.4, 9.8),
            ("2026-02-02", 9.8, 8.5, 8.6),   # confirms first HIGH
            ("2026-02-03", 9.4, 8.4, 9.1),   # updates LOW candidate; no same-bar confirm
            ("2026-02-04", 9.3, 8.8, 9.2),   # confirms LOW from 02-03
            ("2026-02-05", 9.8, 8.9, 9.7),   # updates HIGH candidate
            ("2026-02-06", 9.5, 8.7, 9.0),   # confirms HIGH from 02-05
        ]
    )

    pivots, _, _ = calculate_zigzag(frame, ticker="MWG", config=_config())

    pivot_dates = [pivot.pivot_date for pivot in pivots]
    pivot_types = [pivot.pivot_type for pivot in pivots]

    assert len(pivot_dates) == len(set(pivot_dates))
    assert pivot_dates == sorted(pivot_dates)
    assert all(
        pivot_types[i] != pivot_types[i - 1]
        for i in range(1, len(pivot_types))
    )


def test_confirmed_pivot_date_is_strictly_before_confirmation_date() -> None:
    frame = _frame(BASE_PATH)

    pivots, _, _ = calculate_zigzag(frame, ticker="MWG", config=_config())

    assert pivots
    assert all(
        pivot.pivot_date < pivot.confirmed_at_date
        for pivot in pivots
    )
