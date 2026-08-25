from datetime import date

import pandas as pd
import pytest

from src.calcEngine.calcIndicators import (
    IndicatorComponent,
    IndicatorConfig,
    IndicatorDefinition,
    _period_checkpoint_start,
    _resolve_checkpoint_start_date,
    normalize_indicator_output,
    resample_indicator_timeframe,
    validate_indicator_config,
)


def test_checkpoint_uses_main_days_diff_contract() -> None:
    assert _resolve_checkpoint_start_date(
        source_min_date=date(2025, 1, 1),
        source_max_date=date(2026, 8, 25),
        from_last_day=9,
    ) == date(2026, 8, 16)

    assert _resolve_checkpoint_start_date(
        source_min_date=date(2025, 1, 1),
        source_max_date=date(2026, 8, 25),
        from_last_day=None,
    ) == date(2025, 1, 1)


def test_weekly_and_monthly_cleanup_start_at_period_boundary() -> None:
    assert _period_checkpoint_start(date(2026, 8, 25), "D") == date(2026, 8, 25)
    assert _period_checkpoint_start(date(2026, 8, 25), "W") == date(2026, 8, 24)
    assert _period_checkpoint_start(date(2026, 8, 25), "M") == date(2026, 8, 1)


def test_resample_weekly_uses_last_actual_trading_date() -> None:
    source_df = pd.DataFrame(
        {
            "Ticker": ["FPT", "FPT", "FPT"],
            "Date": pd.to_datetime(["2026-08-24", "2026-08-25", "2026-08-26"]),
            "Open": [100.0, 102.0, 101.0],
            "High": [103.0, 104.0, 105.0],
            "Low": [99.0, 100.0, 100.5],
            "Close": [102.0, 101.0, 104.0],
            "Volume": [10, 20, 30],
        }
    )

    weekly = resample_indicator_timeframe(source_df, "W")

    assert len(weekly) == 1
    assert weekly.loc[0, "Date"] == pd.Timestamp("2026-08-26")
    assert weekly.loc[0, "Open"] == 100.0
    assert weekly.loc[0, "High"] == 105.0
    assert weekly.loc[0, "Low"] == 99.0
    assert weekly.loc[0, "Close"] == 104.0
    assert weekly.loc[0, "Volume"] == 60


def test_normalize_multi_output_uses_longest_component_prefix() -> None:
    index = pd.to_datetime(["2026-08-24", "2026-08-25"])
    raw_output = pd.DataFrame(
        {
            "MACD_12_26_9": [1.0, 1.1],
            "MACDs_12_26_9": [0.8, 0.9],
            "MACDh_12_26_9": [0.2, 0.2],
        },
        index=index,
    )
    config = IndicatorConfig(
        config_id=1,
        config_code="MACD12_26_9_D",
        indicator_code="MACD",
        timeframe="D",
        parameters={"fast": 12, "slow": 26, "signal": 9},
        warmup_bars=35,
    )
    components = [
        IndicatorComponent("MACD", "LINE", "MACD Line", "MACD", 1, True),
        IndicatorComponent("MACD", "SIGNAL", "Signal", "MACDs", 2, False),
        IndicatorComponent("MACD", "HIST", "Histogram", "MACDh", 3, False),
    ]

    normalized = normalize_indicator_output(
        ticker="FPT",
        config=config,
        raw_output=raw_output,
        source_index=index,
        components=components,
    )

    assert set(normalized["ComponentCode"]) == {"LINE", "SIGNAL", "HIST"}
    assert len(normalized) == 6


def test_validate_macd_rejects_fast_greater_than_slow() -> None:
    definition = IndicatorDefinition(
        indicator_code="MACD",
        indicator_name="MACD",
        category="MOMENTUM",
        engine="PANDAS_TA_CLASSIC",
        function_name="macd",
        required_inputs=("Close",),
        parameter_schema=None,
    )
    config = IndicatorConfig(
        config_id=1,
        config_code="BAD_MACD",
        indicator_code="MACD",
        timeframe="D",
        parameters={"fast": 30, "slow": 20, "signal": 9},
        warmup_bars=40,
    )

    with pytest.raises(ValueError, match="fast < slow"):
        validate_indicator_config(config, definition)
