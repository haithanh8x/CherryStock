from __future__ import annotations

from src.mcp_server.duckdb_service import DuckDBReadService


def test_health_check_uses_read_only_project_connection(mcp_test_db):
    service = DuckDBReadService()

    result = service.health_check()

    assert result["status"] == "ok"
    assert result["access"] == "read-only"


def test_table_stats_returns_relation_row_count(mcp_test_db):
    service = DuckDBReadService()

    result = service.table_stats("vw_Ticker_indicators")

    assert result == {
        "schema": "main",
        "relation": "vw_Ticker_indicators",
        "row_count": 7,
    }
