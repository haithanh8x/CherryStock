from __future__ import annotations

import pytest

from src.mcp_server.duckdb_service import DuckDBReadService
from src.mcp_server.security import clamp_query_limit, validate_readonly_sql


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
