# CherryStock Requirements Backlog

This directory is the canonical location for durable business and functional requirements prepared by `.github/agents/BusinessAnalyst.agent.md`.

## Naming

`REQ-<number>-<short-name>.md`

Example:

`REQ-0021-motherduck-synchronization.md`

Use a stable ID. Update the existing requirement when refining the same target outcome; do not create a duplicate.

## States

- `DRAFT`
- `NEEDS_CLARIFICATION`
- `READY_FOR_DESIGN`
- `READY_FOR_IMPLEMENTATION`
- `BLOCKED`
- `IN_IMPLEMENTATION`
- `IMPLEMENTED_PENDING_VALIDATION`
- `DONE`
- `DEFERRED`

Only Business Analyst confirms requirement readiness. Implementation and validation states must reference evidence from their owning roles.

## Required Content

Use `REQUIREMENT_TEMPLATE.md`.

Every requirement must define the business objective, scope, business rules, observable acceptance criteria, non-functional requirements where relevant, dependencies, assumptions, open questions, risks and downstream routing.

A requirement describes WHAT and WHY. Technical design describes HOW and belongs under `docs/architecture/**` and `docs/adr/**`.

## Traceability

When available, link:

```text
REQ
→ Architecture / ADR
→ Implementation / PR / commit
→ Test evidence
→ Change Request / release
```

Backlog is not the Source of Truth for current runtime behavior.
