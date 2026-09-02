from datetime import date

import pandas as pd
import pytest

from src.calcEngine.levelLadder import (
    ConfirmationContext,
    CurrentPrice,
    LevelCandidate,
    MarketContext,
    SOURCE_FAMILY_MARKET_STRUCTURE,
    SOURCE_FAMILY_TREND_AVERAGE,
    SOURCE_FAMILY_VOLATILITY_BAND,
    SOURCE_FAMILY_VOLATILITY_CONTEXT,
    SOURCE_ROLE_LEVEL,
    VALUE_SEMANTIC_PRICE_LEVEL,
    build_level_ladder_from_data,
    load_52w_level_candidates,
    load_previous_period_level_candidates,
    load_swing_level_candidates,
    resolve_adaptive_thresholds,
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


class _FrameResult:
    def __init__(self, dataframe: pd.DataFrame) -> None:
        self._dataframe = dataframe

    def df(self) -> pd.DataFrame:
        return self._dataframe.copy()


class _HistoryConnection:
    def __init__(self, dataframe: pd.DataFrame) -> None:
        self._dataframe = dataframe

    def execute(self, *_args, **_kwargs) -> _FrameResult:
        return _FrameResult(self._dataframe)


def atr_context(value: float, *, source_date: date = AS_OF) -> MarketContext:
    return MarketContext(
        ticker="MWG",
        as_of_date=AS_OF,
        source_code="ATR14_D",
        source_family=SOURCE_FAMILY_VOLATILITY_CONTEXT,
        timeframe="D",
        indicator_code="ATR",
        config_id=37,
        config_code="ATR14_D",
        component_code="VALUE",
        value=value,
        unit="PRICE",
        source_date=source_date,
        metadata={"parameters": {"length": 14}},
    )


def test_atr_adaptive_thresholds_use_percent_floor_and_atr_distance() -> None:
    cluster, neutral = resolve_adaptive_thresholds(
        current_price=current(),
        market_contexts=[atr_context(4.0)],
        min_cluster_pct=0.01,
        min_neutral_pct=0.003,
    )

    assert cluster == pytest.approx(0.02)
    assert neutral == pytest.approx(0.006)


def test_atr_adaptive_thresholds_fallback_when_context_missing() -> None:
    cluster, neutral = resolve_adaptive_thresholds(
        current_price=current(),
        market_contexts=[],
        min_cluster_pct=0.01,
        min_neutral_pct=0.003,
    )

    assert cluster == pytest.approx(0.01)
    assert neutral == pytest.approx(0.003)


def test_future_confirmed_candidate_is_rejected() -> None:
    future = candidate(95.0, "SWING_LOW_TEST")
    future = LevelCandidate(
        **{
            **future.__dict__,
            "source_family": SOURCE_FAMILY_MARKET_STRUCTURE,
            "source_type": "STRUCTURAL",
            "confirmed_at": date(2026, 8, 31),
        }
    )

    with pytest.raises(ValueError, match="confirmed_at"):
        build_level_ladder_from_data(current(), [future])


def test_swing_provider_emits_only_confirmed_pivots() -> None:
    dates = pd.date_range("2026-08-17", periods=10, freq="D")
    frame = pd.DataFrame(
        {
            "Date": dates,
            "High": [10, 11, 12, 20, 13, 12, 11, 15, 14, 13],
            "Low": [8, 8.5, 9, 10, 9, 8.8, 8.7, 9, 8.9, 8.8],
            "Close": [9, 10, 11, 15, 11, 10, 10, 12, 11, 10],
        }
    )
    connection = _HistoryConnection(frame)

    candidates = load_swing_level_candidates(
        connection,
        ticker="MWG",
        as_of_date=date(2026, 8, 26),
    )

    swing_highs = [x for x in candidates if x.metadata.get("structure_kind") == "SWING_HIGH"]
    assert swing_highs
    pivot = next(x for x in swing_highs if x.price == 20.0)
    assert pivot.source_date == date(2026, 8, 20)
    assert pivot.confirmed_at == date(2026, 8, 23)
    assert pivot.confirmed_at <= date(2026, 8, 26)


def test_previous_period_provider_excludes_current_partial_week_and_month() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2026-07-29",
                    "2026-07-31",
                    "2026-08-17",
                    "2026-08-18",
                    "2026-08-19",
                    "2026-08-20",
                    "2026-08-21",
                    "2026-08-24",
                    "2026-08-25",
                    "2026-08-26",
                    "2026-08-27",
                    "2026-08-28",
                ]
            ),
            "High": [60, 62, 70, 71, 72, 73, 74, 90, 91, 92, 93, 94],
            "Low": [55, 56, 65, 64, 63, 62, 61, 50, 49, 48, 47, 46],
            "Close": [58, 60, 68, 69, 70, 71, 72, 75, 76, 77, 78, 79],
        }
    )
    candidates = load_previous_period_level_candidates(
        _HistoryConnection(frame),
        ticker="MWG",
        as_of_date=date(2026, 8, 28),
    )
    values = {item.source_code: item.price for item in candidates}

    assert values["PREV_WEEK_HIGH"] == 74.0
    assert values["PREV_WEEK_LOW"] == 61.0
    assert values["PREV_MONTH_HIGH"] == 62.0
    assert values["PREV_MONTH_LOW"] == 55.0
    assert 94.0 not in values.values()
    assert 46.0 not in values.values()


def test_52w_provider_is_point_in_time_bounded() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                ["2025-09-01", "2026-01-15", "2026-08-20", "2026-08-28", "2026-09-01"]
            ),
            "High": [120, 110, 130, 125, 999],
            "Low": [70, 60, 65, 62, 1],
            "Close": [100, 90, 120, 115, 500],
        }
    )
    candidates = load_52w_level_candidates(
        _HistoryConnection(frame[frame["Date"] <= pd.Timestamp("2026-08-28")]),
        ticker="MWG",
        as_of_date=date(2026, 8, 28),
    )
    values = {item.source_code: item.price for item in candidates}

    assert values["HIGH_52W"] == 130.0
    assert values["LOW_52W"] == 60.0
    assert 999.0 not in values.values()


def test_structural_family_improves_strength_without_changing_rank() -> None:
    baseline = build_level_ladder_from_data(
        current(),
        [candidate(95.0, "MA20_D")],
    )
    structural = candidate(
        95.1,
        "PREV_WEEK_LOW",
        indicator_code="",
        component_code="",
        source_family=SOURCE_FAMILY_MARKET_STRUCTURE,
    )
    structural = LevelCandidate(
        **{
            **structural.__dict__,
            "source_type": "STRUCTURAL",
            "indicator_code": None,
            "config_id": None,
            "config_code": None,
            "component_code": None,
            "confirmed_at": AS_OF,
            "metadata": {"structure_kind": "PREVIOUS_WEEK_LOW"},
        }
    )
    enhanced = build_level_ladder_from_data(
        current(),
        [candidate(95.0, "MA20_D"), structural],
        cluster_threshold_pct=0.01,
    )

    assert enhanced.support_levels[0].rank == baseline.support_levels[0].rank == "S1"
    assert enhanced.support_levels[0].strength_score > baseline.support_levels[0].strength_score
    assert enhanced.support_levels[0].source_family_count == 2

