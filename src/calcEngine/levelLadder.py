"""Support / Resistance Level Ladder V1.

V1 uses MA20/50/100/200 on D/W/M from the Indicator Engine public views.
Database access is read-only; calculation and rendering remain separate.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any, Iterable, Sequence

import pandas as pd

try:
    from Ults.DuckLib import DuckDBManager
except ModuleNotFoundError:  # allows import from repository root in pytest
    from src.Ults.DuckLib import DuckDBManager


LOGGER = logging.getLogger(__name__)
SUPPORTED_TIMEFRAMES = ("D", "W", "M")
V1_MA_LENGTHS = (20, 50, 100, 200)


@dataclass(frozen=True)
class CurrentPrice:
    ticker: str
    as_of_date: date
    price: float


@dataclass(frozen=True)
class LevelCandidate:
    ticker: str
    price: float
    source_type: str
    source_code: str
    timeframe: str | None
    indicator_code: str | None
    config_id: int | None
    config_code: str | None
    component_code: str | None
    source_date: date
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedLevel:
    price: float
    source_type: str
    source_code: str
    timeframe: str | None
    weight: float
    source_date: date
    config_id: int | None
    config_code: str | None
    component_code: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LevelZone:
    zone_id: str
    price_low: float
    price_high: float
    representative_price: float
    sources: tuple[NormalizedLevel, ...]
    source_count: int
    level_type: str | None = None
    distance_pct: float | None = None


@dataclass(frozen=True)
class ScoredLevel:
    zone: LevelZone
    strength_score: float
    confluence_score: float
    timeframe_score: float
    touch_score: float
    recency_score: float
    touch_count: int


@dataclass(frozen=True)
class RankedLevel:
    rank: str
    level_type: str
    price: float
    price_low: float
    price_high: float
    distance_pct: float
    strength_score: float
    source_count: int
    sources: tuple[NormalizedLevel, ...]


@dataclass(frozen=True)
class LevelLadderResult:
    ticker: str
    as_of_date: date
    current_price: float
    resistance_levels: tuple[RankedLevel, ...]
    support_levels: tuple[RankedLevel, ...]
    nearest_support: RankedLevel | None
    nearest_resistance: RankedLevel | None
    upside_to_r1_pct: float | None
    downside_to_s1_pct: float | None
    risk_reward_ratio: float | None


@dataclass(frozen=True)
class StrengthConfig:
    confluence_weight: float = 0.35
    timeframe_weight: float = 0.25
    touch_weight: float = 0.25
    recency_weight: float = 0.15
    touch_target: int = 4
    touch_tolerance_pct: float = 0.003
    recency_days: int = 180
    timeframe_weights: dict[str, float] = field(
        default_factory=lambda: {"D": 1.0, "W": 1.5, "M": 2.0}
    )
    ma_length_weights: dict[int, float] = field(
        default_factory=lambda: {20: 0.8, 50: 1.0, 100: 1.15, 200: 1.3}
    )


def _normalize_ticker(ticker: str) -> str:
    normalized = str(ticker or "").strip().upper()
    if not normalized:
        raise ValueError("ticker is required")
    return normalized


def _validate_timeframes(timeframes: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(str(tf).strip().upper() for tf in timeframes))
    if not normalized:
        raise ValueError("timeframes must not be empty")
    invalid = set(normalized) - set(SUPPORTED_TIMEFRAMES)
    if invalid:
        raise ValueError(f"Unsupported timeframes: {sorted(invalid)}")
    return normalized


def _validate_pct(name: str, value: float, upper: float = 0.05) -> float:
    number = float(value)
    if not 0 < number <= upper:
        raise ValueError(f"{name} must satisfy 0 < value <= {upper}")
    return number


def _parse_parameters(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid indicator Parameters JSON: {value!r}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Indicator Parameters must be a JSON object")
    return parsed


def _require_view_columns(connection: Any, view_name: str, required: set[str]) -> None:
    rows = connection.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE lower(table_catalog) = lower(?)
          AND lower(table_schema) = lower(?)
          AND lower(table_name) = lower(?)
        ORDER BY ordinal_position
        """,
        ["CherryMon", "main", view_name],
    ).fetchall()
    available = {str(row[0]) for row in rows}
    missing = sorted(required - available)
    if missing:
        raise RuntimeError(
            f'Public view "CherryMon"."main"."{view_name}" '
            f"is missing required columns: {missing}. Available={sorted(available)}"
        )


