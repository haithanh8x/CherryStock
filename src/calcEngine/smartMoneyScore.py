from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

import numpy as np
import pandas as pd

from cherrystock.config.settings import settings
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory
from cherrystock.infrastructure.database.repositories.smart_money_repository import (
    SmartMoneyRepository,
)


MARKET_DATA_VIEW = '"CherryMon"."main"."vw_Ticker_OHLC_D"'
BENCHMARK_TABLE = '"CherryMon"."main"."raw_index_eod"'
INDICATOR_VALUE_VIEW = '"CherryMon"."main"."vw_Ticker_indicators"'
INDICATOR_CONFIG_VIEW = '"CherryMon"."main"."vw_Indicator_config"'
TICKER_TABLE = '"CherryMon"."main"."raw_lstTicker"'
BENCHMARK_CODE = "VNINDEX"

PUBLIC_FACTOR_COLUMNS = {
    "FRESH_FLOW": "FreshFlowScore",
    "RELATIVE_LIQUIDITY": "RelativeLiquidityScore",
    "LIQUIDITY_ACCELERATION": "LiquidityAccelerationScore",
    "RELATIVE_STRENGTH": "RelativeStrengthScore",
    "ACCUMULATION": "AccumulationScore",
    "ACCUMULATION_MEMORY": "AccumulationMemoryScore",
    "SUPPLY_LOCK": "SupplyLockScore",
    "LIMIT_UP": "LimitUpScore",
    "TREND": "TrendScore",
    "DISTRIBUTION": "DistributionScore",
}

RAW_FACTOR_COLUMNS = {
    "FRESH_FLOW": "FreshFlowRaw",
    "RELATIVE_LIQUIDITY": "RVAL20",
    "LIQUIDITY_ACCELERATION": "LiquidityAccelerationRaw",
    "RELATIVE_STRENGTH": "RelativeStrengthRaw",
    "ACCUMULATION": "AccumulationRaw",
    "ACCUMULATION_MEMORY": "AccumulationMemoryScore",
    "SUPPLY_LOCK": "SupplyLockScore",
    "LIMIT_UP": "LimitUpScore",
    "TREND": "TrendRaw",
    "DISTRIBUTION": "DistributionRaw",
}

FACTOR_SOURCE = {
    "FRESH_FLOW": "RAW_OHLCV+TRADING_VALUE",
    "RELATIVE_LIQUIDITY": "TRADING_VALUE",
    "LIQUIDITY_ACCELERATION": "TRADING_VALUE",
    "RELATIVE_STRENGTH": "BENCHMARK_VNINDEX",
    "ACCUMULATION": "RAW_OHLCV+INDICATOR",
    "ACCUMULATION_MEMORY": "SMART_MONEY_MEMORY",
    "SUPPLY_LOCK": "SMART_MONEY_COMPOSITE",
    "LIMIT_UP": "MARKET_LIMIT",
    "TREND": "INDICATOR",
    "DISTRIBUTION": "RAW_OHLCV+TRADING_VALUE+BENCHMARK",
}

SCORE_STATES = (
    "ACCUMULATION",
    "BREAKOUT",
    "DEMAND_EXPANSION",
    "SUPPLY_LOCK",
    "MARKUP",
    "DISTRIBUTION",
    "LIQUIDITY_DRYUP",
    "SELLING_CLIMAX",
    "NEUTRAL",
)


def _active_ticker_filter(tickers: Iterable[str] | None) -> tuple[str, list[object]]:
    if not tickers:
        return "", []
    normalized = sorted({str(ticker).strip().upper() for ticker in tickers if str(ticker).strip()})
    if not normalized:
        return "", []
    placeholders = ", ".join("?" for _ in normalized)
    return f" AND e.Ticker IN ({placeholders})", normalized


def load_market_data(connection, tickers: Iterable[str] | None = None) -> pd.DataFrame:
    """Load active-universe daily OHLCV/liquidity inputs through the public market view."""
    ticker_filter, params = _active_ticker_filter(tickers)
    frame = connection.execute(
        f"""
        SELECT
            e.Ticker,
            e.Date,
            e.Open,
            e.High,
            e.Low,
            e.Close,
            e.Volume,
            e.TradingValue,
            e.TradingValue_Source,
            e.TradingValue_IsProxy
        FROM {MARKET_DATA_VIEW} AS e
        INNER JOIN {TICKER_TABLE} AS t
            ON t.Ticker = e.Ticker
        WHERE t.Status = 'Y'
          {ticker_filter}
        ORDER BY e.Ticker, e.Date
        """,
        params,
    ).df()
    if not frame.empty:
        frame["Date"] = pd.to_datetime(frame["Date"])
    return frame


