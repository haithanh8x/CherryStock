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

## Current R/S roadmap

```text
REQ-0022 / V2.4
Source Effectiveness & Indicator Promotion
        ↓
REQ-0023 / V2.5
Historical Reliability & Confident Strength Shadow
        ↓
V2.5 TEST/OOS Promotion Gate
        ↓
REQ-0024 / V2.6
Production Confidence Integration
```

- [[REQ-0022-rs-v2-4-source-effectiveness|REQ-0022 — R/S V2.4 Source Effectiveness & Indicator Promotion Framework]]
- [[REQ-0023-rs-v2-5-historical-reliability-confident-strength|REQ-0023 — R/S V2.5 Historical Reliability & Confident Strength Shadow Evaluation]]
- [[REQ-0024-rs-v2-6-production-confident-strength|REQ-0024 — R/S V2.6 Production Confident Strength Integration]]

Key governance boundary:

- V2.5 is shadow/research and MUST NOT change production Current Strength, R1/S1 ranking or level visibility.
- V2.6 production integration is blocked until V2.5 demonstrates sufficient role-appropriate positive evidence, coverage, OOS quality and stability.
- Missing Source Effectiveness is UNASSESSED, not DROP.
- Confident Strength is a confidence-adjusted score, not a calibrated Hold/Break probability.

## Other active requirements

- [[REQ-0025-smart-money-score|REQ-0025 — Ticker-level SmartMoneyScore]] — state-aware, explainable Smart Money behavioral scoring with independent confidence; architecture approved for implementation.

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