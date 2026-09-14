# CherryStock Skill Catalog

## Purpose

`.github/skills/**` contains reusable, task-scoped procedures for CherryStock AI/developer work.

Ownership rule:

```text
Agent        = outcome owner
Instruction  = mandatory constraints
Skill        = repeatable procedure
Docs         = durable knowledge/design
Tool         = execution capability
```

A Skill is loaded only when the current task needs that procedure. It MUST NOT redefine Agent ownership, override Instructions, or duplicate canonical Docs.

## Current skills

| Skill | Procedure | Typical owner |
|---|---|---|
| `architecture-design` | Evidence-backed solution design, contracts, ADR check and architecture artifact synchronization | Solution Architect |
| `indicator-onboarding` | Technical-indicator discovery, metadata/config lifecycle, targeted backfill and validation handoff | Indicator Management |
| `regression-testing` | Focused deterministic regression/acceptance verification with bounded retry | Test Engineer |
| `data-quality-validation` | Dataset/pipeline freshness, coverage, duplicates, null/range and audit validation | Test Engineer / General Coding |
| `duckdb-migration` | Safe idempotent DuckDB schema/view/data migration and rollback/validation procedure | General Coding / Solution Architect |
| `chart-authoring` | Analytical visualization selection and Flint authoring/validation/rendering | Chart Agent |
| `drawio-skill` | Editable diagrams.net/Draw.io artifact authoring and validation | Solution Architect or routed owner |

## When to create a Skill

Create a Skill when at least one is true:

- the same multi-step procedure is reused across tasks;
- a procedure is too detailed for an Agent role file;
- a procedure coordinates multiple Tools but should not own the final outcome;
- the procedure has its own evidence/validation sequence;
- different Agents may reuse the same procedure under different owned outcomes.

Do not create a Skill for:

- a one-line repository policy → Instruction;
- architecture/domain knowledge → Docs;
- a new business/design/test owner → Agent;
- a raw capability/integration → Tool/adapter;
- a one-off trivial command that adds no reusable workflow.

## Skill contract

Each `SKILL.md` should contain:

```text
YAML name + description
Purpose
Applicable owners / trigger
Required inputs/context
Mandatory constraints / linked Instructions
Procedure
Tool usage boundaries
Evidence / output contract
Stop conditions / handoff
Anti-patterns
```

Prefer links to canonical Docs/Instructions over copied content.

## Precedence

When information conflicts:

```text
Governance
  > authoritative Agent ownership
  > mandatory Instruction
  > canonical Docs / ADR / requirement
  > Skill procedure
  > Tool defaults/examples
```

A conflict must be reported rather than silently resolved by a lower layer.

## Related

- `docs/architecture/agent-harness/AGENT_SKILL_INSTRUCTION_DOC_TOOL.md`
- `docs/adr/ADR-011-agent-harness-responsibility-hierarchy.md`
- `.github/copilot-instructions.md`
