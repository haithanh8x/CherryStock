---
name: architecture-design
description: "Perform evidence-backed CherryStock solution architecture: discover current state, define responsibilities/contracts/data model, decide ADR/migration/testing needs, and synchronize mandatory architecture artifacts. Use for architecture, solution design, structural refactor, integration/data/agent architecture, or cross-module design."
---

# CherryStock Architecture Design Skill

## Owner and purpose

Default owner: `.github/agents/SolutionArchitect.agent.md`.

This Skill owns the repeatable **design procedure**. The Solution Architect still owns design correctness and the `APPROVED_FOR_IMPLEMENTATION` gate.

## Required context

Before executing:

1. Read `.github/copilot-instructions.md` and the Solution Architect Agent contract.
2. Read the ready requirement when one exists.
3. Load matching `.github/instructions/*.instructions.md`.
4. Start knowledge discovery at `docs/00_HOME.md`.
5. Read the smallest relevant architecture/ADR/domain/reference set.
6. Inspect current source, SQL, tests and public contracts as evidence.

Do not design from the prompt alone when repository evidence exists.

## Procedure

### 1. Frame the design concern

Record:
- requirement/objective;
- affected domains;
- in-scope/out-of-scope;
- current Source of Truth;
- compatibility constraints;
- expected downstream owner.

If behavior is materially ambiguous, return to Business Analyst instead of inventing requirements.

### 2. Model current state

Identify only relevant:
- components and responsibilities;
- dependency direction;
- input/output contracts;
- persistence/state;
- data flow;
- logical/physical data model where applicable;
- failure/operational behavior;
- current callers/consumers.

Explicitly report documentation/code conflicts.

### 3. Define target design

For each changed component define:
- responsibility;
- inputs;
- outputs;
- dependencies;
- state/persistence;
- errors/failure behavior;
- observability;
- idempotency/rerun semantics where relevant.

For structured data define:
- business meaning;
- grain;
- keys and relationships/cardinality;
- important types/nullability/default semantics;
- uniqueness/integrity;
- ownership/SSOT;
- lineage and downstream consumers;
- history/versioning/retention where relevant.

### 4. Check responsibility boundaries

Confirm:
- no existing owner already satisfies the responsibility;
- no duplicate Source of Truth is introduced;
- Application code does not depend on avoidable infrastructure details;
- UI/presentation does not absorb domain calculation or raw persistence logic;
- proposed dependencies follow existing architecture direction;
- legacy compatibility is explicit during incremental migration.

### 5. Define compatibility and migration

Specify:
- backward compatibility;
- migration sequence;
- data backfill/config impact;
- feature/rollout boundary when applicable;
- rollback/repair behavior;
- consumers requiring update.

Use `.github/skills/duckdb-migration/SKILL.md` when a material DuckDB migration is part of the design.

### 6. Define validation strategy

State the minimum evidence needed after implementation:
- unit/integration/regression scope;
- data-quality assertions;
- migration/idempotency checks;
- operational or UI checks;
- architecture contract checks.

Do not claim implementation PASS from design review.

### 7. ADR decision

Create/update an ADR when the design makes a durable cross-module choice involving responsibility boundaries, Source of Truth, persistence/integration strategy, compatibility contract or other decision future maintainers need to understand.

### 8. Synchronize architecture artifacts

For approved CherryStock architecture changes, follow the mandatory Solution Architect/Archify contract:

1. update canonical `docs/architecture/**`;
2. update ADR when required;
3. update corresponding Archify typed source under `docs/architecture/diagrams/**`;
4. regenerate/validate the corresponding artifact under `docs/architecture/generated/**` using repository automation;
5. do not claim `APPROVED_FOR_IMPLEMENTATION` while canonical docs and generated representation disagree.

Use `.github/skills/drawio-skill/SKILL.md` only as a supplemental editable diagram procedure when requested/useful. Draw.io does not replace Archify synchronization.

### 9. Handoff

Return an implementation-ready payload containing:
- requirement/reference paths;
- approved design path;
- ADR path/status;
- affected modules/files;
- contracts/invariants to preserve;
- migration steps;
- validation focus;
- known risks;
- next owner.

## Stop conditions

Stop with a handoff instead of continuing when:
- requirement ambiguity changes expected behavior → Business Analyst;
- environment/evidence needed for design is unavailable → BLOCKED;
- design is approved and implementation was not requested → return design result;
- implementation is required → General Coding or authoritative domain agent.

## Anti-patterns

- inventing topology not supported by repository evidence;
- creating a new service/table just to make a diagram symmetrical;
- mixing durable design meaning into generated HTML only;
- placing procedural steps in architecture Docs instead of this Skill/runbook;
- treating Archify or Draw.io as the decision maker.
