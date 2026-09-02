from datetime import date
from types import SimpleNamespace

import pytest

from src.calcEngine.rsEvaluation import LevelEvaluationEvent, RSModelSpec
from src.calcEngine.rsSourceEffectiveness import (
    SourceEffectivenessPolicy,
    SourceEffectivenessRecord,
    SourcePromotionPolicy,
    calculate_source_effectiveness,
    effectiveness_to_dataframe,
    evaluate_source_promotion,
)
from src.calcEngine.rsSourceIdentity import (
    canonical_source_key,
    filter_source_objects,
    normalize_source_key_set,
)


def _event(
    *,
    ticker: str = "MWG",
    split: str,
    regime: str,
    quality_case: str = "good",
    strength_score: float = 70.0,
    sources: tuple[str, ...] = ("MA50_D",),
    families: tuple[str, ...] = ("TREND_AVERAGE",),
) -> LevelEvaluationEvent:
    if quality_case == "good":
        touched, broken, retested, held = True, False, False, True
        favorable, adverse = 8.0, 2.0
    elif quality_case == "break":
        touched, broken, retested, held = True, True, True, False
        favorable, adverse = 2.0, 8.0
    else:
        touched, broken, retested, held = False, False, False, False
        favorable, adverse = 0.0, 0.0

    return LevelEvaluationEvent(
        model_version="M",
        ticker=ticker,
        as_of_date=date(2026, 1, 1),
        level_rank="S1",
        level_type="SUPPORT",
        level_price=100.0,
        strength_score=strength_score,
        horizon_end_date=date(2026, 1, 30),
        touched=touched,
        touch_date=date(2026, 1, 5) if touched else None,
        broken=broken,
        break_date=date(2026, 1, 8) if broken else None,
        retested=retested,
        retest_date=date(2026, 1, 10) if retested else None,
        held=held,
        bars_to_touch=2 if touched else None,
        max_favorable_pct=favorable,
        max_adverse_pct=adverse,
        source_count=len(sources),
        source_family_count=len(set(families)),
        sources=sources,
        source_families=families,
        regime=regime,
        split=split,
    )


def _events(
    ticker: str,
    *,
    source: str = "MA50_D",
    quality_case: str = "good",
    strength_score: float = 70.0,
) -> list[LevelEvaluationEvent]:
    result = []
    for split in ("VALIDATION", "TEST"):
        for regime in ("BULL_LOW_VOL", "RANGE_HIGH_VOL"):
            for _ in range(3):
                result.append(
                    _event(
                        ticker=ticker,
                        split=split,
                        regime=regime,
                        quality_case=quality_case,
                        strength_score=strength_score,
                        sources=(source,),
                    )
                )
    return result


def _record(
    ticker: str,
    *,
    score: float = 80.0,
    validation_lift: float = 0.03,
    test_lift: float = 0.02,
    temporal: float = 0.9,
    regime: float | None = 0.85,
    complexity: float = 0.02,
) -> SourceEffectivenessRecord:
    return SourceEffectivenessRecord(
        ticker=ticker,
        scope_type="SOURCE_CONFIG",
        source_key="MA50_D",
        source_family="TREND_AVERAGE",
        source_role="LEVEL",
        horizon_bars=20,
        attribution_mode="LEVEL_LINEAGE",
        marginal_metric="LEVEL_QUALITY",
        lineage_event_count=20,
        validation_event_count=20,
        test_event_count=10,
        touch_rate=0.7,
        hold_rate_given_touch=0.8,
        break_rate_given_touch=0.2,
        retest_rate_given_break=0.4,
        directional_edge_pct=5.0,
        validation_quality=0.7,
        test_quality=0.69,
        validation_marginal_lift=validation_lift,
        test_marginal_lift=test_lift,
        temporal_stability=temporal,
        regime_stability=regime,
        complexity_delta=complexity,
        effectiveness_score=score,
        recommendation="CORE",
        evidence={},
    )


