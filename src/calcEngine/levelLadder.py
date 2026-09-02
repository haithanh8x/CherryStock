"""Support / Resistance Level Ladder V2.1.

V2.1 extends the multi-source ladder with ATR-adaptive clustering, structural
price levels and point-in-time safety while keeping Indicator Engine public
views as the only technical-indicator read contracts. Database access is read-only; calculation
and rendering remain separate.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Any, Iterable, Sequence

import pandas as pd

try:
    from Ults.DuckLib import DuckDBManager
except ModuleNotFoundError:  # allows import from repository root in pytest
    from src.Ults.DuckLib import DuckDBManager


LOGGER = logging.getLogger(__name__)
SUPPORTED_TIMEFRAMES = ("D", "W", "M")
V1_MA_LENGTHS = (20, 50, 100, 200)
BB_LEVEL_COMPONENTS = ("LOWER", "MIDDLE", "UPPER")

SOURCE_ROLE_LEVEL = "LEVEL"
SOURCE_ROLE_CONTEXT = "CONTEXT"
SOURCE_ROLE_CONFIRMATION = "CONFIRMATION"

SOURCE_FAMILY_TREND_AVERAGE = "TREND_AVERAGE"
SOURCE_FAMILY_VOLATILITY_BAND = "VOLATILITY_BAND"
SOURCE_FAMILY_MOMENTUM_CONFIRMATION = "MOMENTUM_CONFIRMATION"
SOURCE_FAMILY_MARKET_STRUCTURE = "MARKET_STRUCTURE"
SOURCE_FAMILY_VOLATILITY_CONTEXT = "VOLATILITY_CONTEXT"

VALUE_SEMANTIC_PRICE_LEVEL = "PRICE_LEVEL"
VALUE_SEMANTIC_OSCILLATOR = "OSCILLATOR"
VALUE_SEMANTIC_VOLATILITY_DISTANCE = "VOLATILITY_DISTANCE"


@dataclass(frozen=True)
class CurrentPrice:
    ticker: str
    as_of_date: date
    price: float


@dataclass(frozen=True)
class MarketContext:
    ticker: str
    as_of_date: date
    source_code: str
    source_family: str
    timeframe: str | None
    indicator_code: str
    config_id: int
    config_code: str
    component_code: str
    value: float
    unit: str | None
    source_date: date
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConfirmationContext:
    ticker: str
    as_of_date: date
    source_code: str
    source_family: str
    timeframe: str | None
    indicator_code: str
    config_id: int
    config_code: str
    component_code: str
    value: float
    source_date: date
    metadata: dict[str, Any] = field(default_factory=dict)


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
    confirmed_at: date | None = None
    source_role: str = SOURCE_ROLE_LEVEL
    source_family: str = "UNCLASSIFIED"
    value_semantic: str = VALUE_SEMANTIC_PRICE_LEVEL
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedLevel:
    price: float
    source_type: str
    source_code: str
    timeframe: str | None
    weight: float
    source_date: date
    confirmed_at: date
    config_id: int | None
    config_code: str | None
    component_code: str | None
    source_role: str
    source_family: str
    value_semantic: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LevelZone:
    zone_id: str
    price_low: float
    price_high: float
    representative_price: float
    sources: tuple[NormalizedLevel, ...]
    source_count: int
    source_family_count: int
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
    confirmation_score: float
    structural_quality_score: float
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
    source_family_count: int
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
    confirmations: tuple[ConfirmationContext, ...] = ()
    market_contexts: tuple[MarketContext, ...] = ()
    cluster_threshold_pct_used: float | None = None
    neutral_threshold_pct_used: float | None = None


@dataclass(frozen=True)
class StrengthConfig:
    confluence_weight: float = 0.35
    timeframe_weight: float = 0.25
    touch_weight: float = 0.25
    recency_weight: float = 0.15
    confirmation_weight: float = 0.10
    structural_quality_weight: float = 0.15
    family_confluence_target: int = 3
    touch_target: int = 4
    touch_tolerance_pct: float = 0.003
    recency_days: int = 180
    timeframe_weights: dict[str, float] = field(
        default_factory=lambda: {"D": 1.0, "W": 1.5, "M": 2.0}
    )
    ma_length_weights: dict[int, float] = field(
        default_factory=lambda: {20: 0.8, 50: 1.0, 100: 1.15, 200: 1.3}
    )
    bb_component_weights: dict[str, float] = field(
        default_factory=lambda: {"LOWER": 1.0, "MIDDLE": 0.8, "UPPER": 1.0}
    )
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    atr_cluster_multiplier: float = 0.50
    atr_neutral_multiplier: float = 0.15
    structural_recency_days: int = 180


@dataclass(frozen=True)
class StructuralSourceConfig:
    swing_left: int = 3
    swing_right: int = 3
    swing_lookback_bars: int = 252
    swing_max_candidates_each: int = 12
    historical_lookback_days: int = 370


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
            "ValueSemantic",
            "Unit",
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


def _load_latest_indicator_rows(
    connection: Any,
    *,
    ticker: str,
    as_of_date: date,
    indicator_code: str,
    timeframes: Sequence[str],
    component_codes: Sequence[str],
) -> pd.DataFrame:
    """Load latest point-in-time rows for one indicator from public SSOT views."""
    normalized_timeframes = _validate_timeframes(timeframes)
    normalized_components = tuple(
        dict.fromkeys(str(code).strip().upper() for code in component_codes)
    )
    if not normalized_components:
        raise ValueError("component_codes must not be empty")

    _validate_public_views(connection)
    tf_placeholders = ", ".join("?" for _ in normalized_timeframes)
    component_placeholders = ", ".join("?" for _ in normalized_components)
    params: list[Any] = [
        ticker,
        as_of_date,
        str(indicator_code).strip().upper(),
        *normalized_timeframes,
        *normalized_components,
    ]
    return connection.execute(
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
                cfg."ValueSemantic",
                cfg."Unit",
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
              AND cfg."IndicatorCode" = ?
              AND cfg."Timeframe" IN ({tf_placeholders})
              AND cfg."ConfigIsEnabled" = TRUE
              AND cfg."IndicatorIsActive" = TRUE
              AND COALESCE(cfg."ComponentIsActive", TRUE) = TRUE
              AND val."ComponentCode" IN ({component_placeholders})
              AND val."Value" IS NOT NULL
        )
        SELECT
            "Ticker", "Date", "ConfigId", "ComponentCode", "Value",
            "ConfigCode", "IndicatorCode", "Timeframe", "Parameters",
            "ValueSemantic", "Unit"
        FROM ranked
        WHERE rn = 1
        ORDER BY "Timeframe", "ConfigId", "ComponentCode"
        """,
        params,
    ).df()


