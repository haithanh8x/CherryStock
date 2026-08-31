# Runbook — CherryStock DuckDB MCP — Phase 19–22

## 1. Objective

This runbook continues `docs/runbook/MCP_DuckDB.md` after the local MCP server, automated tests, MCP Inspector, and real CherryMon runtime checks have passed.

Target end-to-end architecture:

```text
ChatGPT Web
    |
    | Custom MCP App / Developer Mode
    v
OpenAI MCP connectivity
    |
    | Secure MCP Tunnel for local/private MCP
    v
CherryStock MCP Server
http://127.0.0.1:8765/mcp
    |
    | DuckDBManager(read_only=True)
    v
CherryMon
```

Important: ChatGPT cannot connect directly to `127.0.0.1` on the developer machine. A local/private/on-prem MCP server must be made reachable through the supported Secure MCP Tunnel flow. Do not expose port 8765 directly to the public Internet.

Official OpenAI reference:
- https://help.openai.com/en/articles/12584461

---

# PHASE 19 — Connect the local CherryStock MCP to ChatGPT

## Goal

Make the already-tested local endpoint:

```text
http://127.0.0.1:8765/mcp
```

reachable to ChatGPT without publishing the local DuckDB or MCP port to the public Internet.

## Step 19.1 — Confirm local MCP is still healthy

Terminal 1:

```powershell
cd C:\Github\CherryStock
.\.venv\Scripts\Activate.ps1
.\scripts\start_mcp_duckdb.ps1 -Transport http
```

Expected:

```text
Endpoint: http://127.0.0.1:8765/mcp
Application startup complete.
Uvicorn running on http://127.0.0.1:8765
```

Keep this terminal running.

## Step 19.2 — Confirm Inspector still sees the server

Use MCP Inspector and confirm the eight V1 tools are still present:

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

Do not continue if Inspector cannot call the server locally.

## Step 19.3 — Check ChatGPT plan/workspace capability

OpenAI currently documents:

- Business / Enterprise / Edu: custom MCP apps and full MCP support are available through Developer Mode, subject to workspace/admin controls.
- Pro: custom MCPs can be connected in Developer Mode for read/fetch permissions; full MCP write/modify support is not the target of CherryStock V1 anyway.
- Custom MCP apps are currently a ChatGPT web capability.

CherryStock V1 is deliberately read-only, so do not add write tools merely to satisfy a product capability.

## Step 19.4 — Use Secure MCP Tunnel for the local/private endpoint

ChatGPT does not directly connect to localhost. For a server on a developer machine/private network, use OpenAI Secure MCP Tunnel where available for the account/workspace.

The tunnel must forward ChatGPT MCP traffic to:

```text
http://127.0.0.1:8765/mcp
```

Security rules:

```text
[ ] bind CherryStock MCP to 127.0.0.1 by default
[ ] do not port-forward 8765 from the router
[ ] do not expose 8765 through a generic public tunnel as the production solution
[ ] keep MCP V1 read-only
[ ] retain query_readonly SQL validation
[ ] verify the tunnel target is exactly the CherryStock MCP endpoint
```

Because Secure MCP Tunnel availability/UI can change, follow the current OpenAI Developer Mode/App setup presented by the workspace rather than hard-coding an obsolete tunnel CLI into CherryStock.

## Phase 19 acceptance

```text
[ ] local MCP HTTP server PASS
[ ] local Inspector PASS
[ ] supported ChatGPT plan/workspace confirmed
[ ] Developer Mode available/enabled as required
[ ] Secure MCP Tunnel/private connectivity configured
[ ] no public exposure of local port 8765
```

Verdict: PASS / FAIL / BLOCKED.

---

# PHASE 20 — Register CherryStock as a ChatGPT custom MCP app

## Goal

Register the tunneled CherryStock MCP endpoint in ChatGPT and scan its tools.

## Step 20.1 — Enable Developer Mode

Use ChatGPT Web.

Depending on workspace type and permissions, Developer Mode is managed from the Apps/Advanced Settings or workspace Apps settings. Follow the current ChatGPT UI shown for the account.

Official OpenAI flow is conceptually:

```text
Settings / Workspace Settings
    -> Apps
    -> Developer Mode / Create custom app
```

If the option is absent, stop and mark this phase BLOCKED by plan/workspace permissions rather than changing CherryStock code.

## Step 20.2 — Create the custom app

Create a custom MCP app with a clear name such as:

```text
CherryStock
```

or:

```text
CherryStock DuckDB
```

Use the endpoint supplied by the supported Secure MCP Tunnel/private connectivity flow — not `http://127.0.0.1:8765/mcp` directly.

Authentication:
- use the mechanism required by the tunnel/app configuration;
- do not invent OAuth for CherryStock V1 if the supported private connectivity flow does not require it;
- do not put database credentials into tool descriptions or prompts.

## Step 20.3 — Scan Tools

Use ChatGPT's `Scan Tools` action.

Expected eight tools:

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

Fail if any unexpected database write tool appears, for example:

```text
execute
execute_sql
insert
update
delete
```

## Step 20.4 — Create/save the app

After the tool scan succeeds, create/save the app according to the current ChatGPT UI.

The app should then appear under the account/workspace Apps area, normally with a development/custom indication depending on the current product UI.

## Phase 20 acceptance

```text
[ ] CherryStock custom app created
[ ] Scan Tools PASS
[ ] exactly the expected V1 tool surface is available
[ ] no unrestricted write tool
[ ] app enabled for the testing user
```

Verdict: PASS / FAIL / BLOCKED.

---

# PHASE 21 — Verify ChatGPT tool discovery

## Goal

Verify that a normal ChatGPT web conversation can actually select and invoke CherryStock.

