# CherryStock Development Materials

This directory contains durable developer workflow and non-obvious implementation guidance.

## Contents

- `Development_Workflow.md` — repository-wide development and agent handoff workflow.
- `implementation-notes/` — optional notes for changes with non-obvious migration, operational or developer details.

## Ownership

`.github/agents/GeneralCoding.agent.md` owns implementation readiness but does not own architecture, requirements or final test verdicts.

General Coding primarily changes:

- `src/**`;
- `scripts/**`;
- configuration owned by existing modules;
- focused automated tests under `tests/**`;
- canonical documentation affected by the implementation.

Update the existing architecture, ADR, runbook, requirement or domain material when its contract changes. Do not create a development note merely to repeat a diff.

## Implementation Outcome

Normal handoff:

```text
READY requirement / APPROVED design
→ GeneralCoding
→ IMPLEMENTED_PENDING_VALIDATION
→ TestEngineer
→ PASS / FAIL / BLOCKED / REGRESSION
```
