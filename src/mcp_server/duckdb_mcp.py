"""Read-only MCP server for CherryStock's local DuckDB.

V1 intentionally exposes no database write/DDL tool. All reads use the
centralized CherryStock DuckDB access layer and domain tools prefer public
vw_* contracts over internal persistence tables.

Run:
    python -m src.mcp_server.duckdb_mcp --transport stdio
    python -m src.mcp_server.duckdb_mcp --transport http --port 8765
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = Path(__file__).resolve().parents[1]
for _path in (_PROJECT_ROOT, _SRC_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcp.server import MCPServer

from .config import settings
from .duckdb_service import DuckDBReadService
from .security import clamp_query_limit, validate_readonly_sql


mcp = MCPServer("cherrymon-duckdb")
_service = DuckDBReadService()


@mcp.tool()
def health_check() -> dict[str, Any]:
    """Check that CherryStock DuckDB is reachable through a read-only connection."""

    return _service.health_check()


@mcp.tool()
def list_relations() -> list[dict[str, Any]]:
    """List tables and views in CherryStock main schema."""

    return _service.list_relations()


@mcp.tool()
def describe_relation(relation_name: str) -> list[dict[str, Any]]:
    """Describe columns for one CherryStock table or view."""

    return _service.describe_relation(relation_name)


@mcp.tool()
def get_ticker_indicators(
    ticker: str,
    timeframe: str = "Daily",
) -> dict[str, Any]:
    """Get the latest indicators for a ticker from vw_Ticker_indicators."""

    return _service.get_ticker_indicators(
        ticker=ticker,
        timeframe=timeframe,
    )


@mcp.tool()
def get_indicator_history(
    ticker: str,
    timeframe: str = "Daily",
    limit: int = 30,
) -> dict[str, Any]:
    """Get bounded indicator history from vw_Ticker_indicators."""

    return _service.get_indicator_history(
        ticker=ticker,
        timeframe=timeframe,
        limit=limit,
    )


@mcp.tool()
def get_indicator_config(indicator: str) -> dict[str, Any]:
    """Get indicator configuration from vw_Indicator_config."""

    return _service.get_indicator_config(indicator)


@mcp.tool()
def query_readonly(sql: str, max_rows: int = 100) -> dict[str, Any]:
    """Run one restricted SELECT/WITH query against CherryStock.

    Prefer the domain-specific indicator/metadata tools when they satisfy
    the request. This generic query tool blocks write/DDL, extensions,
    attached databases, filesystem readers, external URLs, and multiple
    statements.
    """

    safe_sql = validate_readonly_sql(sql)
    safe_limit = clamp_query_limit(max_rows, settings.max_query_rows)
    return _service.execute_readonly_query(safe_sql, safe_limit)


@mcp.tool()
def table_stats(relation_name: str) -> dict[str, Any]:
    """Return row count for one CherryStock table/view."""

    return _service.table_stats(relation_name)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CherryStock read-only DuckDB MCP server"
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="stdio for local hosts/IDEs; http for Streamable HTTP.",
    )
    parser.add_argument("--host", default=settings.host)
    parser.add_argument("--port", type=int, default=settings.port)
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the MCP server with stdio or localhost Streamable HTTP transport."""

    args = _build_parser().parse_args(argv)

    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return

    if not 1 <= args.port <= 65535:
        raise ValueError("--port must be between 1 and 65535.")

    mcp.run(
        transport="streamable-http",
        host=args.host,
        port=args.port,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )


if __name__ == "__main__":
    main()
