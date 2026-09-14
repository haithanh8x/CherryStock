# CherryMon Architecture Constitution

## Purpose

This file defines stable CherryStock/CherryMon architecture principles. It is a shared constitution used by routed Agents, not a normal task owner.

Detailed procedures belong in Skills, mandatory domain constraints belong in Instructions, and durable architecture/domain knowledge belongs in `docs/**`.

## Official repository hierarchy

CherryStock follows ADR-011:

```text
L0  Governance      .github/copilot-instructions.md
L1  Agent           .github/agents/*.agent.md
L2  Instruction     .github/instructions/*.instructions.md
L3  Skill           .github/skills/*/SKILL.md
L4  Docs            docs/**
L5  Tool            MCP / GitHub / DuckDB / Flint / Archify / Draw.io / scripts / CLI
L6  Implementation  src/** + runtime entry points
L7  Verification    tests/** + validation evidence
```

Canonical explanation:
`docs/architecture/agent-harness/AGENT_SKILL_INSTRUCTION_DOC_TOOL.md`.

## Runtime architecture direction

CherryStock is incrementally moving toward `src/cherrystock/**` as the canonical layered runtime package:

```text
src/cherrystock/
├── domain/
├── application/
├── infrastructure/
├── interfaces/
└── config/
```

Legacy runtime packages still coexist during migration, including areas such as `src/CrawlStock`, `src/calcEngine`, `src/Chart`, `src/DuckDB`, `src/Orchestrator`, `src/Telegram`, `src/Ults` and `src/AiModels`.

Do not perform a big-bang move merely to satisfy the target tree. Migrate feature-by-feature under the architecture backlog while preserving public/runtime behavior.

## Dependency principles

1. Interfaces/UI consume application/domain contracts; they should not own complex persistence or business calculations.
2. Application orchestration coordinates use cases and should depend on ports/contracts rather than avoidable infrastructure details.
3. Infrastructure implements persistence, external data/provider and platform adapters.
4. Domain calculations/business semantics should be reusable and not hidden in presentation or transport code.
5. Validation is separable from mutation/orchestration side effects.
6. Source-of-Truth objects must be explicit; downstream consumers use declared public contracts when available.
7. New durable cross-module decisions belong in `docs/adr/**`.
8. Migration toward the target package is incremental and backward compatible unless an approved requirement explicitly changes compatibility.

## Agent Harness routing

Executable router: `.github/copilot-instructions.md`.

- requirement readiness → `BusinessAnalyst.agent.md`;
- design readiness → `SolutionArchitect.agent.md`;
- concrete indicator lifecycle → `Indicator_Management.agent.md`;
- chart/Flint outcome → `Chart.agent.md`;
- clear implementation → `GeneralCoding.agent.md`;
- independent validation → `TestEngineer.agent.md`.

The router selects the smallest sufficient route. Not every request passes through every Agent.

## Domain Instruction routing

- DuckDB / SQL / transaction / data quality → `.github/instructions/database.instructions.md`
- technical indicators → `.github/instructions/indicators.instructions.md`
- chart / visualization → `.github/instructions/chart.instructions.md`
- crawlers / ingestion → `.github/instructions/crawler.instructions.md`
- Python execution → `.github/instructions/python.instructions.md`
- testing / validation → `.github/instructions/testing.instructions.md`
- Archify synchronization → `.github/instructions/archify.instructions.md`

Do not duplicate those rules here.

## Skill routing

Reusable procedures are indexed at `.github/skills/README.md`.

Important examples:
- architecture design → `architecture-design`;
- indicator lifecycle → `indicator-onboarding`;
- regression verification → `regression-testing`;
- data quality → `data-quality-validation`;
- DuckDB migration → `duckdb-migration`;
- visualization authoring → `chart-authoring`;
- editable diagrams → `drawio-skill`.

Skills do not own readiness gates or architecture/business Sources of Truth.

## Naming principles

DuckDB object prefixes:
- `raw_*`: source/raw datasets;
- `cal_*`: calculated/internal persistence;
- `dim_*`: dimensions/configuration/master data;
- `vw_*`: public/query-oriented views;
- `sys_*`: operational/audit/monitoring datasets.

Indicator output convention:

```text
<INDICATOR><PERIOD>_<TIMEFRAME>
```

Timeframes: `_D`, `_W`, `_M`.

## Key CherryMon data contracts

Important data objects include:
- `raw_stock_eod`;
- `raw_stock_fa`;
- `raw_stock_index`;
- `dimCalendar`;
- `vw_ACCCNNTD_Price`;
- `sys_data_quality_audit`.

Indicator Engine contracts:
- `dim_indicator`;
- `dim_indicator_component`;
- `dim_indicator_config`;
- `vw_Indicator_config` — configuration SSOT;
- `cal_indicator_values` — internal long-format persistence;
- `vw_Ticker_indicators` — public calculated indicator SSOT.

For current physical database evidence, read `docs/reference/DB_Metadata.md` and current generated metadata snapshots. Behavioral rules come from architecture/ADR/Instructions, not from generated metadata alone.

## Knowledge architecture

GitHub repository Markdown is the engineering knowledge Single Source of Truth.

```text
.github/**      executable AI/developer governance

docs/**         durable requirements, architecture, ADR, domain, reference, runbooks and change history

src/**          runtime implementation
scripts/**      focused operational/migration/backfill/render helpers
tests/**        executable validation
```

Start knowledge discovery from `docs/00_HOME.md`. VS Code and Obsidian read the same repository checkout; Obsidian is a navigation surface, not a second documentation store.
