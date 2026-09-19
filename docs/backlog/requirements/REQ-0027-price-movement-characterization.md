---
id: REQ-0027
title: ZigZag-based Price Movement Foundation
status: IMPLEMENTED_PENDING_VALIDATION
priority: P1
owner: BusinessAnalyst
primary_next_owner: TestEngineer
related:
  architecture:
    - docs/architecture/ZigZag_Engine.md
    - docs/architecture/Price_Movement_Character.md
  adr:
    - docs/adr/ADR-012-price-movement-character-as-separate-analytics-domain.md
    - docs/adr/ADR-013-zigzag-as-price-movement-segmentation-foundation.md
  implementation:
    - src/cherrystock/domain/analytics/zigzag/
    - src/calcEngine/zigzag.py
    - src/DuckDB/sql/zigzag_mvp_schema.sql
    - scripts/initload/init_reload_zigzag_mwg.py
  test:
    - tests/test_zigzag_engine.py
    - scripts/validate_zigzag_mwg.py
---

# REQ-0027 — ZigZag-based Price Movement Foundation

## Business Objective

CherryStock must identify price swing legs from real price extremes before it derives
movement magnitude, velocity, persistence or any downstream movement classification.

The immediate goal is correctness of swing segmentation. A confirmed UP swing must start
at a real trough and end at a real peak; a confirmed DOWN swing must start at a real peak
and end at a real trough. A point in the middle of an already-declining/rising leg must not
be selected as the start merely because a volatility threshold changed state there.

## Background / Problem

The first Price Movement implementation used an ATR-adaptive reversal threshold and
persisted daily movement state. Local validation exposed two material problems:

1. pivot placement could be analytically wrong for visual swing interpretation; MWG
   produced an UP start around 2026-07-23 / 66 even though that point was inside a
   declining leg rather than the trough that should anchor the next UP swing;
2. full-universe calculation recalculated path features per bar and required roughly
   3.5 hours for about 5.0M rows, making that implementation unsuitable for the daily pipeline.

That implementation was rolled back. The replacement must first solve segmentation,
then build higher-level movement analytics on top of confirmed ZigZag pivots.

## Stakeholders / Consumers

- CherryStock analyst;
- chart and visual validation;
- future Price Movement Character engine;
- future Screener / SmartMoney / pattern research;
- TestEngineer.

## Delivery Strategy

REQ-0027 is staged deliberately.

### Phase 1 — MWG ZigZag MVP

Only ticker MWG is in scope.

The MVP shall:

- consume adjusted daily OHLC from vw_Ticker_OHLC_D;
- use a percentage-reversal ZigZag state machine;
- use High for candidate HIGH pivots and Low for candidate LOW pivots;
- use Close for reversal confirmation;
- use configured DeviationPct = 5% for the first evaluation config;
- keep PivotDate separate from ConfirmedAtDate;
- persist confirmed pivots only;
- persist one current provisional-leg row;
- derive swings from adjacent confirmed pivots;
- run only through a manual MWG initload script;
- remain outside run.py, SmartMoney and all-universe processing.

### Phase 2 — after MWG approval

Only after MWG pivot quality is accepted may the solution add:

- more tickers / active-universe initload;
- incremental daily checkpointing;
- alternative deviation configs such as 3% / 8%;
- swing magnitude / duration / velocity;
- persistence/path-quality features;
- ticker-relative swing profiles;
- Price Movement Character labels;
- downstream SmartMoney or screener consumption.

## Functional Requirements — MVP

1. The engine shall process MWG daily OHLC in ascending trading-date order.
2. The engine shall identify alternating confirmed LOW and HIGH pivots.
3. A LOW pivot shall be the tracked lowest Low before a later Close rises by at least
   DeviationPct from that candidate low.
4. A HIGH pivot shall be the tracked highest High before a later Close falls by at least
   DeviationPct from that candidate high.
5. PivotDate shall record the date the extreme occurred.
6. ConfirmedAtDate shall record the first later date on which the configured reversal
   makes that pivot knowable.
7. A confirmed pivot shall never be visible historically before its ConfirmedAtDate.
8. The latest unfinished leg shall remain PROVISIONAL.
9. Confirmed pivots shall be deterministic and idempotent for unchanged OHLC + config.
10. MVP persistence shall be event-first; it shall not recreate a full daily historical
    movement-state table.
11. The engine shall expose stable public read views for pivots, derived swings and current leg.
12. The implementation shall be O(n) over ordered bars for one ticker and shall not rescan
    the entire active leg on every bar.
13. The MWG initload shall not mutate the canonical daily run.py workflow.

## Business Rules

- ZigZag confirmation lag is expected and must be explicit.
- Pivot location is based on the actual tracked High/Low extreme, not the confirmation bar.
- Confirmation uses Close so a wick alone does not confirm a reversal.
- Pivots must alternate LOW → HIGH → LOW or HIGH → LOW → HIGH.
- A derived UP swing is LOW → HIGH; a derived DOWN swing is HIGH → LOW.
- A provisional candidate may repaint until reversal confirmation.
- Confirmed pivot facts are immutable for unchanged source data + config version.
- ATR is not an input to Phase-1 ZigZag segmentation.
- Price-only ZigZag output must not be described as Smart Money intent or a trade signal.