def test_canonical_source_identity_normalizes_dynamic_codes() -> None:
    assert canonical_source_key("swing_high_20260820") == "SWING_HIGH"
    assert canonical_source_key("VP_HVN_02") == "VP_HVN"
    assert canonical_source_key("VP_LVN_01_CONF") == "VP_LVN"
    assert canonical_source_key("BB20_2_D:LOWER") == "BB20_2_D:LOWER"


def test_source_filter_applies_include_and_exclude() -> None:
    values = [
        SimpleNamespace(source_code="MA20_D"),
        SimpleNamespace(source_code="MA50_D"),
        SimpleNamespace(source_code="SWING_HIGH_20260820"),
    ]

    included = filter_source_objects(values, included_source_keys=("MA50_D",))
    excluded = filter_source_objects(values, excluded_source_keys=("SWING_HIGH",))

    assert [x.source_code for x in included] == ["MA50_D"]
    assert [x.source_code for x in excluded] == ["MA20_D", "MA50_D"]


def test_source_filter_rejects_overlap() -> None:
    with pytest.raises(ValueError, match="both included and excluded"):
        filter_source_objects(
            [SimpleNamespace(source_code="MA50_D")],
            included_source_keys=("MA50_D",),
            excluded_source_keys=("ma50_d",),
        )


def test_normalize_source_key_set_is_deterministic() -> None:
    assert normalize_source_key_set(("vp_hvn_02", "MA50_D", "vp_hvn_01")) == (
        "MA50_D",
        "VP_HVN",
    )


def test_model_signature_changes_when_source_filter_changes() -> None:
    baseline = RSModelSpec("M", ("MA",))
    filtered = RSModelSpec("M", ("MA",), excluded_source_keys=("MA50_D",))

    assert baseline.signature != filtered.signature


def test_level_effectiveness_uses_lineage_and_is_bounded() -> None:
    baseline = _events("MWG", quality_case="good")
    ablation = _events("MWG", quality_case="break")
    record = calculate_source_effectiveness(
        ticker="MWG",
        scope_type="SOURCE_CONFIG",
        source_key="MA50_D",
        source_family="TREND_AVERAGE",
        source_role="LEVEL",
        horizon_bars=20,
        baseline_events=baseline,
        ablation_events=ablation,
        policy=SourceEffectivenessPolicy(
            min_validation_events=1,
            min_test_events=1,
        ),
    )

    assert record.lineage_event_count == len(baseline)
    assert record.touch_rate is not None
    assert record.hold_rate_given_touch is not None
    assert 0 <= record.effectiveness_score <= 100
    assert record.validation_marginal_lift > 0
    assert record.test_marginal_lift > 0


def test_confirmation_effectiveness_does_not_fabricate_level_metrics() -> None:
    baseline = _events(
        "MWG",
        source="MA50_D",
        quality_case="good",
        strength_score=90.0,
    )
    ablation = _events(
        "MWG",
        source="MA50_D",
        quality_case="good",
        strength_score=50.0,
    )
    record = calculate_source_effectiveness(
        ticker="MWG",
        scope_type="SOURCE_CONFIG",
        source_key="RSI14_D",
        source_family="MOMENTUM_CONFIRMATION",
        source_role="CONFIRMATION",
        horizon_bars=20,
        baseline_events=baseline,
        ablation_events=ablation,
        policy=SourceEffectivenessPolicy(
            min_validation_events=1,
            min_test_events=1,
            supporting_threshold=40,
            research_threshold=30,
            core_threshold=50,
            min_core_validation_lift=0.0,
        ),
    )

    assert record.marginal_metric == "STRENGTH_BRIER"
    assert record.validation_marginal_lift > 0
    assert record.test_marginal_lift > 0
    assert record.touch_rate is None
    assert record.hold_rate_given_touch is None
    assert record.break_rate_given_touch is None
    assert record.retest_rate_given_break is None
    assert record.directional_edge_pct is None
    assert record.recommendation == "CONFIRM_ONLY"


