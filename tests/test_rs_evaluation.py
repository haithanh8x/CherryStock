from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from src.calcEngine.levelLadder import (
    LevelLadderResult,
    NormalizedLevel,
    RankedLevel,
)
from src.calcEngine.rsEvaluation import (
    EvaluationConfig,
    EvaluationMetrics,
    PromotionPolicy,
    RSModelSpec,
    aggregate_evaluation,
    assign_temporal_splits,
    build_ablation_variants,
    calculate_complexity_score,
    classify_market_regime,
    evaluate_ladder_result,
    evaluate_ranked_level,
    events_to_dataframe,
    metrics_to_dataframe,
    promotion_gate,
    rank_calibration_candidates,
    validate_golden_ladder_invariants,
)


AS_OF = date(2026, 1, 1)


def _source(price: float, code: str = "MA20_D") -> NormalizedLevel:
    return NormalizedLevel(
        price=price,
        source_type="INDICATOR",
        source_code=code,
        timeframe="D",
        weight=1.0,
        source_date=AS_OF,
        confirmed_at=AS_OF,
        config_id=1,
        config_code=code,
        component_code="VALUE",
        source_role="LEVEL",
        source_family="TREND_AVERAGE",
        value_semantic="PRICE_LEVEL",
        metadata={},
    )


def _level(
    price: float,
    *,
    rank: str = "S1",
    level_type: str = "SUPPORT",
) -> RankedLevel:
    source = _source(price)
    return RankedLevel(
        rank=rank,
        level_type=level_type,
        price=price,
        price_low=price,
        price_high=price,
        distance_pct=-5.0 if level_type == "SUPPORT" else 5.0,
        strength_score=70.0,
        source_count=1,
        source_family_count=1,
        sources=(source,),
    )


def _metrics(
    quality: float,
    *,
    events: int = 300,
) -> EvaluationMetrics:
    return EvaluationMetrics(
        event_count=events,
        touch_count=int(events * 0.6),
        break_count=int(events * 0.2),
        retest_count=int(events * 0.1),
        hold_count=int(events * 0.4),
        touch_rate=0.6,
        break_rate_given_touch=0.333333,
        retest_rate_given_break=0.5,
        hold_rate_given_touch=0.666667,
        avg_bars_to_touch=5.0,
        avg_favorable_pct=8.0,
        avg_adverse_pct=4.0,
        directional_edge_pct=4.0,
        quality_score=quality,
    )


def test_support_touch_hold_event() -> None:
    future = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-06"]),
            "High": [102.0, 104.0, 103.0],
            "Low": [99.6, 100.5, 100.2],
            "Close": [101.0, 103.0, 102.0],
        }
    )
    event = evaluate_ranked_level(
        model_version="M1",
        ticker="MWG",
        as_of_date=AS_OF,
        level=_level(100.0),
        future_history=future,
        config=EvaluationConfig(horizon_bars=3),
    )

    assert event.touched is True
    assert event.held is True
    assert event.broken is False
    assert event.touch_date == date(2026, 1, 2)
    assert event.bars_to_touch == 1
    assert event.max_favorable_pct > 0


def test_support_break_and_retest_event() -> None:
    future = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                ["2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07"]
            ),
            "High": [101.0, 100.5, 100.4, 99.0],
            "Low": [99.7, 97.5, 99.6, 96.0],
            "Close": [100.2, 98.0, 100.0, 97.0],
        }
    )
    event = evaluate_ranked_level(
        model_version="M1",
        ticker="MWG",
        as_of_date=AS_OF,
        level=_level(100.0),
        future_history=future,
        config=EvaluationConfig(horizon_bars=4),
    )

    assert event.touched is True
    assert event.broken is True
    assert event.break_date == date(2026, 1, 5)
    assert event.retested is True
    assert event.retest_date == date(2026, 1, 6)
    assert event.held is False


def test_aggregate_metrics_is_deterministic() -> None:
    future = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-02", "2026-01-05"]),
            "High": [101.0, 102.0],
            "Low": [99.8, 100.0],
            "Close": [100.5, 101.0],
        }
    )
    event = evaluate_ranked_level(
        model_version="M1",
        ticker="MWG",
        as_of_date=AS_OF,
        level=_level(100.0),
        future_history=future,
    )
    first = aggregate_evaluation([event])
    second = aggregate_evaluation([event])

    assert first == second
    assert first.event_count == 1
    assert first.touch_rate == 1.0
    assert first.hold_rate_given_touch == 1.0
    assert 0 <= first.quality_score <= 1


def test_temporal_split_is_chronological() -> None:
    dates = [date(2026, 1, day) for day in range(1, 11)]
    split = assign_temporal_splits(dates)

    assert [split[value] for value in dates[:6]] == ["TRAIN"] * 6
    assert [split[value] for value in dates[6:8]] == ["VALIDATION"] * 2
    assert [split[value] for value in dates[8:]] == ["TEST"] * 2


def test_regime_classification_does_not_use_future_rows() -> None:
    past_dates = pd.date_range("2025-10-01", periods=60, freq="B")
    frame = pd.DataFrame(
        {
            "Date": list(past_dates) + [pd.Timestamp("2026-12-31")],
            "High": [101.0] * 60 + [1000.0],
            "Low": [99.0] * 60 + [1.0],
            "Close": [100.0] * 60 + [999.0],
        }
    )

    regime = classify_market_regime(
        frame,
        as_of_date=past_dates[-1].date(),
        config=EvaluationConfig(regime_lookback_bars=60),
    )

    assert regime == "RANGE_LOW_VOL"


