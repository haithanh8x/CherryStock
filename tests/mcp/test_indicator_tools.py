from __future__ import annotations

import pytest

from src.mcp_server.duckdb_service import DuckDBReadService


def test_get_latest_mwg_daily_indicators(mcp_test_db):
    service = DuckDBReadService()

    result = service.get_ticker_indicators("mwg", "Daily")

    assert result["ticker"] == "MWG"
    assert result["timeframe"] == "Daily"
    assert result["as_of_date"] == "2026-08-29"
    assert result["row_count"] == 2
    assert {row["IndicatorCode"] for row in result["rows"]} == {"MA", "RSI"}
    assert {row["Timeframe"] for row in result["rows"]} == {"Daily"}

    values = {
        row["ConfigCode"]: row["Value"]
        for row in result["rows"]
    }
    assert values["MA20_D"] == pytest.approx(75.4)
    assert values["RSI14_D"] == pytest.approx(56.3)


def test_get_weekly_indicator_history_is_bounded(mcp_test_db):
    service = DuckDBReadService()

    result = service.get_indicator_history("MWG", "Weekly", limit=2)

    assert result["row_count"] == 2
    assert [row["Date"] for row in result["rows"]] == [
        "2026-08-29",
        "2026-08-22",
    ]
    assert {row["ConfigCode"] for row in result["rows"]} == {"RSI14_W"}
    assert {row["Timeframe"] for row in result["rows"]} == {"Weekly"}


def test_get_indicator_config_reads_configuration_ssot(mcp_test_db):
    service = DuckDBReadService()

    result = service.get_indicator_config("rsi")

    assert result["indicator"] == "RSI"
    assert result["row_count"] == 3
    assert {row["Timeframe"] for row in result["rows"]} == {
        "Daily",
        "Weekly",
        "Monthly",
    }


def test_invalid_timeframe_is_rejected(mcp_test_db):
    service = DuckDBReadService()

    with pytest.raises(ValueError, match="Daily, Weekly, Monthly"):
        service.get_ticker_indicators("MWG", "Hourly")
