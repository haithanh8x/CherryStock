# CherryStock DuckDB MCP Server

MCP server for the local CherryMon DuckDB. The server supports MCP Python SDK 1.x and 2.x during the SDK migration window.

## Safety contract

- Reads use CherryStock's centralized DuckDB layer through a read-only connection.
- Generic read SQL is limited to a single `SELECT` / `WITH` statement and a maximum of 500 returned rows.
- Writes are limited to a single guarded `INSERT` / `UPDATE` / `DELETE` statement per `execute_write` call. DDL (`CREATE`/`ALTER`/`DROP`/`TRUNCATE`), `ATTACH`/`DETACH`, `COPY`/`EXPORT`/`IMPORT`, `PRAGMA`/`SET`, extension loading, filesystem readers and external URL readers stay forbidden.
- `UPDATE`/`DELETE` without a `WHERE` clause is blocked unless the caller explicitly passes `allow_full_scan=True`.
- Related writes should be wrapped in `begin_transaction()` / `commit_transaction()` / `rollback_transaction()` so a mid-sequence failure rolls back cleanly; a standalone `execute_write` call auto-commits as its own transaction.
- Set `CHERRYSTOCK_MCP_ENABLE_WRITE=false` to disable all write tools at runtime.
- Indicator tools join the long-form public SSOT views `main.vw_Ticker_indicators` and `main.vw_Indicator_config` by `ConfigId + ComponentCode`.

## MCP tools

| Tool | Purpose |
| --- | --- |
| `health_check()` | Verify read-only DB access |
| `list_relations()` | List `main` tables/views |
| `describe_relation(relation_name)` | Inspect relation columns |
| `get_ticker_indicators(ticker, timeframe)` | Latest D/W/M indicators |
| `get_indicator_history(ticker, timeframe, limit)` | Bounded indicator history |
| `get_indicator_config(indicator)` | Indicator configuration SSOT |
| `query_readonly(sql, max_rows)` | Restricted analytical SQL |
| `table_stats(relation_name)` | Relation row count |
| `begin_transaction()` | Open one explicit write transaction |
| `execute_write(sql, params, allow_full_scan)` | Guarded INSERT/UPDATE/DELETE |
| `commit_transaction()` | Commit the open write transaction |
| `rollback_transaction()` | Roll back the open write transaction |

## Install

```powershell
cd C:\Github\CherryStock
.\.venv\Scripts\Activate.ps1
pip install -U -e ".[mcp,dev]"
```

## Run with stdio

```powershell
python -m src.mcp_server.duckdb_mcp --transport stdio
```

## Run with Streamable HTTP

```powershell
.\scripts\start_mcp_duckdb.ps1 -Transport http
```

Endpoint:

```text
http://127.0.0.1:8765/mcp
```

The default bind is localhost only. Do not change it to `0.0.0.0` unless a separate security design explicitly requires it.

## Full runbook

See `docs/runbook/MCP_DuckDB.md`.