def _require_value_semantic(
    row: Any,
    *,
    expected: str,
) -> str:
    semantic = str(row.ValueSemantic or "").strip().upper()
    if semantic != expected:
        raise ValueError(
            "Invalid ValueSemantic for "
            f"{row.IndicatorCode}/{row.ComponentCode}/ConfigId={row.ConfigId}: "
            f"expected={expected!r}, actual={semantic!r}"
        )
    return semantic


def load_ma_level_candidates(
    connection: Any,
    *,
    ticker: str,
    as_of_date: date,
    timeframes: Sequence[str] = SUPPORTED_TIMEFRAMES,
) -> list[LevelCandidate]:
    """MA provider: latest MA20/50/100/200 D/W/M price levels from Indicator SSOT."""
    df = _load_latest_indicator_rows(
        connection,
        ticker=ticker,
        as_of_date=as_of_date,
        indicator_code="MA",
        timeframes=timeframes,
        component_codes=("VALUE",),
    )

    candidates: list[LevelCandidate] = []
    for row in df.itertuples(index=False):
        semantic = _require_value_semantic(
            row, expected=VALUE_SEMANTIC_PRICE_LEVEL
        )
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
                source_role=SOURCE_ROLE_LEVEL,
                source_family=SOURCE_FAMILY_TREND_AVERAGE,
                value_semantic=semantic,
                metadata={
                    "parameters": parameters,
                    "length": length,
                    "unit": row.Unit,
                },
            )
        )
    return candidates


def load_bb_level_candidates(
    connection: Any,
    *,
    ticker: str,
    as_of_date: date,
    timeframes: Sequence[str] = SUPPORTED_TIMEFRAMES,
) -> list[LevelCandidate]:
    """BB provider: only LOWER/MIDDLE/UPPER components may create price levels."""
    df = _load_latest_indicator_rows(
        connection,
        ticker=ticker,
        as_of_date=as_of_date,
        indicator_code="BB",
        timeframes=timeframes,
        component_codes=BB_LEVEL_COMPONENTS,
    )

    candidates: list[LevelCandidate] = []
    for row in df.itertuples(index=False):
        semantic = _require_value_semantic(
            row, expected=VALUE_SEMANTIC_PRICE_LEVEL
        )
        component = str(row.ComponentCode).upper()
        price = float(row.Value)
        if not math.isfinite(price) or price <= 0:
            raise ValueError(f"Invalid BB value for ConfigId={row.ConfigId}: {row.Value!r}")
        candidates.append(
            LevelCandidate(
                ticker=str(row.Ticker).upper(),
                price=price,
                source_type="INDICATOR",
                source_code=f"{row.ConfigCode}:{component}",
                timeframe=str(row.Timeframe).upper(),
                indicator_code=str(row.IndicatorCode).upper(),
                config_id=int(row.ConfigId),
                config_code=str(row.ConfigCode),
                component_code=component,
                source_date=pd.Timestamp(row.Date).date(),
                source_role=SOURCE_ROLE_LEVEL,
                source_family=SOURCE_FAMILY_VOLATILITY_BAND,
                value_semantic=semantic,
                metadata={
                    "parameters": _parse_parameters(row.Parameters),
                    "unit": row.Unit,
                },
            )
        )
    return candidates


