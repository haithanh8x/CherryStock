"""Configuration for the CherryStock DuckDB MCP server."""

from __future__ import annotations

from dataclasses import dataclass
import os


ABSOLUTE_MAX_QUERY_ROWS = 500


def _read_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default

    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc

    if not minimum <= value <= maximum:
        raise ValueError(
            f"{name} must be between {minimum} and {maximum}, got {value}"
        )
    return value


@dataclass(frozen=True)
class MCPSettings:
    """Runtime settings that are specific to the local MCP server."""

    host: str
    port: int
    max_query_rows: int


def load_mcp_settings() -> MCPSettings:
    """Load MCP settings from environment variables with safe local defaults."""

    host = (os.getenv("CHERRYSTOCK_MCP_HOST") or "127.0.0.1").strip()
    if not host:
        host = "127.0.0.1"

    return MCPSettings(
        host=host,
        port=_read_int(
            "CHERRYSTOCK_MCP_PORT",
            8765,
            minimum=1,
            maximum=65535,
        ),
        max_query_rows=_read_int(
            "CHERRYSTOCK_MCP_MAX_QUERY_ROWS",
            ABSOLUTE_MAX_QUERY_ROWS,
            minimum=1,
            maximum=ABSOLUTE_MAX_QUERY_ROWS,
        ),
    )


settings = load_mcp_settings()
