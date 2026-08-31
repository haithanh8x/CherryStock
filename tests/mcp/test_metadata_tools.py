from __future__ import annotations

import asyncio

import pytest

mcp_package = pytest.importorskip("mcp")
Client = mcp_package.Client

from src.mcp_server.duckdb_mcp import mcp
from src.mcp_server.duckdb_service import DuckDBReadService


def test_list_and_describe_indicator_views(mcp_test_db):
    service = DuckDBReadService()

    relations = service.list_relations()
    relation_names = {item["table_name"] for item in relations}

    assert "vw_Ticker_indicators" in relation_names
    assert "vw_Indicator_config" in relation_names

    columns = service.describe_relation("vw_Ticker_indicators")
    column_names = [item["column_name"] for item in columns]
    assert column_names == [
        "Ticker",
        "Date",
        "ConfigId",
        "ComponentCode",
        "Value",
    ]


def test_describe_unknown_relation_is_controlled(mcp_test_db):
    service = DuckDBReadService()

    with pytest.raises(ValueError, match="was not found"):
        service.describe_relation("does_not_exist")


def test_mcp_v1_tool_contract_exposes_no_write_tool():
    async def list_tool_names() -> set[str]:
        async with Client(mcp) as client:
            page = await client.list_tools()
            return {tool.name for tool in page.tools}

    names = asyncio.run(list_tool_names())

    assert {
        "health_check",
        "list_relations",
        "describe_relation",
        "get_ticker_indicators",
        "get_indicator_history",
        "get_indicator_config",
        "query_readonly",
        "table_stats",
    }.issubset(names)
    assert "execute" not in names