def load_rsi_confirmation_contexts(
    connection: Any,
    *,
    ticker: str,
    as_of_date: date,
    timeframes: Sequence[str] = SUPPORTED_TIMEFRAMES,
) -> list[ConfirmationContext]:
    """RSI provider: latest D/W/M values used only as confirmation context."""
    df = _load_latest_indicator_rows(
        connection,
        ticker=ticker,
        as_of_date=as_of_date,
        indicator_code="RSI",
        timeframes=timeframes,
        component_codes=("VALUE",),
    )

    contexts: list[ConfirmationContext] = []
    for row in df.itertuples(index=False):
        _require_value_semantic(row, expected=VALUE_SEMANTIC_OSCILLATOR)
        value = float(row.Value)
        if not math.isfinite(value) or not 0.0 <= value <= 100.0:
            raise ValueError(f"Invalid RSI value for ConfigId={row.ConfigId}: {row.Value!r}")
        contexts.append(
            ConfirmationContext(
                ticker=str(row.Ticker).upper(),
                as_of_date=as_of_date,
                source_code=str(row.ConfigCode),
                source_family=SOURCE_FAMILY_MOMENTUM_CONFIRMATION,
                timeframe=str(row.Timeframe).upper(),
                indicator_code="RSI",
                config_id=int(row.ConfigId),
                config_code=str(row.ConfigCode),
                component_code=str(row.ComponentCode).upper(),
                value=value,
                source_date=pd.Timestamp(row.Date).date(),
                metadata={
                    "parameters": _parse_parameters(row.Parameters),
                    "unit": row.Unit,
                },
            )
        )
    return contexts


def load_atr_market_contexts(
    connection: Any,
    *,
    ticker: str,
    as_of_date: date,
    timeframes: Sequence[str] = SUPPORTED_TIMEFRAMES,
) -> list[MarketContext]:
    """ATR provider: V2.1 uses ATR14_D as volatility context for adaptive distances."""
    del timeframes
    df = _load_latest_indicator_rows(
        connection,
        ticker=ticker,
        as_of_date=as_of_date,
        indicator_code="ATR",
        timeframes=("D",),
        component_codes=("VALUE",),
    )

    contexts: list[MarketContext] = []
    for row in df.itertuples(index=False):
        _require_value_semantic(
            row, expected=VALUE_SEMANTIC_VOLATILITY_DISTANCE
        )
        value = float(row.Value)
        if not math.isfinite(value) or value <= 0:
            raise ValueError(
                f"Invalid ATR value for ConfigId={row.ConfigId}: {row.Value!r}"
            )
        contexts.append(
            MarketContext(
                ticker=str(row.Ticker).upper(),
                as_of_date=as_of_date,
                source_code=str(row.ConfigCode),
                source_family=SOURCE_FAMILY_VOLATILITY_CONTEXT,
                timeframe=str(row.Timeframe).upper(),
                indicator_code="ATR",
                config_id=int(row.ConfigId),
                config_code=str(row.ConfigCode),
                component_code=str(row.ComponentCode).upper(),
                value=value,
                unit=str(row.Unit) if row.Unit is not None else None,
                source_date=pd.Timestamp(row.Date).date(),
                metadata={"parameters": _parse_parameters(row.Parameters)},
            )
        )
    return contexts


