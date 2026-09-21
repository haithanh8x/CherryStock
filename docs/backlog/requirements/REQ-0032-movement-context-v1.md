---
id: REQ-0032
title: MovementContext V1
status: IMPLEMENTED_PENDING_VALIDATION
priority: P1
owner: BusinessAnalyst
primary_next_owner: TestEngineer
related:
  prerequisite:
    - docs/backlog/requirements/REQ-0031-zigzag-price-movement-character-v2.md
  architecture:
    - docs/architecture/Movement_Context_V1.md
    - docs/architecture/Price_Movement_Character_V2.md
  adr:
    - docs/adr/ADR-017-movement-context-as-price-behavior-contract.md
  implementation:
    - src/DuckDB/sql/movement_context_v1_schema.sql
  test:
    - tests/test_movement_context_v1.py
    - docs/runbook/Movement_Context_V1.md
---

# REQ-0032 — MovementContext V1

## Business Objective

Provide one stable ticker-level movement context that translates confirmed Price Movement
statistics and the current provisional ZigZag leg into a compact, explainable vocabulary for
future setup/strategy consumers.

MovementContext answers:

- what movement regime has recently characterized the ticker;
- how large the last confirmed swing was versus that ticker's own typical same-direction swing;
- how clean/persistent recent confirmed swings have been;
- how fast the current provisional leg is moving versus the ticker's typical historical swing speed.

MovementContext must remain a **price-behavior context**, not a trading recommendation.

## Background / Problem

CherryStock currently exposes rich low-level movement facts through:

- `vw_Ticker_Movement_Profile`;
- `vw_Ticker_Price_Movement_Swings`;
- `vw_Ticker_ZigZag_Current`.

Future Strategy/Setup logic should not repeatedly reinterpret these physical columns or invent
different thresholds in every consumer.

A stable semantic context layer is therefore required before a later
`TickerStrategyContext` combines Movement, R/S and SmartMoney evidence.

## Stakeholders / Consumers

- future Setup Engine;
- future TickerStrategyContext;
- Screener / Chart / API consumers needing explainable movement context;
- research/backtest workflows;
- TestEngineer validation.

## Functional Requirements

1. Expose one public row per enabled MovementContext config + ticker.
2. Use `vw_Ticker_Movement_Profile` as the confirmed-history Source of Truth.
3. Use the matching `vw_Ticker_ZigZag_Current` row as provisional current-leg context.
4. Use `vw_Ticker_OHLC_D` only to count current-leg trading intervals between StartPivotDate and AsOfDate.
5. Expose `TrendRegime` from the existing `MovementCharacter`; do not create a second trend-regime Source of Truth.
6. Calculate `LastSwingTypicalPct` from the same-direction historical median and
   `LastSwingExtentRatio = abs(LastSwingPct) / LastSwingTypicalPct`.
7. Classify the last confirmed swing as SHALLOW, BELOW_TYPICAL, TYPICAL, EXTENDED or EXTREME,
   preserving UP/DOWN in `LastSwingState`.
8. Classify `TrendQuality` from historical median PathEfficiency and DirectionalPersistenceRate
   using versioned MovementContext thresholds.
9. Expose historical baselines:
   `TypicalSwingPct`, `TypicalSwingBars`, `TypicalMoveSpeedPctPerBar`.
10. Calculate current-leg `CurrentMoveSpeedPctPerBar`,
    `CurrentMoveSpeedRatio` versus the historical typical move speed, and classify it as
    VERY_SLOW, SLOW, NORMAL, FAST, EXTREME or UNKNOWN.
11. Expose `ContextStatus` as INSUFFICIENT_HISTORY, PROFILE_ONLY or PROFILE_PLUS_CURRENT.
12. MovementContext must not read or derive R/S, SmartMoney, portfolio or BUY/HOLD/SELL semantics.

## Business Rules

1. MovementContext is descriptive context only; it is not a trade signal.
2. Confirmed-history facts and provisional-current-leg facts must remain distinguishable.
3. Current-leg direction/speed may change before the next ZigZag pivot confirms.
4. Missing same-direction historical median produces UNKNOWN last-swing extent/state rather than a fabricated fallback.
5. Missing/invalid current leg produces PROFILE_ONLY rather than failing the confirmed profile.
6. Thresholds are versioned configuration and must not be silently hard-coded in downstream consumers.
7. No new calculated MovementContext persistence is introduced in V1; the public view is derived from existing Sources of Truth.
8. R/S and SmartMoney integration belongs to a later TickerStrategyContext requirement.

