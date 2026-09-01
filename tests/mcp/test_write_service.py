from __future__ import annotations

import pytest

from src.mcp_server.duckdb_service import DuckDBReadService, DuckDBWriteService
from src.mcp_server.security import validate_write_sql


def test_execute_write_auto_commits_single_statement(mcp_test_db):
    write_service = DuckDBWriteService()
    read_service = DuckDBReadService()

    safe_sql = validate_write_sql(
        "UPDATE main.ticker_indicator_source SET Value = 99.9 "
        "WHERE Ticker = 'FPT' AND ConfigId = 1"
    )
    result = write_service.execute_write(safe_sql)

    assert result["status"] == "ok"
    assert result["transaction"] == "auto_committed"
    assert result["affected_rows"] == 1

    row = read_service.table_stats("ticker_indicator_source")
    assert row["row_count"] == 7


def test_explicit_transaction_commit_persists_changes(mcp_test_db):
    write_service = DuckDBWriteService()

    write_service.begin_transaction()
    write_service.execute_write(
        validate_write_sql(
            "DELETE FROM main.ticker_indicator_source WHERE Ticker = 'FPT'"
        )
    )
    result = write_service.commit_transaction()

    assert result["transaction"] == "committed"

    read_service = DuckDBReadService()
    stats = read_service.table_stats("ticker_indicator_source")
    assert stats["row_count"] == 6


def test_explicit_transaction_rollback_discards_changes(mcp_test_db):
    write_service = DuckDBWriteService()

    write_service.begin_transaction()
    write_service.execute_write(
        validate_write_sql(
            "DELETE FROM main.ticker_indicator_source WHERE Ticker = 'FPT'"
        )
    )
    result = write_service.rollback_transaction()

    assert result["transaction"] == "rolled_back"

    read_service = DuckDBReadService()
    stats = read_service.table_stats("ticker_indicator_source")
    assert stats["row_count"] == 7


def test_begin_transaction_twice_raises(mcp_test_db):
    write_service = DuckDBWriteService()
    write_service.begin_transaction()
    try:
        with pytest.raises(RuntimeError, match="already open"):
            write_service.begin_transaction()
    finally:
        write_service.rollback_transaction()


def test_commit_without_transaction_raises(mcp_test_db):
    write_service = DuckDBWriteService()
    with pytest.raises(RuntimeError, match="No open transaction"):
        write_service.commit_transaction()