def _load_structural_history(
    connection: Any,
    *,
    ticker: str,
    as_of_date: date,
    lookback_days: int,
) -> pd.DataFrame:
    if lookback_days <= 0:
        raise ValueError("lookback_days must be > 0")
    start_date = as_of_date - timedelta(days=int(lookback_days))
    df = connection.execute(
        """
        SELECT "Date", "High", "Low", "Close"
        FROM "CherryMon"."main"."raw_stock_eod"
        WHERE "Ticker" = ?
          AND "Date" >= ?
          AND "Date" <= ?
          AND "High" IS NOT NULL
          AND "Low" IS NOT NULL
        ORDER BY "Date"
        """,
        [ticker, start_date, as_of_date],
    ).df()
    if df.empty:
        return pd.DataFrame(columns=["Date", "High", "Low", "Close"])
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for column in ("High", "Low", "Close"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return (
        df.dropna(subset=["Date", "High", "Low"])
        .sort_values("Date")
        .reset_index(drop=True)
    )


def load_swing_level_candidates(
    connection: Any,
    *,
    ticker: str,
    as_of_date: date,
    timeframes: Sequence[str] = SUPPORTED_TIMEFRAMES,
    structural_config: StructuralSourceConfig | None = None,
) -> list[LevelCandidate]:
    """Confirmed daily swing highs/lows with explicit pivot_date and confirmed_at."""
    del timeframes
    config = structural_config or StructuralSourceConfig()
    if config.swing_left <= 0 or config.swing_right <= 0:
        raise ValueError("swing_left and swing_right must be > 0")
    if config.swing_max_candidates_each <= 0:
        raise ValueError("swing_max_candidates_each must be > 0")

    df = _load_structural_history(
        connection,
        ticker=ticker,
        as_of_date=as_of_date,
        lookback_days=max(config.historical_lookback_days, 500),
    )
    if len(df) < config.swing_left + config.swing_right + 1:
        return []

    if len(df) > config.swing_lookback_bars + config.swing_left + config.swing_right:
        df = df.iloc[
            -(config.swing_lookback_bars + config.swing_left + config.swing_right):
        ].reset_index(drop=True)

    highs: list[LevelCandidate] = []
    lows: list[LevelCandidate] = []
    left = config.swing_left
    right = config.swing_right

    for index in range(left, len(df) - right):
        row = df.iloc[index]
        pivot_date = pd.Timestamp(row["Date"]).date()
        confirmed_at = pd.Timestamp(df.iloc[index + right]["Date"]).date()
        if confirmed_at > as_of_date:
            continue

        left_highs = df.iloc[index - left:index]["High"]
        right_highs = df.iloc[index + 1:index + right + 1]["High"]
        left_lows = df.iloc[index - left:index]["Low"]
        right_lows = df.iloc[index + 1:index + right + 1]["Low"]

        high = float(row["High"])
        low = float(row["Low"])
        common_metadata = {
            "pivot_date": pivot_date.isoformat(),
            "confirmed_at": confirmed_at.isoformat(),
            "left": left,
            "right": right,
        }

        if high > float(left_highs.max()) and high >= float(right_highs.max()):
            highs.append(
                LevelCandidate(
                    ticker=ticker.upper(),
                    price=high,
                    source_type="STRUCTURAL",
                    source_code=f"SWING_HIGH_{pivot_date:%Y%m%d}",
                    timeframe="D",
                    indicator_code=None,
                    config_id=None,
                    config_code=None,
                    component_code=None,
                    source_date=pivot_date,
                    confirmed_at=confirmed_at,
                    source_role=SOURCE_ROLE_LEVEL,
                    source_family=SOURCE_FAMILY_MARKET_STRUCTURE,
                    value_semantic=VALUE_SEMANTIC_PRICE_LEVEL,
                    metadata={**common_metadata, "structure_kind": "SWING_HIGH"},
                )
            )

        if low < float(left_lows.min()) and low <= float(right_lows.min()):
            lows.append(
                LevelCandidate(
                    ticker=ticker.upper(),
                    price=low,
                    source_type="STRUCTURAL",
                    source_code=f"SWING_LOW_{pivot_date:%Y%m%d}",
                    timeframe="D",
                    indicator_code=None,
                    config_id=None,
                    config_code=None,
                    component_code=None,
                    source_date=pivot_date,
                    confirmed_at=confirmed_at,
                    source_role=SOURCE_ROLE_LEVEL,
                    source_family=SOURCE_FAMILY_MARKET_STRUCTURE,
                    value_semantic=VALUE_SEMANTIC_PRICE_LEVEL,
                    metadata={**common_metadata, "structure_kind": "SWING_LOW"},
                )
            )

    highs = sorted(highs, key=lambda item: item.source_date, reverse=True)[
        :config.swing_max_candidates_each
    ]
    lows = sorted(lows, key=lambda item: item.source_date, reverse=True)[
        :config.swing_max_candidates_each
    ]
    return sorted(
        [*highs, *lows],
        key=lambda item: (item.price, item.source_code),
    )


def _period_level_candidate(
    *,
    ticker: str,
    source_code: str,
    price: float,
    source_date: date,
    confirmed_at: date,
    timeframe: str,
    structure_kind: str,
) -> LevelCandidate:
    if not math.isfinite(price) or price <= 0:
        raise ValueError(f"Invalid structural level {source_code}: {price!r}")
    return LevelCandidate(
        ticker=ticker.upper(),
        price=price,
        source_type="STRUCTURAL",
        source_code=source_code,
        timeframe=timeframe,
        indicator_code=None,
        config_id=None,
        config_code=None,
        component_code=None,
        source_date=source_date,
        confirmed_at=confirmed_at,
        source_role=SOURCE_ROLE_LEVEL,
        source_family=SOURCE_FAMILY_MARKET_STRUCTURE,
        value_semantic=VALUE_SEMANTIC_PRICE_LEVEL,
        metadata={"structure_kind": structure_kind},
    )


def load_previous_period_level_candidates(
    connection: Any,
    *,
    ticker: str,
    as_of_date: date,
    timeframes: Sequence[str] = SUPPORTED_TIMEFRAMES,
    structural_config: StructuralSourceConfig | None = None,
) -> list[LevelCandidate]:
    """Previous completed week/month H/L only; never uses the current partial period."""
    del timeframes
    config = structural_config or StructuralSourceConfig()
    df = _load_structural_history(
        connection,
        ticker=ticker,
        as_of_date=as_of_date,
        lookback_days=config.historical_lookback_days,
    )
    if df.empty:
        return []

    result: list[LevelCandidate] = []
    current_week_start = as_of_date - timedelta(days=as_of_date.weekday())
    previous_week = df[df["Date"].dt.date < current_week_start].copy()
    if not previous_week.empty:
        iso = previous_week["Date"].dt.isocalendar()
        previous_week["_iso_year"] = iso.year
        previous_week["_iso_week"] = iso.week
        latest_key = previous_week[["_iso_year", "_iso_week"]].iloc[-1]
        group = previous_week[
            (previous_week["_iso_year"] == latest_key["_iso_year"])
            & (previous_week["_iso_week"] == latest_key["_iso_week"])
        ]
        source_date = pd.Timestamp(group["Date"].max()).date()
        result.extend(
            [
                _period_level_candidate(
                    ticker=ticker,
                    source_code="PREV_WEEK_HIGH",
                    price=float(group["High"].max()),
                    source_date=source_date,
                    confirmed_at=current_week_start,
                    timeframe="W",
                    structure_kind="PREVIOUS_WEEK_HIGH",
                ),
                _period_level_candidate(
                    ticker=ticker,
                    source_code="PREV_WEEK_LOW",
                    price=float(group["Low"].min()),
                    source_date=source_date,
                    confirmed_at=current_week_start,
                    timeframe="W",
                    structure_kind="PREVIOUS_WEEK_LOW",
                ),
            ]
        )

    current_month_start = as_of_date.replace(day=1)
    previous_month = df[df["Date"].dt.date < current_month_start].copy()
    if not previous_month.empty:
        previous_month["_period"] = previous_month["Date"].dt.to_period("M")
        latest_period = previous_month["_period"].iloc[-1]
        group = previous_month[previous_month["_period"] == latest_period]
        source_date = pd.Timestamp(group["Date"].max()).date()
        result.extend(
            [
                _period_level_candidate(
                    ticker=ticker,
                    source_code="PREV_MONTH_HIGH",
                    price=float(group["High"].max()),
                    source_date=source_date,
                    confirmed_at=current_month_start,
                    timeframe="M",
                    structure_kind="PREVIOUS_MONTH_HIGH",
                ),
                _period_level_candidate(
                    ticker=ticker,
                    source_code="PREV_MONTH_LOW",
                    price=float(group["Low"].min()),
                    source_date=source_date,
                    confirmed_at=current_month_start,
                    timeframe="M",
                    structure_kind="PREVIOUS_MONTH_LOW",
                ),
            ]
        )
    return result


def load_52w_level_candidates(
    connection: Any,
    *,
    ticker: str,
    as_of_date: date,
    timeframes: Sequence[str] = SUPPORTED_TIMEFRAMES,
    structural_config: StructuralSourceConfig | None = None,
) -> list[LevelCandidate]:
    """Rolling 52-week high/low using only observations available at as_of_date."""
    del timeframes
    config = structural_config or StructuralSourceConfig()
    df = _load_structural_history(
        connection,
        ticker=ticker,
        as_of_date=as_of_date,
        lookback_days=config.historical_lookback_days,
    )
    if df.empty:
        return []

    window_start = as_of_date - timedelta(days=365)
    window = df[df["Date"].dt.date >= window_start]
    if window.empty:
        return []

    high_index = window["High"].idxmax()
    low_index = window["Low"].idxmin()
    high_date = pd.Timestamp(window.loc[high_index, "Date"]).date()
    low_date = pd.Timestamp(window.loc[low_index, "Date"]).date()
    return [
        _period_level_candidate(
            ticker=ticker,
            source_code="HIGH_52W",
            price=float(window.loc[high_index, "High"]),
            source_date=high_date,
            confirmed_at=as_of_date,
            timeframe="D",
            structure_kind="HIGH_52W",
        ),
        _period_level_candidate(
            ticker=ticker,
            source_code="LOW_52W",
            price=float(window.loc[low_index, "Low"]),
            source_date=low_date,
            confirmed_at=as_of_date,
            timeframe="D",
            structure_kind="LOW_52W",
        ),
    ]


def _source_provider_registry() -> dict[str, dict[str, Any]]:
    """Return the V2.1 provider registry without coupling the core pipeline to sources."""
    return {
        "MA": {
            "role": SOURCE_ROLE_LEVEL,
            "family": SOURCE_FAMILY_TREND_AVERAGE,
            "loader": load_ma_level_candidates,
        },
        "BB": {
            "role": SOURCE_ROLE_LEVEL,
            "family": SOURCE_FAMILY_VOLATILITY_BAND,
            "loader": load_bb_level_candidates,
        },
        "SWING": {
            "role": SOURCE_ROLE_LEVEL,
            "family": SOURCE_FAMILY_MARKET_STRUCTURE,
            "loader": load_swing_level_candidates,
            "uses_structural_config": True,
        },
        "PREVIOUS_HL": {
            "role": SOURCE_ROLE_LEVEL,
            "family": SOURCE_FAMILY_MARKET_STRUCTURE,
            "loader": load_previous_period_level_candidates,
            "uses_structural_config": True,
        },
        "52W_HL": {
            "role": SOURCE_ROLE_LEVEL,
            "family": SOURCE_FAMILY_MARKET_STRUCTURE,
            "loader": load_52w_level_candidates,
            "uses_structural_config": True,
        },
        "ATR": {
            "role": SOURCE_ROLE_CONTEXT,
            "family": SOURCE_FAMILY_VOLATILITY_CONTEXT,
            "loader": load_atr_market_contexts,
        },
        "RSI": {
            "role": SOURCE_ROLE_CONFIRMATION,
            "family": SOURCE_FAMILY_MOMENTUM_CONFIRMATION,
            "loader": load_rsi_confirmation_contexts,
        },
    }


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
        confirmed_at = candidate.confirmed_at or candidate.source_date
        if confirmed_at > current_price.as_of_date:
            raise ValueError(
                "Candidate confirmed_at is after CurrentPrice.as_of_date"
            )
        if candidate.timeframe and candidate.timeframe not in SUPPORTED_TIMEFRAMES:
            raise ValueError(f"Unsupported candidate timeframe: {candidate.timeframe}")
        if candidate.source_role != SOURCE_ROLE_LEVEL:
            raise ValueError(
                f"Only LEVEL candidates may enter normalization: {candidate.source_role}"
            )
        if candidate.value_semantic != VALUE_SEMANTIC_PRICE_LEVEL:
            raise ValueError(
                "LEVEL candidate must have ValueSemantic=PRICE_LEVEL: "
                f"{candidate.source_code}={candidate.value_semantic}"
            )
        price = float(candidate.price)
        if not math.isfinite(price) or price <= 0:
            raise ValueError(f"Invalid candidate price: {candidate.price!r}")
        tf_weight = config.timeframe_weights.get(candidate.timeframe or "", 1.0)
        source_weight = 1.0
        if candidate.indicator_code == "MA":
            source_weight = config.ma_length_weights.get(
                int(candidate.metadata.get("length", 0) or 0), 1.0
            )
        elif candidate.indicator_code == "BB":
            source_weight = config.bb_component_weights.get(
                candidate.component_code or "", 1.0
            )
        result.append(
            NormalizedLevel(
                price=price,
                source_type=candidate.source_type,
                source_code=candidate.source_code,
                timeframe=candidate.timeframe,
                weight=float(tf_weight * source_weight),
                source_date=candidate.source_date,
                confirmed_at=confirmed_at,
                config_id=candidate.config_id,
                config_code=candidate.config_code,
                component_code=candidate.component_code,
                source_role=candidate.source_role,
                source_family=candidate.source_family,
                value_semantic=candidate.value_semantic,
                metadata=dict(candidate.metadata),
            )
        )
    return sorted(result, key=lambda x: (x.price, x.source_code, x.timeframe or ""))


def _weighted_price(levels: Sequence[NormalizedLevel]) -> float:
    total = sum(max(level.weight, 0.0) for level in levels)
    if total <= 0:
        return sum(level.price for level in levels) / len(levels)
    return sum(level.price * max(level.weight, 0.0) for level in levels) / total


def resolve_adaptive_thresholds(
    *,
    current_price: CurrentPrice,
    market_contexts: Sequence[MarketContext],
    min_cluster_pct: float,
    min_neutral_pct: float,
    strength_config: StrengthConfig | None = None,
) -> tuple[float, float]:
    """Resolve V2.1 cluster/neutral percentages from ATR14_D with percent floors."""
    config = strength_config or StrengthConfig()
    cluster_floor = _validate_pct("cluster_threshold_pct", min_cluster_pct, 0.10)
    neutral_floor = _validate_pct("neutral_threshold_pct", min_neutral_pct, 0.10)
    if config.atr_cluster_multiplier < 0 or config.atr_neutral_multiplier < 0:
        raise ValueError("ATR multipliers must be >= 0")

    eligible = [
        context
        for context in market_contexts
        if context.indicator_code == "ATR"
        and context.timeframe == "D"
        and context.source_date <= current_price.as_of_date
        and context.value > 0
    ]
    if not eligible:
        return cluster_floor, neutral_floor

    context = max(eligible, key=lambda item: item.source_date)
    atr_pct = float(context.value) / current_price.price
    if not math.isfinite(atr_pct) or atr_pct <= 0:
        return cluster_floor, neutral_floor

    return (
        max(cluster_floor, atr_pct * config.atr_cluster_multiplier),
        max(neutral_floor, atr_pct * config.atr_neutral_multiplier),
    )


def cluster_levels(
    levels: Sequence[NormalizedLevel],
    *,
    cluster_threshold_pct: float = 0.01,
) -> list[LevelZone]:
    """Group nearby levels into deterministic zones."""
    threshold = _validate_pct("cluster_threshold_pct", cluster_threshold_pct, 1.00)
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
            source_family_count=len({x.source_family for x in cluster}),
        )
        for index, cluster in enumerate(clusters, start=1)
    ]


