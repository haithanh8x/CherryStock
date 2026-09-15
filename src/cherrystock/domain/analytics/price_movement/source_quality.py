from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PriceSourceQuality:
    """Diagnostics for OHLC rows consumed by Price Movement Character.

    V1 segmentation/features use High/Low/Close. A bad Open alone therefore does
    not make the bar unusable, but it still degrades the source-quality evidence.
    Rows with invalid High/Low/Close are excluded from calculation so one bad
    historical record cannot crash a full-universe rebuild.
    """

    source_rows: int
    invalid_ohlc_rows: int
    invalid_calculation_rows: int
    open_only_invalid_rows: int
    usable_rows: int

    @property
    def degraded(self) -> bool:
        return self.invalid_ohlc_rows > 0


def _invalid_price(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.isna() | ~np.isfinite(numeric.to_numpy(dtype=float)) | (numeric <= 0)


def inspect_price_source_quality(frame: pd.DataFrame) -> PriceSourceQuality:
    """Inspect price validity without mutating the caller's frame."""
    if frame.empty:
        return PriceSourceQuality(0, 0, 0, 0, 0)

    missing = [column for column in ("High", "Low", "Close") if column not in frame.columns]
    if missing:
        raise ValueError(f"Price Movement source is missing required columns: {missing}")

    high_bad = _invalid_price(frame["High"])
    low_bad = _invalid_price(frame["Low"])
    close_bad = _invalid_price(frame["Close"])
    calc_bad = high_bad | low_bad | close_bad

    if "Open" in frame.columns:
        open_bad = _invalid_price(frame["Open"])
    else:
        open_bad = pd.Series(False, index=frame.index)

    any_bad = calc_bad | open_bad
    open_only_bad = open_bad & ~calc_bad

    return PriceSourceQuality(
        source_rows=int(len(frame)),
        invalid_ohlc_rows=int(any_bad.sum()),
        invalid_calculation_rows=int(calc_bad.sum()),
        open_only_invalid_rows=int(open_only_bad.sum()),
        usable_rows=int((~calc_bad).sum()),
    )


def sanitize_price_movement_frame(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, PriceSourceQuality]:
    """Return calculation-safe bars plus explicit source-quality diagnostics.

    High/Low/Close must be finite and strictly positive because they participate
    directly in reversal detection, ratios and logarithms. Invalid calculation
    bars are dropped. Open is not used by V1 calculations, so an invalid Open is
    retained but marks the ticker source as degraded.
    """
    diagnostics = inspect_price_source_quality(frame)
    if frame.empty:
        return frame.copy(), diagnostics

    data = frame.copy()
    for column in ("Open", "High", "Low", "Close", "ATR"):
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")

    high_bad = _invalid_price(data["High"])
    low_bad = _invalid_price(data["Low"])
    close_bad = _invalid_price(data["Close"])
    calc_bad = high_bad | low_bad | close_bad

    clean = data.loc[~calc_bad].copy()
    clean = clean.sort_values("Date").reset_index(drop=True)
    return clean, diagnostics