def test_context_effectiveness_preserves_context_role() -> None:
    baseline = _events("MWG", quality_case="good")
    ablation = _events("MWG", quality_case="break")
    record = calculate_source_effectiveness(
        ticker="MWG",
        scope_type="SOURCE_CONFIG",
        source_key="ATR14_D",
        source_family="VOLATILITY_CONTEXT",
        source_role="CONTEXT",
        horizon_bars=20,
        baseline_events=baseline,
        ablation_events=ablation,
        policy=SourceEffectivenessPolicy(
            min_validation_events=1,
            min_test_events=1,
            supporting_threshold=40,
            research_threshold=30,
            core_threshold=50,
            min_core_validation_lift=0.0,
        ),
    )

    assert record.source_role == "CONTEXT"
    assert record.recommendation == "CONTEXT_ONLY"


def test_material_negative_test_lift_forces_drop() -> None:
    baseline = _events("MWG", quality_case="break")
    ablation = _events("MWG", quality_case="good")
    record = calculate_source_effectiveness(
        ticker="MWG",
        scope_type="SOURCE_CONFIG",
        source_key="MA50_D",
        source_family="TREND_AVERAGE",
        source_role="LEVEL",
        horizon_bars=20,
        baseline_events=baseline,
        ablation_events=ablation,
        policy=SourceEffectivenessPolicy(
            min_validation_events=1,
            min_test_events=1,
            material_negative_test_lift=-0.001,
        ),
    )

    assert record.test_marginal_lift < 0
    assert record.recommendation == "DROP"


def test_source_family_scope_uses_family_lineage() -> None:
    baseline = _events("MWG", source="MA20_D", quality_case="good") + _events(
        "MWG", source="MA50_D", quality_case="good"
    )
    ablation = _events("MWG", source="BB20_2_D:LOWER", quality_case="break")
    record = calculate_source_effectiveness(
        ticker="MWG",
        scope_type="SOURCE_FAMILY",
        source_key="TREND_AVERAGE",
        source_family="TREND_AVERAGE",
        source_role="LEVEL",
        horizon_bars=20,
        baseline_events=baseline,
        ablation_events=ablation,
        policy=SourceEffectivenessPolicy(
            min_validation_events=1,
            min_test_events=1,
        ),
    )

    assert record.attribution_mode == "FAMILY_ABLATION"
    assert record.lineage_event_count == len(baseline)


def test_promotion_gate_approves_broad_positive_evidence() -> None:
    decision = evaluate_source_promotion(
        [_record("MWG"), _record("FPT"), _record("HPG")],
        policy=SourcePromotionPolicy(
            min_tickers=3,
            min_positive_ticker_ratio=0.60,
        ),
    )

    assert decision.outcome == "APPROVED_FOR_INTEGRATION"
    assert decision.positive_ticker_count == 3


def test_promotion_gate_returns_ticker_selective() -> None:
    decision = evaluate_source_promotion(
        [
            _record("MWG"),
            _record("FPT", score=50, validation_lift=0.0, test_lift=-0.02),
            _record("HPG", score=50, validation_lift=0.0, test_lift=-0.02),
        ],
        policy=SourcePromotionPolicy(
            min_tickers=3,
            min_positive_ticker_ratio=0.80,
        ),
    )

    assert decision.outcome == "TICKER_SELECTIVE"


def test_promotion_gate_is_research_when_ticker_coverage_is_insufficient() -> None:
    decision = evaluate_source_promotion([_record("MWG")])

    assert decision.outcome == "RESEARCH"
    assert "insufficient ticker coverage" in decision.reasons


def test_effectiveness_dataframe_has_persistence_contract() -> None:
    dataframe = effectiveness_to_dataframe("RUN1", [_record("MWG")])

    assert dataframe.iloc[0]["EffectivenessRunId"] == "RUN1"
    assert dataframe.iloc[0]["SourceKey"] == "MA50_D"
    assert dataframe.iloc[0]["Recommendation"] == "CORE"
    assert dataframe.iloc[0]["MarginalMetric"] == "LEVEL_QUALITY"
    assert "EvidenceJson" in dataframe.columns
