"""MCP server for CherryStock's local DuckDB.

Reads use the centralized CherryStock DuckDB access layer and domain tools
prefer public vw_* contracts over internal persistence tables.

Writes are exposed through a guarded ``execute_write`` tool: only
INSERT/UPDATE/DELETE statements are allowed (validated by
``security.validate_write_sql``), DDL/ATTACH/PRAGMA/extension-loading stay
forbidden, and UPDATE/DELETE require a WHERE clause unless the caller passes
``allow_full_scan=True``. Related writes should be wrapped in
``begin_transaction``/``commit_transaction``/``rollback_transaction`` so a
failure mid-sequence rolls back cleanly. Set
``CHERRYSTOCK_MCP_ENABLE_WRITE=false`` to disable the write surface entirely.

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

try:
    # MCP Python SDK 2.x
    from mcp.server import MCPServer

    _MCP_SDK_V2 = True
except ImportError:  # pragma: no cover - exercised on MCP SDK 1.x
    # MCP Python SDK 1.x
    from mcp.server.fastmcp import FastMCP as MCPServer

    _MCP_SDK_V2 = False

try:
    # Package execution (python -m src.mcp_server.duckdb_mcp)
    from .config import settings
    from .duckdb_service import DuckDBReadService, DuckDBWriteService
    from .security import clamp_query_limit, validate_readonly_sql, validate_write_sql
except ImportError:
    # Direct script execution (python path/to/duckdb_mcp.py) has no parent
    # package, so relative imports fail; fall back to absolute imports.
    from mcp_server.config import settings
    from mcp_server.duckdb_service import DuckDBReadService, DuckDBWriteService
    from mcp_server.security import (
        clamp_query_limit,
        validate_readonly_sql,
        validate_write_sql,
    )


def _create_mcp_server() -> Any:
    """Create an MCP server compatible with Python SDK 1.x and 2.x."""

    if _MCP_SDK_V2:
        return MCPServer("cherrymon-duckdb")

    return MCPServer(
        "cherrymon-duckdb",
        host=settings.host,
        port=settings.port,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )


mcp = _create_mcp_server()
_service = DuckDBReadService()
_write_service = DuckDBWriteService()


def _require_write_enabled() -> None:
    if not settings.write_enabled:
        raise RuntimeError(
            "Write tools are disabled. Set CHERRYSTOCK_MCP_ENABLE_WRITE=true to enable."
        )


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


@mcp.tool()
def begin_transaction() -> dict[str, Any]:
    """Open one explicit write transaction for a sequence of related writes."""

    _require_write_enabled()
    return _write_service.begin_transaction()


@mcp.tool()
def execute_write(
    sql: str,
    params: list[Any] | None = None,
    allow_full_scan: bool = False,
) -> dict[str, Any]:
    """Execute one guarded INSERT/UPDATE/DELETE statement against CherryStock.

    Runs inside the transaction opened by ``begin_transaction`` when one is
    open; otherwise auto-commits as its own single-statement transaction.
    UPDATE/DELETE without a WHERE clause is blocked unless
    ``allow_full_scan=True`` is passed explicitly. DDL, ATTACH/DETACH, PRAGMA,
    extension loading and filesystem/export functions remain forbidden.
    """

    _require_write_enabled()
    safe_sql = validate_write_sql(sql, allow_full_scan=allow_full_scan)
    return _write_service.execute_write(safe_sql, params)


@mcp.tool()
def commit_transaction() -> dict[str, Any]:
    """Commit the currently open explicit write transaction."""

    _require_write_enabled()
    return _write_service.commit_transaction()


@mcp.tool()
def rollback_transaction() -> dict[str, Any]:
    """Roll back the currently open explicit write transaction."""

    _require_write_enabled()
    return _write_service.rollback_transaction()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CherryStock DuckDB MCP server"
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

    if _MCP_SDK_V2:
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            streamable_http_path="/mcp",
            stateless_http=True,
            json_response=True,
        )
        return

    # MCP SDK 1.x keeps HTTP configuration on FastMCP.settings.
    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.settings.streamable_http_path = "/mcp"
    mcp.settings.stateless_http = True
    mcp.settings.json_response = True
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