def classify_zones(
    zones: Sequence[LevelZone],
    *,
    current_price: CurrentPrice,
    neutral_threshold_pct: float = 0.003,
) -> list[LevelZone]:
    neutral = _validate_pct("neutral_threshold_pct", neutral_threshold_pct, 1.00)
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


def _rsi_confirmation_score(
    zone: LevelZone,
    confirmations: Sequence[ConfirmationContext],
    config: StrengthConfig,
) -> float:
    if zone.level_type not in {"SUPPORT", "RESISTANCE"} or not confirmations:
        return 0.0

    weighted_total = 0.0
    weight_sum = 0.0
    for context in confirmations:
        if context.indicator_code != "RSI":
            continue
        value = float(context.value)
        if zone.level_type == "SUPPORT":
            denominator = 50.0 - config.rsi_oversold
            raw = (50.0 - value) / denominator * 100.0 if denominator > 0 else 0.0
        else:
            denominator = config.rsi_overbought - 50.0
            raw = (value - 50.0) / denominator * 100.0 if denominator > 0 else 0.0
        score = max(0.0, min(raw, 100.0))
        weight = config.timeframe_weights.get(context.timeframe or "", 1.0)
        weighted_total += score * max(weight, 0.0)
        weight_sum += max(weight, 0.0)

    return weighted_total / weight_sum if weight_sum > 0 else 0.0


