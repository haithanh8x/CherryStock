"""Historical evaluation and model-governance utilities for R/S V2.3.

The module is intentionally calculation-first: event labeling, metrics, temporal
splits, regime classification, ablation metadata and promotion decisions are
pure and deterministic. DuckDB persistence is handled by explicit callers.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


@dataclass(frozen=True)
class EvaluationConfig:
    horizon_bars: int = 20
    touch_tolerance_pct: float = 0.005
    break_tolerance_pct: float = 0.005
    retest_tolerance_pct: float = 0.005
    regime_lookback_bars: int = 60
    regime_trend_threshold_pct: float = 0.08
    regime_high_vol_threshold: float = 0.025


@dataclass(frozen=True)
class TemporalSplitConfig:
    train_ratio: float = 0.60
    validation_ratio: float = 0.20
    test_ratio: float = 0.20


@dataclass(frozen=True)
class RSModelSpec:
    model_version: str
    enabled_sources: tuple[str, ...]
    strength_config: Mapping[str, Any] = field(default_factory=dict)
    volume_profile_config: Mapping[str, Any] = field(default_factory=dict)
    structural_config: Mapping[str, Any] = field(default_factory=dict)
    parent_version: str | None = None
    notes: str | None = None

    def canonical_json(self) -> str:
        payload = asdict(self)
        payload["enabled_sources"] = sorted(self.enabled_sources)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    @property
    def signature(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class LevelEvaluationEvent:
    model_version: str
    ticker: str
    as_of_date: date
    level_rank: str
    level_type: str
    level_price: float
    strength_score: float
    horizon_end_date: date | None
    touched: bool
    touch_date: date | None
    broken: bool
    break_date: date | None
    retested: bool
    retest_date: date | None
    held: bool
    bars_to_touch: int | None
    max_favorable_pct: float
    max_adverse_pct: float
    source_count: int
    source_family_count: int
    sources: tuple[str, ...]
    source_families: tuple[str, ...]
    regime: str | None = None
    split: str | None = None


@dataclass(frozen=True)
class EvaluationMetrics:
    event_count: int
    touch_count: int
    break_count: int
    retest_count: int
    hold_count: int
    touch_rate: float
    break_rate_given_touch: float
    retest_rate_given_break: float
    hold_rate_given_touch: float
    avg_bars_to_touch: float | None
    avg_favorable_pct: float
    avg_adverse_pct: float
    directional_edge_pct: float
    quality_score: float


@dataclass(frozen=True)
class AblationVariant:
    code: str
    enabled_sources: tuple[str, ...]
    removed_sources: tuple[str, ...] = ()
    removed_families: tuple[str, ...] = ()


@dataclass(frozen=True)
class PromotionPolicy:
    min_validation_events: int = 200
    min_test_events: int = 100
    min_validation_quality_delta: float = 0.02
    min_test_quality_delta: float = 0.0
    max_regime_quality_degradation: float = 0.05
    max_complexity_delta: float = 0.15


@dataclass(frozen=True)
class PromotionDecision:
    promote: bool
    baseline_version: str
    challenger_version: str
    validation_quality_delta: float
    test_quality_delta: float
    complexity_delta: float
    worst_regime_delta: float
    reasons: tuple[str, ...]


def _validate_eval_config(config: EvaluationConfig) -> None:
    if config.horizon_bars <= 0:
        raise ValueError("horizon_bars must be > 0")
    for name in (
        "touch_tolerance_pct",
        "break_tolerance_pct",
        "retest_tolerance_pct",
    ):
        value = float(getattr(config, name))
        if not 0 <= value <= 0.10:
            raise ValueError(f"{name} must be between 0 and 0.10")
    if config.regime_lookback_bars < 10:
        raise ValueError("regime_lookback_bars must be >= 10")
    if config.regime_trend_threshold_pct < 0:
        raise ValueError("regime_trend_threshold_pct must be >= 0")
    if config.regime_high_vol_threshold < 0:
        raise ValueError("regime_high_vol_threshold must be >= 0")


def _prepare_history(history: pd.DataFrame) -> pd.DataFrame:
    required = {"Date", "High", "Low", "Close"}
    missing = required - set(history.columns)
    if missing:
        raise ValueError(f"history missing columns: {sorted(missing)}")
    frame = history.loc[:, ["Date", "High", "Low", "Close"]].copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    for col in ("High", "Low", "Close"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return (
        frame.dropna(subset=["Date", "High", "Low", "Close"])
        .sort_values("Date")
        .reset_index(drop=True)
    )


def classify_market_regime(
    history: pd.DataFrame,
    *,
    as_of_date: date,
    config: EvaluationConfig | None = None,
) -> str:
    """Classify regime using only data available at/before as_of_date."""
    cfg = config or EvaluationConfig()
    _validate_eval_config(cfg)
    frame = _prepare_history(history)
    frame = frame[frame["Date"].dt.date <= as_of_date]
    if len(frame) < cfg.regime_lookback_bars:
        return "UNKNOWN"

    window = frame.iloc[-cfg.regime_lookback_bars :]
    first_close = float(window["Close"].iloc[0])
    last_close = float(window["Close"].iloc[-1])
    if first_close <= 0:
        return "UNKNOWN"

    trend = last_close / first_close - 1.0
    returns = window["Close"].pct_change().dropna()
    volatility = float(returns.std(ddof=0)) if not returns.empty else 0.0
    high_vol = volatility >= cfg.regime_high_vol_threshold

    if trend >= cfg.regime_trend_threshold_pct:
        direction = "BULL"
    elif trend <= -cfg.regime_trend_threshold_pct:
        direction = "BEAR"
    else:
        direction = "RANGE"
    return f"{direction}_{'HIGH_VOL' if high_vol else 'LOW_VOL'}"


def _future_window(
    history: pd.DataFrame,
    *,
    as_of_date: date,
    horizon_bars: int,
) -> pd.DataFrame:
    frame = _prepare_history(history)
    future = frame[frame["Date"].dt.date > as_of_date]
    return future.iloc[:horizon_bars].reset_index(drop=True)


def evaluate_ranked_level(
    *,
    model_version: str,
    ticker: str,
    as_of_date: date,
    level: Any,
    future_history: pd.DataFrame,
    config: EvaluationConfig | None = None,
    regime: str | None = None,
    split: str | None = None,
) -> LevelEvaluationEvent:
    """Label one ranked S/R level over a forward horizon."""
    cfg = config or EvaluationConfig()
    _validate_eval_config(cfg)
    if level.level_type not in {"SUPPORT", "RESISTANCE"}:
        raise ValueError("level_type must be SUPPORT or RESISTANCE")

    future = _future_window(
        future_history,
        as_of_date=as_of_date,
        horizon_bars=cfg.horizon_bars,
    )
    price = float(level.price)
    if not math.isfinite(price) or price <= 0:
        raise ValueError("level price must be finite and > 0")

    touch_low = price * (1.0 - cfg.touch_tolerance_pct)
    touch_high = price * (1.0 + cfg.touch_tolerance_pct)

    touch_idx: int | None = None
    break_idx: int | None = None
    retest_idx: int | None = None

    for idx, row in future.iterrows():
        high = float(row["High"])
        low = float(row["Low"])
        close = float(row["Close"])
        touches = low <= touch_high and high >= touch_low
        if touch_idx is None and touches:
            touch_idx = int(idx)

        if touch_idx is not None and idx >= touch_idx and break_idx is None:
            if level.level_type == "SUPPORT":
                broken = close < price * (1.0 - cfg.break_tolerance_pct)
            else:
                broken = close > price * (1.0 + cfg.break_tolerance_pct)
            if broken:
                break_idx = int(idx)
                continue

        if break_idx is not None and idx > break_idx and retest_idx is None and touches:
            retest_idx = int(idx)

    def date_at(index: int | None) -> date | None:
        if index is None:
            return None
        return pd.Timestamp(future.iloc[index]["Date"]).date()

    observed = future.iloc[touch_idx:] if touch_idx is not None else future.iloc[0:0]
    if observed.empty:
        favorable = 0.0
        adverse = 0.0
    elif level.level_type == "SUPPORT":
        favorable = max(float(observed["High"].max()) / price - 1.0, 0.0) * 100.0
        adverse = max(1.0 - float(observed["Low"].min()) / price, 0.0) * 100.0
    else:
        favorable = max(1.0 - float(observed["Low"].min()) / price, 0.0) * 100.0
        adverse = max(float(observed["High"].max()) / price - 1.0, 0.0) * 100.0

    source_codes = tuple(sorted(source.source_code for source in level.sources))
    families = tuple(sorted({source.source_family for source in level.sources}))
    horizon_end = (
        pd.Timestamp(future["Date"].iloc[-1]).date() if not future.empty else None
    )

    touched = touch_idx is not None
    broken = break_idx is not None
    return LevelEvaluationEvent(
        model_version=model_version,
        ticker=ticker.upper(),
        as_of_date=as_of_date,
        level_rank=str(level.rank),
        level_type=str(level.level_type),
        level_price=price,
        strength_score=float(level.strength_score),
        horizon_end_date=horizon_end,
        touched=touched,
        touch_date=date_at(touch_idx),
        broken=broken,
        break_date=date_at(break_idx),
        retested=retest_idx is not None,
        retest_date=date_at(retest_idx),
        held=touched and not broken,
        bars_to_touch=(touch_idx + 1) if touch_idx is not None else None,
        max_favorable_pct=round(favorable, 6),
        max_adverse_pct=round(adverse, 6),
        source_count=int(level.source_count),
        source_family_count=int(level.source_family_count),
        sources=source_codes,
        source_families=families,
        regime=regime,
        split=split,
    )


def evaluate_ladder_result(
    *,
    model_version: str,
    result: Any,
    future_history: pd.DataFrame,
    config: EvaluationConfig | None = None,
    regime: str | None = None,
    split: str | None = None,
) -> list[LevelEvaluationEvent]:
    levels = [*result.support_levels, *result.resistance_levels]
    return [
        evaluate_ranked_level(
            model_version=model_version,
            ticker=result.ticker,
            as_of_date=result.as_of_date,
            level=level,
            future_history=future_history,
            config=config,
            regime=regime,
            split=split,
        )
        for level in levels
    ]


def aggregate_evaluation(
    events: Sequence[LevelEvaluationEvent],
) -> EvaluationMetrics:
    count = len(events)
    if count == 0:
        return EvaluationMetrics(
            event_count=0,
            touch_count=0,
            break_count=0,
            retest_count=0,
            hold_count=0,
            touch_rate=0.0,
            break_rate_given_touch=0.0,
            retest_rate_given_break=0.0,
            hold_rate_given_touch=0.0,
            avg_bars_to_touch=None,
            avg_favorable_pct=0.0,
            avg_adverse_pct=0.0,
            directional_edge_pct=0.0,
            quality_score=0.0,
        )

    touched = [event for event in events if event.touched]
    broken = [event for event in events if event.broken]
    retested = [event for event in events if event.retested]
    held = [event for event in events if event.held]
    bars = [event.bars_to_touch for event in touched if event.bars_to_touch is not None]

    touch_rate = len(touched) / count
    break_rate = len(broken) / len(touched) if touched else 0.0
    retest_rate = len(retested) / len(broken) if broken else 0.0
    hold_rate = len(held) / len(touched) if touched else 0.0
    avg_favorable = sum(event.max_favorable_pct for event in events) / count
    avg_adverse = sum(event.max_adverse_pct for event in events) / count
    edge = avg_favorable - avg_adverse

    edge_component = max(0.0, min((edge + 10.0) / 20.0, 1.0))
    quality = (
        touch_rate * 0.35
        + hold_rate * 0.35
        + retest_rate * 0.10
        + edge_component * 0.20
    )

    return EvaluationMetrics(
        event_count=count,
        touch_count=len(touched),
        break_count=len(broken),
        retest_count=len(retested),
        hold_count=len(held),
        touch_rate=round(touch_rate, 6),
        break_rate_given_touch=round(break_rate, 6),
        retest_rate_given_break=round(retest_rate, 6),
        hold_rate_given_touch=round(hold_rate, 6),
        avg_bars_to_touch=(round(sum(bars) / len(bars), 6) if bars else None),
        avg_favorable_pct=round(avg_favorable, 6),
        avg_adverse_pct=round(avg_adverse, 6),
        directional_edge_pct=round(edge, 6),
        quality_score=round(quality, 6),
    )


def assign_temporal_splits(
    dates: Iterable[date],
    *,
    config: TemporalSplitConfig | None = None,
) -> dict[date, str]:
    cfg = config or TemporalSplitConfig()
    total_ratio = cfg.train_ratio + cfg.validation_ratio + cfg.test_ratio
    if any(value <= 0 for value in (cfg.train_ratio, cfg.validation_ratio, cfg.test_ratio)):
        raise ValueError("temporal split ratios must be > 0")
    if not math.isclose(total_ratio, 1.0, abs_tol=1e-9):
        raise ValueError("temporal split ratios must sum to 1.0")

    ordered = sorted(set(dates))
    if not ordered:
        return {}

    n = len(ordered)
    train_end = max(1, int(n * cfg.train_ratio))
    validation_end = max(train_end + 1, int(n * (cfg.train_ratio + cfg.validation_ratio)))
    validation_end = min(validation_end, n)

    result: dict[date, str] = {}
    for idx, value in enumerate(ordered):
        if idx < train_end:
            split = "TRAIN"
        elif idx < validation_end:
            split = "VALIDATION"
        else:
            split = "TEST"
        result[value] = split
    return result


def build_ablation_variants(
    enabled_sources: Sequence[str],
    source_family_map: Mapping[str, str],
) -> tuple[AblationVariant, ...]:
    normalized = tuple(sorted({str(source).upper() for source in enabled_sources}))
    variants: list[AblationVariant] = [
        AblationVariant(code="FULL", enabled_sources=normalized)
    ]

    for source in normalized:
        remaining = tuple(item for item in normalized if item != source)
        variants.append(
            AblationVariant(
                code=f"DROP_SOURCE_{source}",
                enabled_sources=remaining,
                removed_sources=(source,),
            )
        )

    families = sorted({source_family_map[source] for source in normalized if source in source_family_map})
    for family in families:
        removed = tuple(
            source
            for source in normalized
            if source_family_map.get(source) == family
        )
        remaining = tuple(source for source in normalized if source not in removed)
        variants.append(
            AblationVariant(
                code=f"DROP_FAMILY_{family}",
                enabled_sources=remaining,
                removed_sources=removed,
                removed_families=(family,),
            )
        )
    return tuple(variants)


def calculate_complexity_score(model: RSModelSpec) -> float:
    """Small normalized penalty proxy; higher means more moving parts."""
    sources = len(set(model.enabled_sources))
    strength_changes = len(model.strength_config)
    profile_changes = len(model.volume_profile_config)
    structural_changes = len(model.structural_config)
    raw = (
        sources * 0.02
        + strength_changes * 0.01
        + profile_changes * 0.01
        + structural_changes * 0.01
    )
    return round(min(raw, 1.0), 6)


def promotion_gate(
    *,
    baseline: RSModelSpec,
    challenger: RSModelSpec,
    baseline_validation: EvaluationMetrics,
    challenger_validation: EvaluationMetrics,
    baseline_test: EvaluationMetrics,
    challenger_test: EvaluationMetrics,
    baseline_regime_quality: Mapping[str, float] | None = None,
    challenger_regime_quality: Mapping[str, float] | None = None,
    policy: PromotionPolicy | None = None,
) -> PromotionDecision:
    cfg = policy or PromotionPolicy()
    reasons: list[str] = []

    validation_delta = (
        challenger_validation.quality_score - baseline_validation.quality_score
    )
    test_delta = challenger_test.quality_score - baseline_test.quality_score
    complexity_delta = calculate_complexity_score(challenger) - calculate_complexity_score(baseline)

    if challenger_validation.event_count < cfg.min_validation_events:
        reasons.append("insufficient validation events")
    if challenger_test.event_count < cfg.min_test_events:
        reasons.append("insufficient test events")
    if validation_delta < cfg.min_validation_quality_delta:
        reasons.append("validation quality delta below threshold")
    if test_delta < cfg.min_test_quality_delta:
        reasons.append("test quality delta below threshold")
    if complexity_delta > cfg.max_complexity_delta:
        reasons.append("complexity delta above threshold")

    base_regimes = baseline_regime_quality or {}
    challenger_regimes = challenger_regime_quality or {}
    regime_deltas = [
        challenger_regimes[key] - value
        for key, value in base_regimes.items()
        if key in challenger_regimes
    ]
    worst_regime_delta = min(regime_deltas) if regime_deltas else 0.0
    if worst_regime_delta < -cfg.max_regime_quality_degradation:
        reasons.append("regime degradation above threshold")

    return PromotionDecision(
        promote=not reasons,
        baseline_version=baseline.model_version,
        challenger_version=challenger.model_version,
        validation_quality_delta=round(validation_delta, 6),
        test_quality_delta=round(test_delta, 6),
        complexity_delta=round(complexity_delta, 6),
        worst_regime_delta=round(worst_regime_delta, 6),
        reasons=tuple(reasons),
    )


def metrics_by_scope(
    events: Sequence[LevelEvaluationEvent],
    *,
    field: str,
) -> dict[str, EvaluationMetrics]:
    groups: dict[str, list[LevelEvaluationEvent]] = {}
    for event in events:
        value = getattr(event, field)
        if value is None:
            continue
        groups.setdefault(str(value), []).append(event)
    return {key: aggregate_evaluation(value) for key, value in sorted(groups.items())}
