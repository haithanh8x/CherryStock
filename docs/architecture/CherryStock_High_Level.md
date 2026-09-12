# CherryStock High-Level Architecture

- **Status:** ACTIVE
- **Owner:** `.github/agents/SolutionArchitect.agent.md`
- **Visualization tool:** Archify
- **Mapped runtime revision:** `711b9a582e66e0660966907a82a6e901cd76764d`
- **Archify source:** `docs/architecture/diagrams/cherrystock-high-level.architecture.json`

## Purpose

This document is the canonical high-level system map for CherryStock. It describes the major runtime components, data/control boundaries and consumer surfaces without duplicating the detailed contracts owned by domain architecture documents.

`docs/**` remains the engineering knowledge Source of Truth. The Archify JSON is the deterministic visualization source for this map; Archify renders and validates the representation but does not own architecture decisions or invent missing topology.

## Scope

The map covers the current repository-level architecture:

- daily and monthly runtime entry points;
- market/reference data ingestion;
- application orchestration;
- shared DuckDB transaction and Data Quality gates;
- local DuckDB persistence and public read contracts;
- Trend / Indicator / R/S / SmartMoney analytical engines;
- NiceGUI / Chart / Presentation consumers;
- DuckDB MCP access;
- automation and notification tooling;
- engineering/AI governance as a separate control plane.

Deployment infrastructure that is not evidenced in the repository is intentionally omitted.

## High-Level Components

| Component | Responsibility | Primary evidence |
| --- | --- | --- |
| Market Data Sources | External/local source data consumed by CherryStock | `src/CrawlStock/readAmi.py`, `readYahooFinance.py`, `upsertFA.py` |
| Runtime Entry Points | Start daily, monthly and focused operational runs | `run.py`, `runMonthly.py`, `src/Orchestrator/run_rundeck_ingest_intraday.py` |
| Ingestion & Adapters | Normalize AmiBroker/market/reference inputs behind application-facing adapters/services | `src/cherrystock/infrastructure/amibroker/windows_adapter.py`, sync services |
| Application Orchestration | Own execution order and coordinate daily/monthly jobs | `src/cherrystock/application/services/sync_write_pipeline.py`, `src/Orchestrator/**` |
| Transaction & Data Quality Gate | Keep daily writes atomic and stop commit on blocking validation failures | `DuckDBUnitOfWork`, `DataQualityOrchestration.py`, `DataValidation.py` |
| CherryMon DuckDB | Persist `raw_*`, `dim_*`, `cal_*`, `sys_*` data | centralized connection layer, `src/DuckDB/sql/**` |
| Analytics & Calculation Engines | Build Trend, Indicators, R/S and SmartMoney outputs | `src/calcEngine/**` |
| Public Read Contracts | Expose stable `vw_*` consumer-oriented read surfaces | `vw_Ticker_OHLC_D`, Indicator Engine and SmartMoney architecture contracts |
| Web & Chart Presentation | Present grids/charts and analytical views | `src/webapp/**`, `src/Chart/**`, `src/Presentation/**` |
| DuckDB MCP Server | Expose guarded analytical/read-write tools over stdio or localhost HTTP | `src/mcp_server/**` |
| Automation & Notifications | Operational scripts, notebook entry points and Telegram notifications | `scripts/**`, `src/Jupyter/**`, `src/Telegram/**` |

## Primary Runtime Paths

### Daily write path

The canonical daily path is:

```text
run.py
  → DuckDBUnitOfWork
  → SyncWritePipelineService
  → ingestion + stage Data Quality
  → calculations (Index / Trend / Indicators / SmartMoney)
  → blocking Data Quality gates
  → COMMIT
  → exportDuckDB_metadata()
```

A blocking Data Quality failure before commit raises and causes the shared `DuckDBUnitOfWork` to roll back the daily write set. The exact operational ordering remains owned by `docs/runbook/Daily_Data_Pipeline.md`.

### Data path

