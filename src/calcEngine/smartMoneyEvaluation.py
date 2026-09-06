from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


SCORE_BUCKET_ORDER = ("0-30", "30-50", "50-70", "70-85", "85-100")
CONFIDENCE_BUCKET_ORDER = ("0-40", "40-60", "60-80", "80-100")


@dataclass(frozen=True)
class SmartMoneyTemporalSplit:
    train_ratio: float = 0.60
    validation_ratio: float = 0.20
    test_ratio: float = 0.20


def assign_temporal_splits(
    dates: Iterable[pd.Timestamp],
    *,
    config: SmartMoneyTemporalSplit | None = None,
) -> dict[pd.Timestamp, str]:
    """Chronological 60/20/20 split. Never shuffles time."""
    cfg = config or SmartMoneyTemporalSplit()
    ratios = (cfg.train_ratio, cfg.validation_ratio, cfg.test_ratio)
    if any(value <= 0 for value in ratios):
        raise ValueError("Temporal split ratios must be > 0.")
    if not np.isclose(sum(ratios), 1.0):
        raise ValueError("Temporal split ratios must sum to 1.0.")

    ordered = sorted({pd.Timestamp(value).normalize() for value in dates})
    if not ordered:
        return {}

    n = len(ordered)
    train_end = max(1, int(n * cfg.train_ratio))
    validation_end = max(
        train_end + 1,
        int(n * (cfg.train_ratio + cfg.validation_ratio)),
    )
    validation_end = min(validation_end, n)

    result: dict[pd.Timestamp, str] = {}
    for index, value in enumerate(ordered):
        if index < train_end:
            split = "TRAIN"
        elif index < validation_end:
            split = "VALIDATION"
        else:
            split = "TEST"
        result[value] = split
    return result


def build_forward_labels(
    scores: pd.DataFrame,
    stock_prices: pd.DataFrame,
    benchmark_prices: pd.DataFrame,
    *,
    horizons: Iterable[int] = (5, 10, 20),
) -> pd.DataFrame:
    """Attach future market-session labels without feeding them back into scoring.

    Horizon H means H VNINDEX trading sessions after the score date. A stock must
    have a Close exactly on that future market date; otherwise its label remains
    unavailable instead of silently using a later ticker-specific observation.
    """
    required_scores = {
        "Ticker",
        "Date",
        "SmartMoneyScore",
        "ConfidenceScore",
        "MarketState",
    }
    required_stock = {"Ticker", "Date", "Close"}
    required_benchmark = {"Date", "Close"}
    for label, required, frame in (
        ("scores", required_scores, scores),
        ("stock_prices", required_stock, stock_prices),
        ("benchmark_prices", required_benchmark, benchmark_prices),
    ):
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{label} missing columns: {sorted(missing)}")

    frame = scores.copy()
    frame["Ticker"] = frame["Ticker"].astype(str)
    frame["Date"] = pd.to_datetime(frame["Date"]).dt.normalize()
    frame["SmartMoneyScore"] = pd.to_numeric(frame["SmartMoneyScore"], errors="coerce")
    frame["ConfidenceScore"] = pd.to_numeric(frame["ConfidenceScore"], errors="coerce")

    stock = stock_prices.loc[:, ["Ticker", "Date", "Close"]].copy()
    stock["Ticker"] = stock["Ticker"].astype(str)
    stock["Date"] = pd.to_datetime(stock["Date"]).dt.normalize()
    stock["Close"] = pd.to_numeric(stock["Close"], errors="coerce")
    stock = stock.drop_duplicates(["Ticker", "Date"], keep="last")

    benchmark = benchmark_prices.loc[:, ["Date", "Close"]].copy()
    benchmark["Date"] = pd.to_datetime(benchmark["Date"]).dt.normalize()
    benchmark["Close"] = pd.to_numeric(benchmark["Close"], errors="coerce")
    benchmark = (
        benchmark.dropna(subset=["Date", "Close"])
        .drop_duplicates(["Date"], keep="last")
        .sort_values("Date")
        .reset_index(drop=True)
        .rename(columns={"Close": "BenchmarkClose"})
    )

    frame = frame.merge(stock, on=["Ticker", "Date"], how="left")
    frame = frame.merge(benchmark, on="Date", how="left")

    for horizon_raw in horizons:
        horizon = int(horizon_raw)
        if horizon <= 0:
            raise ValueError("Evaluation horizons must be positive integers.")

        market_map = benchmark.loc[:, ["Date", "BenchmarkClose"]].copy()
        market_map[f"FutureDate{horizon}"] = market_map["Date"].shift(-horizon)
        market_map[f"FutureBenchmarkClose{horizon}"] = market_map[
            "BenchmarkClose"
        ].shift(-horizon)
        market_map[f"BenchmarkForwardReturn{horizon}"] = (
            market_map[f"FutureBenchmarkClose{horizon}"] / market_map["BenchmarkClose"] - 1.0
        )
        frame = frame.merge(
            market_map[
                [
                    "Date",
                    f"FutureDate{horizon}",
                    f"BenchmarkForwardReturn{horizon}",
                ]
            ],
            on="Date",
            how="left",
        )

        future_stock = stock.rename(
            columns={
                "Date": f"FutureDate{horizon}",
                "Close": f"FutureClose{horizon}",
            }
        )
        frame = frame.merge(
            future_stock,
            on=["Ticker", f"FutureDate{horizon}"],
            how="left",
        )
        frame[f"ForwardReturn{horizon}"] = (
            frame[f"FutureClose{horizon}"] / frame["Close"] - 1.0
        )
        frame[f"ExcessReturn{horizon}"] = (
            frame[f"ForwardReturn{horizon}"]
            - frame[f"BenchmarkForwardReturn{horizon}"]
        )

    split_map = assign_temporal_splits(frame["Date"].dropna().unique())
    frame["Split"] = frame["Date"].map(split_map)

    frame["ScoreBucket"] = pd.cut(
        frame["SmartMoneyScore"],
        bins=[-np.inf, 30.0, 50.0, 70.0, 85.0, np.inf],
        labels=SCORE_BUCKET_ORDER,
        right=True,
    )
    frame["ConfidenceBucket"] = pd.cut(
        frame["ConfidenceScore"],
        bins=[-np.inf, 40.0, 60.0, 80.0, np.inf],
        labels=CONFIDENCE_BUCKET_ORDER,
        right=True,
    )
    return frame