def test_ablation_variants_cover_source_and_family_removal() -> None:
    variants = build_ablation_variants(
        ("MA", "BB", "ATR"),
        {
            "MA": "TREND_AVERAGE",
            "BB": "VOLATILITY_BAND",
            "ATR": "VOLATILITY_CONTEXT",
        },
    )
    codes = {variant.code for variant in variants}

    assert "FULL" in codes
    assert "DROP_SOURCE_MA" in codes
    assert "DROP_FAMILY_TREND_AVERAGE" in codes
    assert next(v for v in variants if v.code == "DROP_SOURCE_MA").enabled_sources == (
        "ATR",
        "BB",
    )


def test_model_signature_is_order_independent_for_sources() -> None:
    first = RSModelSpec("M1", ("MA", "BB", "ATR"))
    second = RSModelSpec("M1", ("ATR", "MA", "BB"))

    assert first.signature == second.signature
    assert first.canonical_json() == second.canonical_json()


def test_calibration_ranking_applies_complexity_penalty() -> None:
    simple = RSModelSpec("SIMPLE", ("MA", "BB"))
    complex_model = RSModelSpec(
        "COMPLEX",
        ("MA", "BB", "ATR", "RSI", "SWING", "VOLUME_PROFILE"),
        strength_config={"confirmation_weight": 0.12},
    )
    ranked = rank_calibration_candidates(
        [simple, complex_model],
        {
            "SIMPLE": _metrics(0.70),
            "COMPLEX": _metrics(0.705),
        },
        complexity_lambda=0.20,
    )

    assert ranked[0].model_version == "SIMPLE"
    assert calculate_complexity_score(complex_model) > calculate_complexity_score(simple)


def test_promotion_gate_accepts_incremental_challenger() -> None:
    baseline = RSModelSpec("BASE", ("MA", "BB"))
    challenger = RSModelSpec("CHAL", ("MA", "BB", "ATR"))
    decision = promotion_gate(
        baseline=baseline,
        challenger=challenger,
        baseline_validation=_metrics(0.50),
        challenger_validation=_metrics(0.54),
        baseline_test=_metrics(0.50),
        challenger_test=_metrics(0.51),
        baseline_regime_quality={"BULL_LOW_VOL": 0.50, "BEAR_HIGH_VOL": 0.45},
        challenger_regime_quality={"BULL_LOW_VOL": 0.53, "BEAR_HIGH_VOL": 0.43},
        policy=PromotionPolicy(
            min_validation_events=100,
            min_test_events=100,
            min_validation_quality_delta=0.02,
            min_test_quality_delta=0.0,
            max_regime_quality_degradation=0.05,
            max_complexity_delta=0.10,
        ),
    )

    assert decision.promote is True
    assert decision.reasons == ()


def test_promotion_gate_rejects_validation_regression() -> None:
    baseline = RSModelSpec("BASE", ("MA", "BB"))
    challenger = RSModelSpec("CHAL", ("MA", "BB", "ATR"))
    decision = promotion_gate(
        baseline=baseline,
        challenger=challenger,
        baseline_validation=_metrics(0.55),
        challenger_validation=_metrics(0.54),
        baseline_test=_metrics(0.50),
        challenger_test=_metrics(0.51),
        policy=PromotionPolicy(
            min_validation_events=100,
            min_test_events=100,
            min_validation_quality_delta=0.0,
            min_test_quality_delta=0.0,
        ),
    )

    assert decision.promote is False
    assert "validation quality delta below threshold" in decision.reasons


def test_golden_invariants_pass_for_well_formed_ladder() -> None:
    support = _level(95.0, rank="S1", level_type="SUPPORT")
    resistance = _level(105.0, rank="R1", level_type="RESISTANCE")
    result = LevelLadderResult(
        ticker="MWG",
        as_of_date=AS_OF,
        current_price=100.0,
        resistance_levels=(resistance,),
        support_levels=(support,),
        nearest_support=support,
        nearest_resistance=resistance,
        upside_to_r1_pct=5.0,
        downside_to_s1_pct=5.0,
        risk_reward_ratio=1.0,
        model_version="M1",
    )

    check = validate_golden_ladder_invariants(result)

    assert check.passed is True
    assert check.errors == ()


def test_event_and_metric_dataframe_contracts() -> None:
    future = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-02", "2026-01-05"]),
            "High": [101.0, 102.0],
            "Low": [99.8, 100.0],
            "Close": [100.5, 101.0],
        }
    )
    event = evaluate_ranked_level(
        model_version="M1",
        ticker="MWG",
        as_of_date=AS_OF,
        level=_level(100.0),
        future_history=future,
        regime="RANGE_LOW_VOL",
        split="VALIDATION",
    )

    event_df = events_to_dataframe("RUN1", [event])
    metric_df = metrics_to_dataframe("RUN1", [event])

    assert event_df.iloc[0]["EvaluationRunId"] == "RUN1"
    assert event_df.iloc[0]["SourcesJson"] == '["MA20_D"]'
    assert set(metric_df["ScopeType"]) >= {"OVERALL", "SPLIT", "TICKER", "REGIME"}
    assert "quality_score" in set(metric_df["MetricCode"])


def test_evaluate_ladder_result_labels_both_sides() -> None:
    support = _level(95.0, rank="S1", level_type="SUPPORT")
    resistance = _level(105.0, rank="R1", level_type="RESISTANCE")
    result = SimpleNamespace(
        ticker="MWG",
        as_of_date=AS_OF,
        support_levels=(support,),
        resistance_levels=(resistance,),
    )
    future = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-02", "2026-01-05"]),
            "High": [106.0, 107.0],
            "Low": [94.5, 96.0],
            "Close": [100.0, 101.0],
        }
    )

    events = evaluate_ladder_result(
        model_version="M1",
        result=result,
        future_history=future,
    )

    assert {event.level_type for event in events} == {"SUPPORT", "RESISTANCE"}
