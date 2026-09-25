---
id: REQ-0036
title: Weekly Full-Universe Movement Pipeline
status: IMPLEMENTED_PENDING_VALIDATION
priority: P1
owner: BusinessAnalyst
primary_next_owner: TestEngineer
related:
  prerequisite:
    - docs/backlog/requirements/REQ-0033-active-ticker-movement-initload.md
    - docs/backlog/requirements/REQ-0034-daily-incremental-movement-pipeline.md
  architecture:
    - docs/architecture/Weekly_Movement_Pipeline.md
  adr:
    - docs/adr/ADR-020-weekly-movement-scheduling.md
  implementation:
    - runWeekly.py
    - src/cherrystock/application/services/movement_weekly_pipeline.py
    - run.py
    - src/DuckDB/sql/movement_context_v1_schema.sql
  test:
    - tests/test_movement_weekly_pipeline.py
    - tests/test_run_daily_movement_integration.py
    - tests/test_movement_context_v1.py
    - scripts/validate_weekly_movement.py
    - docs/runbook/Weekly_Movement_Pipeline.md
---

# REQ-0036 — Weekly Full-Universe Movement Pipeline

## Business Objective

Reduce normal CherryStock daily runtime by moving the expensive full-universe ZigZag + Price
Movement refresh from daily execution to a weekly execution lane, while preserving the validated
full-history calculation semantics and providing explicit freshness metadata to downstream consumers.

## Background

REQ-0034 integrated Movement after the daily core commit, but the current ZigZag implementation is
only incremental at ticker selection level. On a new trading date almost all active tickers become
stale, and each selected ticker still performs a deterministic full-history ZigZag rebuild.

Observed operational cost is approximately 60 minutes per daily Movement run.

The weekly design reduces expected full-universe Movement execution frequency from roughly five
times per trading week to once per week, while retaining on-demand ticker refresh for exceptional use.

## Functional Requirements

1. Normal `run.py` MUST NOT execute full-universe ZigZag or Price Movement.
2. A new `runWeekly.py` MUST own the normal full-universe Movement schedule.
3. Weekly Movement MUST use `vw_Ticker_Active` as universe SSOT.
4. Weekly Movement MUST reuse the already validated REQ-0033 full-history orchestration.
5. Weekly Movement MUST rebuild ZigZag before Price Movement for every selected active ticker.
6. The existing fixed lineage remains `ZZ_D_5_MVP` → `PM_ZZ_D_V2`.
7. Transaction isolation remains one ticker per stage.
8. Existing manual/on-demand ticker refresh remains available via `scripts/run_daily_movement.py`.
9. `vw_Ticker_Movement_Context` MUST expose `LatestOHLCDate`, `MovementAgeTradingDays` and `MovementFreshnessStatus`.
10. `MovementAgeTradingDays` MUST count ticker trading sessions strictly after `ContextAsOfDate` through latest available OHLC.
11. Freshness policy MUST be: `FRESH` when age=0; `AGING` when age=1–5; `STALE` when age>5; `UNKNOWN` when unresolved.
12. Weekly validator MUST fail when any active ticker is missing MovementContext, freshness is `UNKNOWN` or `STALE`, or age exceeds five trading sessions.
13. Existing daily core EOD/Indicator/SmartMoney transaction ordering MUST remain unchanged.
14. No ZigZag or Price Movement formula change is authorized.
15. No historical data rewrite is authorized beyond the normal deterministic weekly refresh.
16. Existing `runMonthly.py` remains independent.

## Business Rules

- Weekly means scheduling frequency only; analytical timeframe remains daily (D).
- Consumers must treat AGING context as weekly-lagged context, not daily-current.
- STALE means the expected weekly SLA has been missed.
- On-demand ticker refresh may return one ticker to FRESH before the next full weekly run.
- REQ-0034 remains historical evidence for the prior daily design, but ADR-020 supersedes its normal scheduling decision.

## Scope

### In Scope
- remove normal Movement invocation from run.py;
- add runWeekly.py;
- add weekly Movement application service;
- add weekly freshness fields to MovementContext;
- add weekly validator;
- update architecture/ADR/runbooks/Archify;
- keep on-demand refresh.

### Out of Scope
- stateful O(1)-bar ZigZag advancement;
- parallelizing ZigZag calculation;
- changing deviation configuration;
- Strategy/Setup changes;
- SmartMoney/R/S changes;
- OS scheduler configuration.

## Acceptance Criteria

- AC-01 run.py contains no Movement invocation.
- AC-02 runWeekly.py invokes MovementWeeklyPipelineService.
- AC-03 weekly service delegates to validated full-universe runner.
- AC-04 weekly full run preserves structural parity.
- AC-05 immediately after weekly refresh context age=0 and FRESH.
- AC-06 after 1–5 new trading sessions context is AGING.
- AC-07 after >5 sessions context is STALE.
- AC-08 weekly validator fails on STALE or UNKNOWN.
- AC-09 manual force refresh remains functional.
- AC-10 formulas/lineage unchanged.
- AC-11 daily core regression PASS.
- AC-12 the reused full-universe runner remains structurally idempotent; local REQ-0036 validation may use a bounded MWG/FPT rerun because REQ-0033 already proved full-universe idempotency for the same calculation path.
- AC-13 MovementContext one row per eligible ticker/config.
- AC-14 Archify depicts Movement weekly/manual.
- AC-15 runMonthly.py remains unchanged.

## Non-functional Requirements

- Daily runtime no longer pays full-universe Movement cost.
- Weekly per-ticker/stage isolation remains unchanged.
- Freshness is explicit in public MovementContext.
- Freshness fields are additive.
- Weekly and manual entry points are independently runnable.

## Risks

- Current-leg context may lag up to five trading sessions.
- Strategy consumers requiring daily-current movement must check freshness.
- Missed weekly run makes context STALE.
- Weekly runtime remains approximately one current full Movement execution.

## Handoff

~~~text
Status: IMPLEMENTED_PENDING_VALIDATION
Primary next owner: TestEngineer
Acceptance criteria count: 15
Blocking questions: none
~~~
