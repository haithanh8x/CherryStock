# CherryStock ADLC — Agent Execution Flow and Repository Material Map

## Purpose

Detailed execution companion to `docs/architecture/agent-harness/README.md` and the responsibility hierarchy in `AGENT_SKILL_INSTRUCTION_DOC_TOOL.md`.

This document explains which Agent owns each outcome, which Instructions constrain it, which Docs provide knowledge, which Skills supply repeatable procedures, which Tools execute work, and where implementation/verification evidence belongs.

## 1. Official stack

```text
L0 Governance      .github/copilot-instructions.md
L1 Agent           .github/agents/*.agent.md
L2 Instruction     .github/instructions/*.instructions.md
L3 Skill           .github/skills/*/SKILL.md
L4 Docs            docs/**
L5 Tool            MCP / GitHub / DuckDB / Flint / Archify / Draw.io / scripts / CLI
L6 Implementation  src/** + runtime entry points
L7 Verification    tests/** + reproducible evidence
```

Responsibility rule:

```text
Agent        = outcome
Instruction  = constraints
Skill        = procedure
Docs         = knowledge/design
Tool         = capability
Implementation = runtime behavior
Verification = proof
```

Operational loading normally reads Docs before executing a Skill so the procedure receives current architecture/requirement context.

## 2. Shared bootstrap

```text
User request
  ↓
.github/copilot-instructions.md
  ↓
.github/agents/CherryMon.agent.md
  ↓
intent-specific .github/agents/*.agent.md
  ↓
matching .github/instructions/*.instructions.md
  ↓
docs/00_HOME.md → smallest relevant docs/** set
  ↓
matching .github/skills/*/SKILL.md when procedure applies
  ↓
Tool / src implementation / tests according to ownership
```

No task should blindly load every Skill or every document.

## 3. Agent roster

### Default Repository Agent / Router

Control: `.github/copilot-instructions.md`.

Owns routing/context preservation, not specialist outcomes.

```text
interpret intent
  → choose authoritative owner
  → attach mandatory Instructions
  → route knowledge through docs/00_HOME.md
  → attach task-specific Skill when needed
  → preserve gate/acceptance criteria
  → consolidate terminal result
```

### CherryMon Architecture Constitution

File: `.github/agents/CherryMon.agent.md`.

Shared constitution only. Defines architecture direction, stable SSOT/dependency principles and routing vocabulary. It is not a normal lifecycle stage.

### Business Analyst

Owner: requirement readiness.

Primary durable output:

```text
docs/backlog/requirements/REQ-*.md
```

Exits:
- `READY_FOR_DESIGN` → Solution Architect;
- `READY_FOR_IMPLEMENTATION` → General Coding/domain owner;
- `DRAFT`, `NEEDS_CLARIFICATION`, `BLOCKED` → remains unresolved.

BA does not author production code or final test verdicts.

### Solution Architect

Owner: design readiness.

Layers:

```text
Agent        .github/agents/SolutionArchitect.agent.md
Instruction  matching domain Instructions + archify.instructions.md
Docs         requirement + architecture + ADR + current source evidence
Skill        .github/skills/architecture-design/SKILL.md
Tool         Archify; optional Draw.io; GitHub/source inspection
Output       docs/architecture/** + docs/adr/** + typed/generated architecture artifacts
```

Exit:

```text
APPROVED_FOR_IMPLEMENTATION
```

Only after required canonical Markdown/ADR and Archify representation are synchronized/validated.

### Indicator Management

Owner: concrete technical-indicator lifecycle.

```text
Agent        .github/agents/Indicator_Management.agent.md
Instruction  .github/instructions/indicators.instructions.md
Docs         docs/architecture/Indicator_Engine.md + ADR-002 + DB metadata
Skill        .github/skills/indicator-onboarding/SKILL.md
Tool         CherryMon/DuckDB MCP + targeted refresh_technical_indicators wrapper
Output       affected metadata/config/fact scope + lifecycle evidence
```

Procedure:

```text
DISCOVER → METADATA/CONFIG → TARGETED BACKFILL → VALIDATE → HANDOFF
```

Exit:

```text
IMPLEMENTED_PENDING_VALIDATION → TestEngineer
```

The old `.github/agents/Instructions/Indicator_Engine.md` path is retired. Historical material is only at `docs/reference/Indicator_Engine_Legacy_Reference.md`.

### Chart Agent

Owner: visualization recommendation/spec/render outcome.

```text
Agent        .github/agents/Chart.agent.md
Instruction  .github/instructions/chart.instructions.md
Docs         docs/architecture/Chart_Architecture.md + actual dataset contract
Skill        .github/skills/chart-authoring/SKILL.md
Tool         Flint MCP
```

Production integration after the chart contract is ready routes to General Coding and then Test Engineer. Draw.io is not a replacement for Flint chart authoring.

### General Coding

Owner: implementation readiness for clear changes not owned end-to-end by a specialist.

Relevant Skills when applicable:
- `duckdb-migration`;
- `data-quality-validation` for developer-side pipeline checks.

Primary outputs:

```text
src/**
scripts/**
configuration owned by the repository
affected canonical docs/change records
tests/** when implementation-side test changes are part of the delivery
```

Exit:

```text
IMPLEMENTED_PENDING_VALIDATION → TestEngineer
```

General Coding cannot self-declare final PASS.

### Test Engineer

Owner: independent evidence-backed verdict.