def _aggregate_scope(
    labels: pd.DataFrame,
    *,
    horizon: int,
    scope_type: str,
    scope_column: str,
) -> pd.DataFrame:
    forward = f"ForwardReturn{horizon}"
    benchmark = f"BenchmarkForwardReturn{horizon}"
    excess = f"ExcessReturn{horizon}"

    valid = labels.loc[
        labels[forward].notna()
        & labels[benchmark].notna()
        & labels[scope_column].notna()
        & labels["Split"].notna()
    ].copy()
    if valid.empty:
        return pd.DataFrame(
            columns=[
                "Split",
                "HorizonBars",
                "ScopeType",
                "ScopeKey",
                "SampleSize",
                "AvgForwardReturn",
                "MedianForwardReturn",
                "AvgBenchmarkReturn",
                "AvgExcessReturn",
                "MedianExcessReturn",
                "WinRate",
                "ExcessWinRate",
                "AvgSmartMoneyScore",
                "AvgConfidenceScore",
            ]
        )

    grouped = valid.groupby(["Split", scope_column], observed=True)
    metrics = grouped.agg(
        SampleSize=(forward, "size"),
        AvgForwardReturn=(forward, "mean"),
        MedianForwardReturn=(forward, "median"),
        AvgBenchmarkReturn=(benchmark, "mean"),
        AvgExcessReturn=(excess, "mean"),
        MedianExcessReturn=(excess, "median"),
        AvgSmartMoneyScore=("SmartMoneyScore", "mean"),
        AvgConfidenceScore=("ConfidenceScore", "mean"),
    ).reset_index()
    win_rate = grouped[forward].apply(lambda values: float((values > 0.0).mean()))
    excess_win_rate = grouped[excess].apply(lambda values: float((values > 0.0).mean()))
    rates = pd.DataFrame(
        {
            "WinRate": win_rate,
            "ExcessWinRate": excess_win_rate,
        }
    ).reset_index()

    metrics = metrics.merge(rates, on=["Split", scope_column], how="left")
    metrics = metrics.rename(columns={scope_column: "ScopeKey"})
    metrics.insert(1, "HorizonBars", int(horizon))
    metrics.insert(2, "ScopeType", scope_type)
    return metrics[
        [
            "Split",
            "HorizonBars",
            "ScopeType",
            "ScopeKey",
            "SampleSize",
            "AvgForwardReturn",
            "MedianForwardReturn",
            "AvgBenchmarkReturn",
            "AvgExcessReturn",
            "MedianExcessReturn",
            "WinRate",
            "ExcessWinRate",
            "AvgSmartMoneyScore",
            "AvgConfidenceScore",
        ]
    ]


def evaluate_smart_money_labels(
    labels: pd.DataFrame,
    *,
    horizons: Iterable[int] = (5, 10, 20),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate score-bucket/state/confidence OOS evidence and monotonicity."""
    metric_parts: list[pd.DataFrame] = []
    monotonic_rows: list[dict[str, object]] = []

    for horizon_raw in horizons:
        horizon = int(horizon_raw)
        for scope_type, scope_column in (
            ("SCORE_BUCKET", "ScoreBucket"),
            ("STATE", "MarketState"),
            ("CONFIDENCE_BUCKET", "ConfidenceBucket"),
        ):
            metric_parts.append(
                _aggregate_scope(
                    labels,
                    horizon=horizon,
                    scope_type=scope_type,
                    scope_column=scope_column,
                )
            )

        score_metrics = metric_parts[-3]
        score_metrics = score_metrics.loc[
            score_metrics["ScopeType"].eq("SCORE_BUCKET")
        ]
        for split in ("TRAIN", "VALIDATION", "TEST"):
            current = score_metrics.loc[score_metrics["Split"].eq(split)].copy()
            if current.empty:
                continue
            order_map = {label: index for index, label in enumerate(SCORE_BUCKET_ORDER)}
            current["BucketOrder"] = current["ScopeKey"].astype(str).map(order_map)
            current = current.dropna(subset=["BucketOrder", "AvgExcessReturn"]).sort_values(
                "BucketOrder"
            )
            if len(current) >= 2:
                x = current["BucketOrder"].to_numpy(dtype=float)
                y = current["AvgExcessReturn"].to_numpy(dtype=float)
                monotonic_corr = (
                    float(np.corrcoef(x, y)[0, 1])
                    if len(current) >= 3 and np.std(y) > 0
                    else np.nan
                )
                top_minus_bottom = float(y[-1] - y[0])
            else:
                monotonic_corr = np.nan
                top_minus_bottom = np.nan

            monotonic_rows.append(
                {
                    "Split": split,
                    "HorizonBars": horizon,
                    "BucketCount": len(current),
                    "ScoreBucketMonotonicCorr": monotonic_corr,
                    "TopMinusBottomAvgExcess": top_minus_bottom,
                }
            )

    metrics = (
        pd.concat(metric_parts, ignore_index=True)
        if metric_parts
        else pd.DataFrame()
    )
    monotonicity = pd.DataFrame(monotonic_rows)
    return metrics, monotonicity
