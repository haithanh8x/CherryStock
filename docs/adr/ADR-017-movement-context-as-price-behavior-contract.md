# ADR-017 — MovementContext as a Price-Behavior Contract

- **Status:** Accepted
- **Date:** 2026-09-21
- **Requirement:** REQ-0032
- **Related:** ADR-012, ADR-013, ADR-016

## Context

CherryStock already has three separate movement facts:

- confirmed ZigZag swing boundaries;
- enriched confirmed Price Movement history/profile;
- one provisional current ZigZag leg.

Future Strategy/Setup consumers need a compact semantic vocabulary such as last-swing extent,
trend quality and current move-speed state.

If each strategy interprets low-level movement metrics independently, threshold semantics will
drift across consumers. Conversely, combining R/S and SmartMoney directly inside the movement
domain would make movement analytics depend on unrelated decision domains.

## Decision

Introduce **MovementContext V1** as a descriptive price-behavior public contract.

Dependency direction:

```text
vw_Ticker_Movement_Profile
vw_Ticker_ZigZag_Current
vw_Ticker_OHLC_D (trading-bar count only)
        ↓
vw_Ticker_Movement_Context
        ↓
future TickerStrategyContext / Setup consumers
```

MovementContext does not read R/S or SmartMoney.

## Dynamic View Decision

V1 will not persist a separate calculated MovementContext table.

The provisional current leg may change before confirmation. A derived public view therefore
avoids duplicating current-state facts and synchronization/staleness risk.

Only interpretation policy is persisted in:

```text
dim_movement_context_config
```

## Confirmed vs Provisional Decision

Confirmed historical fields retain Price Movement semantics.

Current-leg fields retain ZigZag provisional semantics and must never be presented as confirmed
swing facts.

`ContextStatus` communicates whether a row contains only the confirmed profile or also a usable
current provisional leg.

## Classification Decision

V1 adds deterministic descriptive labels:

- LastSwingState;
- TrendQuality;
- CurrentMoveSpeedState.

Thresholds are versioned in MovementContext configuration.

These labels are **not** BUY/HOLD/SELL and are not calibrated return probabilities.

## Strategy Boundary

A future composition layer may combine:

```text
MovementContext + RSContext + SmartMoneyContext
    -> TickerStrategyContext
```

That future integration requires its own requirement/design and must not be implemented by
silently expanding MovementContext.

## Compatibility

The change is additive:

- no ZigZag object is changed;
- no Price Movement object is changed;
- no SmartMoney/R/S object is changed;
- no daily pipeline integration is added.

## Consequences

Positive:

- one reusable movement vocabulary for future strategy consumers;
- no duplicate movement Source of Truth;
- provisional/current semantics remain explicit;
- interpretation thresholds are versioned;
- consumers avoid reimplementing ratios/buckets.

Trade-offs:

- the public view performs a bounded OHLC join to count current-leg trading bars;
- heuristic thresholds still need later empirical validation;
- V1 is latest-state context, not a historical daily context dataset.

## Validation

Independent validation must prove formulas, threshold boundaries, missing-current behavior and
the absence of R/S/SmartMoney dependencies before merge/promotion.
