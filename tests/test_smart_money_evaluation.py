from __future__ import annotations

import pandas as pd
import pytest

from calcEngine.smartMoneyEvaluation import (
    SmartMoneyTemporalSplit,
    assign_temporal_splits,
    build_forward_labels,
    evaluate_smart_money_labels,
)


def test_temporal_split_is_chronological() -> None:
    dates = pd.date_range("2026-01-01", periods=10, freq="D")

    split = assign_temporal_splits(
        dates,
        config=SmartMoneyTemporalSplit(0.60, 0.20, 0.20),
    )

    assert [split[value] for value in dates[:6]] == ["TRAIN"] * 6
    assert [split[value] for value in dates[6:8]] == ["VALIDATION"] * 2
    assert [split[value] for value in dates[8:]] == ["TEST"] * 2


def test_forward_label_uses_market_session_date_not_next_ticker_observation() -> None:
    scores = pd.DataFrame(
        {
            "Ticker": ["AAA"],
            "Date": ["2026-09-01"],
            "SmartMoneyScore": [80.0],
            "ConfidenceScore": [75.0],
            "MarketState": ["BREAKOUT"],
        }
    )
    benchmark = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"]
            ),
            "Close": [100.0, 101.0, 102.0, 103.0],
        }
    )
    # AAA does not trade on the exact +2 market-session date (2026-09-03).
    stock = pd.DataFrame(
        {
            "Ticker": ["AAA", "AAA"],
            "Date": pd.to_datetime(["2026-09-01", "2026-09-04"]),
            "Close": [10.0, 12.0],
        }
    )

    labels = build_forward_labels(
        scores,
        stock,
        benchmark,
        horizons=(2,),
    )

    assert labels.loc[0, "FutureDate2"] == pd.Timestamp("2026-09-03")
    assert pd.isna(labels.loc[0, "ForwardReturn2"])


def test_forward_label_and_excess_return_are_correct() -> None:
    scores = pd.DataFrame(
        {
            "Ticker": ["AAA"],
            "Date": ["2026-09-01"],
            "SmartMoneyScore": [90.0],
            "ConfidenceScore": [90.0],
            "MarketState": ["SUPPLY_LOCK"],
        }
    )
    benchmark = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-09-01", "2026-09-02", "2026-09-03"]),
            "Close": [100.0, 101.0, 102.0],
        }
    )
    stock = pd.DataFrame(
        {
            "Ticker": ["AAA", "AAA"],
            "Date": pd.to_datetime(["2026-09-01", "2026-09-03"]),
            "Close": [10.0, 11.0],
        }
    )

    labels = build_forward_labels(scores, stock, benchmark, horizons=(2,))

    assert labels.loc[0, "ForwardReturn2"] == pytest.approx(0.10)
    assert labels.loc[0, "BenchmarkForwardReturn2"] == pytest.approx(0.02)
    assert labels.loc[0, "ExcessReturn2"] == pytest.approx(0.08)


def test_evaluation_emits_score_state_and_confidence_scopes() -> None:
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    labels = pd.DataFrame(
        {
            "Date": dates,
            "Ticker": ["AAA"] * 30,
            "SmartMoneyScore": [20.0] * 10 + [60.0] * 10 + [90.0] * 10,
            "ConfidenceScore": [50.0] * 10 + [70.0] * 10 + [90.0] * 10,
            "MarketState": ["NEUTRAL"] * 10 + ["ACCUMULATION"] * 10 + ["BREAKOUT"] * 10,
            "ForwardReturn5": [0.01] * 10 + [0.03] * 10 + [0.08] * 10,
            "BenchmarkForwardReturn5": [0.02] * 30,
            "ExcessReturn5": [-0.01] * 10 + [0.01] * 10 + [0.06] * 10,
            "Split": ["TRAIN"] * 18 + ["VALIDATION"] * 6 + ["TEST"] * 6,
            "ScoreBucket": pd.cut(
                [20.0] * 10 + [60.0] * 10 + [90.0] * 10,
                bins=[float("-inf"), 30, 50, 70, 85, float("inf")],
                labels=["0-30", "30-50", "50-70", "70-85", "85-100"],
            ),
            "ConfidenceBucket": pd.cut(
                [50.0] * 10 + [70.0] * 10 + [90.0] * 10,
                bins=[float("-inf"), 40, 60, 80, float("inf")],
                labels=["0-40", "40-60", "60-80", "80-100"],
            ),
        }
    )

    metrics, monotonicity = evaluate_smart_money_labels(labels, horizons=(5,))

    assert set(metrics["ScopeType"]) == {
        "SCORE_BUCKET",
        "STATE",
        "CONFIDENCE_BUCKET",
    }
    assert set(metrics["Split"]).issubset({"TRAIN", "VALIDATION", "TEST"})
    assert set(monotonicity["HorizonBars"]) == {5}
