# 🍒 CherryStock Engineering Knowledge Base

This is the canonical knowledge-routing entry point for CherryStock. GitHub repository Markdown is the engineering Single Source of Truth; VS Code and Obsidian read the same repository checkout.

Agents should load the **smallest relevant context**, not scan the repository blindly.

## Official Agent Harness hierarchy

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
- [[architecture/agent-harness/AGENT_SKILL_INSTRUCTION_DOC_TOOL|Agent / Skill / Instruction / Docs / Tool hierarchy]]
- [[adr/ADR-011-agent-harness-responsibility-hierarchy|ADR-011 Agent Harness Responsibility Hierarchy]]
- [[architecture/agent-harness/README|Agent Harness ADLC Architecture]]
- [[architecture/agent-harness/AGENT_EXECUTION_FLOW|Agent Execution Flow]]

## AI Governance / Agents

- [[../.github/copilot-instructions|Global Governance / Router]]
- [[../.github/agents/CherryMon.agent|CherryMon Architecture Constitution]]
- [[../.github/agents/BusinessAnalyst.agent|Business Analyst]]
- [[../.github/agents/SolutionArchitect.agent|Solution Architect]]
- [[../.github/agents/Indicator_Management.agent|Indicator Management]]
- [[../.github/agents/Chart.agent|Chart]]
- [[../.github/agents/GeneralCoding.agent|General Coding]]
- [[../.github/agents/TestEngineer.agent|Test Engineer]]

## Instructions — mandatory constraints

- [[../.github/instructions/database.instructions|Database]]
- [[../.github/instructions/indicators.instructions|Indicators]]
- [[../.github/instructions/chart.instructions|Chart]]
- [[../.github/instructions/crawler.instructions|Crawler]]
- [[../.github/instructions/python.instructions|Python]]
- [[../.github/instructions/testing.instructions|Testing]]
- [[../.github/instructions/archify.instructions|Archify]]

## Skills — repeatable procedures

Catalog: `../.github/skills/README.md`

- `architecture-design` — solution architecture procedure and synchronized design handoff.
- `indicator-onboarding` — indicator lifecycle metadata/backfill/validation procedure.
- `regression-testing` — focused deterministic verification.
- `data-quality-validation` — freshness/coverage/duplicate/null/range/idempotency procedure.
- `duckdb-migration` — safe DuckDB migration procedure.
- `chart-authoring` — visualization selection + Flint authoring/validation/rendering.
- `drawio-skill` — editable Draw.io diagram procedure.

## Requirement / Backlog routing

Requirement analysis, scope, business rules, acceptance criteria and backlog readiness:

1. use `BusinessAnalyst.agent.md`;
2. inspect `backlog/requirements/**`;
3. load related domain/architecture context below;
4. store durable requirement output under `docs/backlog/requirements/**`;
5. hand off with `READY_FOR_DESIGN` or `READY_FOR_IMPLEMENTATION` when ready.

A small explicit implementation request does not require a new requirement document.

### Backlog

- [[backlog/Backlog_Status|Backlog Status Dashboard]]
- [[backlog/README|Backlog Guide]]
- [[backlog/requirements/README|Requirements Backlog]]
- [[backlog/requirements/REQUIREMENT_TEMPLATE|Requirement Template]]
- [[backlog/Architecture_Backlog|Architecture Backlog]]
- [[backlog/Harness_Backlog|Agent Harness Backlog]]

Backlog material describes planned work; it is not current runtime Source of Truth.

## Design / Architecture routing

Architecture/system/solution/data/integration/refactor work:

1. use `SolutionArchitect.agent.md`;
2. obey matching Instructions;
3. load the smallest relevant architecture/ADR/domain/reference context;
4. use `architecture-design` Skill;
5. inspect implementation/tests as evidence;
6. synchronize Archify artifacts before an approved design is treated as implementation-ready.

### Core architecture

- [[architecture/CherryStock_High_Level|CherryStock High-Level Architecture]]
- [[architecture/Data_Architecture|Data Architecture]]
- [[architecture/Indicator_Engine|Indicator Engine]]
- [[architecture/Chart_Architecture|Chart Architecture]]
- [[architecture/theme|Theme Architecture]]
- [[architecture/Second_Brain|Second Brain Architecture]]
- [[architecture/agent-harness/README|Agent Harness / ADLC]]

### Smart Money

- [[architecture/AsTraded_Market_Limit|As-Traded Market Limit Architecture]]
- [[backlog/requirements/REQ-0025-smart-money-score|REQ-0025 SmartMoneyScore]]
- [[architecture/SmartMoneyScore|SmartMoneyScore Architecture]]
- [[backlog/requirements/REQ-0026-smart-money-strategy|REQ-0026 Smart Money Strategy]]
- [[architecture/SmartMoneyStrategy|SmartMoneyStrategy]]
- [[runbook/SmartMoneyStrategy_V1|SmartMoneyStrategy V1 Runbook]]
- [[runbook/SmartMoneyTradeActionConfidence_V1|TradeActionConfidence V1 Runbook]]
- [[runbook/SmartMoney_NiceGUI_Tab|SmartMoney NiceGUI Runbook]]

### R/S / chart-related architecture

- [[architecture/RS_Ladder|R/S Ladder]]
- [[architecture/RS_Source_Effectiveness|R/S Source Effectiveness]]

## Technical Indicators

Canonical chain:

```text
Indicator_Management.agent.md
  → indicators.instructions.md
  → docs/architecture/Indicator_Engine.md + ADR-002
  → indicator-onboarding Skill
  → CherryMon MCP / calcEngine
  → TestEngineer
```

