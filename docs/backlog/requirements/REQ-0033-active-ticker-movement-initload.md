---
id: REQ-0033
title: Active Ticker ZigZag and Price Movement Initial Load
status: DONE
priority: P1
owner: BusinessAnalyst
primary_next_owner: None
related:
  prerequisite:
    - docs/backlog/requirements/REQ-0027-price-movement-characterization.md
    - docs/backlog/requirements/REQ-0031-zigzag-price-movement-character-v2.md
    - docs/backlog/requirements/REQ-0032-movement-context-v1.md
  architecture:
    - docs/architecture/Active_Ticker_Movement_Initload.md
  implementation:
    - src/Orchestrator/active_ticker_movement_initload.py
    - scripts/initload/init_reload_zigzag_price_movement_active.py
  test:
    - tests/test_active_ticker_movement_initload.py
    - scripts/validate_movement_active.py
    - docs/runbook/Active_Ticker_Movement_Initload.md
---

# REQ-0033 — Active Ticker ZigZag and Price Movement Initial Load

## Business Objective

Expand the validated ZigZag + Price Movement analytical chain from MWG-first/manual scope to
the complete current ticker universe defined by "CherryMon"."main"."vw_Ticker_Active".

The initial load must create deterministic ZigZag state and, where confirmed swings exist,
matching Price Movement swing/profile rows for every active ticker with valid daily OHLC.

## Background / Problem

REQ-0027/REQ-0031 validated the analytical chain on MWG. REQ-0032 then added a derived
MovementContext contract.

The reusable Price Movement entry point already accepts arbitrary tickers, while the ZigZag
calculation entry point remained MWG-specific. CherryStock therefore needs an explicit,
failure-isolated, universe-level initial-load workflow before Strategy or screening consumers
can rely on broad movement coverage.

## Stakeholders / Consumers

- MovementContext consumers;
- future TickerStrategyContext / Setup Engine;
- Chart / Screener / API;
- research workflows requiring broad ticker coverage;
- TestEngineer.

## Functional Requirements

1. The canonical initial-load universe MUST come from vw_Ticker_Active.Ticker.
2. Ticker values MUST be trimmed, upper-cased, de-duplicated and processed deterministically.
3. ZigZag MUST run first for every selected active ticker using the current production-facing
   baseline config ZZ_D_5_MVP.
4. ZigZag MUST continue to use canonical adjusted daily OHLC from vw_Ticker_OHLC_D.
5. Price Movement MUST run only after the ticker's ZigZag stage has committed successfully.
6. A ticker with one or more confirmed ZigZag swings MUST have Price Movement rebuilt using
   PM_ZZ_D_V2.
7. A ticker with no confirmed ZigZag swing MUST retain ZigZag current state, clear any stale
   Price Movement rows for PM_ZZ_D_V2, and be reported as SKIPPED_NO_CONFIRMED_SWING.
8. An active ticker with no daily OHLC MUST be a hard validation failure, not silently ignored.
9. One ticker/stage failure MUST NOT roll back already committed successful tickers.
10. Default execution MUST continue across failures and return non-zero when hard failures exist.
11. Canary execution MUST support explicit active tickers and deterministic first-N limits.
12. The workflow MUST export optional per-ticker and aggregate evidence for TestEngineer review.
13. run.py MUST remain unchanged; this requirement authorizes initial load/manual rerun only.
14. MovementContext MUST not be separately persisted or loaded; its existing derived view should
    automatically expose newly created Price Movement profiles.

## Business Rules

1. vw_Ticker_Active is the universe Source of Truth for this rollout.
2. REQ-0033 does not promote calibrated/static/regime-aware ZigZag research configs.
3. The active ZigZag baseline remains ZZ_D_5_MVP until a separate promotion requirement changes it.
4. Transaction boundary is one ticker per stage:
   - ZigZag ticker transaction;
   - Price Movement ticker transaction.
5. A Price Movement failure may not erase a committed ZigZag result.
6. No-confirmed-swing is a valid data state, not an execution error.
7. No-OHLC for an active ticker is an execution/data-coverage failure.
8. Re-running the full initial load must be deterministic/idempotent at the business-row level.
9. Stale downstream Price Movement rows must not survive when current ZigZag has zero confirmed swings.
10. Full-universe PASS requires structural coverage, not trading-performance evaluation.

## Scope

### In Scope

- generic per-ticker ZigZag refresh;
- all-active-ticker initial-load orchestrator;
- ZigZag → Price Movement stage ordering;
- per-ticker transaction/failure isolation;
- stale Price Movement cleanup for zero-swing tickers;
- canary options;
- full-universe validator;
- evidence export;
- local execution runbook.