def load_benchmark_data(connection) -> pd.DataFrame:
    frame = connection.execute(
        f"""
        SELECT
            Date,
            Close
        FROM {BENCHMARK_TABLE}
        WHERE Ticker = ?
        ORDER BY Date
        """,
        [BENCHMARK_CODE],
    ).df()
    if not frame.empty:
        frame["Date"] = pd.to_datetime(frame["Date"])
        frame["BenchmarkClose"] = pd.to_numeric(frame["Close"], errors="coerce")
        frame = frame.drop(columns=["Close"])
        for window in (5, 20, 60):
            frame[f"BenchmarkReturn{window}"] = frame["BenchmarkClose"].pct_change(
                periods=window,
                fill_method=None,
            )
    return frame


def load_daily_indicator_data(connection) -> pd.DataFrame:
    """Load the V1 MA/OBV/AD evidence through public Indicator Engine views."""
    frame = connection.execute(
        f"""
        SELECT
            v.Ticker,
            v.Date,
            cfg.ConfigCode,
            v.Value
        FROM {INDICATOR_VALUE_VIEW} AS v
        INNER JOIN {INDICATOR_CONFIG_VIEW} AS cfg
            ON cfg.ConfigId = v.ConfigId
           AND cfg.ComponentCode = v.ComponentCode
        WHERE cfg.ConfigCode IN ('MA20_D', 'MA50_D', 'OBV_D', 'AD_D')
          AND cfg.ConfigIsEnabled = TRUE
          AND cfg.IndicatorIsActive = TRUE
          AND cfg.ComponentIsActive = TRUE
          AND v.ComponentCode = 'VALUE'
        ORDER BY v.Ticker, v.Date, cfg.ConfigCode
        """
    ).df()
    if frame.empty:
        return pd.DataFrame(columns=["Ticker", "Date", "MA20", "MA50", "OBV", "AD"])

    frame["Date"] = pd.to_datetime(frame["Date"])
    pivoted = (
        frame.pivot_table(
            index=["Ticker", "Date"],
            columns="ConfigCode",
            values="Value",
            aggfunc="last",
        )
        .reset_index()
        .rename(
            columns={
                "MA20_D": "MA20",
                "MA50_D": "MA50",
                "OBV_D": "OBV",
                "AD_D": "AD",
            }
        )
    )
    for column in ("MA20", "MA50", "OBV", "AD"):
        if column not in pivoted.columns:
            pivoted[column] = np.nan
    return pivoted[["Ticker", "Date", "MA20", "MA50", "OBV", "AD"]]