```text
AmiBroker / Yahoo / FA sources
  → ingestion & adapters
  → raw_* / reference data in DuckDB
  → analytical engines
  → calculated persistence + public vw_* contracts
  → Web/Chart | MCP | automation/notifications
```

The public read layer is intentionally separated from internal calculated persistence. Consumers should prefer stable `vw_*` contracts when a public read contract exists.

### Monthly path

`runMonthly.py` is a separate manually invoked runtime entry point. The current configured monthly job is R/S V2.4 Full Source Effectiveness Evaluation. It is not part of the atomic daily write sequence.

### MCP access path

The DuckDB MCP Server is a consumer/interface path into the local CherryMon database, not the owner of the daily pipeline. It uses the centralized DuckDB layer and applies its own SQL/write guardrails. HTTP mode binds to `127.0.0.1:8765/mcp` by default.

## Engineering / AI Control Plane

The following material governs how CherryStock is changed rather than participating in the market-data runtime path:

```text
.github/copilot-instructions.md
.github/agents/**
.github/instructions/**
        ↓
SolutionArchitect / domain agents
        ↓
docs/** + ADRs + source + tests
```

For architecture work, `SolutionArchitect.agent.md` remains the authority. Archify is its visualization/validation tool. Generated diagrams must be grounded in repository evidence and cannot override architecture documents, ADRs or implementation facts.

## Archify Artifact

Source:

```text
docs/architecture/diagrams/cherrystock-high-level.architecture.json
```

The source uses Archify `architecture` schema v1, `quality_profile=showcase`, at most 12 primary nodes, and repository evidence pinned to the mapped runtime revision.

Because authored labels are Vietnamese while Archify's renderer-owned locale currently supports only `en` and `zh-CN`, `meta.locale` is intentionally omitted; fixed Viewer UI falls back to English while authored CherryStock content remains unchanged.

### Validate locally

From the CherryStock repository after Archify has been installed globally:

```powershell
$archify = "$env:USERPROFILE\.agents\skills\archify\bin\archify.mjs"
node $archify validate architecture docs/architecture/diagrams/cherrystock-high-level.architecture.json --quality showcase --json
```

### Deliver interactive HTML

```powershell
New-Item -ItemType Directory -Force docs/architecture/generated | Out-Null
$archify = "$env:USERPROFILE\.agents\skills\archify\bin\archify.mjs"
node $archify deliver architecture docs/architecture/diagrams/cherrystock-high-level.architecture.json docs/architecture/generated/CherryStock_High_Level.html --quality showcase --json
```

The HTML is a derived presentation artifact. The architectural facts remain governed by this document, related domain architecture documents, ADRs and runtime source.

## Architecture Boundaries / Non-Claims

- No cloud/region/deployment topology is inferred from repository structure.
- MotherDuck is not shown because the inspected current runtime revision does not provide repository evidence that it belongs to this high-level execution map.
- The approved As-Traded market-limit architecture is not shown as an active daily stage until its migration is implemented and validated.
- The legacy DrawIO material under `.kiro/specs/` is not the engineering Source of Truth; durable architecture belongs under `docs/architecture/**`.

## Related Architecture

- `docs/architecture/Data_Architecture.md`
- `docs/architecture/Indicator_Engine.md`
- `docs/architecture/SmartMoneyScore.md`
- `docs/architecture/Chart_Architecture.md`
- `docs/architecture/agent-harness/README.md`
- `docs/runbook/Daily_Data_Pipeline.md`
- `src/mcp_server/README.md`

## Maintenance Rule

`SolutionArchitect.agent.md` should refresh this high-level map with Archify whenever an approved change materially alters a major runtime component, a top-level dependency/data path, the public consumer boundary, or the engineering control-plane relationship shown here. Domain-only changes that do not change this abstraction level should update their own architecture documents without churning the high-level map.

## ADR

**Not required.** This artifact documents and visualizes the current architecture; it does not introduce a new cross-module architecture decision.
