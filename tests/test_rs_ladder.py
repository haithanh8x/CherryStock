from datetime import date

import pytest

from src.calcEngine.levelLadder import (
    CurrentPrice,
    LevelCandidate,
    build_level_ladder_from_data,
)


AS_OF = date(2026, 8, 28)


def candidate(
    price: float,
    code: str,
    *,
    timeframe: str = "D",
    length: int = 20,
) -> LevelCandidate:
    return LevelCandidate(
        ticker="MWG",
        price=price,
        source_type="INDICATOR",
        source_code=code,
        timeframe=timeframe,
        indicator_code="MA",
        config_id=sum(
            (index + 1) * ord(char)
            for index, char in enumerate(f"{code}:{timeframe}:{length}")
        ),
        config_code=code,
        component_code="VALUE",
        source_date=AS_OF,
        metadata={"length": length, "parameters": {"length": length}},
    )


def current(price: float = 100.0) -> CurrentPrice:
    return CurrentPrice(ticker="MWG", as_of_date=AS_OF, price=price)


def test_rank_is_proximity_not_strength() -> None:
    result = build_level_ladder_from_data(
        current(),
        [
            candidate(95.0, "MA20_D"),
            candidate(90.0, "MA200_M", timeframe="M", length=200),
            candidate(90.2, "MA100_W", timeframe="W", length=100),
            candidate(90.3, "MA50_D", timeframe="D", length=50),
            candidate(105.0, "MA20_W", timeframe="W"),
            candidate(115.0, "MA200_D", length=200),
        ],
        cluster_threshold_pct=0.01,
    )

    assert result.support_levels[0].rank == "S1"
    assert result.support_levels[0].price == pytest.approx(95.0)
    assert result.support_levels[1].rank == "S2"
    assert result.support_levels[1].strength_score >= result.support_levels[0].strength_score
    assert result.resistance_levels[0].rank == "R1"
    assert result.resistance_levels[0].price == pytest.approx(105.0)


def test_nearby_sources_are_clustered_into_one_zone() -> None:
    result = build_level_ladder_from_data(
        current(),
        [
            candidate(99.0, "MA20_D"),
            candidate(99.5, "MA50_W", timeframe="W", length=50),
            candidate(110.0, "MA200_M", timeframe="M", length=200),
        ],
        cluster_threshold_pct=0.01,
        neutral_threshold_pct=0.003,
    )

    assert len(result.support_levels) == 1
    assert result.support_levels[0].source_count == 2
    assert 99.0 <= result.support_levels[0].price <= 99.5


def test_empty_candidates_return_empty_ladder() -> None:
    result = build_level_ladder_from_data(current(), [])

    assert result.support_levels == ()
    assert result.resistance_levels == ()
    assert result.nearest_support is None
    assert result.nearest_resistance is None
    assert result.risk_reward_ratio is None


def test_neutral_zone_is_not_ranked_as_support_or_resistance() -> None:
    result = build_level_ladder_from_data(
        current(),
        [candidate(100.1, "MA20_D")],
        neutral_threshold_pct=0.003,
    )

    assert result.support_levels == ()
    assert result.resistance_levels == ()


def test_invalid_cluster_threshold_raises() -> None:
    with pytest.raises(ValueError, match="cluster_threshold_pct"):
        build_level_ladder_from_data(
            current(),
            [candidate(95.0, "MA20_D")],
            cluster_threshold_pct=0,
        )


def test_result_is_deterministic() -> None:
    candidates = [
        candidate(95.0, "MA20_D"),
        candidate(94.8, "MA50_W", timeframe="W", length=50),
        candidate(106.0, "MA100_M", timeframe="M", length=100),
    ]

    first = build_level_ladder_from_data(current(), candidates)
    second = build_level_ladder_from_data(current(), candidates)

    assert first == second