def _validate_public_views(connection: Any) -> None:
    _require_view_columns(
        connection,
        "vw_Ticker_indicators",
        {"Ticker", "Date", "ConfigId", "ComponentCode", "Value"},
    )
    _require_view_columns(
        connection,
        "vw_Indicator_config",
        {
            "ConfigId",
            "ConfigCode",
            "IndicatorCode",
            "Timeframe",
            "Parameters",
            "ConfigIsEnabled",
            "IndicatorIsActive",
            "ComponentCode",
            "ComponentIsActive",
        },
    )


def load_current_price(
    connection: Any,
    *,
    ticker: str,
    as_of_date: date | None = None,
) -> CurrentPrice:
    """Resolve latest valid close at or before the requested date."""
    normalized = _normalize_ticker(ticker)
    if as_of_date is None:
        row = connection.execute(
            """
            SELECT "Ticker", "Date", "Close"
            FROM "CherryMon"."main"."raw_stock_eod"
            WHERE "Ticker" = ? AND "Close" IS NOT NULL
            ORDER BY "Date" DESC
            LIMIT 1
            """,
            [normalized],
        ).fetchone()
    else:
        row = connection.execute(
            """
            SELECT "Ticker", "Date", "Close"
            FROM "CherryMon"."main"."raw_stock_eod"
            WHERE "Ticker" = ?
              AND "Date" <= ?
              AND "Close" IS NOT NULL
            ORDER BY "Date" DESC
            LIMIT 1
            """,
            [normalized, as_of_date],
        ).fetchone()
    if row is None:
        raise ValueError(f"No price data for ticker={normalized} as_of_date={as_of_date}")
    price = float(row[2])
    if not math.isfinite(price) or price <= 0:
        raise ValueError(f"Invalid current price for {normalized}: {row[2]!r}")
    return CurrentPrice(normalized, pd.Timestamp(row[1]).date(), price)


def load_price_history(
    connection: Any,
    *,
    ticker: str,
    as_of_date: date,
    limit: int = 252,
) -> pd.DataFrame:
    """Load one read-only OHLC history window for touch scoring."""
    if limit <= 0:
        raise ValueError("history limit must be > 0")
    df = connection.execute(
        """
        SELECT "Date", "High", "Low", "Close"
        FROM "CherryMon"."main"."raw_stock_eod"
        WHERE "Ticker" = ? AND "Date" <= ?
        ORDER BY "Date" DESC
        LIMIT ?
        """,
        [ticker, as_of_date, int(limit)],
    ).df()
    if df.empty:
        return pd.DataFrame(columns=["Date", "High", "Low", "Close"])
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for col in ("High", "Low", "Close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return (
        df.dropna(subset=["Date", "High", "Low", "Close"])
        .sort_values("Date")
        .reset_index(drop=True)
    )


