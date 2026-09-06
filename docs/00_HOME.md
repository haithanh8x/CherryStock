# 🍒 CherryStock Engineering Knowledge Base

This page is the canonical knowledge-routing entry point for CherryStock. Open the repository root as an Obsidian Vault and start navigation here.

AI agents MUST use this page to discover relevant engineering knowledge before architecture/design/test work. Do not scan every document blindly; follow the smallest relevant path below.

## AI Governance
- [[../.github/copilot-instructions|Copilot Instructions]]
- [[architecture/agent-harness/README|Agent Harness Architecture]]
- [[../.github/agents/CherryMon.agent|CherryMon Architecture Constitution]]
- [[../.github/agents/BusinessAnalyst.agent|Business Analyst Agent]]
- [[../.github/agents/SolutionArchitect.agent|Solution Architect Agent]]
- [[../.github/agents/Indicator_Management.agent|Indicator Management Agent]]
- [[../.github/agents/GeneralCoding.agent|General Coding Agent]]
- [[../.github/agents/TestEngineer.agent|Test Engineer Agent]]

## Requirement / Backlog Routing

When the request involves requirement analysis, clarification, scope, business rules, acceptance criteria, impact discovery, backlog creation/refinement or decomposition:

1. Read `../.github/agents/BusinessAnalyst.agent.md`.
2. Review existing materials under `backlog/requirements/`.
3. Follow the smallest relevant domain/architecture links below.
4. Store durable requirement output under `docs/backlog/requirements/`.
5. End with `DRAFT`, `NEEDS_CLARIFICATION`, `READY_FOR_DESIGN`, `READY_FOR_IMPLEMENTATION` or `BLOCKED`.

A small explicit implementation request does not require a new backlog document.

## Design / Architecture Routing

When the request involves architecture, system design, solution design, component design, technical design, data model, workflow, integration, migration or architecture refactor:

