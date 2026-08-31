# CherryStock DuckDB MCP Server

Read-only MCP V1 for the local CherryMon DuckDB.

## Safety contract

- All database access is read-only through CherryStock's centralized DuckDB layer.
- No `execute`, INSERT, UPDATE, DELETE, DDL, ATTACH, COPY, extension loading, filesystem readers, or external URL readers are exposed.
- Generic SQL is limited to a single `SELECT` / `WITH` statement and a maximum of 500 returned rows.
- Indicator tools read the public SSOT views `main.vw_Ticker_indicators` and `main.vw_Indicator_config`.

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

## Install

```powershell
cd C:\Github\CherryStock
.\.venv\Scripts\Activate.ps1
pip install -e ".[mcp,dev]"
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
