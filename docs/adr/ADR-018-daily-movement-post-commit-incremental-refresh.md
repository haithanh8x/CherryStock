# ADR-018 — Daily Movement Uses Post-Commit Ticker-Level Incremental Refresh

- **Status:** Accepted
- **Date:** 2026-09-22
- **Requirement:** REQ-0034

## Context

REQ-0033 validated ZigZag → Price Movement → MovementContext across the full active universe.
The normal daily pipeline previously committed EOD/Indicator/SmartMoney in one shared DuckDB
transaction and did not run Movement.

Two concerns conflict if Movement is simply inserted inside that transaction:

1. Movement needs newly synchronized EOD.
2. Full-universe/ticker Movement processing benefits from per-ticker failure isolation and must not
   cause one symbol defect to roll back all ingestion/Indicator/SmartMoney work.

A second decision is required for incremental behavior. The validated ZigZag engine is a
full-history deterministic calculation; introducing a new stateful bar-by-bar engine in the same
production rollout would expand the correctness surface substantially.

## Decision

Daily execution has two commit domains:

~~~text
Phase A
core daily shared UoW
→ COMMIT

Phase B
MovementDailyPipelineService
→ select stale/recovery tickers
→ ticker-local ZigZag transaction when needed
→ ticker-local Price Movement transaction when needed
~~~

Incremental V1 is defined as:

- set-based ticker selection by latest OHLC vs ZigZag watermark;
- PM-only recovery when confirmed downstream lineage is stale;
- no write for aligned same-day reruns;
- full deterministic ZigZag rebuild for each ticker selected for ZigZag.

## Failure Decision

Movement failures do not roll back Phase A.

After all selected ticker work is attempted, run.py raises when hard failures exist so external
scheduling observes a failed daily run and the Movement validator/runbook can be used for repair.

## Price Movement Decision

Price Movement refresh is conditional on confirmed ZigZag lineage changes/inconsistency.

A provisional current-leg update alone does not refresh Price Movement. MovementContext sees the
updated current leg dynamically.

## Same-Date Correction Decision

Date-based incremental selection cannot prove a same-date OHLC row changed because the current
public input contract has no row-version watermark.

V1 therefore provides explicit forced maintenance execution rather than pretending corrections
are automatically detected.

## Consequences

Positive:

- reuses fully validated calculation semantics;
- same-day rerun becomes NOOP;
- PM computation is skipped when no confirmed swing changed;
- same-day retry repairs PM-only failures;
- one ticker cannot roll back core daily data or other successful Movement tickers.

Trade-offs:

- on each new trading day, most active tickers may require ZigZag full-history rebuild;
- core daily data can be committed while Movement is partially stale if Phase B fails;
- same-date corrections require explicit force.

## Future Optimization Gate

A true stateful ZigZag bar-advance engine may replace per-ticker full rebuild only after a separate
requirement proves replay parity with the canonical full-history engine across broad history and
edge cases.