1. Read ../.github/agents/SolutionArchitect.agent.md.
2. Identify affected domain(s).
3. Follow the related Architecture / ADR / Domain Knowledge links below.
4. Read matching .github/instructions/*.instructions.md.
5. Inspect current implementation and tests before finalizing the design.

### Data / DuckDB
- [[architecture/Data_Architecture|Data Architecture]]
- [[adr/ADR-001-duckdb-connection|ADR-001 DuckDB Connection]]
- [[../.github/instructions/database.instructions|Database Instructions]]
- [[reference/DB_Metadata|DB Metadata]]
- [[runbook/MCP_DuckDB|DuckDB MCP Runbook]]

### Generated Database Context
- [[reference/DB_Metadata|DB Metadata]]
- `reference/dim_indicator.csv`
- `reference/dim_indicator_component.csv`
- `reference/dim_indicator_config.csv`

Read the Markdown file for structure, then the CSV snapshots for current indicator metadata/configuration values. The four files are refreshed together by `exportDuckDB_metadata()`.

### Technical Indicators
- [[architecture/Indicator_Engine|Indicator Engine Architecture]]
- [[adr/ADR-002-indicator-source-of-truth|ADR-002 Indicator Source of Truth]]
- [[../.github/instructions/indicators.instructions|Indicator Instructions]]
- [[../.github/agents/Instructions/Indicator_Engine|Legacy Detailed Indicator Engine Reference]]

### Smart Money / Flow Analytics
- [[architecture/AsTraded_Market_Limit|As-Traded Market Limit Architecture]]
- [[backlog/requirements/REQ-0025-smart-money-score|REQ-0025 Ticker-level SmartMoneyScore]]
- [[architecture/SmartMoneyScore|SmartMoneyScore Architecture]]
- [[adr/ADR-009-smart-money-score-state-aware-scoring|ADR-009 SmartMoneyScore State-Aware Scoring]]
- Uses [[architecture/Data_Architecture|Data Architecture]] and may consume [[architecture/Indicator_Engine|Indicator Engine]] through public indicator contracts.

### Chart / Visualization
- [[architecture/Chart_Architecture|Chart Architecture]]
- [[architecture/theme|Theme Architecture]]
- [[architecture/RS_Ladder|RS Ladder Architecture]]
- [[architecture/RS_Source_Effectiveness|R/S Source Effectiveness Architecture]]
- [[adr/ADR-003-centralized-theme-system|ADR-003 Centralized Theme System]]
- [[adr/ADR-004-rs-v2-source-semantics|ADR-004 R/S V2.0 Source Semantics]]
- [[adr/ADR-005-rs-v2-1-adaptive-structural|ADR-005 R/S V2.1 Adaptive Structural Levels]]
- [[adr/ADR-006-rs-v2-2-volume-profile|ADR-006 R/S V2.2 Volume Profile Domain]]
- [[adr/ADR-007-rs-v2-3-evaluation-governance|ADR-007 R/S V2.3 Evaluation Governance]]
- [[adr/ADR-008-rs-v2-4-source-effectiveness-promotion|ADR-008 R/S V2.4 Source Effectiveness Promotion]]
- [[../.github/instructions/chart.instructions|Chart Instructions]]

### Crawlers / Data Ingestion
- [[../.github/instructions/crawler.instructions|Crawler Instructions]]
- [[architecture/Data_Architecture|Data Architecture]]

### Testing / Validation
- [[../.github/agents/TestEngineer.agent|Test Engineer Agent]]
- [[../.github/instructions/testing.instructions|Testing Instructions]]
- [[development/Development_Workflow|Development Workflow]]

Testing requests should use the Test Engineer Agent first, then the testing instructions. Test execution must be bounded: one objective/hypothesis at a time, finite retry budget, explicit terminal verdict, and STOP after the objective is decided.

## Architecture
- [[architecture/agent-harness/README|Agent Harness Architecture]]
- [[architecture/Second_Brain|Second Brain Architecture]]
- [[architecture/Indicator_Engine|Indicator Engine]]
- [[architecture/Data_Architecture|Data Architecture]]
- [[architecture/SmartMoneyScore|SmartMoneyScore]]
- [[architecture/Chart_Architecture|Chart Architecture]]
- [[architecture/theme|Theme Architecture]]
- [[architecture/RS_Ladder|RS Ladder Architecture]]

## Architecture Decision Records
- [[adr/ADR-010-separate-adjusted-as-traded-market-limit|ADR-010 Adjusted vs As-Traded Market Limits]]
- [[adr/ADR-001-duckdb-connection|ADR-001 DuckDB Connection]]
- [[adr/ADR-002-indicator-source-of-truth|ADR-002 Indicator Source of Truth]]
- [[adr/ADR-003-centralized-theme-system|ADR-003 Centralized Theme System]]
- [[adr/ADR-009-smart-money-score-state-aware-scoring|ADR-009 SmartMoneyScore State-Aware Scoring]]

## Runbooks
- [[runbook/AsTraded_Market_Limit_Migration|As-Traded Market-Limit Migration]]
- [[runbook/vw_raw_stock_eod|Enriched Stock EOD Market Limits]]
- [[runbook/Indicator_OBV_AD|OBV + AD Line Activation and Historical Initload]]
- [[runbook/MCP_DuckDB|CherryStock Local DuckDB MCP]]
- [[runbook/RS_V2_4_Monthly_Full_Evaluation|R/S V2.4 Monthly Full Source Effectiveness]]

## Domain Knowledge
- [[../.github/agents/Instructions/StockTerm|Stock Terms]]
- [[../.github/agents/StockStrategies|Stock Strategies]]
- [[../.github/agents/Instructions/project_structured|Project Structure - Legacy Reference]]

## Reference
- [[reference/DB_Metadata|DB Metadata]]

## Backlog
- [[backlog/Backlog_Status|Backlog Status Dashboard]]
- [[backlog/README|Backlog Guide]]
- [[backlog/requirements/README|Requirements Backlog]]
- [[backlog/requirements/REQUIREMENT_TEMPLATE|Requirement Template]]
- [[backlog/Architecture_Backlog|Architecture Backlog]]
- [[backlog/Harness_Backlog|Agent Harness Backlog]]

Backlog documents record planned work and technical debt only. They are not the Source of Truth for current runtime behavior.

## Development
- [[development/README|Development Materials]]
- [[development/Development_Workflow|Development Workflow]]
- [[development/implementation-notes/README|Implementation Notes]]

## Knowledge Ownership

| Area | Owner | Purpose |
|---|---|---|
| Global AI governance | .github/copilot-instructions.md | Repository-wide AI/developer behavior |
| Architecture constitution | .github/agents/CherryMon.agent.md | Stable CherryStock architecture principles |
| Agent Harness architecture | docs/architecture/agent-harness/** | Role ownership, routing, handoffs and material locations |
| Requirement workflow | .github/agents/BusinessAnalyst.agent.md | Requirement quality, backlog readiness and acceptance criteria |
| Design workflow | .github/agents/SolutionArchitect.agent.md | How AI researches and produces architecture/design |
| General implementation workflow | .github/agents/GeneralCoding.agent.md | Focused implementation and validation handoff |
| Test workflow | .github/agents/TestEngineer.agent.md | How AI designs/executes focused tests and terminates bounded investigations |
| Domain execution rules | .github/instructions/*.instructions.md | MUST/MUST NOT rules for implementation |
| System architecture | docs/architecture/** | How the system works |
| Architecture decisions | docs/adr/** | Why important decisions were made |
| Requirement backlog | docs/backlog/requirements/** | Business/functional requirements and readiness state |
| Engineering backlog | docs/backlog/** | Planned work, technical debt and migration tracking |
| Domain/reference knowledge | linked docs / legacy references | Terms, metadata and supporting knowledge |
| Implementation | src/** | Runtime source code |
| Validation | tests/** | Automated verification and focused execution runbooks |

## Knowledge Rules
- GitHub repository Markdown is the Single Source of Truth.
- VS Code and Obsidian read the same local files.
- .github/** defines AI/developer governance.
- docs/** is the engineering knowledge base and primary research surface for architecture/design.
- docs/architecture/** describes how the system works.
- docs/adr/** records why important architecture decisions were made.
- docs/backlog/** records planned work and technical debt; it must not be treated as implemented architecture.
- docs/00_HOME.md is the routing index, not a duplicate of detailed documentation.
- Design agents should load only relevant documents, then verify assumptions against existing source code.
- Test agents should load only the production code, domain rules and nearest tests required for the current objective.
- When documentation and implementation conflict, explicitly report the conflict; do not silently invent a rule.
- Implementation remains in src/**, validation in tests/**, and focused operational scripts in scripts/**.