## Step 21.1 — Start a new ChatGPT conversation

Use ChatGPT Web, not MCP Inspector.

Select/mention the CherryStock app for the message according to the current Apps UI.

App selection is message-scoped; when a follow-up needs fresh CherryMon data, select or `@mention` CherryStock again if required by the UI.

## Step 21.2 — Health check from ChatGPT

Prompt:

```text
@CherryStock kiểm tra kết nối CherryStock MCP. Chỉ sử dụng CherryStock, không dùng web.
```

Expected routing:

```text
health_check()
```

Expected result includes:

```text
status = ok
access = read-only
```

## Step 21.3 — Metadata discovery from ChatGPT

Prompt:

```text
@CherryStock liệt kê các relation trong schema main. Chỉ sử dụng CherryStock MCP.
```

Preferred routing:

```text
list_relations()
```

Confirm at least:

```text
vw_Ticker_indicators
vw_Indicator_config
```

## Step 21.4 — Indicator domain tool routing

Prompt:

```text
@CherryStock lấy technical indicators mới nhất của MWG ở timeframe Daily. Chỉ lấy dữ liệu từ CherryStock MCP.
```

Preferred routing:

```text
get_ticker_indicators(
    ticker="MWG",
    timeframe="Daily"
)
```

Expected:

```text
ticker = MWG
timeframe = Daily
row_count > 0
as_of_date != null
```

## Step 21.5 — Configuration routing

Prompt:

```text
@CherryStock RSI đang được cấu hình thế nào? Chỉ sử dụng CherryStock MCP.
```

Preferred routing:

```text
get_indicator_config(indicator="RSI")
```

## Phase 21 acceptance

```text
[ ] ChatGPT can select/mention CherryStock
[ ] health_check invoked successfully
[ ] list_relations invoked successfully
[ ] get_ticker_indicators invoked successfully
[ ] get_indicator_config invoked successfully
[ ] responses are based on CherryStock data rather than web search
```

Verdict: PASS / FAIL / BLOCKED.

---

# PHASE 22 — End-to-end ChatGPT -> MCP -> CherryMon acceptance

## Goal

Prove that ChatGPT can answer a concrete CherryStock data question through the MCP path.

## Test 22.1 — MWG price on 2026-08-26

Prompt:

```text
@CherryStock giá đóng cửa của MWG ngày 26-Aug-2026 là bao nhiêu?
Chỉ sử dụng dữ liệu từ CherryStock MCP, không dùng web.
Cho biết relation/field đã dùng để lấy kết quả.
```

### Current V1 routing

CherryStock V1 does not yet expose a dedicated `get_ticker_price` domain tool. Therefore ChatGPT may use:

```text
query_readonly(...)
```

Before constructing SQL, ChatGPT should discover the relevant price relation/schema when necessary using:

```text
list_relations()
describe_relation(<price relation>)
```

Do not hard-code a guessed price table/view name in this runbook.

Expected flow:

```text
User prompt
    -> CherryStock app selected
    -> list_relations / describe_relation if needed
    -> query_readonly
    -> CherryStock MCP
    -> DuckDBManager(read_only=True)
    -> CherryMon price SSOT
    -> result returned to ChatGPT
```

Acceptance criteria:

```text
[ ] no web search used
[ ] data came through CherryStock app/MCP
[ ] ticker = MWG
[ ] requested date = 2026-08-26
[ ] close price returned
[ ] source relation/field identified
[ ] no database mutation
```

## Test 22.2 — Security from ChatGPT

Prompt:

```text
@CherryStock xóa indicator RSI khỏi database.
```

Expected:

```text
No write tool is available.
No mutation occurs.
```

ChatGPT must not bypass the MCP safety model by constructing a DELETE through `query_readonly`; the SQL validator must block it.

## Test 22.3 — Web isolation

Prompt:

```text
@CherryStock lấy giá MWG ngày 26-Aug-2026 chỉ từ CherryStock MCP. Nếu CherryStock không có dữ liệu thì báo không có dữ liệu, không fallback sang web.
```

Expected behavior:
- return CherryStock data if present;
- otherwise state that CherryStock did not return the requested data;
- do not silently substitute TradingView, CafeF, FireAnt, Google, or another web source.

---

# Recommended V2 follow-up — dedicated price tool

Once Phase 22 works through `query_readonly`, prefer adding a domain-specific price tool rather than relying on arbitrary SQL for common price questions.

Suggested contract:

```text
get_ticker_price(
    ticker,
    date,
    timeframe="Daily"
)
```

Possible response contract:

```json
{
  "ticker": "MWG",
  "date": "2026-08-26",
  "timeframe": "Daily",
  "open": null,
  "high": null,
  "low": null,
  "close": null,
  "volume": null,
  "source_relation": "<actual price SSOT>"
}
```

Before implementing this tool, inspect CherryStock's current price SSOT and reuse the public `vw_*` contract if one exists. Do not create a second price Source of Truth.

---

# Final Definition of Done

CherryStock ChatGPT MCP integration is complete when all of the following are true:

```text
Phase 14  Streamable HTTP runtime                 PASS
Phase 15  MCP Inspector / 8 tools                 PASS
Phase 17  tests/mcp                               PASS
Phase 18  real CherryMon MCP runtime              PASS
Phase 19  private ChatGPT connectivity            PASS
Phase 20  ChatGPT custom app registration         PASS
Phase 21  ChatGPT tool discovery/invocation       PASS
Phase 22  ChatGPT -> MCP -> CherryMon E2E         PASS
```

The final proof is not merely that MCP Inspector works. The final proof is that a ChatGPT web conversation can select CherryStock, invoke its MCP tools, retrieve real CherryMon data, and preserve the V1 read-only security boundary.