```text
Agent        .github/agents/TestEngineer.agent.md
Instruction  .github/instructions/testing.instructions.md + matching domain Instructions
Docs         requirement + architecture/ADR + implementation handoff
Skill        regression-testing and/or data-quality-validation
Tool         pytest/Python/DuckDB-MCP/scripts/UI tooling as appropriate
Evidence     tests/** + reproducible command/output
```

Terminal outcomes:

```text
PASS | FAIL | BLOCKED | REGRESSION
```

Failure routing:
- requirement gap → BA;
- design/data-model/contract gap → SA;
- implementation defect → General Coding/domain owner;
- dependency/environment blocker → Router/User.

## 4. Domain Instruction map

| Domain | Mandatory Instruction |
|---|---|
| DuckDB / SQL / transaction / data quality | `.github/instructions/database.instructions.md` |
| Technical indicators | `.github/instructions/indicators.instructions.md` |
| Chart / visualization | `.github/instructions/chart.instructions.md` |
| Crawler / ingestion | `.github/instructions/crawler.instructions.md` |
| Python | `.github/instructions/python.instructions.md` |
| Testing | `.github/instructions/testing.instructions.md` |
| Archify | `.github/instructions/archify.instructions.md` |

Instructions constrain whichever Agent owns the current outcome; they do not become the task owner.

## 5. Skill map

| Skill | Purpose | Typical owner |
|---|---|---|
| `architecture-design` | current-state → target design → ADR/migration/test → synchronized design handoff | Solution Architect |
| `indicator-onboarding` | indicator metadata/config → targeted backfill → lifecycle validation | Indicator Management |
| `regression-testing` | focused deterministic behavioral verification | Test Engineer |
| `data-quality-validation` | freshness/coverage/duplicate/null/range/idempotency verification | Test Engineer / General Coding |
| `duckdb-migration` | bounded schema/view/data migration | General Coding / Solution Architect |
| `chart-authoring` | visualization selection + Flint authoring/render | Chart Agent |
| `drawio-skill` | editable diagrams.net artifact | Solution Architect or routed owner |

Skill catalog: `.github/skills/README.md`.

## 6. Folder ownership

```text
.github/
  copilot-instructions.md       L0 router/governance
  agents/                       L1 outcome owners
  instructions/                 L2 mandatory constraints
  skills/                       L3 reusable procedures

docs/
  00_HOME.md                    L4 knowledge router
  backlog/requirements/         durable requirement contracts
  architecture/                 durable system/design Source of Truth
  architecture/diagrams/        typed/editable diagram sources
  architecture/generated/       presentation output only
  adr/                          durable decisions/rationale
  domain/                       market/business/domain knowledge
  reference/                    current generated + historical reference
  runbook/                      reproducible operating procedures
  ChangeRequest/                change/release traceability
src/                            L6 runtime implementation
scripts/                        L5 focused execution helpers
.vscode/mcp.json                L5 MCP tool configuration
tests/                          L7 executable verification
```

## 7. Canonical flows

### Material / unclear capability

```text
User
 → Router
 → Business Analyst
 → READY_FOR_DESIGN
 → Solution Architect + architecture-design Skill
 → APPROVED_FOR_IMPLEMENTATION
 → General Coding / domain Agent + applicable Skill
 → IMPLEMENTED_PENDING_VALIDATION
 → Test Engineer + validation Skill
 → PASS | FAIL | BLOCKED | REGRESSION
```

### Clear bounded implementation

```text
User → General Coding/domain Agent → applicable Skill → Test Engineer → verdict
```

### Indicator lifecycle

```text
User
 → Indicator Management
 → indicators Instructions + Indicator Engine Docs
 → indicator-onboarding Skill
 → CherryMon MCP / calcEngine
 → IMPLEMENTED_PENDING_VALIDATION
 → Test Engineer
```

### Chart / Flint

```text
User
 → Chart Agent
 → chart Instructions + actual data contract
 → chart-authoring Skill
 → Flint
 → advisory/spec/render result
```

Production integration continues:

```text
Chart contract → General Coding → Test Engineer
```

### Architecture visualization

```text
Solution Architect
 → architecture-design Skill
 → canonical Markdown / ADR
 → Archify typed source + validated generated representation
 → APPROVED_FOR_IMPLEMENTATION
```

Optional editable review artifact:

```text
Solution Architect → drawio-skill → Draw.io source/export
```

Draw.io does not replace the Archify gate.

## 8. Handoff payload

Every non-trivial handoff should contain:

```text
Objective / requirement
Upstream owner and gate
Canonical paths inspected
In scope / out of scope
Acceptance criteria
Approved contracts/invariants
Affected modules/files
Skills/tools used
Evidence produced
Known risks/blockers
Expected next owner/output/gate
```

## 9. Runtime migration boundary

This Harness reorganization does not perform a big-bang move of legacy source packages. `src/cherrystock/**` remains the target canonical layered runtime package while legacy modules are migrated feature-by-feature under the architecture backlog.

Governance/material ownership can be normalized independently from runtime package migration.

## 10. Synchronized visualization

Canonical typed workflow:

```text
docs/architecture/diagrams/cherrystock-adlc-agent-harness.workflow.json
```

Generated representation:

```text
docs/architecture/generated/CherryStock_ADLC_Agent_Harness.html
```

The GitHub Archify workflow validates/regenerates the presentation artifact when the typed workflow/execution map changes. Generated HTML is not manually edited as architecture meaning.