## MVP Configuration

    ConfigCode         = ZZ_D_5_MVP
    Timeframe          = D
    DeviationPct       = 0.05
    PivotPriceSource   = HIGH_LOW
    ConfirmationSource = CLOSE
    MinimumSwingBars   = 1
    Scope              = MWG only

The value 5% is an evaluation configuration, not a universal market rule. Expansion to
additional configs requires separate validation evidence.

## Acceptance Criteria

### AC-01 — LOW pivot anchored at an extreme

Given MWG is declining and later rebounds by the configured deviation,
when the LOW pivot becomes confirmed,
then PivotDate/PivotPrice refer to the tracked lowest Low before confirmation, not the
confirmation bar and not an intermediate point in the decline.

### AC-02 — HIGH pivot anchored at an extreme

Given MWG is rising and later reverses downward by the configured deviation,
when the HIGH pivot becomes confirmed,
then PivotDate/PivotPrice refer to the tracked highest High before confirmation.

### AC-03 — Alternating pivot sequence

For all confirmed MWG pivots under one config, adjacent pivots alternate HIGH/LOW and
PivotSeq is strictly increasing.

### AC-04 — Point-in-time safety

For every confirmed pivot:

    PivotDate <= ConfirmedAtDate

and no consumer may treat the pivot as confirmed before ConfirmedAtDate.

### AC-05 — Swing direction

Adjacent LOW → HIGH pivots yield an UP swing and adjacent HIGH → LOW pivots yield
a DOWN swing.

### AC-06 — Local-extreme validation

For every interior confirmed pivot, its price equals the corresponding local minimum
(LOW) or maximum (HIGH) across the interval bounded by adjacent confirmed pivots,
subject only to equal-price ties.

### AC-07 — Provisional current leg

After the final confirmed pivot, exactly one MWG current-leg record exists with
Status = PROVISIONAL and a candidate opposite pivot.

### AC-08 — Idempotent MWG initload

Running the MWG initload twice with unchanged source/config produces the same confirmed
pivot sequence and does not create duplicates.

### AC-09 — Event-first persistence

The MVP persists confirmed pivots plus one current-state row; it does not persist one
movement-state row per historical trading date.

### AC-10 — Daily pipeline isolation

python run.py remains unchanged by the MVP and does not invoke ZigZag.

### AC-11 — Performance shape

The ZigZag calculation performs one forward scan over MWG bars. No per-bar DataFrame
slice/copy, regression, percentile rebuild or full-leg rescan is allowed in the state-machine loop.

### AC-12 — MWG rollout gate

No other ticker is enabled until MWG validation shows:

- zero structural pivot validation errors;
- zero duplicate pivots;
- pivot sequence visually agrees with the intended major/intermediate legs for the
  Jul–Sep 2026 review window;
- user accepts the 5% configuration as a valid starting behavior or explicitly selects a
  replacement config.

## Non-functional Requirements

- Correctness first: scaling is blocked until MWG is accepted.
- Performance: O(n) state-machine calculation for one ticker.
- Reliability: full MWG rebuild is deterministic/idempotent.
- Observability: initload prints source rows, confirmed pivot count, current direction
  and elapsed calculation time.
- Compatibility: no changes to run.py, Indicator, SmartMoney or R/S contracts in MVP.
- Reproducibility: every row contains ConfigId/config identity through public views.

## Dependencies

- vw_Ticker_OHLC_D;
- ordered daily adjusted OHLC for MWG;
- CherryStock DuckDB connection/UoW conventions;
- approved ZigZag architecture / ADR.

ATR and Indicator Engine values are explicitly not dependencies for Phase 1.

## Risks

- A 5% deviation can still be too sensitive or too coarse for some regimes; that is why
  only MWG is enabled initially.
- ZigZag pivots repaint while provisional; consumers must use confirmation time correctly.
- Daily OHLC cannot reveal intraday order when both extremes occur in the same bar; the
  bootstrap tie-break must therefore remain deterministic and documented.
- Visual agreement alone is not sufficient; structural/extreme validation is mandatory.

## Expansion Gate

The rollout state is:

    MWG_MVP
      → structural validation
      → Jul–Sep 2026 visual review
      → user acceptance
      → multi-ticker pilot
      → only then consider daily integration / Movement Character features

## BA Handoff

    REQUIREMENT HANDOFF
    Requirement ID: REQ-0027
    Outcome: ZigZag-based swing segmentation foundation
    Status at BA gate: READY_FOR_DESIGN
    Primary next owner: SolutionArchitect.agent.md
    Material: docs/backlog/requirements/REQ-0027-price-movement-characterization.md
    Open questions: None blocking for MWG MVP
    Acceptance criteria count: 12

## Current Delivery State

Architecture and MVP implementation have been produced from this requirement. The current
overall state is:

    IMPLEMENTED_PENDING_VALIDATION

Final functional verdict belongs to TestEngineer.agent.md and the explicit MWG visual gate.
