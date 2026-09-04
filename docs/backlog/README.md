# CherryStock Engineering Backlog

## Purpose

`docs/backlog/` is the canonical Markdown backlog for planned engineering work that has not yet become an implemented system contract.

Use backlog documents to record:
- analyzed business/functional requirements under `requirements/`;
- technical debt;
- architecture refactors;
- planned migrations;
- cross-module improvements;
- AI/platform evolution;
- work that needs prioritization before implementation.

Backlog is **not** the Source of Truth for current system behavior.

Current architecture belongs in `docs/architecture/**`.
Accepted architectural decisions belong in `docs/adr/**`.
Executable AI/developer rules belong in `.github/**`.

## Status

Use one of:

- `TODO` — accepted as backlog, not started.
- `READY` — sufficiently designed and ready for implementation.
- `IN_PROGRESS` — implementation is active.
- `BLOCKED` — cannot proceed until a dependency is resolved.
- `DONE` — implemented, validated, and documentation updated.
- `DEFERRED` — intentionally postponed.

## Priority

- `P0` — security, data-loss, production-blocking or repository-integrity issue.
- `P1` — important architecture / maintainability work.
- `P2` — valuable structural improvement that can be migrated incrementally.
- `P3` — future capability / optimization.

## Backlog item contract

Each material backlog item should contain:

```text
ID
Title
Priority
Status
Problem
Target
Scope
Acceptance Criteria
Dependencies
Related Architecture / ADR
Notes
```

Large items may be split into their own Markdown file when implementation tracking becomes complex.

## Current Backlogs

- [[Backlog_Status|Backlog Status Dashboard]] — consolidated current status across Requirements, Architecture and Agent Harness backlogs.
- [[requirements/README|Requirements Backlog]]
- [[requirements/REQUIREMENT_TEMPLATE|Requirement Template]]
- [[Architecture_Backlog|Architecture Backlog]]
- [[Harness_Backlog|Agent Harness Backlog]]

## Workflow

```text
Idea / User Request
    ↓
BusinessAnalyst when clarification/material analysis is required
    ↓
docs/backlog/requirements/REQ-*.md
    ↓
READY_FOR_DESIGN or READY_FOR_IMPLEMENTATION
    ↓
Architecture/design if needed
    ↓
docs/architecture/** + docs/adr/**
    ↓
GeneralCoding or authoritative domain implementation
    ↓
IMPLEMENTED_PENDING_VALIDATION
    ↓
TestEngineer / tests / validation
    ↓
DONE
```

When a backlog item is completed:
1. update the relevant architecture / ADR documentation;
2. mark the backlog item `DONE`;
3. keep the item as implementation history unless the backlog becomes too large, then move completed items to a future `docs/backlog/done/` archive.
