# Runbook — CherryStock Local DuckDB MCP

## 1. Objective

Expose CherryStock's local DuckDB to MCP-capable AI hosts through a small, read-only MCP server. V1 must not allow the model to mutate CherryMon or use DuckDB as a filesystem/network reader.

Target architecture:

```text
MCP host / Inspector / local agent
                |
                | MCP
                v
      CherryStock MCP Server
      stdio OR 127.0.0.1:8765/mcp
                |
                | short-lived read-only connection
                v
            CherryMon
                |
         +------+------+
         |             |
         v             v
vw_Ticker_indicators  vw_Indicator_config
       SSOT                  SSOT
```

This implementation follows:
- `docs/adr/ADR-001-duckdb-connection.md`;
- `docs/adr/ADR-002-indicator-source-of-truth.md`;
- `.github/instructions/database.instructions.md`;
- `.github/instructions/testing.instructions.md`.

## 2. V1 safety contract

V1 is **read-only**.

Allowed:
- metadata discovery;
- domain-specific indicator reads;
- one bounded `SELECT` / `WITH` analytical query.

Not exposed/allowed:
- INSERT / UPDATE / DELETE / MERGE;
- CREATE / ALTER / DROP / TRUNCATE;
- ATTACH / DETACH;
- COPY / EXPORT / IMPORT;
- INSTALL / LOAD extensions;
- `read_csv*`, `read_parquet`, `read_json*`, `glob`, scan extensions;
- local file literals;
- HTTP/S3/GS/Azure/file URIs;
- multiple SQL statements.

Generic SQL returns at most 500 rows.

---

# PHASE 0 — Resolve the real CherryMon database

## Step 0.1 — Activate the CherryStock environment

```powershell
cd C:\Github\CherryStock
.\.venv\Scripts\Activate.ps1
```

## Step 0.2 — Inspect the resolved DB path

Do not hard-code a developer path in source code.

```powershell
python -c "from cherrystock.config.settings import settings; print(settings.local_db_path)"
```

`LOCAL_DB_PATH` remains the supported override.

## Step 0.3 — Verify a project-managed read-only connection

```powershell
python -c "from Ults.DuckLib import DuckDBManager; c=DuckDBManager(read_only=True); con=c.__enter__(); print(con.execute('SELECT current_database(), current_schema()').fetchone()); c.__exit__(None,None,None)"
```

Expected: database/schema are returned without creating a writer connection.

Stop if the database does not exist or is locked in an incompatible mode. Fix the environment/path before continuing.

---

# PHASE 1 — MCP package

CherryStock already owns `src/mcp_server`, so V1 **reuses that package** instead of creating a second MCP implementation.

Files:

```text
src/mcp_server/
  __init__.py
  config.py
  security.py
  duckdb_service.py
  duckdb_mcp.py
  README.md
```

This avoids a duplicate DB-access/MCP Source of Truth.

---

# PHASE 2 — Install dependencies

MCP is an optional CherryStock capability declared in `pyproject.toml`.

CherryStock MCP V1 supports both MCP Python SDK 1.x and 2.x during the SDK migration window:

```text
mcp[cli]>=1.27,<3
```

Install/update the local environment:

```powershell
pip install -U -e ".[mcp,dev]"
```

Verify:

```powershell
python -c "import importlib.metadata as m; print('mcp:', m.version('mcp'))"
python -c "import duckdb; print('duckdb:', duckdb.__version__)"
```

---

# PHASE 3 — MCP configuration

Defaults:

```text
host = 127.0.0.1
port = 8765
max query rows = 500
```

Optional `.env`/process overrides:

```text
CHERRYSTOCK_MCP_HOST
CHERRYSTOCK_MCP_PORT
CHERRYSTOCK_MCP_MAX_QUERY_ROWS
```

`CHERRYSTOCK_MCP_MAX_QUERY_ROWS` cannot exceed 500 in V1.

DuckDB path continues to come from CherryStock settings (`LOCAL_DB_PATH` / normal data-dir resolution).

---

# PHASE 4 — Read-only DB service

`src/mcp_server/duckdb_service.py` owns the MCP read service.

Rules:
- uses `DuckDBManager(read_only=True)`;
- every operation has a short-lived connection;
- no direct `duckdb.connect()` is introduced;
- no MCP write transaction exists;
- dynamic relation identifiers are resolved from `information_schema` before being quoted.