def _market_limit_view_exists(connection) -> bool:
    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.views
        WHERE lower(table_schema) = 'main'
          AND lower(table_name) = 'vw_stock_market_limit_eod'
        """
    ).fetchone()[0]
    return int(count) > 0


def load_market_limit_data(connection) -> pd.DataFrame:
    """Load point-in-time market-limit evidence when the approved target view exists."""
    if not _market_limit_view_exists(connection):
        return pd.DataFrame(
            columns=[
                "Ticker",
                "Date",
                "LimitUp",
                "LimitUpStreak",
                "MarketLimitQuality",
            ]
        )

    frame = connection.execute(
        """
        SELECT
            Ticker,
            Date,
            LimitUp,
            LimitUpStreak,
            MarketLimitQuality
        FROM "CherryMon"."main"."vw_stock_market_limit_eod"
        ORDER BY Ticker, Date
        """
    ).df()
    if not frame.empty:
        frame["Date"] = pd.to_datetime(frame["Date"])
    return frame


def _rolling(grouped, column: str, window: int, *, min_periods: int | None = None) -> pd.Series:
    minimum = window if min_periods is None else min_periods
    return grouped[column].transform(lambda values: values.rolling(window, min_periods=minimum).mean())


def _pct_change(grouped, column: str, periods: int) -> pd.Series:
    return grouped[column].transform(
        lambda values: values.pct_change(periods=periods, fill_method=None)
    )


def cross_sectional_percentile(
    frame: pd.DataFrame,
    raw_column: str,
    *,
    min_count: int = 5,
) -> pd.Series:
    """Same-date percentile normalization without cross-date look-ahead."""
    def _rank(values: pd.Series) -> pd.Series:
        valid = values.notna().sum()
        if int(valid) < int(min_count):
            return pd.Series(np.nan, index=values.index, dtype=float)
        return values.rank(method="average", pct=True) * 100.0

    return frame.groupby("Date", group_keys=False)[raw_column].transform(_rank)


def _safe_mean(columns: list[pd.Series]) -> pd.Series:
    return pd.concat(columns, axis=1).mean(axis=1, skipna=True)


def _geometric_composite(frame: pd.DataFrame, columns: list[str], min_available: int) -> pd.Series:
    values = frame[columns].astype(float)
    available = values.notna().sum(axis=1)
    clipped = values.clip(lower=1e-6, upper=100.0) / 100.0
    logs = np.log(clipped)
    result = np.exp(logs.mean(axis=1, skipna=True)) * 100.0
    return result.where(available >= min_available)


def calculate_base_features(
    market_data: pd.DataFrame,
    benchmark_data: pd.DataFrame,
    indicator_data: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate point-in-time raw V1 features for the complete normalization universe."""
    if market_data.empty:
        return market_data.copy()

    frame = market_data.copy()
    frame = frame.sort_values(["Ticker", "Date"]).reset_index(drop=True)
    numeric_columns = ["Open", "High", "Low", "Close", "Volume", "TradingValue"]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    grouped = frame.groupby("Ticker", group_keys=False)
    for window in (1, 5, 20, 60):
        frame[f"Return{window}"] = _pct_change(grouped, "Close", window)

    spread = frame["High"] - frame["Low"]
    frame["CLV"] = (
        ((frame["Close"] - frame["Low"]) - (frame["High"] - frame["Close"])) / spread
    ).where(spread != 0)

    for window in (5, 20, 60):
        frame[f"ALV{window}"] = _rolling(grouped, "TradingValue", window)

    frame["RVAL20"] = (frame["TradingValue"] / frame["ALV20"]).where(frame["ALV20"] > 0)
    frame["LiquidityAccelerationRaw"] = (frame["ALV5"] / frame["ALV20"]).where(
        frame["ALV20"] > 0
    )
    frame["LiquidityAccelerationLong"] = (frame["ALV20"] / frame["ALV60"]).where(
        frame["ALV60"] > 0
    )
    frame["LiquidityCompressionRaw"] = 1.0 - frame["LiquidityAccelerationRaw"].clip(
        lower=0.0,
        upper=1.0,
    )
    frame["CLV20"] = grouped["CLV"].transform(
        lambda values: values.rolling(20, min_periods=10).mean()
    )
    frame["High60"] = grouped["High"].transform(
        lambda values: values.rolling(60, min_periods=20).max()
    )
    frame["NearHigh60"] = (frame["Close"] / frame["High60"] - 1.0).where(
        frame["High60"] > 0
    )
    frame["HistoryDepthSessions"] = grouped.cumcount() + 1

    if benchmark_data is not None and not benchmark_data.empty:
        frame = frame.merge(benchmark_data, on="Date", how="left")
    else:
        for column in (
            "BenchmarkClose",
            "BenchmarkReturn5",
            "BenchmarkReturn20",
            "BenchmarkReturn60",
        ):
            frame[column] = np.nan

    for window in (5, 20, 60):
        frame[f"RS{window}"] = frame[f"Return{window}"] - frame[f"BenchmarkReturn{window}"]

    frame["RelativeStrengthRaw"] = (
        frame[["RS5", "RS20", "RS60"]]
        .mul([0.20, 0.50, 0.30], axis=1)
        .sum(axis=1, min_count=1)
    )

    if indicator_data is not None and not indicator_data.empty:
        frame = frame.merge(indicator_data, on=["Ticker", "Date"], how="left")
    else:
        for column in ("MA20", "MA50", "OBV", "AD"):
            frame[column] = np.nan

    frame["TrendRaw"] = _safe_mean(
        [
            (frame["Close"] / frame["MA20"] - 1.0).where(frame["MA20"] > 0),
            (frame["Close"] / frame["MA50"] - 1.0).where(frame["MA50"] > 0),
        ]
    )

    grouped = frame.groupby("Ticker", group_keys=False)
    volume20 = _rolling(grouped, "Volume", 20, min_periods=10).replace(0, np.nan)
    frame["OBVSlope20"] = (
        grouped["OBV"].transform(lambda values: values - values.shift(20)) / volume20
    )
    frame["ADSlope20"] = (
        grouped["AD"].transform(lambda values: values - values.shift(20)) / volume20
    )

    frame["FreshFlowRaw"] = (
        frame["CLV"].fillna(0.0)
        + 2.0 * frame["Return5"].fillna(0.0)
        + 1.5 * frame["RS5"].fillna(0.0)
    ) * np.log1p(frame["RVAL20"].clip(lower=0.0).fillna(0.0))

    accumulation_parts = pd.concat(
        [
            frame["CLV20"],
            frame["RS20"] * 10.0,
            frame["OBVSlope20"],
            frame["ADSlope20"],
        ],
        axis=1,
    )
    frame["AccumulationRaw"] = accumulation_parts.mean(axis=1, skipna=True).where(
        accumulation_parts.notna().sum(axis=1) >= 2
    )

    weakness = (-frame["Return5"]).clip(lower=0.0)
    relative_weakness = (-frame["RS20"]).clip(lower=0.0)
    close_weakness = (-frame["CLV"]).clip(lower=0.0)
    participation = (frame["RVAL20"] - 1.0).clip(lower=0.0)
    frame["DistributionRaw"] = (
        participation
        * (0.40 * close_weakness + 0.35 * weakness * 10.0 + 0.25 * relative_weakness * 10.0)
    )

    frame["CloseStrengthRaw"] = _safe_mean(
        [
            (frame["CLV"] + 1.0) / 2.0,
            (1.0 + frame["NearHigh60"].clip(lower=-1.0, upper=0.0)),
        ]
    )

    normalize_pairs = {
        "FreshFlowRaw": "FreshFlowScore",
        "RVAL20": "RelativeLiquidityScore",
        "LiquidityAccelerationRaw": "LiquidityAccelerationScore",
        "RelativeStrengthRaw": "RelativeStrengthScore",
        "AccumulationRaw": "AccumulationScore",
        "TrendRaw": "TrendScore",
        "DistributionRaw": "DistributionScore",
        "LiquidityCompressionRaw": "LiquidityCompressionScore",
        "CloseStrengthRaw": "CloseStrengthScore",
        "ALV20": "LiquidityAdequacyScore",
        "Return1": "Return1Score",
    }
    for raw_column, normalized_column in normalize_pairs.items():
        frame[normalized_column] = cross_sectional_percentile(frame, raw_column)

    exact_quality = np.select(
        [
            frame["TradingValue_Source"].eq("INTRADAY_TICK"),
            frame["TradingValue_Source"].eq("NO_TRADE"),
            frame["TradingValue_IsProxy"].eq(True),
        ],
        [100.0, 100.0, 70.0],
        default=0.0,
    )
    frame["TradingValueQualityPoint"] = exact_quality
    grouped = frame.groupby("Ticker", group_keys=False)
    frame["TradingValueQuality20"] = grouped["TradingValueQualityPoint"].transform(
        lambda values: values.rolling(20, min_periods=1).mean()
    )

    return frame