def load_ma_level_candidates(
    connection: Any,
    *,
    ticker: str,
    as_of_date: date,
    timeframes: Sequence[str] = SUPPORTED_TIMEFRAMES,
) -> list[LevelCandidate]:
    """Load latest MA20/50/100/200 D/W/M values from public Indicator Engine views."""
    normalized_timeframes = _validate_timeframes(timeframes)
    _validate_public_views(connection)
    placeholders = ", ".join("?" for _ in normalized_timeframes)
    params: list[Any] = [ticker, as_of_date, *normalized_timeframes]
    df = connection.execute(
        f"""
        WITH ranked AS (
            SELECT
                val."Ticker",
                val."Date",
                val."ConfigId",
                val."ComponentCode",
                val."Value",
                cfg."ConfigCode",
                cfg."IndicatorCode",
                cfg."Timeframe",
                cfg."Parameters",
                ROW_NUMBER() OVER (
                    PARTITION BY val."ConfigId", val."ComponentCode"
                    ORDER BY val."Date" DESC
                ) AS rn
            FROM "CherryMon"."main"."vw_Ticker_indicators" val
            INNER JOIN "CherryMon"."main"."vw_Indicator_config" cfg
                ON cfg."ConfigId" = val."ConfigId"
               AND cfg."ComponentCode" = val."ComponentCode"
            WHERE val."Ticker" = ?
              AND val."Date" <= ?
              AND cfg."IndicatorCode" = 'MA'
              AND cfg."Timeframe" IN ({placeholders})
              AND cfg."ConfigIsEnabled" = TRUE
              AND cfg."IndicatorIsActive" = TRUE
              AND COALESCE(cfg."ComponentIsActive", TRUE) = TRUE
              AND val."ComponentCode" = 'VALUE'
              AND val."Value" IS NOT NULL
        )
        SELECT
            "Ticker", "Date", "ConfigId", "ComponentCode", "Value",
            "ConfigCode", "IndicatorCode", "Timeframe", "Parameters"
        FROM ranked
        WHERE rn = 1
        ORDER BY "Timeframe", "ConfigId"
        """,
        params,
    ).df()

    candidates: list[LevelCandidate] = []
    for row in df.itertuples(index=False):
        parameters = _parse_parameters(row.Parameters)
        length_raw = parameters.get("length")
        if length_raw is None:
            continue
        try:
            length = int(length_raw)
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid MA length in ConfigId={row.ConfigId}: {length_raw!r}"
            ) from None
        if length not in V1_MA_LENGTHS:
            continue
        price = float(row.Value)
        if not math.isfinite(price) or price <= 0:
            raise ValueError(f"Invalid MA value for ConfigId={row.ConfigId}: {row.Value!r}")
        candidates.append(
            LevelCandidate(
                ticker=str(row.Ticker).upper(),
                price=price,
                source_type="INDICATOR",
                source_code=str(row.ConfigCode),
                timeframe=str(row.Timeframe).upper(),
                indicator_code=str(row.IndicatorCode).upper(),
                config_id=int(row.ConfigId),
                config_code=str(row.ConfigCode),
                component_code=str(row.ComponentCode).upper(),
                source_date=pd.Timestamp(row.Date).date(),
                metadata={"parameters": parameters, "length": length},
            )
        )
    return candidates


def normalize_levels(
    candidates: Iterable[LevelCandidate],
    *,
    current_price: CurrentPrice,
    strength_config: StrengthConfig | None = None,
) -> list[NormalizedLevel]:
    config = strength_config or StrengthConfig()
    result: list[NormalizedLevel] = []
    for candidate in candidates:
        if candidate.ticker.upper() != current_price.ticker:
            raise ValueError("Candidate ticker does not match CurrentPrice")
        if candidate.source_date > current_price.as_of_date:
            raise ValueError("Candidate source_date is after CurrentPrice.as_of_date")
        if candidate.timeframe and candidate.timeframe not in SUPPORTED_TIMEFRAMES:
            raise ValueError(f"Unsupported candidate timeframe: {candidate.timeframe}")
        price = float(candidate.price)
        if not math.isfinite(price) or price <= 0:
            raise ValueError(f"Invalid candidate price: {candidate.price!r}")
        tf_weight = config.timeframe_weights.get(candidate.timeframe or "", 1.0)
        ma_weight = 1.0
        if candidate.indicator_code == "MA":
            ma_weight = config.ma_length_weights.get(
                int(candidate.metadata.get("length", 0) or 0), 1.0
            )
        result.append(
            NormalizedLevel(
                price=price,
                source_type=candidate.source_type,
                source_code=candidate.source_code,
                timeframe=candidate.timeframe,
                weight=float(tf_weight * ma_weight),
                source_date=candidate.source_date,
                config_id=candidate.config_id,
                config_code=candidate.config_code,
                component_code=candidate.component_code,
                metadata=dict(candidate.metadata),
            )
        )
    return sorted(result, key=lambda x: (x.price, x.source_code, x.timeframe or ""))