def _structural_quality_score(
    zone: LevelZone,
    *,
    current_price: CurrentPrice,
    config: StrengthConfig,
) -> tuple[float, bool]:
    structural = [
        source
        for source in zone.sources
        if source.source_family == SOURCE_FAMILY_MARKET_STRUCTURE
    ]
    if not structural:
        return 0.0, False
    if config.structural_recency_days <= 0:
        raise ValueError("structural_recency_days must be > 0")

    scores = []
    for source in structural:
        age = max((current_price.as_of_date - source.source_date).days, 0)
        scores.append(
            max(0.0, 1.0 - age / float(config.structural_recency_days)) * 100.0
        )
    return sum(scores) / len(scores), True


def score_zones(
    zones: Sequence[LevelZone],
    *,
    current_price: CurrentPrice,
    price_history: pd.DataFrame | None,
    strength_config: StrengthConfig | None = None,
    confirmations: Sequence[ConfirmationContext] = (),
) -> list[ScoredLevel]:
    """Strength V2.1 adds structural quality while preserving family diversity."""
    config = strength_config or StrengthConfig()
    base_weights = (
        config.confluence_weight,
        config.timeframe_weight,
        config.touch_weight,
        config.recency_weight,
    )
    all_weights = (
        *base_weights,
        config.confirmation_weight,
        config.structural_quality_weight,
    )
    if any(w < 0 for w in all_weights) or sum(base_weights) <= 0:
        raise ValueError("Strength weights must be non-negative and base weights sum to > 0")
    if config.family_confluence_target <= 0:
        raise ValueError("family_confluence_target must be > 0")
    if config.touch_target <= 0 or config.recency_days <= 0:
        raise ValueError("touch_target and recency_days must be > 0")
    if not 0 <= config.touch_tolerance_pct <= 0.05:
        raise ValueError("touch_tolerance_pct must be between 0 and 0.05")
    if not 0 <= config.rsi_oversold < 50 < config.rsi_overbought <= 100:
        raise ValueError("RSI thresholds must satisfy 0 <= oversold < 50 < overbought <= 100")

    for context in confirmations:
        if context.ticker.upper() != current_price.ticker:
            raise ValueError("Confirmation ticker does not match CurrentPrice")
        if context.source_date > current_price.as_of_date:
            raise ValueError("Confirmation source_date is after CurrentPrice.as_of_date")

    tf_total = (
        sum(config.timeframe_weights.get(tf, 0.0) for tf in SUPPORTED_TIMEFRAMES)
        or 1.0
    )
    result: list[ScoredLevel] = []
    for zone in zones:
        confluence = min(
            zone.source_family_count / float(config.family_confluence_target),
            1.0,
        ) * 100.0
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
        confirmation = _rsi_confirmation_score(zone, confirmations, config)
        structural_quality, has_structural = _structural_quality_score(
            zone,
            current_price=current_price,
            config=config,
        )

        weighted_score = (
            confluence * config.confluence_weight
            + timeframe * config.timeframe_weight
            + touch * config.touch_weight
            + recency * config.recency_weight
        )
        effective_weight = sum(base_weights)
        if confirmations and zone.level_type in {"SUPPORT", "RESISTANCE"}:
            weighted_score += confirmation * config.confirmation_weight
            effective_weight += config.confirmation_weight
        if has_structural:
            weighted_score += (
                structural_quality * config.structural_quality_weight
            )
            effective_weight += config.structural_quality_weight

        score = weighted_score / effective_weight
        result.append(
            ScoredLevel(
                zone=zone,
                strength_score=round(score, 2),
                confluence_score=round(confluence, 2),
                timeframe_score=round(timeframe, 2),
                touch_score=round(touch, 2),
                recency_score=round(recency, 2),
                confirmation_score=round(confirmation, 2),
                structural_quality_score=round(structural_quality, 2),
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
            source_family_count=zone.source_family_count,
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
    confirmations: Sequence[ConfirmationContext] = (),
    market_contexts: Sequence[MarketContext] = (),
) -> LevelLadderResult:
    """Pure V2.1 pipeline with optional ATR-adaptive distance context."""
    cluster_pct_used, neutral_pct_used = resolve_adaptive_thresholds(
        current_price=current_price,
        market_contexts=market_contexts,
        min_cluster_pct=cluster_threshold_pct,
        min_neutral_pct=neutral_threshold_pct,
        strength_config=strength_config,
    )
    normalized = normalize_levels(
        candidates, current_price=current_price, strength_config=strength_config
    )
    zones = cluster_levels(normalized, cluster_threshold_pct=cluster_pct_used)
    zones = classify_zones(
        zones,
        current_price=current_price,
        neutral_threshold_pct=neutral_pct_used,
    )
    scored = score_zones(
        zones,
        current_price=current_price,
        price_history=price_history,
        strength_config=strength_config,
        confirmations=confirmations,
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
        confirmations=tuple(confirmations),
        market_contexts=tuple(market_contexts),
        cluster_threshold_pct_used=round(cluster_pct_used, 6),
        neutral_threshold_pct_used=round(neutral_pct_used, 6),
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
    structural_config: StructuralSourceConfig | None = None,
    connection: Any | None = None,
) -> LevelLadderResult:
    """Build R/S Ladder V2.1 from LEVEL, CONTEXT and CONFIRMATION providers."""
    normalized_ticker = _normalize_ticker(ticker)
    normalized_timeframes = _validate_timeframes(timeframes)
    _validate_pct("cluster_threshold_pct", cluster_threshold_pct, 0.10)
    _validate_pct("neutral_threshold_pct", neutral_threshold_pct, 0.10)
    if max_support_levels <= 0 or max_resistance_levels <= 0:
        raise ValueError("max_support_levels and max_resistance_levels must be > 0")

    registry = _source_provider_registry()
    sources = (
        set(registry)
        if enabled_sources is None
        else {str(source).strip().upper() for source in enabled_sources}
    )
    unsupported = sources - set(registry)
    if unsupported:
        raise ValueError(
            f"Unsupported R/S V2.1 sources: {sorted(unsupported)}; "
            f"supported={sorted(registry)}"
        )

    LOGGER.info(
        "RS Ladder V2.1 start | ticker=%s as_of=%s timeframes=%s sources=%s cluster_floor=%.4f",
        normalized_ticker,
        as_of_date,
        normalized_timeframes,
        sorted(sources),
        cluster_threshold_pct,
    )

    def calculate(con: Any) -> LevelLadderResult:
        current = load_current_price(
            con, ticker=normalized_ticker, as_of_date=as_of_date
        )
        candidates: list[LevelCandidate] = []
        confirmations: list[ConfirmationContext] = []
        market_contexts: list[MarketContext] = []

        for source in sorted(sources):
            spec = registry[source]
            loader_kwargs: dict[str, Any] = {
                "ticker": normalized_ticker,
                "as_of_date": current.as_of_date,
                "timeframes": normalized_timeframes,
            }
            if spec.get("uses_structural_config"):
                loader_kwargs["structural_config"] = (
                    structural_config or StructuralSourceConfig()
                )
            loaded = spec["loader"](con, **loader_kwargs)
            if spec["role"] == SOURCE_ROLE_LEVEL:
                candidates.extend(loaded)
            elif spec["role"] == SOURCE_ROLE_CONTEXT:
                market_contexts.extend(loaded)
            elif spec["role"] == SOURCE_ROLE_CONFIRMATION:
                confirmations.extend(loaded)
            else:
                raise RuntimeError(
                    f"Unsupported provider role in V2.1 registry: {spec['role']}"
                )

        history = load_price_history(
            con, ticker=normalized_ticker, as_of_date=current.as_of_date
        )
        LOGGER.info(
            "RS Ladder V2.1 inputs | ticker=%s date=%s candidates=%d "
            "contexts=%d confirmations=%d history=%d",
            normalized_ticker,
            current.as_of_date,
            len(candidates),
            len(market_contexts),
            len(confirmations),
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
            confirmations=confirmations,
            market_contexts=market_contexts,
        )
        LOGGER.info(
            "RS Ladder V2.1 success | ticker=%s supports=%d resistances=%d "
            "cluster=%.4f neutral=%.4f",
            normalized_ticker,
            len(result.support_levels),
            len(result.resistance_levels),
            result.cluster_threshold_pct_used or cluster_threshold_pct,
            result.neutral_threshold_pct_used or neutral_threshold_pct,
        )
        return result

    if connection is not None:
        return calculate(connection)

    try:
        with DuckDBManager(read_only=True) as con:
            return calculate(con)
    except Exception:
        LOGGER.exception("RS Ladder V2.1 failed | ticker=%s", normalized_ticker)
        raise