def _apply_accumulation_memory(frame: pd.DataFrame, memory_lambda: float) -> pd.Series:
    alpha = 1.0 - float(memory_lambda)
    if not 0.0 < alpha <= 1.0:
        raise ValueError("MEMORY_LAMBDA must be in [0, 1).")
    return frame.groupby("Ticker", group_keys=False)["AccumulationScore"].transform(
        lambda values: values.ewm(alpha=alpha, adjust=False, ignore_na=True).mean()
    )


def _apply_market_limit_evidence(
    frame: pd.DataFrame,
    market_limit_data: pd.DataFrame,
    *,
    streak_k: float = 0.55,
) -> pd.DataFrame:
    result = frame.copy()
    if market_limit_data is None or market_limit_data.empty:
        result["LimitUp"] = pd.NA
        result["LimitUpStreak"] = np.nan
        result["MarketLimitQuality"] = "UNAVAILABLE"
        result["LimitUpScore"] = np.nan
        return result

    result = result.merge(market_limit_data, on=["Ticker", "Date"], how="left")
    trusted = result["MarketLimitQuality"].isin(
        ["AUTHORITATIVE", "VALIDATED_PROVIDER", "DERIVED_AS_TRADED"]
    )
    streak = pd.to_numeric(result["LimitUpStreak"], errors="coerce").clip(lower=0.0)
    score = np.where(
        result["LimitUp"].eq(True),
        100.0 * (1.0 - np.exp(-float(streak_k) * streak.fillna(1.0))),
        np.where(result["LimitUp"].eq(False), 0.0, np.nan),
    )
    result["LimitUpScore"] = pd.Series(score, index=result.index).where(trusted)
    return result