def _weighted_price(levels: Sequence[NormalizedLevel]) -> float:
    total = sum(max(level.weight, 0.0) for level in levels)
    if total <= 0:
        return sum(level.price for level in levels) / len(levels)
    return sum(level.price * max(level.weight, 0.0) for level in levels) / total


def cluster_levels(
    levels: Sequence[NormalizedLevel],
    *,
    cluster_threshold_pct: float = 0.01,
) -> list[LevelZone]:
    """Group nearby levels into deterministic zones."""
    threshold = _validate_pct("cluster_threshold_pct", cluster_threshold_pct)
    if not levels:
        return []
    clusters: list[list[NormalizedLevel]] = []
    for level in sorted(levels, key=lambda x: (x.price, x.source_code)):
        if not clusters:
            clusters.append([level])
            continue
        representative = _weighted_price(clusters[-1])
        if abs(level.price - representative) / representative <= threshold:
            clusters[-1].append(level)
        else:
            clusters.append([level])
    return [
        LevelZone(
            zone_id=f"ZONE_{index:03d}",
            price_low=min(x.price for x in cluster),
            price_high=max(x.price for x in cluster),
            representative_price=_weighted_price(cluster),
            sources=tuple(cluster),
            source_count=len(cluster),
        )
        for index, cluster in enumerate(clusters, start=1)
    ]


def classify_zones(
    zones: Sequence[LevelZone],
    *,
    current_price: CurrentPrice,
    neutral_threshold_pct: float = 0.003,
) -> list[LevelZone]:
    neutral = _validate_pct("neutral_threshold_pct", neutral_threshold_pct, 0.02)
    result: list[LevelZone] = []
    for zone in zones:
        distance = (
            (zone.representative_price - current_price.price)
            / current_price.price
            * 100.0
        )
        if (
            zone.price_low <= current_price.price <= zone.price_high
            or abs(distance) <= neutral * 100.0
        ):
            level_type = "CURRENT"
        elif zone.representative_price < current_price.price:
            level_type = "SUPPORT"
        else:
            level_type = "RESISTANCE"
        result.append(replace(zone, level_type=level_type, distance_pct=distance))
    return result


def _touch_count(
    zone: LevelZone,
    price_history: pd.DataFrame | None,
    tolerance_pct: float,
) -> int:
    if price_history is None or price_history.empty:
        return 0
    missing = {"High", "Low"} - set(price_history.columns)
    if missing:
        raise ValueError(f"price_history missing columns: {sorted(missing)}")
    highs = pd.to_numeric(price_history["High"], errors="coerce")
    lows = pd.to_numeric(price_history["Low"], errors="coerce")
    low = zone.price_low * (1.0 - tolerance_pct)
    high = zone.price_high * (1.0 + tolerance_pct)
    return int(((lows <= high) & (highs >= low)).fillna(False).sum())


