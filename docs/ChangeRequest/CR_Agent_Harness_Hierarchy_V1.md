# Change Request — Agent Harness Responsibility Hierarchy V1

- **Change ID:** `CR-HARNESS-V1-20260915`
- **Date:** 2026-09-15
- **Type:** Architecture / AI Agent Harness / Documentation Governance / Refactor
- **Status:** DONE — repository validation PASS
- **Runtime database migration:** None
- **Runtime behavior change:** None intended; one ATR onboarding helper docstring was updated, with no logic change.

## 1. Objective

Reorganize CherryStock around one official responsibility hierarchy so AI/developer material has a single clear owner:

```text
L0 Governance
L1 Agent
L2 Instruction
L3 Skill
L4 Docs
L5 Tool
L6 Implementation
L7 Verification
```

Core rule:

```text
Agent        owns the OUTCOME.
Skill        owns the PROCEDURE.
Instruction  owns mandatory RULES / CONSTRAINTS.
Docs         own durable KNOWLEDGE / DESIGN.
Tool         provides EXECUTION CAPABILITY.
```

Implementation and verification remain distinct lower layers.

## 2. Before

CherryStock already had strong Agent/Instruction/Docs separation, but:

- reusable procedures were still embedded in long Agent files;
- only a small number of native Skills existed;
- domain/reference content remained under `.github/agents/Instructions/**`;
- Indicator lifecycle architecture, operational procedure and Agent behavior were partly duplicated;
- the Agent Harness diagram did not explicitly model Skill and Tool as separate layers;
- `.github/agents/Instructions/project_structured.md` remained a stale generated legacy artifact.

## 3. After

Canonical responsibility structure:

```text
.github/
├── copilot-instructions.md              # L0 governance/router
├── agents/                              # L1 outcome owners
├── instructions/                        # L2 mandatory constraints
└── skills/                              # L3 reusable procedures
    ├── architecture-design/
    ├── indicator-onboarding/
    ├── regression-testing/
    ├── data-quality-validation/
    ├── duckdb-migration/
    ├── chart-authoring/
    └── drawio-skill/

docs/                                    # L4 durable knowledge/design
├── architecture/
├── adr/
├── domain/
├── reference/
├── runbook/
├── backlog/
└── ChangeRequest/

Tooling / MCP / scripts / CLI             # L5 capability
src/**                                    # L6 runtime behavior
tests/**                                  # L7 executable verification
```

## 4. Key changes

### Governance

- Formalized the hierarchy in `.github/copilot-instructions.md`.
- Added explicit Skill routing and precedence rules.
- Kept fast paths; not every task is forced through BA → SA → Dev → Test.

### Agent files

- Solution Architect now owns design readiness and delegates repeatable design steps to `architecture-design`.
- Indicator Management owns lifecycle readiness and delegates Discover → Metadata → Backfill → Validate to `indicator-onboarding`.
- Test Engineer owns the independent terminal verdict and delegates test/data-quality procedures to Skills.
- General Coding can use `duckdb-migration` / `data-quality-validation` without becoming the architecture/test owner.

### Skills

Introduced canonical native procedures:

```text
architecture-design
indicator-onboarding
regression-testing
data-quality-validation
duckdb-migration
```

Existing `chart-authoring` and `drawio-skill` remain in place.

### Knowledge migration

Legacy `.github/agents/Instructions/**` ownership is retired:

- `StockTerm.md` → `docs/domain/market/Stock_Terms.md`;
- `StockStrategies.md` → `docs/domain/strategy/Stock_Strategies.md`;
- long-form Indicator Engine legacy detail → `docs/reference/Indicator_Engine_Legacy_Reference.md`;
- indicator lifecycle procedure → `.github/skills/indicator-onboarding/SKILL.md`;
- stale `project_structured.md` → removed.

### Architecture decision

Added:

```text
docs/adr/ADR-011-agent-harness-responsibility-hierarchy.md
```

### Architecture visualization

Updated:

```text
docs/architecture/diagrams/cherrystock-adlc-agent-harness.workflow.json
```

The typed workflow now visualizes:
- L0 governance;
- L1 Agents;
- L2 Instructions;
- L3 Skills;
- L4 Docs;
- L5 Tools;
- L6 implementation;
- L7 verification.

GitHub Actions validated the workflow with Archify `v2.16.0`, rendered the synchronized HTML, applied repository typography, enriched the semantic passport, synchronized the status block and committed the regenerated artifact.

## 5. Compatibility

This change intentionally **does not** perform the runtime package migration tracked by CS-ARCH-001/002.

Legacy runtime packages such as:

```text
src/CrawlStock
src/calcEngine
src/Chart
src/DuckDB
src/Orchestrator
src/Telegram
src/Ults
src/AiModels
```

remain supported. `src/cherrystock/**` remains the target canonical layered package and will be migrated incrementally in separate changes.

Therefore this release is primarily a governance/material-ownership refactor and does not intentionally change market-data, indicator calculation, UI or database runtime behavior.

## 6. Database impact

```text
DuckDB schema change: NO
Data backfill: NO
View change: NO
Migration script: N/A
```

## 7. Validation result

**Verdict: PASS** for the scope of this governance/architecture reorganization.

Evidence:

1. legacy `.github/agents/Instructions/**` ownership was removed;
2. seven Skills are discoverable under `.github/skills/**`;
3. core Agents point to their applicable Skills;
4. `docs/00_HOME.md` routes domain knowledge to `docs/domain/**`;
5. `Indicator_Engine.md` points to the native lifecycle Skill and historical reference path;
6. ADR-011 exists and matches repository governance;
7. Archify workflow `Render Archify Agent Harness` run `34874598478` completed successfully, including validation, rendering, semantic-passport enrichment and generated artifact synchronization;
8. generated artifact commit: `41456056d00d75085d742db1462344386cb3d899`;
9. no DuckDB schema/data migration was introduced;
10. `scripts/seed_atr14_onboarding.py` received documentation-only text updates; calculation/mutation logic was not changed by this Change Request.

## 8. Rollback

Because there is no database/runtime migration, rollback is Git-based:

- revert the harness/governance commits if routing breaks;
- restore previous Agent/Instruction paths from Git history only as a temporary recovery measure;
- no data rollback is required.

Do not restore `.github/agents/Instructions/**` as a long-term ownership model; repair canonical routing instead.

## 9. Related material

- `docs/adr/ADR-011-agent-harness-responsibility-hierarchy.md`
- `docs/architecture/agent-harness/AGENT_SKILL_INSTRUCTION_DOC_TOOL.md`
- `docs/architecture/agent-harness/AGENT_EXECUTION_FLOW.md`
- `.github/skills/README.md`
- `docs/backlog/Harness_Backlog.md`
- `docs/backlog/Architecture_Backlog.md`
- `docs/backlog/Backlog_Status.md`
