"""Pure Volume Profile engine for R/S V2.2.

The engine consumes historical daily OHLCV and produces deterministic
price-by-volume nodes. It has no DuckDB or UI dependency.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Sequence

import pandas as pd


@dataclass(frozen=True)
class VolumeProfileConfig:
    window_bars: int = 120
    bins: int = 48
    min_records: int = 30
    hvn_quantile: float = 0.80
    lvn_quantile: float = 0.20
    max_hvn: int = 4
    max_lvn: int = 4


@dataclass(frozen=True)
class VolumeProfileNode:
    node_type: str
    price: float
    volume: float
    volume_share: float
    relative_volume: float
    score: float


@dataclass(frozen=True)
class VolumeProfileResult:
    as_of_date: date
    window_start: date
    window_end: date
    bars: int
    bins: int
    price_low: float
    price_high: float
    total_volume: float
    poc: VolumeProfileNode
    hvn: tuple[VolumeProfileNode, ...]
    lvn: tuple[VolumeProfileNode, ...]


def _validate_config(config: VolumeProfileConfig) -> None:
    if config.window_bars <= 0:
        raise ValueError("window_bars must be > 0")
    if not 8 <= config.bins <= 256:
        raise ValueError("bins must satisfy 8 <= bins <= 256")
    if config.min_records <= 0:
        raise ValueError("min_records must be > 0")
    if not 0 < config.lvn_quantile < config.hvn_quantile < 1:
        raise ValueError("require 0 < lvn_quantile < hvn_quantile < 1")
    if config.max_hvn < 0 or config.max_lvn < 0:
        raise ValueError("max_hvn/max_lvn must be >= 0")


def _quantile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    series = pd.Series(list(values), dtype="float64")
    return float(series.quantile(q))


def build_volume_profile_from_history(
    history: pd.DataFrame,
    *,
    as_of_date: date,
    config: VolumeProfileConfig | None = None,
) -> VolumeProfileResult:
    """Build a deterministic daily-OHLCV Volume Profile.

    Each bar's volume is distributed uniformly across the price bins crossed
    by that bar's Low/High range. This avoids pretending daily OHLCV contains
    intraday tick-level volume-at-price precision.
    """
    cfg = config or VolumeProfileConfig()
    _validate_config(cfg)

    required = {"Date", "High", "Low", "Volume"}
    missing = required - set(history.columns)
    if missing:
        raise ValueError(f"history missing columns: {sorted(missing)}")

    frame = history.loc[:, ["Date", "High", "Low", "Volume"]].copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    for col in ("High", "Low", "Volume"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    frame = frame[
        frame["Date"].notna()
        & (frame["Date"].dt.date <= as_of_date)
        & frame["High"].notna()
        & frame["Low"].notna()
        & frame["Volume"].notna()
        & (frame["High"] >= frame["Low"])
        & (frame["Low"] > 0)
        & (frame["Volume"] > 0)
    ].sort_values("Date")

    if len(frame) > cfg.window_bars:
        frame = frame.iloc[-cfg.window_bars:]

    if len(frame) < cfg.min_records:
        raise ValueError(
            f"insufficient Volume Profile history: {len(frame)} < {cfg.min_records}"
        )

    price_low = float(frame["Low"].min())
    price_high = float(frame["High"].max())
    if not math.isfinite(price_low) or not math.isfinite(price_high) or price_low <= 0:
        raise ValueError("invalid Volume Profile price range")
    if price_high <= price_low:
        price_high = price_low * 1.001

    bin_width = (price_high - price_low) / cfg.bins
    volumes = [0.0 for _ in range(cfg.bins)]

    for row in frame.itertuples(index=False):
        low = float(row.Low)
        high = float(row.High)
        volume = float(row.Volume)
        start = max(0, min(cfg.bins - 1, int((low - price_low) / bin_width)))
        end = max(0, min(cfg.bins - 1, int((high - price_low) / bin_width)))
        if end < start:
            start, end = end, start
        touched = end - start + 1
        allocation = volume / touched
        for idx in range(start, end + 1):
            volumes[idx] += allocation

    total = float(sum(volumes))
    if total <= 0:
        raise ValueError("Volume Profile total volume must be > 0")

    positive = [v for v in volumes if v > 0]
    avg = total / cfg.bins
    hvn_cutoff = _quantile(positive, cfg.hvn_quantile)
    lvn_cutoff = _quantile(positive, cfg.lvn_quantile)
    max_volume = max(volumes)
    poc_idx = min(i for i, v in enumerate(volumes) if v == max_volume)

    def node(idx: int, node_type: str) -> VolumeProfileNode:
        value = float(volumes[idx])
        relative = value / avg if avg > 0 else 0.0
        if node_type == "POC":
            score = 100.0
        elif node_type == "HVN":
            score = max(50.0, min(value / max_volume * 100.0, 100.0))
        else:
            score = max(0.0, min(value / max_volume * 100.0, 49.99))
        return VolumeProfileNode(
            node_type=node_type,
            price=price_low + (idx + 0.5) * bin_width,
            volume=value,
            volume_share=value / total,
            relative_volume=relative,
            score=score,
        )

    hvn_indexes: list[int] = []
    lvn_indexes: list[int] = []
    for idx in range(1, cfg.bins - 1):
        value = volumes[idx]
        if idx != poc_idx and value >= hvn_cutoff:
            if value >= volumes[idx - 1] and value >= volumes[idx + 1]:
                hvn_indexes.append(idx)
        if value > 0 and value <= lvn_cutoff:
            if value <= volumes[idx - 1] and value <= volumes[idx + 1]:
                lvn_indexes.append(idx)

    hvn_indexes = sorted(
        hvn_indexes, key=lambda i: (-volumes[i], i)
    )[: cfg.max_hvn]
    lvn_indexes = sorted(
        lvn_indexes, key=lambda i: (volumes[i], i)
    )[: cfg.max_lvn]

    window_start = pd.Timestamp(frame["Date"].iloc[0]).date()
    window_end = pd.Timestamp(frame["Date"].iloc[-1]).date()
    return VolumeProfileResult(
        as_of_date=as_of_date,
        window_start=window_start,
        window_end=window_end,
        bars=len(frame),
        bins=cfg.bins,
        price_low=price_low,
        price_high=price_high,
        total_volume=total,
        poc=node(poc_idx, "POC"),
        hvn=tuple(node(i, "HVN") for i in hvn_indexes),
        lvn=tuple(node(i, "LVN") for i in lvn_indexes),
    )