def score_zones(
    zones: Sequence[LevelZone],
    *,
    current_price: CurrentPrice,
    price_history: pd.DataFrame | None,
    strength_config: StrengthConfig | None = None,
) -> list[ScoredLevel]:
    """Strength V1 = confluence + timeframe + touches + recency, normalized 0..100."""
    config = strength_config or StrengthConfig()
    weights = (
        config.confluence_weight,
        config.timeframe_weight,
        config.touch_weight,
        config.recency_weight,
    )
    if any(w < 0 for w in weights) or sum(weights) <= 0:
        raise ValueError("Strength weights must be non-negative and sum to > 0")
    if config.touch_target <= 0 or config.recency_days <= 0:
        raise ValueError("touch_target and recency_days must be > 0")
    if not 0 <= config.touch_tolerance_pct <= 0.05:
        raise ValueError("touch_tolerance_pct must be between 0 and 0.05")
    tf_total = sum(config.timeframe_weights.get(tf, 0.0) for tf in SUPPORTED_TIMEFRAMES) or 1.0
    result: list[ScoredLevel] = []
    for zone in zones:
        confluence = min(zone.source_count / 4.0, 1.0) * 100.0
        timeframes = {x.timeframe for x in zone.sources if x.timeframe}
        timeframe = min(
            sum(config.timeframe_weights.get(tf, 0.0) for tf in timeframes) / tf_total,
            1.0,
        ) * 100.0
        touches = _touch_count(zone, price_history, config.touch_tolerance_pct)
        touch = min(touches / float(config.touch_target), 1.0) * 100.0
        latest = max(x.source_date for x in zone.sources)
        age = max((current_price.as_of_date - latest).days, 0)
        recency = max(0.0, 1.0 - age / float(config.recency_days)) * 100.0
        score = (
            confluence * config.confluence_weight
            + timeframe * config.timeframe_weight
            + touch * config.touch_weight
            + recency * config.recency_weight
        ) / sum(weights)
        result.append(
            ScoredLevel(
                zone=zone,
                strength_score=round(score, 2),
                confluence_score=round(confluence, 2),
                timeframe_score=round(timeframe, 2),
                touch_score=round(touch, 2),
                recency_score=round(recency, 2),
                touch_count=touches,
            )
        )
    return result


def rank_levels(
    levels: Sequence[ScoredLevel],
    *,
    max_support_levels: int = 3,
    max_resistance_levels: int = 3,
) -> tuple[tuple[RankedLevel, ...], tuple[RankedLevel, ...]]:
    """S1/R1 are nearest levels; strength never changes rank order."""
    if max_support_levels <= 0 or max_resistance_levels <= 0:
        raise ValueError("max_support_levels and max_resistance_levels must be > 0")
    supports = sorted(
        (x for x in levels if x.zone.level_type == "SUPPORT"),
        key=lambda x: x.zone.representative_price,
        reverse=True,
    )
    resistances = sorted(
        (x for x in levels if x.zone.level_type == "RESISTANCE"),
        key=lambda x: x.zone.representative_price,
    )

    def build(item: ScoredLevel, rank: str) -> RankedLevel:
        zone = item.zone
        if zone.level_type is None or zone.distance_pct is None:
            raise ValueError("Zone must be classified before ranking")
        return RankedLevel(
            rank=rank,
            level_type=zone.level_type,
            price=round(zone.representative_price, 4),
            price_low=round(zone.price_low, 4),
            price_high=round(zone.price_high, 4),
            distance_pct=round(zone.distance_pct, 4),
            strength_score=item.strength_score,
            source_count=zone.source_count,
            sources=zone.sources,
        )

    return (
        tuple(build(x, f"S{i}") for i, x in enumerate(supports[:max_support_levels], 1)),
        tuple(build(x, f"R{i}") for i, x in enumerate(resistances[:max_resistance_levels], 1)),
    )


def build_level_ladder_from_data(
    current_price: CurrentPrice,
    candidates: Sequence[LevelCandidate],
    *,
    price_history: pd.DataFrame | None = None,
    cluster_threshold_pct: float = 0.01,
    neutral_threshold_pct: float = 0.003,
    max_support_levels: int = 3,
    max_resistance_levels: int = 3,
    strength_config: StrengthConfig | None = None,
) -> LevelLadderResult:
    """Pure calculation pipeline used by production and focused tests."""
    normalized = normalize_levels(
        candidates, current_price=current_price, strength_config=strength_config
    )
    zones = cluster_levels(normalized, cluster_threshold_pct=cluster_threshold_pct)
    zones = classify_zones(
        zones,
        current_price=current_price,
        neutral_threshold_pct=neutral_threshold_pct,
    )
    scored = score_zones(
        zones,
        current_price=current_price,
        price_history=price_history,
        strength_config=strength_config,
    )
    supports, resistances = rank_levels(
        scored,
        max_support_levels=max_support_levels,
        max_resistance_levels=max_resistance_levels,
    )
    s1 = supports[0] if supports else None
    r1 = resistances[0] if resistances else None
    upside = r1.distance_pct if r1 else None
    downside = abs(s1.distance_pct) if s1 else None
    rr = (
        upside / downside
        if upside is not None and downside is not None and downside > 0
        else None
    )
    return LevelLadderResult(
        ticker=current_price.ticker,
        as_of_date=current_price.as_of_date,
        current_price=current_price.price,
        resistance_levels=resistances,
        support_levels=supports,
        nearest_support=s1,
        nearest_resistance=r1,
        upside_to_r1_pct=round(upside, 4) if upside is not None else None,
        downside_to_s1_pct=round(downside, 4) if downside is not None else None,
        risk_reward_ratio=round(rr, 4) if rr is not None else None,
    )


