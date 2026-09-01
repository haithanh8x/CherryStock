from datetime import date

import pytest

from src.calcEngine.levelLadder import (
    ConfirmationContext,
    CurrentPrice,
    LevelCandidate,
    SOURCE_FAMILY_TREND_AVERAGE,
    SOURCE_FAMILY_VOLATILITY_BAND,
    SOURCE_ROLE_LEVEL,
    VALUE_SEMANTIC_PRICE_LEVEL,
    build_level_ladder_from_data,
)


AS_OF = date(2026, 8, 28)


def candidate(
    price: float,
    code: str,
    *,
    timeframe: str = "D",
    length: int = 20,
    indicator_code: str = "MA",
    component_code: str = "VALUE",
    source_family: str = SOURCE_FAMILY_TREND_AVERAGE,
    value_semantic: str = VALUE_SEMANTIC_PRICE_LEVEL,
) -> LevelCandidate:
    return LevelCandidate(
        ticker="MWG",
        price=price,
        source_type="INDICATOR",
        source_code=code,
        timeframe=timeframe,
        indicator_code=indicator_code,
        config_id=sum(
            (index + 1) * ord(char)
            for index, char in enumerate(f"{code}:{timeframe}:{length}")
        ),
        config_code=code,
        component_code=component_code,
        source_date=AS_OF,
        source_role=SOURCE_ROLE_LEVEL,
        source_family=source_family,
        value_semantic=value_semantic,
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


def confirmation(value: float, *, timeframe: str = "D") -> ConfirmationContext:
    return ConfirmationContext(
        ticker="MWG",
        as_of_date=AS_OF,
        source_code=f"RSI14_{timeframe}",
        source_family="MOMENTUM_CONFIRMATION",
        timeframe=timeframe,
        indicator_code="RSI",
        config_id=900 + ord(timeframe),
        config_code=f"RSI14_{timeframe}",
        component_code="VALUE",
        value=value,
        source_date=AS_OF,
        metadata={"parameters": {"length": 14}},
    )


def test_bb_level_can_cluster_with_ma_and_preserves_family_diversity() -> None:
    result = build_level_ladder_from_data(
        current(),
        [
            candidate(95.0, "MA20_D"),
            candidate(
                95.2,
                "BB20_2_D:LOWER",
                indicator_code="BB",
                component_code="LOWER",
                source_family=SOURCE_FAMILY_VOLATILITY_BAND,
            ),
        ],
        cluster_threshold_pct=0.01,
    )

    assert result.support_levels[0].source_count == 2
    assert result.support_levels[0].source_family_count == 2
    assert {source.source_family for source in result.support_levels[0].sources} == {
        SOURCE_FAMILY_TREND_AVERAGE,
        SOURCE_FAMILY_VOLATILITY_BAND,
    }


def test_same_family_sources_do_not_count_as_independent_families() -> None:
    result = build_level_ladder_from_data(
        current(),
        [
            candidate(95.0, "MA20_D"),
            candidate(95.1, "MA50_D", length=50),
            candidate(95.2, "MA100_D", length=100),
            candidate(95.3, "MA200_D", length=200),
        ],
        cluster_threshold_pct=0.01,
    )

    level = result.support_levels[0]
    assert level.source_count == 4
    assert level.source_family_count == 1


def test_rsi_confirmation_changes_strength_but_not_proximity_rank() -> None:
    candidates = [
        candidate(95.0, "MA20_D"),
        candidate(90.0, "MA50_D", length=50),
    ]

    baseline = build_level_ladder_from_data(current(), candidates)
    confirmed = build_level_ladder_from_data(
        current(),
        candidates,
        confirmations=[confirmation(25.0)],
    )

    assert [level.rank for level in confirmed.support_levels] == ["S1", "S2"]
    assert [level.price for level in confirmed.support_levels] == [
        level.price for level in baseline.support_levels
    ]
    assert confirmed.support_levels[0].strength_score > baseline.support_levels[0].strength_score
    assert confirmed.confirmations[0].indicator_code == "RSI"


def test_non_price_semantic_is_rejected_from_level_pipeline() -> None:
    bad = candidate(
        95.0,
        "RSI14_D",
        indicator_code="RSI",
        value_semantic="OSCILLATOR",
    )

    with pytest.raises(ValueError, match="ValueSemantic=PRICE_LEVEL"):
        build_level_ladder_from_data(current(), [bad])

