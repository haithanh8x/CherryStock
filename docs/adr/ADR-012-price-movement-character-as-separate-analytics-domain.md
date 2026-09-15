# ADR-012 — Price Movement Character as a Separate Analytics Domain

- **Status:** Accepted for design; implementation pending
- **Date:** 2026-09-15
- **Requirement:** `REQ-0027`
- **Decision scope:** Analytics component boundary, persistence ownership and dependency direction

## Context

REQ-0027 requires CherryStock to characterize how a ticker moves using:

- confirmed and provisional directional swings;
- swing magnitude and duration;
- movement velocity;
- ATR/volatility-relative magnitude;
- historical same-direction percentiles;
- path efficiency, regression fit and adverse pullback;
- separate Magnitude, Velocity and Persistence scores;
- an explainable movement-character classification.

This behavior is more than a conventional technical indicator. A ZigZag-like swing model is stateful and event-oriented: a pivot may occur on one date but becomes knowable only on a later reversal-confirmation date. The model therefore needs both event grain and daily as-of state, and must preserve the distinction between confirmed history and a provisional current leg.

The existing Indicator Engine owns metadata-driven indicator calculation with long-format persistence at:

```text
Ticker + Date + ConfigId + ComponentCode
```

and exposes calculated values through `vw_Ticker_indicators`.

Forcing swing events, pivot confirmation dates and movement-profile state into that contract would either distort the Indicator Engine's grain or introduce hidden event semantics behind scalar indicator components.

## Decision

CherryStock SHALL implement **Price Movement Character** as a separate calculated analytics domain.

The domain will:

1. consume adjusted daily OHLC from the existing public/analytical price contract;
2. consume ATR through the Indicator Engine public contract where available rather than reading `cal_indicator_values` directly;
3. own swing segmentation and pivot confirmation semantics;
4. own confirmed swing-event persistence;
5. own daily point-in-time movement-state persistence;
6. expose public read views for confirmed swings, daily movement state and latest historical profile;
7. run in the daily analytics transaction after Technical Indicators and before SmartMoneyScore;
8. remain analytically independent from SmartMoneyScore V1, while permitting SmartMoney or strategy models to consume its public contracts in a later requirement.

## Dependency Direction

```text
Adjusted OHLC public contract
          │
          ├───────────────┐
          │               │
          ▼               ▼
Technical Indicator   Price Movement Character
Engine (ATR)           Engine
          │               │
          └── public ATR ──┘
                          │
                          ▼
                Price Movement public views
                          │
             ┌────────────┼─────────────┐
             ▼            ▼             ▼
           Chart       Screener     Future models
```

The Price Movement domain MUST NOT depend directly on internal Indicator persistence.

## Why Not Model It as Ordinary Indicators?

Some individual inputs/metrics such as ATR, Efficiency Ratio or regression statistics can be expressed as indicators. The aggregate requirement, however, has different state semantics:

- confirmed swing events have start/end/confirmation dates;
- provisional pivots can repaint;
- historical swing distributions are event-history statistics;
- a daily as-of state must not leak a future confirmation backward;
- the domain has multiple grains and a state machine, not only `Ticker + Date + indicator component`.

Keeping it separate preserves the Indicator Engine's existing contract and makes the no-look-ahead rule explicit and testable.

## Persistence Decision

Target calculated objects:

```text
dim_price_movement_model
dim_price_movement_config
cal_price_movement_swing
cal_price_movement_daily
vw_Ticker_Movement_Swings
vw_Ticker_Movement_D
vw_Ticker_Movement_Profile
```

The confirmed swing-event table and daily as-of table are separate Sources of Truth for different business facts; neither should be reconstructed by mutating the other at query time.

## Point-in-Time Decision

Each confirmed pivot/swing stores both:

- the **pivot/extreme date** where the price extreme actually occurred; and
- the later **confirmation date** when the reversal threshold made that pivot knowable.

Historical/as-of logic MUST filter knowledge by `ConfirmedAtDate`, not only by pivot date.

Daily outputs are generated sequentially using only information available through that date. When a pivot is confirmed, the active leg may legitimately reference an earlier pivot date from that confirmation date onward; earlier daily rows are not retroactively rewritten to pretend the pivot was known sooner.

## Reversal Threshold Decision

The initial design uses a volatility-adaptive ZigZag reversal threshold:

```text
ReversalThresholdPct = max(
    MinReversalPct,
    ATRMultiplier * ATR / reference_price
)
```

where ATR is resolved through the public Indicator contract. Configuration is versioned.

If ATR is unavailable but valid price history exists, the engine may use the configured percentage floor as a fallback only when it records degraded provenance/quality. Missing ATR must not silently masquerade as full-quality volatility normalization.

## Scoring Decision

The domain exposes three independent dimensions:

```text
MagnitudeScore
VelocityScore
PersistenceScore
```

It SHALL NOT replace them with one opaque master score in V1.

Movement-character labels are derived from direction plus those dimensions through versioned, documented thresholds.

## Consequences

### Positive

- preserves clean Indicator Engine grain and ownership;
- makes ZigZag repaint/confirmation semantics explicit;
- supports point-in-time-safe backtesting;
- provides reusable swing/event history for multiple consumers;
- separates large/fast moves from persistent trends;
- allows future SmartMoney models to consume a stable public contract rather than reimplement price-path logic.

### Costs

- introduces a new calculated analytics domain and additive DuckDB objects;
- adds one daily pipeline stage and Data Quality profile;
- requires historical backfill and incremental-state equivalence testing;
- requires versioned configuration because threshold changes can materially alter swing segmentation.

## Rejected Alternatives

### A. Put every metric into `cal_indicator_values`

Rejected because confirmed swing events and confirmation dates do not fit the Indicator Engine's value-component grain without obscuring event/state semantics.

### B. Derive everything on demand in Chart/Screener

Rejected because this duplicates algorithm logic, breaks reproducibility across consumers and makes point-in-time behavior difficult to govern.

### C. Use only a fixed percentage ZigZag threshold

Rejected as the sole production definition because a single percentage has materially different meaning across tickers with different volatility regimes. A percentage floor remains useful as a configured fallback/minimum threshold.

### D. Use only endpoint return

Rejected because it cannot distinguish a smooth durable trend from a volatile path with the same start/end return.

## Compatibility

The change is additive. Existing Indicator, R/S, SmartMoney and Chart contracts are not changed by REQ-0027 V1.

Any future use of Price Movement features inside SmartMoneyScore or SmartMoneyStrategy requires a separate requirement/design change rather than implicit coupling.

## Validation Required

Implementation is not production-ready until TestEngineer independently verifies at least:

- pivot confirmation/no-look-ahead behavior;
- full-history vs incremental equivalence for finalized history;
- same-direction historical percentile behavior;
- confirmed/provisional separation;
- fallback provenance when ATR is absent;
- database key uniqueness and rerun idempotency;
- public-view compatibility and Data Quality behavior.

## Related

- `docs/backlog/requirements/REQ-0027-price-movement-characterization.md`
- `docs/architecture/Price_Movement_Character.md`
- `docs/architecture/Indicator_Engine.md`
- `docs/architecture/Data_Architecture.md`
- `docs/adr/ADR-002-indicator-source-of-truth.md`
