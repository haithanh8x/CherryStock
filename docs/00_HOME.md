# 🍒 CherryStock Engineering Knowledge Base

This page is the canonical knowledge-routing entry point for CherryStock. Open the repository root as an Obsidian Vault and start navigation here.

AI agents MUST use this page to discover relevant engineering knowledge before architecture/design/test work. Do not scan every document blindly; follow the smallest relevant path below.

## AI Governance
- [[../.github/copilot-instructions|Copilot Instructions]]
- [[../.github/agents/CherryMon.agent|CherryMon Architecture Constitution]]
- [[../.github/agents/SolutionArchitect.agent|Solution Architect Agent]]
- [[../.github/agents/TestEngineer.agent|Test Engineer Agent]]

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
- [[../.github/agents/DB_Metadata|DB Metadata]]
- [[runbook/MCP_DuckDB|DuckDB MCP Runbook]]

### Technical Indicators
- [[architecture/Indicator_Engine|Indicator Engine Architecture]]
- [[adr/ADR-002-indicator-source-of-truth|ADR-002 Indicator Source of Truth]]
- [[../.github/instructions/indicators.instructions|Indicator Instructions]]
- [[../.github/agents/Instructions/Indicator_Engine|Legacy Detailed Indicator Engine Reference]]

### Chart / Visualization
- [[architecture/Chart_Architecture|Chart Architecture]]
- [[architecture/theme|Theme Architecture]]
- [[architecture/RS_Ladder|RS Ladder Architecture]]
- [[adr/ADR-003-centralized-theme-system|ADR-003 Centralized Theme System]]
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
- [[architecture/Second_Brain|Second Brain Architecture]]
- [[architecture/Indicator_Engine|Indicator Engine]]
- [[architecture/Data_Architecture|Data Architecture]]
- [[architecture/Chart_Architecture|Chart Architecture]]
- [[architecture/theme|Theme Architecture]]
- [[architecture/RS_Ladder|RS Ladder Architecture]]

## Architecture Decision Records
- [[adr/ADR-001-duckdb-connection|ADR-001 DuckDB Connection]]
- [[adr/ADR-002-indicator-source-of-truth|ADR-002 Indicator Source of Truth]]
- [[adr/ADR-003-centralized-theme-system|ADR-003 Centralized Theme System]]

## Runbooks
- [[runbook/MCP_DuckDB|CherryStock Local DuckDB MCP]]

## Domain Knowledge
- [[../.github/agents/Instructions/StockTerm|Stock Terms]]
- [[../.github/agents/StockStrategies|Stock Strategies]]
- [[../.github/agents/Instructions/project_structured|Project Structure - Legacy Reference]]

## Reference
- [[../.github/agents/DB_Metadata|DB Metadata]]

## Backlog
- [[backlog/README|Backlog Guide]]
- [[backlog/Architecture_Backlog|Architecture Backlog]]

Backlog documents record planned work and technical debt only. They are not the Source of Truth for current runtime behavior.

## Development
- [[development/Development_Workflow|Development Workflow]]

## Knowledge Ownership

| Area | Owner | Purpose |
|---|---|---|
| Global AI governance | .github/copilot-instructions.md | Repository-wide AI/developer behavior |
| Architecture constitution | .github/agents/CherryMon.agent.md | Stable CherryStock architecture principles |
| Design workflow | .github/agents/SolutionArchitect.agent.md | How AI researches and produces architecture/design |
| Test workflow | .github/agents/TestEngineer.agent.md | How AI designs/executes focused tests and terminates bounded investigations |
| Domain execution rules | .github/instructions/*.instructions.md | MUST/MUST NOT rules for implementation |
| System architecture | docs/architecture/** | How the system works |
| Architecture decisions | docs/adr/** | Why important decisions were made |
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