def _detect_states(frame: pd.DataFrame, config: dict[str, object]) -> pd.Series:
    state = pd.Series("NEUTRAL", index=frame.index, dtype="object")

    distribution_threshold = float(config.get("STATE_DISTRIBUTION_THRESHOLD", 70.0))
    supply_threshold = float(config.get("STATE_SUPPLY_LOCK_THRESHOLD", 70.0))
    breakout_threshold = float(config.get("STATE_BREAKOUT_THRESHOLD", 70.0))
    accumulation_threshold = float(config.get("STATE_ACCUMULATION_THRESHOLD", 65.0))
    markup_threshold = float(config.get("STATE_MARKUP_THRESHOLD", 65.0))
    dryup_threshold = float(config.get("STATE_DRYUP_THRESHOLD", 75.0))

    # Apply low-precedence states first; higher-precedence states overwrite later.
    state.loc[
        (frame["LiquidityCompressionScore"] >= dryup_threshold)
        & (frame["RelativeStrengthScore"] < 55.0)
    ] = "LIQUIDITY_DRYUP"

    state.loc[
        (frame["DistributionScore"] >= 60.0)
        & (frame["RelativeLiquidityScore"] >= 80.0)
        & (frame["Return1"] < 0.0)
    ] = "SELLING_CLIMAX"

    state.loc[
        (frame["TrendScore"] >= markup_threshold)
        & (frame["RelativeStrengthScore"] >= 60.0)
    ] = "MARKUP"

    state.loc[
        (frame["AccumulationScore"] >= accumulation_threshold)
        & (frame["AccumulationMemoryScore"] >= 60.0)
    ] = "ACCUMULATION"

    state.loc[
        (frame["RelativeLiquidityScore"] >= 70.0)
        & (frame["LiquidityAccelerationScore"] >= 65.0)
        & (frame["RelativeStrengthScore"] >= 55.0)
    ] = "DEMAND_EXPANSION"

    state.loc[
        (frame["FreshFlowScore"] >= breakout_threshold)
        & (frame["RelativeLiquidityScore"] >= 70.0)
        & (frame["RelativeStrengthScore"] >= 60.0)
    ] = "BREAKOUT"

    state.loc[
        (frame["SupplyLockScore"] >= supply_threshold)
        & (frame["AccumulationMemoryScore"] >= 60.0)
    ] = "SUPPLY_LOCK"

    # DISTRIBUTION is highest precedence in V1.
    state.loc[frame["DistributionScore"] >= distribution_threshold] = "DISTRIBUTION"
    return state


def _score_by_state(
    frame: pd.DataFrame,
    weights: pd.DataFrame,
    config: dict[str, object],
) -> pd.DataFrame:
    result = frame.copy()
    result["PositiveScore"] = np.nan
    result["FactorCoverage"] = 0.0

    weight_profiles: dict[str, dict[str, float]] = {}
    for market_state, group in weights.groupby("MarketState"):
        weight_profiles[str(market_state)] = {
            str(row.FactorCode): float(row.Weight)
            for row in group.itertuples(index=False)
        }

    for market_state in SCORE_STATES:
        mask = result["MarketState"].eq(market_state)
        if not mask.any():
            continue
        profile = weight_profiles.get(market_state) or weight_profiles.get("NEUTRAL", {})
        total_weight = float(sum(profile.values()))
        if total_weight <= 0:
            raise ValueError(f"No positive SmartMoney weights for state={market_state}.")

        numerator = pd.Series(0.0, index=result.index)
        available_weight = pd.Series(0.0, index=result.index)
        for factor_code, weight in profile.items():
            column = PUBLIC_FACTOR_COLUMNS.get(factor_code)
            if not column or column not in result.columns:
                continue
            available = result[column].notna()
            numerator = numerator + result[column].fillna(0.0) * float(weight)
            available_weight = available_weight + available.astype(float) * float(weight)

        positive = (numerator / available_weight.replace(0.0, np.nan)).clip(0.0, 100.0)
        result.loc[mask, "PositiveScore"] = positive.loc[mask]
        result.loc[mask, "FactorCoverage"] = (
            available_weight.loc[mask] / total_weight
        ).clip(0.0, 1.0)

    default_penalty = float(config.get("DISTRIBUTION_PENALTY_DEFAULT", 0.35))
    distribution_penalty = float(
        config.get("DISTRIBUTION_PENALTY_DISTRIBUTION", 0.75)
    )
    penalty_factor = pd.Series(default_penalty, index=result.index)
    penalty_factor.loc[result["MarketState"].eq("DISTRIBUTION")] = distribution_penalty

    result["SmartMoneyScore"] = (
        result["PositiveScore"]
        - penalty_factor * result["DistributionScore"].fillna(0.0)
    ).clip(0.0, 100.0)
    return result


