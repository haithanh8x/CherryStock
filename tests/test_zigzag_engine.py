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
