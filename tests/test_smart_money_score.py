from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from calcEngine.smartMoneyScore import (
    _apply_accumulation_memory,
    _apply_market_limit_evidence,
    _detect_states,
    _score_by_state,
    cross_sectional_percentile,
)


def test_cross_sectional_percentile_is_date_scoped() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                ["2026-09-01", "2026-09-01", "2026-09-02", "2026-09-02"]
            ),
            "Raw": [1.0, 3.0, 100.0, 200.0],
        }
    )

    ranked = cross_sectional_percentile(frame, "Raw", min_count=2)

    assert ranked.tolist() == pytest.approx([50.0, 100.0, 50.0, 100.0])


def test_cross_sectional_percentile_requires_minimum_universe() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-09-01", "2026-09-01"]),
            "Raw": [1.0, 2.0],
        }
    )

    ranked = cross_sectional_percentile(frame, "Raw", min_count=5)

    assert ranked.isna().all()


def test_accumulation_memory_matches_recursive_contract() -> None:
    frame = pd.DataFrame(
        {
            "Ticker": ["AAA", "AAA", "AAA"],
            "AccumulationScore": [20.0, 80.0, 80.0],
        }
    )

    memory = _apply_accumulation_memory(frame, 0.90)

    assert memory.iloc[0] == pytest.approx(20.0)
    assert memory.iloc[1] == pytest.approx(26.0)
    assert memory.iloc[2] == pytest.approx(31.4)


def test_missing_market_limit_remains_unavailable_not_zero() -> None:
    frame = pd.DataFrame(
        {
            "Ticker": ["AAA"],
            "Date": pd.to_datetime(["2026-09-04"]),
        }
    )

    result = _apply_market_limit_evidence(frame, pd.DataFrame())

    assert result["LimitUpScore"].isna().all()
    assert result.loc[0, "MarketLimitQuality"] == "UNAVAILABLE"


def test_distribution_has_highest_state_precedence() -> None:
    frame = pd.DataFrame(
        {
            "LiquidityCompressionScore": [90.0],
            "RelativeStrengthScore": [90.0],
            "TrendScore": [90.0],
            "AccumulationScore": [90.0],
            "AccumulationMemoryScore": [90.0],
            "RelativeLiquidityScore": [90.0],
            "LiquidityAccelerationScore": [90.0],
            "FreshFlowScore": [90.0],
            "SupplyLockScore": [90.0],
            "DistributionScore": [95.0],
            "Return1": [-0.05],
        }
    )

    state = _detect_states(frame, {})

    assert state.iloc[0] == "DISTRIBUTION"


def test_supply_lock_scoring_renormalizes_missing_limit_up() -> None:
    frame = pd.DataFrame(
        {
            "MarketState": ["SUPPLY_LOCK"],
            "FreshFlowScore": [80.0],
            "RelativeLiquidityScore": [np.nan],
            "LiquidityAccelerationScore": [np.nan],
            "RelativeStrengthScore": [80.0],
            "AccumulationScore": [np.nan],
            "AccumulationMemoryScore": [80.0],
            "SupplyLockScore": [80.0],
            "LimitUpScore": [np.nan],
            "TrendScore": [80.0],
            "DistributionScore": [0.0],
        }
    )
    weights = pd.DataFrame(
        {
            "MarketState": ["SUPPLY_LOCK"] * 6,
            "FactorCode": [
                "ACCUMULATION_MEMORY",
                "SUPPLY_LOCK",
                "LIMIT_UP",
                "RELATIVE_STRENGTH",
                "TREND",
                "FRESH_FLOW",
            ],
            "Weight": [0.25, 0.25, 0.20, 0.15, 0.10, 0.05],
        }
    )

    result = _score_by_state(
        frame,
        weights,
        {
            "DISTRIBUTION_PENALTY_DEFAULT": 0.35,
            "DISTRIBUTION_PENALTY_DISTRIBUTION": 0.75,
        },
    )

    assert result.loc[0, "FactorCoverage"] == pytest.approx(0.80)
    assert result.loc[0, "PositiveScore"] == pytest.approx(80.0)
    assert result.loc[0, "SmartMoneyScore"] == pytest.approx(80.0)
