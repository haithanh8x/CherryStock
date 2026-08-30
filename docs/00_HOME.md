# 🍒 CherryStock Engineering Knowledge Base

This page is the entry point for the CherryStock Second Brain. Open the repository root as an Obsidian Vault and start navigation here.

## AI Governance
- [[../.github/copilot-instructions|Copilot Instructions]]
- [[../.github/agents/CherryMon.agent|CherryMon Architecture Constitution]]

## Domain Instructions
- [[../.github/instructions/database.instructions|Database Instructions]]
- [[../.github/instructions/indicators.instructions|Indicator Instructions]]
- [[../.github/instructions/chart.instructions|Chart Instructions]]
- [[../.github/instructions/crawler.instructions|Crawler Instructions]]
- [[../.github/instructions/testing.instructions|Testing Instructions]]

## Architecture
- [[architecture/Second_Brain|Second Brain Architecture]]
- [[architecture/Indicator_Engine|Indicator Engine]]
- [[architecture/Data_Architecture|Data Architecture]]
- [[architecture/Chart_Architecture|Chart Architecture]]

## Architecture Decision Records
- [[adr/ADR-001-duckdb-connection|ADR-001 DuckDB Connection]]
- [[adr/ADR-002-indicator-source-of-truth|ADR-002 Indicator Source of Truth]]

## Domain Knowledge
- [[../.github/agents/DB_Metadata|DB Metadata]]
- [[../.github/agents/Instructions/StockTerm|Stock Terms]]
- [[../.github/agents/StockStrategies|Stock Strategies]]
- [[../.github/agents/Instructions/project_structured|Project Structure - Legacy Reference]]

## Development
- [[development/Development_Workflow|Development Workflow]]

## Knowledge Rules
- GitHub repository Markdown is the Single Source of Truth.
- VS Code and Obsidian read the same local files.
- `.github/**` defines AI/developer governance.
- `docs/architecture/**` describes how the system works.
- `docs/adr/**` records why important architecture decisions were made.
- Implementation remains in `src/**`, validation in `tests/**`, and focused operational scripts in `scripts/**`.