## Scope

### In Scope

- versioned MovementContext config;
- public `vw_Ticker_Movement_Context`;
- confirmed-history interpretation;
- provisional current-leg interpretation;
- current trading-bar count from canonical daily OHLC;
- focused tests, MWG validator and local execution runbook;
- architecture/ADR/knowledge-map synchronization.

### Out of Scope

- R/S integration;
- SmartMoney integration;
- Setup Engine;
- BUY/HOLD/SELL;
- position sizing / portfolio risk;
- multi-ticker production scheduling;
- `run.py` integration;
- historical point-in-time reconstruction of the provisional current leg for every past date.

## Acceptance Criteria

### AC-01
Given an enabled Price Movement profile,
when MovementContext is queried,
then exactly one context row is exposed for the matching enabled MovementContext config/ticker.

### AC-02
Given a DOWN last swing and a valid MedianDownSwingAbsPct,
when the context is built,
then LastSwingExtentRatio uses `abs(LastSwingPct) / MedianDownSwingAbsPct`.

### AC-03
Given an UP last swing and a valid MedianUpSwingPct,
then the same-direction median is used for LastSwingExtentRatio.

### AC-04
Given an extent ratio near 1.0,
then LastSwingState is TYPICAL_<DIRECTION>_SWING under the V1 thresholds.

### AC-05
Given historical MovementCharacter,
then TrendRegime equals that value exactly.

### AC-06
Given historical efficiency/persistence metrics,
then TrendQuality follows the enabled versioned threshold contract.

### AC-07
Given a valid provisional current leg,
then CurrentTradingBars equals canonical OHLC row-count minus one between StartPivotDate and AsOfDate inclusive.

### AC-08
Given CurrentTradingBars > 0,
then CurrentMoveSpeedPctPerBar equals CurrentMovePct / CurrentTradingBars.

### AC-09
Given a positive historical TypicalMoveSpeedPctPerBar,
then CurrentMoveSpeedRatio equals abs(CurrentMoveSpeedPctPerBar) / TypicalMoveSpeedPctPerBar.

### AC-10
Given no usable current leg,
then the context remains queryable with ContextStatus=PROFILE_ONLY and current-speed labels UNKNOWN/NULL as applicable.

### AC-11
Given MovementCharacter=INSUFFICIENT_HISTORY,
then ContextStatus=INSUFFICIENT_HISTORY and TrendQuality=INSUFFICIENT_HISTORY.

### AC-12
No implementation artifact for REQ-0032 may depend on R/S or SmartMoney public contracts.

## Non-functional Requirements

- Performance: one set-based public view; no query-per-ticker or query-per-bar runtime loop.
- Reliability: view creation is additive/idempotent; missing provisional data does not delete confirmed context.
- Security: no credentials or machine-specific paths.
- Observability: local validator prints the context row plus deterministic failure list.
- Compatibility: existing ZigZag and Price Movement tables/views remain unchanged; `run.py` remains unchanged.

## Dependencies

- REQ-0031 Price Movement V2;
- `vw_Ticker_Movement_Profile`;
- `vw_Ticker_ZigZag_Current`;
- `vw_Ticker_OHLC_D`;
- active ZigZag config referenced by the Price Movement profile.

## Constraints

- Initial validation remains MWG-first/manual.
- No production scheduling is authorized.
- Generated DB metadata is refreshed only after the local DuckDB migration is actually applied.

## Assumptions

- one active ZigZag current-leg row exists at most per ConfigId + Ticker;
- daily OHLC contains the current-leg start and as-of trading dates when a usable current leg exists.

## Open Questions

None blocking for V1.

## Risks

- heuristic context thresholds require later empirical validation before being treated as strategy evidence;
- provisional current-leg values can change until a new pivot is confirmed;
- a future promoted ZigZag config requires the MovementContext config mapping to be versioned/updated explicitly.

## Suggested Routing

- Architecture required: Yes
- Primary next owner: TestEngineer
- Domain instructions: database.instructions.md, testing.instructions.md
- Validation owner: TestEngineer

## Handoff

```text
Status: IMPLEMENTED_PENDING_VALIDATION
Primary next owner: TestEngineer
Acceptance criteria count: 12
Blocking questions: none
```
