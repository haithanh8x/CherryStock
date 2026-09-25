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

## Other requirements

- [[REQ-0025-smart-money-score|REQ-0025 — Ticker-level SmartMoneyScore]] — **DONE**; state-aware, explainable Smart Money behavioral scoring with independent confidence; TestEngineer PASS / KEEP on 2026-09-06. OOS calibration remains a separate production-activation gate.
- [[REQ-0026-smart-money-strategy|REQ-0026 — Smart Money BUY / HOLD / SELL Strategy Action]] — **IMPLEMENTED_PENDING_VALIDATION**; additive `TradeAction` + `TradeActionConfidenceScore` overlay on `vw_Ticker_SmartMoney`, derived from existing quality/state/factor evidence without changing REQ-0025 persistence. GitHub focused CI is green; local CherryMon validation remains required before functional re-closure.
- [[REQ-0027-price-movement-characterization|REQ-0027 — ZigZag-based Price Movement Foundation]] — **IMPLEMENTED_PENDING_VISUAL_ACCEPTANCE**; MWG technical runbook PASS (7 tests, 279 pivots, 0 structural errors, idempotent, pipeline regression PASS); multi-ticker rollout blocked pending MWG visual/user acceptance.

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

## ZigZag deviation roadmap

- [[REQ-0028-zigzag-deviation-calibration-v1-1|REQ-0028 — ZigZag Deviation Calibration V1.1]] — **IMPLEMENTED_PENDING_VALIDATION**
- [[REQ-0029-zigzag-multi-ticker-pilot-v1-2|REQ-0029 — ZigZag Multi-Ticker Pilot V1.2]] — **IMPLEMENTED_PENDING_VALIDATION**; prerequisite V1.1 PASS
- [[REQ-0030-zigzag-regime-aware-v2|REQ-0030 — ZigZag Regime-Aware Swing-Locked Deviation V2]] — **IMPLEMENTED_PENDING_VALIDATION**; manual research only

Execution order:

    REQ-0028 / V1.1
      -> TestEngineer PASS
      -> REQ-0029 / V1.2
      -> TestEngineer PASS / pilot decision
      -> REQ-0030 / V2
      -> TestEngineer PASS / research decision


## Price Movement characterization

- [[REQ-0031-zigzag-price-movement-character-v2|REQ-0031 — ZigZag-based Price Movement Characterization V2]] — **DONE**; TestEngineer PASS on MWG (19 focused/regression tests, 278/278 swings, structural validation PASS, idempotency PASS, reconciliation TotalCoreErrors=0). Evidence: `docs/reference/data/price_movement/mwg/`.
- [[REQ-0032-movement-context-v1|REQ-0032 — MovementContext V1]] — **DONE**; TestEngineer PASS / KEEP on 2026-09-21 (13/13 focused tests, migration + MWG validator + idempotency + daily regression PASS, Archify showcase ok=true, DB metadata refreshed).
- [[REQ-0033-active-ticker-movement-initload|REQ-0033 — Active Ticker ZigZag + Price Movement Initial Load]] — **DONE**; TestEngineer PASS / KEEP on 2026-09-22 across 349 active tickers, with 0 OHLC gaps, 0 structural mismatches, 349/349 MovementContext coverage, idempotent row counts, and daily regression 3/3 PASS.
- [[REQ-0034-daily-incremental-movement-pipeline|REQ-0034 — Daily Incremental Movement Pipeline]] — **DONE**; local TestEngineer PASS / KEEP on 2026-09-22 (39/39 focused tests, 349/349 structural coverage, zero stale/parity/geometry/profile errors, NOOP/idempotency PASS, Archify 9/9). Full `run.py` live path was blocked before core commit by a pre-existing Yahoo DQ error, recorded as a separate operational blocker.
- [[REQ-0035-yahoo-vndx-source-specific-dq-policy|REQ-0035 — Yahoo VND=X Source-Specific OHLC Data Quality Policy]] — **IMPLEMENTED_PENDING_VALIDATION**; preserves generic OHLC rules, downgrades only evidenced `VND=X` Yahoo envelope anomalies to auditable WARNING, and keeps all other Yahoo/non-OHLC failures blocking.

Validation:

    docs/runbook/ZigZag_Price_Movement_Character_V2.md
    docs/runbook/ZigZag_Price_Movement_Reconciliation.md
    docs/runbook/Active_Ticker_Movement_Initload.md
    docs/runbook/Daily_Incremental_Movement_Pipeline.md


## Yahoo source-specific Data Quality

- [[REQ-0035-yahoo-vndx-source-specific-dq-policy|REQ-0035 — Yahoo VND=X Source-Specific OHLC Data Quality Policy]]
- Architecture: [[../../architecture/Yahoo_Source_Specific_DQ_Policy|Yahoo Source-Specific DQ Policy]]
- ADR: [[../../adr/ADR-019-yahoo-vndx-source-specific-ohlc-dq-policy|ADR-019]]
- Runbook: [[../../runbook/Yahoo_VNDX_Source_Specific_DQ_Policy|Yahoo VND=X Source-Specific DQ Policy]]