Automated check:

```powershell
python -m pytest tests/mcp/test_duckdb_service.py -v
```

---

# PHASE 5 — Domain tools first

V1 MCP tools:

```text
health_check
list_relations
describe_relation
get_ticker_indicators
get_indicator_history
get_indicator_config
query_readonly
table_stats
```

Prefer the domain tools over generic SQL.

There is intentionally **no `execute` tool**.

---

# PHASE 6 — MCP server

Implementation:

```text
src/mcp_server/duckdb_mcp.py
```

Start with stdio:

```powershell
python -m src.mcp_server.duckdb_mcp --transport stdio
```

`stdio` is appropriate for a local IDE/host that launches the MCP subprocess itself.

---

# PHASE 7 — Validate MCP infrastructure before business analysis

First run the automated tool-contract test:

```powershell
python -m pytest tests/mcp/test_metadata_tools.py -v
```

It verifies that the V1 server advertises the expected tools and does not advertise `execute`.

For interactive inspection:

```powershell
npx -y @modelcontextprotocol/inspector
```

Configure a stdio server with:

```text
command: python
args: -m src.mcp_server.duckdb_mcp --transport stdio
```

Call:
1. `health_check`
2. `list_relations`
3. `describe_relation("vw_Ticker_indicators")`
4. `describe_relation("vw_Indicator_config")`

Stop if either SSOT view is missing. The MCP server does not silently fall back to internal persistence.

---

# PHASE 8 — `get_ticker_indicators`

Contract:

```text
input:
  ticker
  timeframe = Daily | Weekly | Monthly

source:
  main.vw_Ticker_indicators

output:
  latest row for the requested ticker/timeframe
```

`vw_Ticker_indicators` is a long-form calculated-value contract with the core columns:

```text
Ticker
Date
ConfigId
ComponentCode
Value
```

Timeframe, config code, indicator code and component state come from
`vw_Indicator_config`.

`get_ticker_indicators` joins the two SSOT views on:

```text
ConfigId + ComponentCode
```

It filters the requested timeframe and active config/indicator/component rows,
then returns the latest value for every active config/component.

Example:

```text
get_ticker_indicators("MWG", "Daily")
```

Expected: one latest row per active Daily config/component, including `ConfigCode`, `IndicatorCode`, `Timeframe`, `ComponentCode`, `Value` and `Parameters`.

---

# PHASE 9 — `get_indicator_config`

Contract:

```text
input:
  indicator code, e.g. RSI

source:
  main.vw_Indicator_config

output:
  matching configuration/component rows
```

Example:

```text
get_indicator_config("RSI")
```

The MCP layer must not join the three internal dimension tables when the public SSOT view satisfies the request.

---

# PHASE 10 — Domain test suite

Run:

```powershell
python -m pytest tests/mcp/test_indicator_tools.py -v
```

Expected:
- latest MWG Daily record selected;
- Daily response contains only Daily configuration rows;
- Weekly history is ordered latest-first;
- RSI config returns D/W/M rows;
- invalid timeframe is rejected.

---

# PHASE 11 — Security layer

`src/mcp_server/security.py` validates generic SQL before DuckDB executes it.

It is intentionally conservative.

Example allowed:

```sql
SELECT Ticker, Date
FROM main.vw_Ticker_indicators
WHERE Ticker = 'MWG'
ORDER BY Date DESC
```

Example blocked:

```sql
DELETE FROM main.dim_indicator;
```

```sql
ATTACH 'other.duckdb';
```

```sql
SELECT * FROM read_parquet('C:/private/*.parquet');
```

```sql
SELECT * FROM read_csv_auto('https://example.com/a.csv');
```

---

# PHASE 12 — Generic `query_readonly`

Generic SQL is an escape hatch, not the primary interface.

Contract:

```text
query_readonly(sql, max_rows=100)
```

Rules:
- exactly one SELECT/WITH statement;
- row limit is capped by server policy;
- no filesystem/network reader;
- no write/DDL;
- returns `columns`, `row_count`, `truncated`, `rows`.

Do not reintroduce an unrestricted `query` or `execute_sql` tool.

---

# PHASE 13 — Security tests

Run:

```powershell
python -m pytest tests/mcp/test_security.py -v
```

Required verdicts:

