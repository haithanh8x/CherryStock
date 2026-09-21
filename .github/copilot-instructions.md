# CherryStock Agent Harness — Governance and Routing

## Purpose

This file is the mandatory repository-level entry point for AI-assisted work in CherryStock. It defines routing, ownership, precedence, handoff, bounded execution and the official responsibility hierarchy.

Canonical architecture:
- `docs/architecture/agent-harness/README.md`
- `docs/architecture/agent-harness/AGENT_SKILL_INSTRUCTION_DOC_TOOL.md`
- `docs/adr/ADR-011-agent-harness-responsibility-hierarchy.md`

## Canonical execution boundary

All CherryStock work MUST be performed against this repository:

```text
https://github.com/haithanh8x/CherryStock
```

GitHub is the project Source of Truth. A local VS Code checkout is only the execution workspace for that same repository; Obsidian is a navigation/knowledge view over the same versioned files.

Rules:

- **ChatGPT direct-write policy:** when ChatGPT creates, modifies, renames or deletes CherryStock artifacts, the write MUST be performed directly against `https://github.com/haithanh8x/CherryStock` through the GitHub connection. Do not use a local checkout, container filesystem, temporary workspace or another storage system as a staging/write target for CherryStock changes unless the user explicitly requests that exception.
- ChatGPT MAY use local/container tooling for transient analysis or validation only when it does not become the write location or Source of Truth for CherryStock artifacts.
- Read, create, modify, validate and hand off CherryStock code, documentation, runbooks, scripts, tests, architecture artifacts and reusable evidence only within this repository.
- Do not create a parallel local-only project, personal copy, external document, or untracked handoff as a substitute for repository work.
- For a durable change, update the repository working tree, run the applicable validation, then commit and push the change to the GitHub repository. A local edit is not complete until it is represented in GitHub.
- Use repository-relative paths and project configuration; never make a user's Desktop, Downloads, temporary directory, or machine-specific path the canonical location.
- Before changing files, synchronize the checkout with the repository and preserve unrelated user changes. Use a branch/worktree and pull request when the active repository workflow requires it.
- ChatGPT-readable evidence remains under `docs/reference/data/**`; reusable safe evidence should be committed with its owning change.

## Official responsibility hierarchy

```text
L0  Governance      .github/copilot-instructions.md
L1  Agent           .github/agents/*.agent.md
L2  Instruction     .github/instructions/*.instructions.md
L3  Skill           .github/skills/*/SKILL.md
L4  Docs            docs/**
L5  Tool            MCP / GitHub / DuckDB / Flint / Archify / Draw.io / scripts / CLI
L6  Implementation  src/** + runtime entry points
L7  Verification    tests/** + reproducible validation evidence
```

Core ownership rule:

```text
Agent        owns the OUTCOME.
Skill        owns the PROCEDURE.
Instruction  owns mandatory RULES / CONSTRAINTS.
Docs         own durable KNOWLEDGE / DESIGN.
Tool         provides EXECUTION CAPABILITY.
Implementation owns runtime behavior.
Verification owns evidence that behavior satisfies the contract.
```

This hierarchy defines responsibility and precedence; it is not a requirement to load every layer for every task. Use the smallest sufficient context.

## Precedence and task loading

When material is relevant, use this precedence:

1. Repository governance in this file.
2. Authoritative Agent contract.
3. Matching mandatory Instructions.
4. Canonical Docs / ADR / requirement contracts.
5. Task-specific Skill procedure.
6. Tool/runtime evidence.

Normal task loading:

```text
User request
  → classify intent
  → authoritative Agent
  → mandatory Instructions
  → smallest relevant docs/** set
  → Skill when a repeatable specialist procedure exists
  → Tool / implementation
  → independent verification when required
```

A Skill MUST NOT override an Instruction, architecture document, ADR or Agent ownership. A Tool MUST NOT become a business or architecture Source of Truth.

## Authoritative Agent routing

| Primary intent | Owner |
|---|---|
| Requirement analysis, scope, business rules, acceptance criteria, backlog readiness | `.github/agents/BusinessAnalyst.agent.md` |
| Architecture, system/solution design, structural refactor, integration/data/agent architecture | `.github/agents/SolutionArchitect.agent.md` |
| Concrete technical-indicator lifecycle | `.github/agents/Indicator_Management.agent.md` |
| Chart recommendation, visualization mapping, Flint authoring/rendering | `.github/agents/Chart.agent.md` |
| Clear implementation, focused bug fix, contract-preserving refactor | `.github/agents/GeneralCoding.agent.md` |
| Independent test/validation/reproduction/regression verdict | `.github/agents/TestEngineer.agent.md` |

