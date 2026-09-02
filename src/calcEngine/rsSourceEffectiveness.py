"""R/S V2.4 Source Effectiveness and source-promotion calculations."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

import pandas as pd

try:
    from calcEngine.rsEvaluation import (
        EvaluationMetrics,
        LevelEvaluationEvent,
        aggregate_evaluation,
    )
    from calcEngine.rsSourceIdentity import canonical_source_key
except ModuleNotFoundError:
    from src.calcEngine.rsEvaluation import (
        EvaluationMetrics,
        LevelEvaluationEvent,
        aggregate_evaluation,
    )
    from src.calcEngine.rsSourceIdentity import canonical_source_key


ROLE_LEVEL = "LEVEL"
ROLE_CONTEXT = "CONTEXT"
ROLE_CONFIRMATION = "CONFIRMATION"

ATTRIBUTION_LEVEL_LINEAGE = "LEVEL_LINEAGE"
ATTRIBUTION_MARGINAL_ONLY = "MARGINAL_ONLY"
ATTRIBUTION_FAMILY_ABLATION = "FAMILY_ABLATION"


@dataclass(frozen=True)
class SourceEffectivenessPolicy:
    min_validation_events: int = 20
    min_test_events: int = 10
    core_threshold: float = 75.0
    supporting_threshold: float = 65.0
    research_threshold: float = 55.0
    min_core_validation_lift: float = 0.01
    min_nonnegative_test_lift: float = 0.0
    material_negative_test_lift: float = -0.01
    directional_edge_scale_pct: float = 20.0
    marginal_lift_scale: float = 0.05
    temporal_quality_scale: float = 0.10
    temporal_lift_scale: float = 0.05
    regime_range_scale: float = 0.20
    break_penalty_points: float = 10.0
    complexity_penalty_points: float = 20.0


@dataclass(frozen=True)
class SourceEffectivenessRecord:
    ticker: str
    scope_type: str
    source_key: str
    source_family: str
    source_role: str
    horizon_bars: int
    attribution_mode: str
    marginal_metric: str
    lineage_event_count: int
    validation_event_count: int
    test_event_count: int
    touch_rate: float | None
    hold_rate_given_touch: float | None
    break_rate_given_touch: float | None
    retest_rate_given_break: float | None
    directional_edge_pct: float | None
    validation_quality: float
    test_quality: float
    validation_marginal_lift: float
    test_marginal_lift: float
    temporal_stability: float
    regime_stability: float | None
    complexity_delta: float
    effectiveness_score: float
    recommendation: str
    evidence: Mapping[str, Any]


@dataclass(frozen=True)
class SourcePromotionPolicy:
    min_tickers: int = 3
    min_validation_events_per_ticker: int = 20
    min_test_events_per_ticker: int = 10
    min_positive_ticker_ratio: float = 0.60
    min_effectiveness_score: float = 65.0
    min_validation_lift: float = 0.01
    min_test_lift: float = 0.0
    min_temporal_stability: float = 0.70
    min_regime_stability: float = 0.60
    max_complexity_delta: float = 0.15
    max_negative_test_lift: float = -0.01


@dataclass(frozen=True)
class SourcePromotionDecision:
    outcome: str
    source_key: str
    source_family: str
    source_role: str
    horizon_bars: int
    ticker_count: int
    positive_ticker_count: int
    positive_ticker_ratio: float
    avg_effectiveness_score: float
    avg_validation_lift: float
    avg_test_lift: float
    avg_temporal_stability: float
    avg_regime_stability: float | None
    max_complexity_delta: float
    reasons: tuple[str, ...]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(float(value), high))


def _validate_policy(policy: SourceEffectivenessPolicy) -> None:
    if policy.min_validation_events < 0 or policy.min_test_events < 0:
        raise ValueError("minimum event counts must be >= 0")
    for value in (
        policy.core_threshold,
        policy.supporting_threshold,
        policy.research_threshold,
    ):
        if not 0 <= value <= 100:
            raise ValueError("recommendation thresholds must be in [0,100]")
    if not (policy.core_threshold >= policy.supporting_threshold >= policy.research_threshold):
        raise ValueError("thresholds must satisfy core >= supporting >= research")
    for value in (
        policy.directional_edge_scale_pct,
        policy.marginal_lift_scale,
        policy.temporal_quality_scale,
        policy.temporal_lift_scale,
        policy.regime_range_scale,
    ):
        if value <= 0:
            raise ValueError("effectiveness normalization scales must be > 0")


def _split_metrics(
    events: Sequence[LevelEvaluationEvent],
    split: str,
) -> EvaluationMetrics:
    return aggregate_evaluation([event for event in events if event.split == split])


def _events_for_source(
    events: Sequence[LevelEvaluationEvent],
    source_key: str,
) -> list[LevelEvaluationEvent]:
    key = canonical_source_key(source_key)
    result: list[LevelEvaluationEvent] = []
    for event in events:
        event_keys = {canonical_source_key(value) for value in event.sources}
        if key in event_keys:
            result.append(event)
    return result


def _events_for_family(
    events: Sequence[LevelEvaluationEvent],
    source_family: str,
) -> list[LevelEvaluationEvent]:
    family = str(source_family).upper()
    return [
        event
        for event in events
        if family in {str(value).upper() for value in event.source_families}
    ]


def strength_predictive_score(
    events: Sequence[LevelEvaluationEvent],
) -> float:
    """Brier-derived quality: does Strength predict hold after a touch?"""
    touched = [event for event in events if event.touched]
    if not touched:
        return 0.0
    squared_errors = []
    for event in touched:
        probability = _clamp(float(event.strength_score) / 100.0)
        actual = 1.0 if event.held else 0.0
        squared_errors.append((probability - actual) ** 2)
    return round(1.0 - sum(squared_errors) / len(squared_errors), 6)


def _split_strength_score(
    events: Sequence[LevelEvaluationEvent],
    split: str,
) -> float:
    return strength_predictive_score(
        [event for event in events if event.split == split]
    )


def _regime_strength_quality(
    events: Sequence[LevelEvaluationEvent],
) -> dict[str, float]:
    groups: dict[str, list[LevelEvaluationEvent]] = {}
    for event in events:
        if event.regime is None or event.split not in {"VALIDATION", "TEST"}:
            continue
        groups.setdefault(event.regime, []).append(event)
    return {
        key: strength_predictive_score(values)
        for key, values in sorted(groups.items())
        if values
    }


def _regime_quality(
    events: Sequence[LevelEvaluationEvent],
) -> dict[str, float]:
    groups: dict[str, list[LevelEvaluationEvent]] = {}
    for event in events:
        if event.regime is None or event.split not in {"VALIDATION", "TEST"}:
            continue
        groups.setdefault(event.regime, []).append(event)
    return {
        key: aggregate_evaluation(values).quality_score
        for key, values in sorted(groups.items())
        if values
    }


def _regime_lift(
    baseline: Sequence[LevelEvaluationEvent],
    ablation: Sequence[LevelEvaluationEvent],
) -> dict[str, float]:
    base = _regime_quality(baseline)
    drop = _regime_quality(ablation)
    return {key: base[key] - drop[key] for key in base.keys() & drop.keys()}


def _regime_stability(values: Mapping[str, float], scale: float) -> float | None:
    if len(values) < 2:
        return None
    spread = max(values.values()) - min(values.values())
    return round(1.0 - _clamp(spread / scale), 6)


def _temporal_stability(first: float, second: float, scale: float) -> float:
    return round(1.0 - _clamp(abs(first - second) / scale), 6)


def _weighted_available(components: Sequence[tuple[float | None, float]]) -> float:
    available = [(float(value), weight) for value, weight in components if value is not None]
    if not available:
        return 0.0
    weight_sum = sum(weight for _, weight in available)
    if weight_sum <= 0:
        return 0.0
    return sum(value * weight for value, weight in available) / weight_sum


def _recommend(
    *,
    role: str,
    score: float,
    validation_lift: float,
    test_lift: float,
    validation_events: int,
    test_events: int,
    policy: SourceEffectivenessPolicy,
) -> str:
    enough = (
        validation_events >= policy.min_validation_events
        and test_events >= policy.min_test_events
    )
    if test_lift < policy.material_negative_test_lift:
        return "DROP"
    if not enough:
        return "RESEARCH"

    if role == ROLE_LEVEL:
        if (
            score >= policy.core_threshold
            and validation_lift >= policy.min_core_validation_lift
            and test_lift >= policy.min_nonnegative_test_lift
        ):
            return "CORE"
        if score >= policy.supporting_threshold and test_lift >= policy.min_nonnegative_test_lift:
            return "SUPPORTING"
        return "RESEARCH" if score >= policy.research_threshold else "DROP"

    if role == ROLE_CONFIRMATION:
        if (
            score >= policy.supporting_threshold
            and validation_lift >= policy.min_core_validation_lift
            and test_lift >= policy.min_nonnegative_test_lift
        ):
            return "CONFIRM_ONLY"
        return "RESEARCH" if score >= policy.research_threshold else "DROP"

    if role == ROLE_CONTEXT:
        if (
            score >= policy.supporting_threshold
            and validation_lift >= policy.min_core_validation_lift
            and test_lift >= policy.min_nonnegative_test_lift
        ):
            return "CONTEXT_ONLY"
        return "RESEARCH" if score >= policy.research_threshold else "DROP"

    raise ValueError(f"unsupported source_role: {role}")


def calculate_source_effectiveness(
    *,
    ticker: str,
    scope_type: str,
    source_key: str,
    source_family: str,
    source_role: str,
    horizon_bars: int,
    baseline_events: Sequence[LevelEvaluationEvent],
    ablation_events: Sequence[LevelEvaluationEvent],
    complexity_delta: float = 0.0,
    attribution_mode: str | None = None,
    policy: SourceEffectivenessPolicy | None = None,
) -> SourceEffectivenessRecord:
    """Calculate one per-ticker/source/horizon V2.4 effectiveness record."""
    cfg = policy or SourceEffectivenessPolicy()
    _validate_policy(cfg)
    if horizon_bars <= 0:
        raise ValueError("horizon_bars must be > 0")
    role = str(source_role).upper()
    if role not in {ROLE_LEVEL, ROLE_CONTEXT, ROLE_CONFIRMATION}:
        raise ValueError(f"unsupported source_role: {source_role}")

    ticker_code = str(ticker).upper()
    baseline = [event for event in baseline_events if event.ticker.upper() == ticker_code]
    ablation = [event for event in ablation_events if event.ticker.upper() == ticker_code]

    base_val = _split_metrics(baseline, "VALIDATION")
    base_test = _split_metrics(baseline, "TEST")
    drop_val = _split_metrics(ablation, "VALIDATION")
    drop_test = _split_metrics(ablation, "TEST")

    if role == ROLE_CONFIRMATION:
        baseline_validation_quality = _split_strength_score(baseline, "VALIDATION")
        baseline_test_quality = _split_strength_score(baseline, "TEST")
        ablation_validation_quality = _split_strength_score(ablation, "VALIDATION")
        ablation_test_quality = _split_strength_score(ablation, "TEST")
        validation_lift = baseline_validation_quality - ablation_validation_quality
        test_lift = baseline_test_quality - ablation_test_quality
        marginal_metric = "STRENGTH_BRIER"
    else:
        baseline_validation_quality = base_val.quality_score
        baseline_test_quality = base_test.quality_score
        ablation_validation_quality = drop_val.quality_score
        ablation_test_quality = drop_test.quality_score
        validation_lift = baseline_validation_quality - ablation_validation_quality
        test_lift = baseline_test_quality - ablation_test_quality
        marginal_metric = "LEVEL_QUALITY"

    normalized_scope = str(scope_type).upper()
    mode = attribution_mode or (
        ATTRIBUTION_FAMILY_ABLATION
        if normalized_scope == "SOURCE_FAMILY"
        else (
            ATTRIBUTION_LEVEL_LINEAGE
            if role == ROLE_LEVEL
            else ATTRIBUTION_MARGINAL_ONLY
        )
    )

    touch_rate: float | None = None
    hold_rate: float | None = None
    break_rate: float | None = None
    retest_rate: float | None = None
    directional_edge: float | None = None
    lineage_count = 0

    if role == ROLE_LEVEL:
        lineage = (
            _events_for_family(baseline, source_family)
            if normalized_scope == "SOURCE_FAMILY"
            else _events_for_source(baseline, source_key)
        )
        lineage_oos = [event for event in lineage if event.split in {"VALIDATION", "TEST"}]
        lineage_val = _split_metrics(lineage, "VALIDATION")
        lineage_test = _split_metrics(lineage, "TEST")
        lineage_all = aggregate_evaluation(lineage_oos)
        lineage_count = len(lineage)
        touch_rate = lineage_all.touch_rate
        hold_rate = lineage_all.hold_rate_given_touch
        break_rate = lineage_all.break_rate_given_touch
        retest_rate = lineage_all.retest_rate_given_break
        directional_edge = lineage_all.directional_edge_pct
        temporal = _temporal_stability(
            lineage_val.quality_score,
            lineage_test.quality_score,
            cfg.temporal_quality_scale,
        )
        regimes = _regime_quality(lineage)
        regime_stability = _regime_stability(regimes, cfg.regime_range_scale)
        directional_score = _clamp(
            0.5 + float(directional_edge) / cfg.directional_edge_scale_pct
        )
        marginal_score = _clamp(
            0.5 + ((validation_lift + test_lift) / 2.0) / cfg.marginal_lift_scale
        )
        raw = _weighted_available(
            [
                (hold_rate, 0.25),
                (touch_rate, 0.15),
                (retest_rate, 0.10),
                (directional_score, 0.20),
                (temporal, 0.10),
                (regime_stability, 0.10),
                (marginal_score, 0.10),
            ]
        ) * 100.0
        raw -= float(break_rate or 0.0) * cfg.break_penalty_points
        val_events = lineage_val.event_count
        test_events = lineage_test.event_count
        validation_quality = lineage_val.quality_score
        test_quality = lineage_test.quality_score
        regime_evidence: Mapping[str, float] = regimes
    else:
        temporal = _temporal_stability(
            validation_lift,
            test_lift,
            cfg.temporal_lift_scale,
        )
        if role == ROLE_CONFIRMATION:
            base_regimes = _regime_strength_quality(baseline)
            drop_regimes = _regime_strength_quality(ablation)
            regime_lifts = {
                key: base_regimes[key] - drop_regimes[key]
                for key in base_regimes.keys() & drop_regimes.keys()
            }
        else:
            regime_lifts = _regime_lift(baseline, ablation)
        regime_stability = _regime_stability(regime_lifts, cfg.regime_range_scale)
        validation_score = _clamp(0.5 + validation_lift / cfg.marginal_lift_scale)
        test_score = _clamp(0.5 + test_lift / cfg.marginal_lift_scale)
        raw = _weighted_available(
            [
                (validation_score, 0.35),
                (test_score, 0.35),
                (temporal, 0.15),
                (regime_stability, 0.15),
            ]
        ) * 100.0
        val_events = min(base_val.event_count, drop_val.event_count)
        test_events = min(base_test.event_count, drop_test.event_count)
        validation_quality = baseline_validation_quality
        test_quality = baseline_test_quality
        regime_evidence = regime_lifts

    raw -= max(float(complexity_delta), 0.0) * cfg.complexity_penalty_points
    score = round(max(0.0, min(raw, 100.0)), 4)
    recommendation = _recommend(
        role=role,
        score=score,
        validation_lift=validation_lift,
        test_lift=test_lift,
        validation_events=val_events,
        test_events=test_events,
        policy=cfg,
    )

    return SourceEffectivenessRecord(
        ticker=ticker_code,
        scope_type=normalized_scope,
        source_key=canonical_source_key(source_key),
        source_family=str(source_family).upper(),
        source_role=role,
        horizon_bars=int(horizon_bars),
        attribution_mode=mode,
        marginal_metric=marginal_metric,
        lineage_event_count=lineage_count,
        validation_event_count=val_events,
        test_event_count=test_events,
        touch_rate=touch_rate,
        hold_rate_given_touch=hold_rate,
        break_rate_given_touch=break_rate,
        retest_rate_given_break=retest_rate,
        directional_edge_pct=directional_edge,
        validation_quality=round(validation_quality, 6),
        test_quality=round(test_quality, 6),
        validation_marginal_lift=round(validation_lift, 6),
        test_marginal_lift=round(test_lift, 6),
        temporal_stability=round(temporal, 6),
        regime_stability=regime_stability,
        complexity_delta=round(float(complexity_delta), 6),
        effectiveness_score=score,
        recommendation=recommendation,
        evidence={
            "regime_evidence": dict(regime_evidence),
            "policy": asdict(cfg),
        },
    )


def _validate_promotion_policy(policy: SourcePromotionPolicy) -> None:
    if policy.min_tickers <= 0:
        raise ValueError("min_tickers must be > 0")
    if (
        policy.min_validation_events_per_ticker < 0
        or policy.min_test_events_per_ticker < 0
    ):
        raise ValueError("promotion sample thresholds must be >= 0")
    for name in (
        "min_positive_ticker_ratio",
        "min_temporal_stability",
        "min_regime_stability",
    ):
        value = float(getattr(policy, name))
        if not 0 <= value <= 1:
            raise ValueError(f"{name} must be in [0,1]")
    if not 0 <= policy.min_effectiveness_score <= 100:
        raise ValueError("min_effectiveness_score must be in [0,100]")


def evaluate_source_promotion(
    records: Sequence[SourceEffectivenessRecord],
    *,
    policy: SourcePromotionPolicy | None = None,
) -> SourcePromotionDecision:
    """Evaluate cross-ticker readiness without mutating runtime configuration."""
    cfg = policy or SourcePromotionPolicy()
    _validate_promotion_policy(cfg)
    if not records:
        raise ValueError("records must be non-empty")
    first = records[0]
    for record in records:
        if (
            record.source_key != first.source_key
            or record.source_family != first.source_family
            or record.source_role != first.source_role
            or record.horizon_bars != first.horizon_bars
        ):
            raise ValueError("promotion records must describe one source/family/role/horizon")

    unique = {record.ticker: record for record in records}
    rows = list(unique.values())
    ticker_count = len(rows)

    def sample_ready(record: SourceEffectivenessRecord) -> bool:
        return (
            record.validation_event_count >= cfg.min_validation_events_per_ticker
            and record.test_event_count >= cfg.min_test_events_per_ticker
        )

    def positive(record: SourceEffectivenessRecord) -> bool:
        regime_ok = (
            record.regime_stability is not None
            and record.regime_stability >= cfg.min_regime_stability
        )
        return (
            sample_ready(record)
            and record.effectiveness_score >= cfg.min_effectiveness_score
            and record.validation_marginal_lift >= cfg.min_validation_lift
            and record.test_marginal_lift >= cfg.min_test_lift
            and record.temporal_stability >= cfg.min_temporal_stability
            and regime_ok
            and record.complexity_delta <= cfg.max_complexity_delta
        )

    positive_rows = [record for record in rows if positive(record)]
    positive_ratio = len(positive_rows) / ticker_count if ticker_count else 0.0
    avg_score = sum(record.effectiveness_score for record in rows) / ticker_count
    avg_val = sum(record.validation_marginal_lift for record in rows) / ticker_count
    avg_test = sum(record.test_marginal_lift for record in rows) / ticker_count
    avg_temporal = sum(record.temporal_stability for record in rows) / ticker_count
    regime_values = [
        record.regime_stability for record in rows if record.regime_stability is not None
    ]
    avg_regime = sum(regime_values) / len(regime_values) if regime_values else None
    max_complexity = max(record.complexity_delta for record in rows)

    reasons: list[str] = []
    severe_negative = any(
        record.test_marginal_lift < cfg.max_negative_test_lift for record in rows
    )
    all_samples_ready = all(sample_ready(record) for record in rows)
    any_regime_evidence = any(
        record.regime_stability is not None for record in rows
    )

    if ticker_count < cfg.min_tickers:
        outcome = "RESEARCH"
        reasons.append("insufficient ticker coverage")
    elif not all_samples_ready:
        outcome = "RESEARCH"
        reasons.append("insufficient per-ticker OOS sample")
    elif not any_regime_evidence:
        outcome = "RESEARCH"
        reasons.append("insufficient regime breadth")
    elif (
        positive_ratio >= cfg.min_positive_ticker_ratio
        and not severe_negative
        and avg_val >= cfg.min_validation_lift
        and avg_test >= cfg.min_test_lift
        and max_complexity <= cfg.max_complexity_delta
    ):
        outcome = "APPROVED_FOR_INTEGRATION"
    elif positive_rows:
        outcome = "TICKER_SELECTIVE"
        if positive_ratio < cfg.min_positive_ticker_ratio:
            reasons.append("positive ticker ratio below global threshold")
        if severe_negative:
            reasons.append("material negative TEST lift exists on at least one ticker")
    else:
        outcome = "REJECTED"
        reasons.append("no ticker satisfies source-promotion evidence thresholds")

    return SourcePromotionDecision(
        outcome=outcome,
        source_key=first.source_key,
        source_family=first.source_family,
        source_role=first.source_role,
        horizon_bars=first.horizon_bars,
        ticker_count=ticker_count,
        positive_ticker_count=len(positive_rows),
        positive_ticker_ratio=round(positive_ratio, 6),
        avg_effectiveness_score=round(avg_score, 6),
        avg_validation_lift=round(avg_val, 6),
        avg_test_lift=round(avg_test, 6),
        avg_temporal_stability=round(avg_temporal, 6),
        avg_regime_stability=round(avg_regime, 6) if avg_regime is not None else None,
        max_complexity_delta=round(max_complexity, 6),
        reasons=tuple(reasons),
    )


def effectiveness_to_dataframe(
    effectiveness_run_id: str,
    records: Sequence[SourceEffectivenessRecord],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in records:
        row = asdict(record)
        row["EffectivenessRunId"] = effectiveness_run_id
        row["EvidenceJson"] = json.dumps(row.pop("evidence"), sort_keys=True, default=str)
        rows.append(
            {
                "EffectivenessRunId": row["EffectivenessRunId"],
                "Ticker": row["ticker"],
                "ScopeType": row["scope_type"],
                "SourceKey": row["source_key"],
                "SourceFamily": row["source_family"],
                "SourceRole": row["source_role"],
                "HorizonBars": row["horizon_bars"],
                "AttributionMode": row["attribution_mode"],
                "MarginalMetric": row["marginal_metric"],
                "LineageEventCount": row["lineage_event_count"],
                "ValidationEventCount": row["validation_event_count"],
                "TestEventCount": row["test_event_count"],
                "TouchRate": row["touch_rate"],
                "HoldRateGivenTouch": row["hold_rate_given_touch"],
                "BreakRateGivenTouch": row["break_rate_given_touch"],
                "RetestRateGivenBreak": row["retest_rate_given_break"],
                "DirectionalEdgePct": row["directional_edge_pct"],
                "ValidationQuality": row["validation_quality"],
                "TestQuality": row["test_quality"],
                "ValidationMarginalLift": row["validation_marginal_lift"],
                "TestMarginalLift": row["test_marginal_lift"],
                "TemporalStability": row["temporal_stability"],
                "RegimeStability": row["regime_stability"],
                "ComplexityDelta": row["complexity_delta"],
                "EffectivenessScore": row["effectiveness_score"],
                "Recommendation": row["recommendation"],
                "EvidenceJson": row["EvidenceJson"],
            }
        )
    return pd.DataFrame(rows)


def promotion_decision_json(decision: SourcePromotionDecision) -> str:
    return json.dumps(asdict(decision), sort_keys=True, default=str)
