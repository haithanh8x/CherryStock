from __future__ import annotations

import pytest

from src.mcp_server.duckdb_service import DuckDBReadService
from src.mcp_server.security import (
    clamp_query_limit,
    validate_readonly_sql,
    validate_write_sql,
)


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM main.ticker_indicator_source",
        "DROP TABLE main.ticker_indicator_source",
        "ATTACH 'other.duckdb'",
        "SELECT * FROM read_parquet('C:/private/*.parquet')",
        "SELECT * FROM 'C:/private/data.parquet'",
        "SELECT * FROM read_csv_auto('https://example.com/data.csv')",
        "SELECT 1; SELECT 2",
        "PRAGMA database_list",
    ],
)
def test_unsafe_sql_is_blocked(sql):
    with pytest.raises(ValueError):
        validate_readonly_sql(sql)


def test_comments_do_not_bypass_readonly_policy():
    with pytest.raises(ValueError, match="Forbidden SQL keyword"):
        validate_readonly_sql(
            "WITH x AS (SELECT 1) /* harmless */ DELETE FROM main.t"
        )


def test_readonly_sql_and_limit_are_allowed_and_bounded(mcp_test_db):
    service = DuckDBReadService()
    sql = validate_readonly_sql(
        "SELECT Ticker, Date FROM main.vw_Ticker_indicators ORDER BY Date DESC"
    )

    result = service.execute_readonly_query(
        sql,
        clamp_query_limit(999, 500),
    )

    assert result["row_count"] == 7
    assert result["truncated"] is False
    assert clamp_query_limit(999, 500) == 500


def test_query_result_is_truncated_at_requested_limit(mcp_test_db):
    service = DuckDBReadService()
    sql = validate_readonly_sql(
        "SELECT Ticker, Date FROM main.vw_Ticker_indicators ORDER BY Date DESC"
    )

    result = service.execute_readonly_query(sql, 2)

    assert result["row_count"] == 2
    assert result["truncated"] is True


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE main.dim_indicator",
        "TRUNCATE main.cal_indicator_values",
        "ALTER TABLE main.dim_indicator ADD COLUMN x INT",
        "ATTACH 'other.duckdb'",
        "CREATE TABLE t (x INT)",
        "PRAGMA database_list",
        "SET GLOBAL memory_limit='10GB'",
        "SELECT 1",
        "MERGE INTO t USING s ON t.id = s.id",
        "INSERT INTO t VALUES (1); DELETE FROM t",
    ],
)
def test_unsafe_write_sql_is_blocked(sql):
    with pytest.raises(ValueError):
        validate_write_sql(sql)


def test_update_delete_without_where_is_blocked_by_default():
    with pytest.raises(ValueError, match="WHERE clause"):
        validate_write_sql("UPDATE main.dim_indicator SET IsActive = TRUE")
    with pytest.raises(ValueError, match="WHERE clause"):
        validate_write_sql("DELETE FROM main.dim_indicator_config")


def test_update_delete_without_where_allowed_with_explicit_flag():
    safe_sql = validate_write_sql(
        "DELETE FROM main.dim_indicator_config", allow_full_scan=True
    )
    assert safe_sql == "DELETE FROM main.dim_indicator_config"


def test_insert_update_delete_with_where_are_allowed():
    assert validate_write_sql(
        "INSERT INTO main.dim_indicator (IndicatorCode) VALUES ('ATR')"
    )
    assert validate_write_sql(
        "UPDATE main.dim_indicator SET IsActive = TRUE WHERE IndicatorCode = 'ATR'"
    )
    assert validate_write_sql(
        "DELETE FROM main.dim_indicator_config WHERE ConfigId = 1"
    )
