"""MCP server exposing read/write/DDL access to the local CherryMon DuckDB.

Run standalone:
    python -m src.mcp_server.duckdb_mcp
or register in VS Code / Claude settings with:
    command: <python>  args: [c:/Github/CherryStock/src/mcp_server/duckdb_mcp.py]

Tools:
- list_tables        : list tables/views in the database
- describe_table     : column schema of a table
- query              : run a SELECT/WITH query, return rows as JSON
- execute            : run INSERT/UPDATE/DELETE/ALTER/CREATE ... (write or DDL)
- table_stats        : row count + quick stats for a table

Safety: `execute` requires explicit confirmation flag because it mutates data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow direct script execution (python path/to/duckdb_mcp.py)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = Path(__file__).resolve().parents[1]
for _path in (_PROJECT_ROOT, _SRC_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcp.server.mcpserver import MCPServer

from cherrystock.config.settings import load_settings
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory

settings = load_settings()

mcp = MCPServer("cherrymon-duckdb")

_READ_KEYWORDS = ("select", "with", "pragma", "show", "describe")
_WRITE_KEYWORDS = (
    "insert", "update", "delete", "alter", "create", "drop",
    "truncate", "copy", "attach", "detach", "merge",
)


def _get_factory() -> DuckDBConnectionFactory:
    return DuckDBConnectionFactory(
        db_path=settings.local_db_path,
        duckdb_env=settings.duckdb_env,
        motherduck_token=settings.motherduck_token,
    )


def _classify(sql: str) -> str:
    """Classify a SQL statement as 'read' or 'write' based on leading keyword."""
    first_word = sql.lstrip().split(" ", 1)[0].lower().rstrip(";")
    if first_word in _READ_KEYWORDS:
        return "read"
    if first_word in _WRITE_KEYWORDS:
        return "write"
    return "unknown"


@mcp.tool()
def list_tables() -> str:
    """List all tables and views in the CherryMon DuckDB."""
    factory = _get_factory()
    with factory.create_reader() as con:
        rows = con.execute(
            """
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_schema, table_name
            """
        ).fetchall()
    return json.dumps(
        [
            {"schema": r[0], "name": r[1], "type": r[2]}
            for r in rows
        ],
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def describe_table(table_name: str) -> str:
    """Return the column schema of a table (name, type, nullable)."""
    if not table_name.replace("_", "").isalnum():
        raise ValueError(f"Invalid table name: {table_name!r}")
    factory = _get_factory()
    with factory.create_reader() as con:
        rows = con.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = ?
            ORDER BY ordinal_position
            """,
            [table_name],
        ).fetchall()
    if not rows:
        raise ValueError(f"Table not found: {table_name}")
    return json.dumps(
        [{"column": r[0], "type": r[1], "nullable": r[2]} for r in rows],
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def query(sql: str, max_rows: int = 100) -> str:
    """Execute a read-only SQL query (SELECT/WITH) and return rows as JSON.

    Args:
        sql: The SQL query. Must start with SELECT/WITH/SHOW/DESCRIBE.
        max_rows: Maximum number of rows to return (default 100).
    """
    kind = _classify(sql)
    if kind != "read":
        raise ValueError(
            f"query() only accepts read statements (SELECT/WITH). "
            f"Got {kind}. Use execute() for writes."
        )
    factory = _get_factory()
    with factory.create_reader() as con:
        cursor = con.execute(sql)
        columns = [d[0] for d in cursor.description]
        rows = cursor.fetchmany(max_rows)
    return json.dumps(
        {
            "columns": columns,
            "row_count": len(rows),
            "truncated": len(rows) == max_rows,
            "rows": rows,
        },
        ensure_ascii=False,
        default=str,
    )


@mcp.tool()
def execute(sql: str, confirm: bool = False) -> str:
    """Execute a write/DDL statement (INSERT/UPDATE/DELETE/ALTER/CREATE/DROP).

    Args:
        sql: The SQL statement to execute.
        confirm: Must be True to actually mutate the database.
    """
    kind = _classify(sql)
    if kind != "write":
        raise ValueError(
            f"execute() only accepts write/DDL statements. Got {kind!r}. "
            f"Use query() for reads."
        )
    if not confirm:
        return (
            "REFUSED: This statement modifies the database. "
            "Re-call execute() with confirm=true to apply it.\n"
            f"Statement: {sql}"
        )
    factory = _get_factory()
    with factory.create_writer() as con:
        con.execute(sql)
    return json.dumps({"status": "ok", "statement": sql})


@mcp.tool()
def table_stats(table_name: str) -> str:
    """Return row count and basic stats for a table."""
    if not table_name.replace("_", "").isalnum():
        raise ValueError(f"Invalid table name: {table_name!r}")
    factory = _get_factory()
    with factory.create_reader() as con:
        count = con.execute(
            f'SELECT COUNT(*) FROM "{table_name}"'
        ).fetchone()[0]
    return json.dumps({"table": table_name, "row_count": count})


if __name__ == "__main__":
    mcp.run(transport="stdio")