def _calculate_confidence(frame: pd.DataFrame, config: dict[str, object]) -> pd.DataFrame:
    result = frame.copy()
    history = (result["HistoryDepthSessions"] / 60.0).clip(0.0, 1.0) * 100.0
    liquidity = result["LiquidityAdequacyScore"].fillna(0.0).clip(0.0, 100.0)
    trading_value_quality = result["TradingValueQuality20"].fillna(0.0).clip(0.0, 100.0)
    benchmark = result["RS20"].notna().astype(float) * 100.0
    indicator = (
        50.0
        + result["OBV"].notna().astype(float) * 25.0
        + result["AD"].notna().astype(float) * 25.0
    )
    market_limit = np.where(result["LimitUpScore"].notna(), 100.0, 60.0)

    result["ConfidenceScore"] = (
        0.30 * result["FactorCoverage"].clip(0.0, 1.0) * 100.0
        + 0.15 * history
        + 0.15 * liquidity
        + 0.15 * trading_value_quality
        + 0.10 * benchmark
        + 0.10 * indicator
        + 0.05 * market_limit
    ).clip(0.0, 100.0)

    preferred_coverage = float(config.get("PREFERRED_FACTOR_COVERAGE", 0.80))
    result["DataQualityStatus"] = np.where(
        result["SmartMoneyScore"].isna(),
        "INVALID",
        np.where(
            (result["ConfidenceScore"] >= 60.0)
            & (result["FactorCoverage"] >= preferred_coverage),
            "PASS",
            "WARNING",
        ),
    )
    return result


