---
id: REQ-0038
title: R/S V2.4 Daily Incremental Source Effectiveness Evaluation
status: DRAFT
priority: P1
owner: BusinessAnalyst
primary_next_owner: BusinessAnalyst
related:
  requirements: REQ-0022
  architecture: docs/architecture/RS_Source_Effectiveness.md
  adr: docs/adr/ADR-008-rs-v2-4-source-effectiveness-promotion.md
  implementation:
  test:
  change_request:
---

# REQ-0038 — R/S V2.4 Daily Incremental Source Effectiveness Evaluation

## Business Objective

Enable R/S V2.4 Source Effectiveness to run incrementally after each successful daily market-data commit, evaluating only newly eligible or affected point-in-time observations instead of repeating a full-universe historical evaluation every day, while preserving exact, auditable research semantics.

## Background / Problem

REQ-0022 delivered the source-effectiveness and promotion framework. A monthly/full-evaluation runner and later provider warm-up, BB and VP fixes exist as follow-up work. Daily full-history recomputation can be expensive. Incremental evaluation must not confuse a new observation with a matured label: 5/10/20/40-bar outcomes become eligible only after their respective horizons complete. Changes in provider logic, historical corrections, model configuration or temporal splits can invalidate previously accumulated evidence.

## Scope

### In scope

- Daily post-commit incremental R/S V2.4 evaluation on the eligible active ticker universe.
- Per-ticker/source/config/role/horizon progress checkpoints and watermark tracking.
- Maturity-aware outcome processing for 5, 10, 20 and 40 trading-bar horizons.
- Reuse of immutable historical observations, source lineage and prior validated computations where possible.
- Idempotent upsert and resumable processing, with partial failure isolation and explicit retry.
- Detection of late-arriving data, corrections, missing history and provider warm-up; bounded replay/invalidation.
- Version-aware invalidation on changes to source registry, indicators, evaluation policy, code/model, data adjustment or split definitions.
- Daily observability: processed/skipped/replayed/failed ticker counts, lag, runtime and reconciliation status.
- Scheduled full reconciliation against the existing full runner, with a configurable tolerance and mismatch investigation.
- Public latest-complete effectiveness snapshot with freshness/as-of information and incomplete/unassessed semantics.

### Out of scope

- Automatically promoting sources, changing production Strength/ranking/weights, or deploying new R/S models.
- Replacing REQ-0022 full historical evaluation, source attribution, OOS governance or promotion gates.
- Intraday/tick-level evaluation.
- Prescribing specific persistence tables or implementation classes before SolutionArchitect review.

## Business Rules

1. The existing REQ-0022 full evaluation remains the reconciliation/reference baseline.
2. Only data available as of the relevant historical decision time may be used; label outcomes cannot be finalized before the horizon matures.
3. Re-running the same day with unchanged data and version must not duplicate or change published results.
4. An incomplete daily run cannot replace the latest successfully completed public snapshot.
5. Missing or immature evidence is UNASSESSED/pending, never automatically DROP.
6. Source effectiveness and promotion evidence remain separate from production runtime R/S Strength and visibility.
7. Source-role semantics, source-config ablation, TRAIN/VALIDATION/TEST separation and out-of-sample promotion protections from REQ-0022 remain binding.
8. When historical data or evaluation logic changes, affected results must be invalidated/replayed rather than silently combined across incompatible versions.
9. The daily incremental workflow must not introduce future leakage through revised splits, horizons or retrospective source configuration.

## Functional Requirements

1. Trigger a daily incremental evaluation after successful daily EOD commit and relevant data-quality gates; support manual rerun/backfill.
2. Detect newly eligible ticker/date/source/config/horizon observations and matured outcomes independently.
3. Maintain auditable run identity, input data cutoff, evaluation version, checkpoint and completion status.
4. Reuse prior valid results and compute only changed or newly mature contributions, while ensuring the same semantics as full evaluation.
5. Support partial recovery and replay for affected tickers/dates without forcing unrelated tickers to recompute.
6. Produce complete public snapshots only when consistency checks pass; preserve previous successful snapshot on failure.
7. Provide reconciliation against a full historical evaluation and flag material divergence.
8. Report incremental versus full runtime, compute savings and freshness/lag.

## Acceptance Criteria

- **AC-01 Daily trigger:** Following a successful daily EOD commit, a new incremental run processes eligible data; failed upstream DQ prevents publication.
- **AC-02 Horizon maturity:** An observation from day T is not scored for an H-bar outcome until H eligible trading bars have elapsed; no future-bar leakage occurs.
- **AC-03 No-op idempotency:** Repeating the same input cutoff and versions produces no duplicate records and no changed public metrics.
- **AC-04 Incremental scope:** A single newly eligible day does not trigger an unconditional full-universe historical recomputation.
- **AC-05 Corrections:** A revised OHLC/provider history invalidates and replays affected keys and horizons with traceable lineage.
- **AC-06 Failure recovery:** A partial failure resumes safely and never publishes incomplete results as complete.
- **AC-07 Full parity:** On the same as-of cutoff, versions, population and temporal splits, incremental outputs reconcile with the full runner within preapproved numeric tolerances; mismatches are surfaced.
- **AC-08 Governance isolation:** Incremental execution cannot automatically alter source-promotion approval, runtime weights, R1/S1 ranking or level visibility.
- **AC-09 Freshness:** Dashboard/public read contract identifies as-of date, last successful run, completeness and stale state.
- **AC-10 Performance:** A representative daily benchmark records wall time, recomputed scope and savings versus full evaluation; targets are approved during design.

## Non-functional Requirements

- Point-in-time correctness and reproducibility.
- Bounded CPU, memory and I/O use on the local daily pipeline.
- Transactional publication and safe restartability.
- Explicit logs/metrics without exposing sensitive configuration.
- Backward compatibility with REQ-0022 and existing monthly/full evaluation.

## Dependencies

- REQ-0022 R/S V2.4 full Source Effectiveness contract and evaluation outputs.
- Daily EOD/AmiBroker pipeline and adjusted market-data SSOT.
- Current BB/VP provider warm-up and historical evaluation fixes must be independently validated.
- SolutionArchitect design for checkpoint, invalidation, temporal split and reconciliation semantics.

## Open Questions / Design Handoff

- Should daily publication refresh only matured outcome metrics, or also preliminary unlabelled evidence?
- What is the authoritative daily post-commit trigger and its DQ gating boundary?
- What reconciliation cadence, numeric tolerances and target runtime are acceptable?
- How should historical temporal splits be frozen or versioned as new dates arrive?

## Next Step

BusinessAnalyst to confirm acceptance criteria and move to READY_FOR_DESIGN; SolutionArchitect then defines incremental persistence/replay design, ADR impact and test plan. Do not mark DONE without independent full-parity, leakage, failure-recovery and performance validation.