Do not force every request through every Agent. Select one authoritative owner for the current outcome and use explicit handoff only when the next owned outcome is required.

## Skill routing

Skills package repeatable procedures. Current canonical catalog is `.github/skills/README.md`.

| Procedure | Skill | Typical owner |
|---|---|---|
| Architecture/design procedure and design synchronization | `.github/skills/architecture-design/SKILL.md` | Solution Architect |
| Technical-indicator lifecycle | `.github/skills/indicator-onboarding/SKILL.md` | Indicator Management |
| Focused regression/acceptance verification | `.github/skills/regression-testing/SKILL.md` | Test Engineer |
| Pipeline/dataset data-quality verification | `.github/skills/data-quality-validation/SKILL.md` | Test Engineer / General Coding |
| DuckDB schema/view/data migration | `.github/skills/duckdb-migration/SKILL.md` | General Coding / Solution Architect |
| Analytical visualization + Flint authoring | `.github/skills/chart-authoring/SKILL.md` | Chart Agent |
| Editable diagrams.net/Draw.io artifact | `.github/skills/drawio-skill/SKILL.md` | Solution Architect or routed owner |

Load a Skill only when its procedure materially applies. Do not copy the procedure back into Agent or Instruction files.

## Domain Instruction routing

- DuckDB / SQL / transaction / data quality → `.github/instructions/database.instructions.md`
- Technical indicators → `.github/instructions/indicators.instructions.md`
- Chart / visualization → `.github/instructions/chart.instructions.md`
- Crawler / ingestion → `.github/instructions/crawler.instructions.md`
- Python execution → `.github/instructions/python.instructions.md`
- Testing / validation → `.github/instructions/testing.instructions.md`
- Archify synchronization → `.github/instructions/archify.instructions.md`

Instructions are mandatory constraints, not tutorials and not task owners.

## Knowledge routing

Start durable knowledge discovery at `docs/00_HOME.md`. Use only the smallest relevant set of:

- `docs/backlog/requirements/**` — requirement contracts;
- `docs/architecture/**` — how the system works / target design;
- `docs/adr/**` — why durable architecture decisions were made;
- `docs/domain/**` — market/business/domain knowledge;
- `docs/reference/**` — generated/reference contracts and historical references;
- `docs/runbook/**` — reproducible operational procedures;
- `docs/development/**` — developer workflow/material;
- `docs/ChangeRequest/**` — release/change traceability.

Backlog items describe planned work and MUST NOT be treated as implemented runtime behavior.

## Canonical ADLC handoff

```text
User
  → Router
  → BA when requirement readiness is needed
  → SA when design readiness is needed
  → GeneralCoding / authoritative domain owner
  → TestEngineer
  → PASS | FAIL | BLOCKED | REGRESSION
```

Primary gates:

- Business Analyst: `READY_FOR_DESIGN` or `READY_FOR_IMPLEMENTATION`.
- Solution Architect: `APPROVED_FOR_IMPLEMENTATION`.
- Implementation owner: `IMPLEMENTED_PENDING_VALIDATION`.
- Test Engineer: `PASS | FAIL | BLOCKED | REGRESSION`.

Implementation owners MUST NOT self-certify final PASS.

Fast paths are allowed:

- clear bounded implementation → General Coding/domain owner → Test Engineer;
- concrete indicator lifecycle → Indicator Management → Test Engineer;
- chart advice/spec/render → Chart Agent → user;
- test-only request → Test Engineer;
- architecture-only request → Solution Architect, with implementation handoff only when requested.

## Architecture / design rule

Architecture/design requests MUST use `.github/agents/SolutionArchitect.agent.md` and `.github/skills/architecture-design/SKILL.md`.

Approved architecture changes must update canonical `docs/architecture/**`, an ADR when required, and the corresponding Archify typed source/generated artifact according to the Solution Architect and Archify contracts. Archify is a visualization/validation capability, not architecture authority.

Draw.io is supplemental and is used when editable diagrams are explicitly requested or useful. It never replaces canonical Markdown/ADR or mandatory Archify synchronization.

## Indicator lifecycle rule

Concrete onboarding, activation, parameter-family change, repair, backfill, deactivation or deletion MUST use:

- `.github/agents/Indicator_Management.agent.md`;
- `.github/instructions/indicators.instructions.md`;
- `.github/skills/indicator-onboarding/SKILL.md`.

Broad Indicator Engine redesign remains a Solution Architect task.

## Chart rule

Chart recommendation, visualization selection and Flint authoring/rendering MUST use:

