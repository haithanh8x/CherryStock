from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RegimePolicyConfig:
    atr_window: int = 20
    percentile_window: int = 252
    percentile_min_periods: int = 60
    low_percentile: float = 0.30
    high_percentile: float = 0.70
    low_multiplier: float = 0.80
    normal_multiplier: float = 1.00
    high_multiplier: float = 1.30
    minimum_deviation_pct: float = 0.02
    maximum_deviation_pct: float = 0.15


def _last_percentile(values: np.ndarray) -> float:
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    if array.size == 0:
        return float("nan")
    current = array[-1]
    return float(np.mean(array <= current))


def build_regime_context(
    frame: pd.DataFrame,
    *,
    policy: RegimePolicyConfig | None = None,
) -> pd.DataFrame:
    resolved = policy or RegimePolicyConfig()
    required = {"Date", "High", "Low", "Close"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"regime source is missing columns: {sorted(missing)}")
    if resolved.atr_window < 2:
        raise ValueError("atr_window must be >= 2.")
    if resolved.percentile_window < resolved.atr_window:
        raise ValueError("percentile_window must be >= atr_window.")

    data = frame.loc[:, ["Date", "High", "Low", "Close"]].copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="raise")
    data = data.sort_values("Date").reset_index(drop=True)

    previous_close = data["Close"].shift(1)
    true_range = pd.concat(
        [
            data["High"] - data["Low"],
            (data["High"] - previous_close).abs(),
            (data["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = true_range.rolling(
        window=resolved.atr_window,
        min_periods=resolved.atr_window,
    ).mean()
    atr_pct = atr / data["Close"]

    min_periods = min(
        resolved.percentile_min_periods,
        resolved.percentile_window,
    )
    percentile = atr_pct.rolling(
        window=resolved.percentile_window,
        min_periods=min_periods,
    ).apply(_last_percentile, raw=True)

    regime = np.where(
        percentile.isna(),
        "NORMAL",
        np.where(
            percentile < resolved.low_percentile,
            "LOW_VOL",
            np.where(
                percentile > resolved.high_percentile,
                "HIGH_VOL",
                "NORMAL",
            ),
        ),
    )

    return pd.DataFrame(
        {
            "Date": data["Date"],
            "TrueRange": true_range.astype(float),
            "ATR": atr.astype(float),
            "ATRPct": atr_pct.astype(float),
            "ATRPercentile": percentile.astype(float),
            "Regime": regime,
        }
    )


class RegimeDeviationResolver:
    """Point-in-time deviation resolver called only after pivot confirmation."""

    def __init__(
        self,
        context: pd.DataFrame,
        *,
        policy: RegimePolicyConfig | None = None,
    ) -> None:
        self.policy = policy or RegimePolicyConfig()
        self.context = context.reset_index(drop=True).copy()

    def regime_at(self, index: int) -> str:
        if index < 0 or index >= len(self.context):
            return "NORMAL"
        value = str(self.context.iloc[index]["Regime"])
        if value not in {"LOW_VOL", "NORMAL", "HIGH_VOL"}:
            return "NORMAL"
        return value

    def multiplier_at(self, index: int) -> float:
        regime = self.regime_at(index)
        if regime == "LOW_VOL":
            return self.policy.low_multiplier
        if regime == "HIGH_VOL":
            return self.policy.high_multiplier
        return self.policy.normal_multiplier

    def deviation_at(self, index: int, base_deviation_pct: float) -> float:
        raw = float(base_deviation_pct) * self.multiplier_at(index)
        return float(
            min(
                max(raw, self.policy.minimum_deviation_pct),
                self.policy.maximum_deviation_pct,
            )
        )

    def __call__(
        self,
        confirmed_at_date,
        confirmed_at_index: int,
        base_deviation_pct: float,
    ) -> float:
        return self.deviation_at(confirmed_at_index, base_deviation_pct)


def regime_counts(context: pd.DataFrame) -> dict[str, int]:
    counts = context["Regime"].value_counts().to_dict()
    return {
        "LOW_VOL": int(counts.get("LOW_VOL", 0)),
        "NORMAL": int(counts.get("NORMAL", 0)),
        "HIGH_VOL": int(counts.get("HIGH_VOL", 0)),
    }