def calculate_model_frame(
    base_features: pd.DataFrame,
    market_limit_data: pd.DataFrame,
    *,
    config: dict[str, object],
    weights: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate one model version over a precomputed no-look-ahead base feature frame."""
    frame = base_features.copy()
    frame["AccumulationMemoryScore"] = _apply_accumulation_memory(
        frame,
        float(config.get("MEMORY_LAMBDA", 0.90)),
    )

    frame = _apply_market_limit_evidence(frame, market_limit_data)

    supply_components = [
        "AccumulationMemoryScore",
        "CloseStrengthScore",
        "RelativeStrengthScore",
        "TrendScore",
        "LiquidityCompressionScore",
    ]
    supply_base = _geometric_composite(frame, supply_components, min_available=4)
    frame["SupplyLockScore"] = (
        supply_base * (1.0 - frame["DistributionScore"].fillna(0.0) / 100.0)
    ).clip(0.0, 100.0)

    frame["MarketState"] = _detect_states(frame, config)
    frame = _score_by_state(frame, weights, config)
    frame = _calculate_confidence(frame, config)
    return frame


def _factor_quality(frame: pd.DataFrame, factor_code: str) -> pd.Series:
    if factor_code in {"RELATIVE_LIQUIDITY", "LIQUIDITY_ACCELERATION"}:
        return np.where(
            frame["TradingValue_Source"].eq("MISSING_INPUT"),
            "UNAVAILABLE",
            np.where(frame["TradingValue_IsProxy"].eq(True), "PROXY", "EXACT"),
        )
    if factor_code == "FRESH_FLOW":
        return np.where(
            frame[PUBLIC_FACTOR_COLUMNS[factor_code]].isna(),
            "UNAVAILABLE",
            np.where(frame["TradingValue_IsProxy"].eq(True), "PROXY", "EXACT"),
        )
    if factor_code == "RELATIVE_STRENGTH":
        return np.where(frame["RS20"].notna(), "EXACT", "UNAVAILABLE")
    if factor_code == "TREND":
        return np.where(frame["TrendScore"].notna(), "EXACT", "UNAVAILABLE")
    if factor_code == "ACCUMULATION":
        indicator_count = frame[["OBV", "AD"]].notna().sum(axis=1)
        return np.where(
            frame["AccumulationScore"].isna(),
            "UNAVAILABLE",
            np.where(indicator_count >= 2, "EXACT", "PARTIAL"),
        )
    if factor_code == "ACCUMULATION_MEMORY":
        return np.where(frame["AccumulationMemoryScore"].notna(), "PARTIAL", "UNAVAILABLE")
    if factor_code == "SUPPLY_LOCK":
        return np.where(frame["SupplyLockScore"].notna(), "PARTIAL", "UNAVAILABLE")
    if factor_code == "LIMIT_UP":
        quality = frame.get("MarketLimitQuality")
        if quality is None:
            return np.full(len(frame), "UNAVAILABLE", dtype=object)
        normalized = quality.fillna("PARTIAL").map(
            {
                "AUTHORITATIVE": "EXACT",
                "VALIDATED_PROVIDER": "EXACT",
                "DERIVED_AS_TRADED": "PARTIAL",
                "PARTIAL": "PARTIAL",
                "UNAVAILABLE": "UNAVAILABLE",
            }
        ).fillna("PARTIAL")
        return np.where(
            frame["LimitUpScore"].isna(),
            "UNAVAILABLE",
            normalized,
        )
    if factor_code == "DISTRIBUTION":
        return np.where(
            frame["DistributionScore"].isna(),
            "UNAVAILABLE",
            np.where(frame["TradingValue_IsProxy"].eq(True), "PROXY", "EXACT"),
        )
    return np.where(
        frame[PUBLIC_FACTOR_COLUMNS[factor_code]].notna(),
        "PARTIAL",
        "UNAVAILABLE",
    )


def build_factor_rows(
    model_frame: pd.DataFrame,
    factor_catalog: pd.DataFrame,
    *,
    model_id: int,
) -> pd.DataFrame:
    factor_ids = {
        str(row.FactorCode): int(row.FactorId)
        for row in factor_catalog.itertuples(index=False)
    }
    rows: list[pd.DataFrame] = []
    for factor_code, normalized_column in PUBLIC_FACTOR_COLUMNS.items():
        factor_id = factor_ids.get(factor_code)
        if factor_id is None:
            raise ValueError(f"Missing factor metadata for {factor_code}.")
        raw_column = RAW_FACTOR_COLUMNS[factor_code]
        part = pd.DataFrame(
            {
                "ModelId": int(model_id),
                "Ticker": model_frame["Ticker"],
                "Date": model_frame["Date"],
                "FactorId": int(factor_id),
                "RawValue": pd.to_numeric(model_frame[raw_column], errors="coerce"),
                "NormalizedValue": pd.to_numeric(
                    model_frame[normalized_column],
                    errors="coerce",
                ).clip(0.0, 100.0),
                "DataQuality": _factor_quality(model_frame, factor_code),
                "SourceCode": FACTOR_SOURCE[factor_code],
            }
        )
        rows.append(part)
    return pd.concat(rows, ignore_index=True)


def _target_start_date(source_max: pd.Timestamp, from_last_day: int | None) -> pd.Timestamp:
    if from_last_day is None:
        return pd.Timestamp.min.normalize()
    if int(from_last_day) < 0:
        raise ValueError("from_last_day cannot be negative.")
    return source_max.normalize() - pd.Timedelta(days=int(from_last_day))


def refresh_smart_money_score(
    from_last_day: int | None = None,
    tickers: Iterable[str] | None = None,
    model_ids: Iterable[int] | None = None,
    connection=None,
    repository: SmartMoneyRepository | None = None,
) -> dict[str, object]:
    """Calculate and atomically replace SmartMoneyScore checkpoint rows.

    V1 intentionally reads the full active-universe source history before replacing
    only target checkpoint rows. This guarantees deterministic rolling windows and
    accumulation memory for full versus incremental overlap.
    """
    owns_connection = connection is None
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    con = connection or factory.create_writer()
    repo = repository or SmartMoneyRepository(con)
    owns_transaction = owns_connection
    if owns_transaction:
        con.execute("BEGIN")

    try:
        # Always load the full active universe so same-date percentiles do not depend
        # on the requested persistence subset.
        market_data = load_market_data(con, tickers=None)
        if market_data.empty:
            summary = {
                "status": "NO_DATA",
                "factor_rows_upserted": 0,
                "score_rows_upserted": 0,
                "warnings": 1,
            }
            if owns_transaction:
                con.execute("COMMIT")
                owns_transaction = False
            return summary

        source_max = pd.Timestamp(market_data["Date"].max())
        target_start = _target_start_date(source_max, from_last_day)
        requested = None
        if tickers:
            requested = {
                str(ticker).strip().upper()
                for ticker in tickers
                if str(ticker).strip()
            }

        benchmark = load_benchmark_data(con)
        indicators = load_daily_indicator_data(con)
        market_limits = load_market_limit_data(con)
        base = calculate_base_features(market_data, benchmark, indicators)

        models = repo.load_enabled_models(model_ids)
        if not models:
            raise RuntimeError(
                "No enabled SmartMoney model. Run src/DuckDB/sql/smart_money_v1_schema.sql first."
            )

        factor_catalog = repo.load_factor_catalog()
        total_factor_rows = 0
        total_score_rows = 0
        state_counts: dict[str, int] = {}
        warning_count = 0
        low_confidence_count = 0
        proxy_liquidity_count = 0
        model_summaries: list[dict[str, object]] = []

        for model in models:
            as_of_date = source_max.date()
            config = repo.load_model_config(model.model_id, as_of_date)
            weights = repo.load_state_weights(model.model_id, as_of_date)
            if weights.empty:
                raise RuntimeError(f"No state weights for ModelId={model.model_id}.")

            model_frame = calculate_model_frame(
                base,
                market_limits,
                config=config,
                weights=weights,
            )

            target_mask = model_frame["Date"].ge(target_start)
            target_mask &= model_frame["Date"].ge(pd.Timestamp(model.effective_from))
            if model.effective_to is not None:
                target_mask &= model_frame["Date"].le(pd.Timestamp(model.effective_to))
            if requested is not None:
                target_mask &= model_frame["Ticker"].isin(requested)

            target = model_frame.loc[target_mask].copy()
            target = target.loc[target["SmartMoneyScore"].notna()].copy()
            if target.empty:
                model_summaries.append(
                    {
                        "model": model.model_code,
                        "version": model.model_version,
                        "scores": 0,
                        "factors": 0,
                    }
                )
                continue

            minimum_coverage = float(config.get("MIN_FACTOR_COVERAGE", 0.50))
            target = target.loc[target["FactorCoverage"] >= minimum_coverage].copy()
            if target.empty:
                continue

            factor_rows = build_factor_rows(
                target,
                factor_catalog,
                model_id=model.model_id,
            )
            score_rows = pd.DataFrame(
                {
                    "ModelId": int(model.model_id),
                    "Ticker": target["Ticker"],
                    "Date": target["Date"],
                    "SmartMoneyScore": target["SmartMoneyScore"].clip(0.0, 100.0),
                    "ConfidenceScore": target["ConfidenceScore"].clip(0.0, 100.0),
                    "MarketState": target["MarketState"],
                    "FactorCoverage": target["FactorCoverage"].clip(0.0, 1.0),
                    "DataQualityStatus": target["DataQualityStatus"],
                }
            )

            cleanup = pd.DataFrame(
                {
                    "ModelId": int(model.model_id),
                    "Ticker": sorted(score_rows["Ticker"].unique()),
                    "StartDate": target_start.date()
                    if target_start != pd.Timestamp.min.normalize()
                    else model.effective_from,
                }
            )

            factor_count, score_count = repo.replace_checkpoint(
                factor_values=factor_rows,
                ticker_scores=score_rows,
                cleanup=cleanup,
            )
            total_factor_rows += factor_count
            total_score_rows += score_count

            counts = target["MarketState"].value_counts().to_dict()
            for key, value in counts.items():
                state_counts[str(key)] = state_counts.get(str(key), 0) + int(value)
            warnings = int(target["DataQualityStatus"].eq("WARNING").sum())
            lows = int((target["ConfidenceScore"] < 60.0).sum())
            proxies = int(target["TradingValue_IsProxy"].eq(True).sum())
            warning_count += warnings
            low_confidence_count += lows
            proxy_liquidity_count += proxies
            model_summaries.append(
                {
                    "model": model.model_code,
                    "version": model.model_version,
                    "scores": score_count,
                    "factors": factor_count,
                }
            )

        summary = {
            "status": "OK",
            "source_start": str(pd.Timestamp(market_data["Date"].min()).date()),
            "source_end": str(source_max.date()),
            "target_start": None
            if target_start == pd.Timestamp.min.normalize()
            else str(target_start.date()),
            "models": model_summaries,
            "factor_rows_upserted": total_factor_rows,
            "score_rows_upserted": total_score_rows,
            "warning_count": warning_count,
            "low_confidence_count": low_confidence_count,
            "proxy_liquidity_count": proxy_liquidity_count,
            "state_distribution": state_counts,
        }
        if owns_transaction:
            con.execute("COMMIT")
        return summary
    except Exception:
        if owns_transaction:
            con.execute("ROLLBACK")
        raise
    finally:
        if owns_connection:
            con.close()