- `.github/agents/Chart.agent.md`;
- `.github/instructions/chart.instructions.md`;
- `.github/skills/chart-authoring/SKILL.md`.

Production integration after the chart contract is ready routes to General Coding. Reusable chart architecture remains a Solution Architect concern.

## Database migration rule

A material DuckDB schema/view/data migration MUST obey `.github/instructions/database.instructions.md` and use `.github/skills/duckdb-migration/SKILL.md` when the repeatable migration procedure applies. The migration must define forward change, idempotency, validation, downstream impact and rollback/repair behavior before production readiness is claimed.

## ChatGPT-readable data export rule

Any CherryStock workflow that produces data, reconciliation evidence, diagnostic extracts,
query results, snapshots or other machine-readable files intended for ChatGPT review MUST
export them under:

```text
docs/reference/data/
```

Rules:

- Do not use ad-hoc locations such as repository-root `export/`, `tmp/`, `data/` or local-only folders for ChatGPT handoff artifacts.
- Prefer domain-scoped subfolders, for example `docs/reference/data/zigzag/mwg/`.
- CSV is the default tabular interchange format unless another format is materially better.
- Use deterministic, descriptive filenames containing the subject and purpose; include a date/range when relevant.
- Export only the smallest sufficient evidence needed for review; do not dump the entire database by default.
- Files under `docs/reference/data/**` are reference/evidence artifacts, not runtime Source of Truth.
- When a runbook asks the user to provide data back to ChatGPT, its export command MUST target `docs/reference/data/**`.
- Generated evidence that should be reusable across ChatGPT/GitHub sessions SHOULD be committed to Git when safe and reasonably sized.
- Never export credentials, tokens, secrets, personal data or other sensitive values into this path.

This rule applies across Agents, Skills, scripts, SQL export statements and runbooks.

## Testing / validation rule

Test-focused tasks MUST use `.github/agents/TestEngineer.agent.md` and `.github/instructions/testing.instructions.md`.

Use `.github/skills/regression-testing/SKILL.md` for focused behavioral/regression verification and `.github/skills/data-quality-validation/SKILL.md` for dataset/pipeline quality validation.

Testing is finite:

```text
ONE objective
→ ONE focused execution path
→ ONE evidence-backed verdict
→ STOP or explicit bounded handoff
```

## Anti-loop execution governance

1. Define one current objective before execution.
2. Do not repeat the same analysis, file read, command or edit without new evidence.
3. Never rerun an unchanged failed command.
4. Default maximum two focused repair attempts for the same defect.
5. After two materially equivalent failures, return FAIL/BLOCKED and stop.
6. Do not opportunistically broaden scope.
7. A terminal verdict ends the current execution path.
8. A new hypothesis requires explicit authorization or a runbook that explicitly permits it.

## Implementation principles

- Prefer the smallest backward-compatible change.
- Reuse existing services/repositories/utilities before introducing abstractions.
- Keep data access, business logic, orchestration, validation and presentation responsibilities separate.
- Use declared public/SSOT contracts instead of internal persistence when available.
- Do not hard-code credentials or environment-specific paths already owned by configuration.
- Do not silently swallow failures.
- Use explicit SQL columns; avoid `SELECT *` in production queries.
- Batch database/API work when practical instead of issuing avoidable calls in loops.
- Preserve idempotency/rerun behavior for data workflows.
- Cross-module architecture decisions belong in `docs/adr/**`.

## Material ownership

```text
.github/copilot-instructions.md       global governance / router
.github/agents/*.agent.md             WHO owns outcomes and readiness gates
.github/instructions/*.instructions.md mandatory constraints
.github/skills/*/SKILL.md             HOW repeatable procedures are performed
docs/**                               durable engineering/domain knowledge
.vscode/mcp.json + scripts + CLIs     tool configuration/capability adapters
src/**                                runtime implementation
tests/**                              executable verification
```

Do not create a second knowledge Source of Truth inside Agent, Skill or generated diagram files.

## Change policy

- Update an existing canonical document instead of duplicating it.
- Requirement changes update the owning REQ material when one exists.
- Architecture contract changes update `docs/architecture/**`; durable cross-module choices update `docs/adr/**`.
- Operational procedures update `docs/runbook/**`.
- Major release/architecture changes update `docs/ChangeRequest/**`.
- GitHub repository content at `https://github.com/haithanh8x/CherryStock` remains the engineering Single Source of Truth; VS Code and Obsidian read the same checkout.
- No CherryStock change is complete until its durable artifacts and applicable evidence are committed and pushed to this repository.

## Completion rule

A routed owner may claim only the state it owns. Report changed artifacts, evidence, residual risks and next owner. Never invent runtime or validation evidence.