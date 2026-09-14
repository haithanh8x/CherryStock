---
name: duckdb-migration
description: "Design and execute a bounded CherryStock DuckDB schema/view/data migration with explicit dependencies, idempotency, transaction behavior, metadata refresh, downstream validation and rollback/repair evidence."
---

# CherryStock DuckDB Migration Skill

## Applicable owners

- Solution Architect uses this Skill when defining a migration contract as part of an approved design.
- General Coding uses it when implementing an approved DuckDB migration.
- Test Engineer independently validates the delivered behavior; this Skill does not own the final PASS verdict.

Mandatory constraints: `.github/instructions/database.instructions.md`.

Canonical knowledge:
- `docs/architecture/Data_Architecture.md`;
- `docs/reference/DB_Metadata.md`;
- affected architecture/ADR/requirement.

## Procedure

### 1. Discover current state

Identify:
- target database/schema/object;
- current object definition/grain/key;
- upstream dependencies;
- downstream views/services/scripts/tests;
- data volume and backfill impact;
- current public Source-of-Truth contract.

Prefer extending an existing owner over creating a duplicate table/view.

### 2. Define migration contract

State explicitly:
- forward change;
- compatibility expectations;
- DDL/DML sequence;
- transaction boundary;
- idempotency/rerun behavior;
- backfill scope;
- view/public-contract impact;
- rollback or forward-repair strategy;
- validation queries/tests.

A migration is not ready when the only plan is `run this SQL`.

### 3. Author migration

Rules:
- use explicit object and column names;
- preserve existing data unless destructive behavior is explicitly approved;
- make reruns safe where practical;
- batch related writes inside the appropriate transaction boundary;
- avoid arbitrary mutation through normal read-only MCP paths;
- isolate privileged/admin mutation capability according to repository governance;
- do not embed credentials, machine-specific paths or environment secrets.

Place durable SQL in the existing `src/DuckDB/sql/**` convention unless the approved architecture has migrated that ownership.

### 4. Preflight

Before mutation verify:
- expected source objects exist;
- required columns/types are present;
- no conflicting object already owns the proposed contract;
- expected connection/database is selected;
- the migration's destructive scope matches the approved request.

### 5. Execute bounded migration

Run the narrowest approved scope. Capture:
- command/tool;
- migration file/version;
- transaction result;
- affected rows/objects when available;
- any warning/failure.

On failure, rollback/repair according to the defined contract. Do not keep retrying unchanged SQL.

### 6. Refresh repository database context

When physical metadata changed, refresh the canonical generated/reference database context using the repository's existing metadata export mechanism. Do not hand-edit generated DB metadata to pretend the database changed.

### 7. Validate

Verify as applicable:
- object/column definition;
- keys/uniqueness;
- row/backfill coverage;
- NULL/default semantics;
- source/output reconciliation;
- public view behavior;
- unaffected downstream contracts;
- idempotent rerun;
- rollback/repair viability.

Use `data-quality-validation` when dataset-level quality checks are material.

### 8. Trace the change

For material migrations update:
- canonical architecture/ADR if the approved contract changed;
- runbook if operators need a reproducible procedure;
- related Change Request for release traceability.

### 9. Handoff

Return:

```text
DUCKDB MIGRATION HANDOFF
Migration/object:
Forward change:
Compatibility:
Transaction result:
Backfill/data impact:
Metadata refresh:
Developer validation:
Rollback/repair path:
Changed files:
Outcome: IMPLEMENTED_PENDING_VALIDATION | BLOCKED | IMPLEMENTATION_FAILED
Next owner: TestEngineer | SolutionArchitect | User
```

## Anti-patterns

- creating a second Source of Truth to avoid updating an existing owner;
- unbounded `DELETE`/`UPDATE`/DDL with no impact discovery;
- assuming a migration is idempotent without a rerun check;
- modifying production data in a read-only validation task;
- using generated reference files as the place to author target design;
- claiming final PASS from migration execution alone.