References:
- [[architecture/Indicator_Engine|Indicator Engine Architecture]]
- [[adr/ADR-002-indicator-source-of-truth|ADR-002 Indicator Source of Truth]]
- [[reference/DB_Metadata|DB Metadata]]
- [[reference/Indicator_Engine_Legacy_Reference|Historical Indicator Engine Reference]]

The historical reference is not current procedure ownership.

## Data / DuckDB

- [[architecture/Data_Architecture|Data Architecture]]
- [[adr/ADR-001-duckdb-connection|ADR-001 DuckDB Connection]]
- [[reference/DB_Metadata|DB Metadata]]
- [[runbook/MCP_DuckDB|DuckDB MCP Runbook]]

Generated metadata/snapshots under `docs/reference/**` are evidence of current physical state, not target-design ownership.

## Chart / Visualization

- [[architecture/Chart_Architecture|Chart Architecture]]
- [[architecture/theme|Theme Architecture]]
- `../.github/skills/chart-authoring/SKILL.md`
- `../.github/skills/drawio-skill/SKILL.md`

Chart recommendation/Flint authoring is owned by Chart Agent. Reusable chart architecture is owned by Solution Architect. Production integration after the chart contract is approved is owned by General Coding.

## Crawlers / Data ingestion

- [[architecture/Data_Architecture|Data Architecture]]
- [[../.github/instructions/crawler.instructions|Crawler Instructions]]

## Testing / Validation

- [[../.github/agents/TestEngineer.agent|Test Engineer]]
- [[../.github/instructions/testing.instructions|Testing Instructions]]
- `../.github/skills/regression-testing/SKILL.md`
- `../.github/skills/data-quality-validation/SKILL.md`
- [[development/Development_Workflow|Development Workflow]]
- [[development/Python_Execution_Conventions|Python Execution Conventions]]

Testing remains bounded: one objective/hypothesis, minimum sufficient evidence, finite retry budget, explicit terminal verdict and STOP.

## Domain knowledge

Canonical domain knowledge no longer lives under `.github/agents/Instructions/**`.

### Market terminology
- [[domain/market/Stock_Terms|Stock Terms — active trading and supply/demand]]

### Strategy
- [[domain/strategy/Stock_Strategies|Top-Down Stock Buy Evaluation Strategy]]

## Architecture Decision Records

- [[adr/ADR-001-duckdb-connection|ADR-001 DuckDB Connection]]
- [[adr/ADR-002-indicator-source-of-truth|ADR-002 Indicator Source of Truth]]
- [[adr/ADR-003-centralized-theme-system|ADR-003 Centralized Theme System]]
- [[adr/ADR-004-rs-v2-source-semantics|ADR-004 R/S V2.0 Source Semantics]]
- [[adr/ADR-005-rs-v2-1-adaptive-structural|ADR-005 R/S V2.1 Adaptive Structural]]
- [[adr/ADR-006-rs-v2-2-volume-profile|ADR-006 R/S V2.2 Volume Profile]]
- [[adr/ADR-007-rs-v2-3-evaluation-governance|ADR-007 R/S V2.3 Evaluation Governance]]
- [[adr/ADR-008-rs-v2-4-source-effectiveness-promotion|ADR-008 R/S V2.4 Source Effectiveness]]
- [[adr/ADR-009-smart-money-score-state-aware-scoring|ADR-009 SmartMoneyScore State-Aware Scoring]]
- [[adr/ADR-010-separate-adjusted-as-traded-market-limit|ADR-010 Adjusted vs As-Traded Market Limits]]
- [[adr/ADR-011-agent-harness-responsibility-hierarchy|ADR-011 Agent Harness Responsibility Hierarchy]]

## Runbooks

- [[runbook/Daily_Data_Pipeline|Daily Data Pipeline]]
- [[runbook/MCP_DuckDB|CherryStock DuckDB MCP]]
- [[runbook/Indicator_OBV_AD|OBV + AD Activation / Initload]]
- [[runbook/SmartMoneyScore_V1|SmartMoneyScore V1]]
- [[runbook/SmartMoneyStrategy_V1|SmartMoneyStrategy V1]]
- [[runbook/RS_V2_4_Monthly_Full_Evaluation|R/S V2.4 Monthly Evaluation]]
- [[runbook/Drawio_Skill|Draw.io Skill]]

## Development

- [[development/README|Development Materials]]
- [[development/Development_Workflow|Development Workflow]]
- [[development/Python_Execution_Conventions|Python Execution / Import Conventions]]
- [[development/implementation-notes/README|Implementation Notes]]

## Change / release traceability

- [[ChangeRequest/01_Change_Request_Tracking|Master Change Request Tracking]]

Major architecture, data-model, integration, Agent Harness and production changes should have a dedicated record under `docs/ChangeRequest/**`.

## Knowledge ownership summary

| Layer | Owner / path | Responsibility |
|---|---|---|
| Governance | `.github/copilot-instructions.md` | routing, precedence, bounded execution |
| Agent | `.github/agents/*.agent.md` | WHO owns outcome/gate |
| Instruction | `.github/instructions/*.instructions.md` | mandatory constraints |
| Skill | `.github/skills/*/SKILL.md` | repeatable procedure |
| Docs | `docs/**` | durable knowledge/design/decisions/requirements |
| Tool | MCP/scripts/CLI/connectors | execution capability |
| Implementation | `src/**` | runtime behavior |
| Verification | `tests/**` | executable evidence |

When documentation and implementation conflict, report the conflict. Do not silently invent a rule or treat a generated artifact/backlog item as current runtime truth.