### Out of Scope

- daily/incremental scheduling in run.py;
- ticker-specific calibrated ZigZag promotion;
- regime-aware deviation promotion;
- SmartMoney changes;
- R/S changes;
- Strategy/BUY/HOLD/SELL;
- portfolio logic;
- historical daily MovementContext persistence.

## Acceptance Criteria

### AC-01
Given vw_Ticker_Active, when the universe is loaded, then tickers are normalized, unique and deterministically sorted.

### AC-02
Given an active ticker with OHLC, when initial load runs, then exactly one ZigZag current row exists for ZZ_D_5_MVP.

### AC-03
Given a ticker with confirmed ZigZag swings, then Price Movement swing count equals ZigZag swing count for the configured lineage.

### AC-04
Given a ticker with at least one confirmed ZigZag swing, then exactly one Price Movement profile exists.

### AC-05
Given a ticker with zero confirmed ZigZag swings, then Price Movement swing/profile rows are zero after the run.

### AC-06
Given an active ticker with no OHLC, then the run records FAILED_NO_OHLC and exits non-zero.

### AC-07
Given one ticker calculation error, then other selected tickers continue when fail-fast is not enabled.

### AC-08
Given a Price Movement calculation error, then the previously committed ZigZag rows for that ticker remain intact.

### AC-09
Given an explicit --ticker canary, then only requested tickers that exist in vw_Ticker_Active are processed.

### AC-10
Given --limit N, then the first N normalized active tickers are processed deterministically.

### AC-11
Given a successful full run followed by an unchanged rerun, then validation counts and business values remain structurally equivalent with no duplicates.

### AC-12
Given the completed load, then vw_Ticker_Movement_Context can derive context for newly available movement profiles without a separate context backfill.

### AC-13
The full validator must report no ZigZag/Price Movement count mismatch and no stale downstream rows.

### AC-14
run.py remains unchanged.

## Non-functional Requirements

- Performance: ticker-local calculation; no query-per-bar database loop inside the domain engine.
- Reliability: per-ticker/stage transaction isolation and deterministic reruns.
- Security: no credentials or machine-specific secrets.
- Observability: progress line per ticker/stage plus aggregate and per-ticker evidence.
- Compatibility: existing MWG entry points and validated public contracts remain backward compatible.

## Dependencies

- vw_Ticker_Active with a Ticker column;
- vw_Ticker_OHLC_D;
- ZZ_D_5_MVP;
- PM_ZZ_D_V2;
- existing ZigZag and Price Movement schemas.

## Constraints

- The current repository metadata snapshot may not document vw_Ticker_Active; runtime validation
  therefore verifies the view/column contract directly on local CherryMon.
- Initial rollout remains manual until an explicit daily scheduling requirement is approved.

## Assumptions

- vw_Ticker_Active represents the user's intended current tradable/active universe.
- Active tickers normally have daily OHLC; exceptions are treated as data-quality failures.

## Open Questions

None blocking for initial-load implementation.

## Risks

- Full-universe runtime can be materially longer than MWG validation.
- Newly listed/low-volatility tickers may legitimately have no confirmed 5% swing yet.
- The fixed 5% baseline can segment tickers differently across volatility regimes; this rollout
  intentionally does not resolve that separate research question.

## Validation Evidence

Independent full-universe integration validation completed on 2026-09-22 with PASS / KEEP:

- focused tests: 24/24 PASS;
- active universe: 349 tickers;
- OHLC prerequisite: 349/349, zero missing;
- MWG + FPT canary: 2/2 PASS;
- deterministic 20-ticker canary: 20/20 PASS;
- full ZigZag: 349/349 PASS;
- full Price Movement: 349/349 PASS;
- structural validator: validation_failures=0;
- MovementContext downstream: 349/349 PASS;
- idempotency: business row counts unchanged after rerun;
- daily pipeline regression: 3/3 PASS;
- run.py unchanged.

Stable row counts after unchanged rerun:

~~~text
cal_zigzag_pivot              154795
cal_zigzag_current_leg           349
cal_price_movement_swing      154446
cal_price_movement_profile       349
~~~

Evidence commit:

~~~text
7e872c1b5b51834e8cec8f847bf6658fa03e9167
~~~

## Suggested Routing

- Architecture required: Yes — completed
- Primary next owner: None
- Validation owner: TestEngineer — PASS / KEEP

## Handoff

~~~text
Status: DONE
Primary next owner: None
Acceptance criteria count: 14
Blocking questions: none
~~~