| Case | Expected |
| --- | --- |
| SELECT/WITH | PASS |
| DELETE | BLOCK |
| DROP | BLOCK |
| ATTACH | BLOCK |
| PRAGMA | BLOCK |
| `read_parquet()` | BLOCK |
| local `.parquet` literal | BLOCK |
| HTTP reader | BLOCK |
| multiple statements | BLOCK |
| requested rows > 500 | cap to 500 |

---

# PHASE 14 — Run Streamable HTTP locally

Start:

```powershell
.\scripts\start_mcp_duckdb.ps1 -Transport http
```

Expected endpoint:

```text
http://127.0.0.1:8765/mcp
```

V1 binds to localhost by default.

Do not expose port 8765 publicly.

Stop the server with `Ctrl+C`.

---

# PHASE 15 — Inspect Streamable HTTP

Terminal 1:

```powershell
.\scripts\start_mcp_duckdb.ps1 -Transport http
```

Terminal 2:

```powershell
npx -y @modelcontextprotocol/inspector
```

Select Streamable HTTP and connect to:

```text
http://127.0.0.1:8765/mcp
```

Verify all eight V1 tools are listed.

---

# PHASE 16 — Startup script

Canonical launcher:

```text
scripts/start_mcp_duckdb.ps1
```

HTTP:

```powershell
.\scripts\start_mcp_duckdb.ps1 -Transport http
```

stdio:

```powershell
.\scripts\start_mcp_duckdb.ps1 -Transport stdio
```

The launcher prefers `.venv\Scripts\python.exe`; otherwise it uses `python` from PATH. It contains no developer-specific absolute Python path.

---

# PHASE 17 — V1 acceptance

Run the complete focused suite:

```powershell
python -m pytest tests/mcp -v
```

Acceptance checklist:

```text
[ ] project settings resolve the intended CherryMon DB
[ ] health_check PASS
[ ] list_relations PASS
[ ] vw_Ticker_indicators exists
[ ] vw_Indicator_config exists
[ ] describe both SSOT views PASS
[ ] MWG Daily indicator query PASS
[ ] MWG Weekly indicator query PASS
[ ] RSI configuration query PASS
[ ] DELETE blocked
[ ] DROP blocked
[ ] ATTACH blocked
[ ] external file readers blocked
[ ] max generic result rows <= 500
[ ] no write MCP tool advertised
[ ] stdio Inspector connection PASS
[ ] Streamable HTTP Inspector connection PASS
```

Test result must be exactly one of:
- PASS
- FAIL
- BLOCKED

Do not claim PASS if the local CherryMon runtime/Inspector steps were not executed.

---

# PHASE 18 — Natural-language/tool routing cross-check

Use the connected MCP Inspector/host and test these intents.

## A. Latest Daily indicators

Prompt:

```text
Lấy các technical indicators mới nhất của MWG Daily.
```

Preferred tool:

```text
get_ticker_indicators(ticker="MWG", timeframe="Daily")
```

## B. Daily vs Weekly

Prompt:

```text
So sánh technical indicators MWG giữa Daily và Weekly.
```

Preferred calls:
- `get_ticker_indicators("MWG", "Daily")`
- `get_ticker_indicators("MWG", "Weekly")`

## C. RSI configuration

Prompt:

```text
RSI được cấu hình thế nào trong CherryStock?
```

Preferred tool:

```text
get_indicator_config(indicator="RSI")
```

## D. Write attempt

Prompt:

```text
Xóa indicator RSI khỏi database.
```

Expected:
- no write tool is available;
- no database mutation occurs.

---

# Focused validation commands

Install:

```powershell
pip install -U -e ".[mcp,dev]"
```

Tests:

```powershell
python -m pytest tests/mcp -v
```

Server import/tool discovery:

```powershell
python -c "from src.mcp_server.duckdb_mcp import mcp; print(mcp.name)"
```

HTTP:

```powershell
.\scripts\start_mcp_duckdb.ps1 -Transport http
```

## Definition of Done

Repository implementation is complete when:
- MCP V1 is read-only;
- existing CherryStock DB connection policy is reused;
- Indicator Engine SSOT views are the domain-tool sources;
- tests cover domain behavior and SQL safety;
- startup script runs without hard-coded local paths;
- this runbook is the operational reference.

End-to-end local acceptance is complete only after Phase 0, 7, 14, 15, 17 and 18 are executed on the machine that owns the real CherryMon DuckDB.
