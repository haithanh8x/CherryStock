---
id: REQ-0034
title: Daily Incremental Movement Pipeline
status: IMPLEMENTED_PENDING_VALIDATION
priority: P1
owner: BusinessAnalyst
primary_next_owner: TestEngineer
related:
  prerequisite:
    - docs/backlog/requirements/REQ-0033-active-ticker-movement-initload.md
  architecture:
    - docs/architecture/Daily_Incremental_Movement_Pipeline.md
  adr:
    - docs/adr/ADR-018-daily-movement-post-commit-incremental-refresh.md
  implementation:
    - src/cherrystock/application/services/movement_daily_pipeline.py
    - run.py
    - scripts/run_daily_movement.py
  test:
    - tests/test_movement_daily_pipeline.py
    - scripts/validate_daily_movement.py
    - docs/runbook/Daily_Incremental_Movement_Pipeline.md
---

# REQ-0034 — Daily Incremental Movement Pipeline

## Business Objective

Operationalize the validated all-active-ticker movement chain as part of the normal daily
CherryStock run while preserving deterministic ZigZag/Price Movement semantics and avoiding
unnecessary same-day recomputation.

## Functional Requirements

1. The normal run.py flow MUST invoke Movement only after the existing canonical daily
   EOD/Indicator/SmartMoney transaction commits.
2. Daily Movement selection MUST use vw_Ticker_Active as universe SSOT.
3. A ticker MUST be selected when:
   - ZigZag current state is missing;
   - LatestOHLCDate > ZigZagAsOfDate;
   - Price Movement lineage is stale relative to confirmed ZigZag swings;
   - a maintenance caller explicitly forces it.
4. A same-day rerun with aligned ZigZag + Price Movement MUST select zero tickers.
5. For a selected stale ZigZag ticker, V1 MUST run the existing deterministic full-history
   per-ticker ZigZag rebuild rather than introduce a new stateful ZigZag algorithm.
6. After ZigZag refresh, Price Movement MUST refresh only when confirmed swing lineage changed
   or downstream rows/profile are incomplete/stale.
7. If ZigZag is already current but Price Movement is stale, rerun MUST repair Price Movement
   without rebuilding ZigZag.
8. Zero-confirmed-swing tickers MUST clear stale Price Movement rows, if any.
9. One ticker failure MUST NOT roll back already committed core daily EOD/Indicator/SmartMoney data.
10. One ticker failure MUST NOT roll back successful Movement work for other tickers.
11. Any hard Movement failure MUST make run.py exit non-zero after processing, so operations
    can detect partial Movement freshness.
12. MovementContext MUST remain a derived view; no daily MovementContext persistence step is added.
13. A standalone runner MUST support dry-run planning, explicit tickers, limit, force, and evidence export.
14. A daily validator MUST detect stale ZigZag, source rewind, ZigZag/Price Movement row-count or confirmed-geometry mismatch, stale Movement Profile, and MovementContext coverage mismatch.

## Business Rules

- Daily incremental means incremental ticker selection and downstream recomputation, while
  ZigZag V1 remains deterministic full-history rebuild for each selected ticker.
- ZZ_D_5_MVP and PM_ZZ_D_V2 remain the active lineage.
- Same-day OHLC correction without a newer Date is not auto-detectable from current source contracts;
  operational repair uses --force.
- Price Movement depends on confirmed swings; a changed provisional ZigZag current leg alone does
  not require Price Movement recomputation.
- Core daily commit and Movement daily commit are deliberately separate failure domains.

## Scope

### In Scope
- daily post-commit Movement stage in run.py;
- stale/missing/recovery planner;
- per-ticker isolated execution;
- Price Movement lineage-aware skip/refresh;
- standalone runner and validator;
- runbook and architecture/ADR synchronization.

### Out of Scope
- stateful O(1)-bar ZigZag advancement;
- volatility-aware ZigZag promotion;
- SmartMoney/R/S/Strategy consumption changes;
- portfolio logic;
- persistence of MovementContext;
- automatic detection of same-date source corrections without force.

## Acceptance Criteria

- AC-01 aligned same-day universe produces selected_ticker_count=0.
- AC-02 newer OHLC selects only stale ticker(s).
- AC-03 missing ZigZag selects ticker.
- AC-04 stale Price Movement with current ZigZag selects ticker for PM-only repair.
- AC-05 selected stale ZigZag ticker ends with ZigZagAsOfDate=LatestOHLCDate.
- AC-06 unchanged confirmed swing lineage results in PriceMovementStatus=UP_TO_DATE.
- AC-07 changed confirmed swing lineage results in PriceMovementStatus=REFRESHED.
- AC-08 no confirmed swings leave zero Price Movement/profile rows.
- AC-09 one ticker failure is isolated and reported.
- AC-10 run.py invokes Movement after core UoW commit.
- AC-11 Movement failure returns non-zero/raises after core commit.
- AC-12 validator reports stale_zigzag_count=0 after successful daily run.
- AC-13 global ZigZag/Price Movement swing row-count and confirmed geometry parity remain zero mismatch.
- AC-14 MovementContext remains covered for all eligible profiles.
- AC-15 rerun after successful daily run is a NOOP unless forced.
- AC-16 existing daily pipeline tests and REQ-0033 full-universe contracts do not regress.

## Non-functional Requirements

- Reliability: failure isolation by ticker/stage.
- Idempotency: same-day aligned rerun does no Movement writes.
- Performance: avoid Price Movement recomputation when confirmed swings did not change.
- Observability: plan/result summary with selected/skipped/failure counts.
- Compatibility: reuse validated REQ-0033 calculation functions and public contracts.

## Dependencies

- REQ-0033 DONE and initial load present;
- vw_Ticker_Active;
- vw_Ticker_OHLC_D;
- vw_Ticker_ZigZag_Current;
- vw_Ticker_ZigZag_Swings;
- vw_Ticker_Price_Movement_Swings;
- vw_Ticker_Movement_Profile;
- vw_Ticker_Movement_Context.

## Risks

- On a normal new trading date, most/all active tickers may be selected because every ticker receives new EOD.
- Full-history ZigZag rebuild per selected ticker is correctness-first, not final performance optimization.
- Same-date source corrections require --force.

## Handoff

~~~text
Status: IMPLEMENTED_PENDING_VALIDATION
Primary next owner: TestEngineer
Acceptance criteria count: 16
Blocking questions: none
~~~