def build_level_ladder(
    ticker: str,
    *,
    as_of_date: date | None = None,
    timeframes: tuple[str, ...] = SUPPORTED_TIMEFRAMES,
    max_support_levels: int = 3,
    max_resistance_levels: int = 3,
    enabled_sources: tuple[str, ...] | None = None,
    cluster_threshold_pct: float = 0.01,
    neutral_threshold_pct: float = 0.003,
    strength_config: StrengthConfig | None = None,
    connection: Any | None = None,
) -> LevelLadderResult:
    """Build RS Ladder V1 from current Close and MA20/50/100/200 D/W/M."""
    normalized_ticker = _normalize_ticker(ticker)
    normalized_timeframes = _validate_timeframes(timeframes)
    _validate_pct("cluster_threshold_pct", cluster_threshold_pct)
    _validate_pct("neutral_threshold_pct", neutral_threshold_pct, 0.02)
    if max_support_levels <= 0 or max_resistance_levels <= 0:
        raise ValueError("max_support_levels and max_resistance_levels must be > 0")

    sources = {"MA"} if enabled_sources is None else {
        str(source).strip().upper() for source in enabled_sources
    }
    unsupported = sources - {"MA"}
    if unsupported:
        raise ValueError(
            f"RS Ladder V1 only supports MA; unsupported={sorted(unsupported)}"
        )

    LOGGER.info(
        "RS Ladder V1 start | ticker=%s as_of=%s timeframes=%s cluster=%.4f",
        normalized_ticker,
        as_of_date,
        normalized_timeframes,
        cluster_threshold_pct,
    )

    def calculate(con: Any) -> LevelLadderResult:
        current = load_current_price(
            con, ticker=normalized_ticker, as_of_date=as_of_date
        )
        candidates = (
            load_ma_level_candidates(
                con,
                ticker=normalized_ticker,
                as_of_date=current.as_of_date,
                timeframes=normalized_timeframes,
            )
            if "MA" in sources
            else []
        )
        history = load_price_history(
            con, ticker=normalized_ticker, as_of_date=current.as_of_date
        )
        LOGGER.info(
            "RS Ladder V1 inputs | ticker=%s date=%s candidates=%d history=%d",
            normalized_ticker,
            current.as_of_date,
            len(candidates),
            len(history),
        )
        result = build_level_ladder_from_data(
            current,
            candidates,
            price_history=history,
            cluster_threshold_pct=cluster_threshold_pct,
            neutral_threshold_pct=neutral_threshold_pct,
            max_support_levels=max_support_levels,
            max_resistance_levels=max_resistance_levels,
            strength_config=strength_config,
        )
        LOGGER.info(
            "RS Ladder V1 success | ticker=%s supports=%d resistances=%d",
            normalized_ticker,
            len(result.support_levels),
            len(result.resistance_levels),
        )
        return result

    if connection is not None:
        return calculate(connection)

    try:
        with DuckDBManager(read_only=True) as con:
            return calculate(con)
    except Exception:
        LOGGER.exception("RS Ladder V1 failed | ticker=%s", normalized_ticker)
        raise
