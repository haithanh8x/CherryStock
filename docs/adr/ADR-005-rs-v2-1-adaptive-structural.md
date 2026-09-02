# ADR-005 — R/S V2.1 Adaptive Volatility and Point-in-Time Structural Levels

- **Status:** Accepted
- **Date:** 2026-09-02
- **Scope:** Support / Resistance Engine V2.1

## Context

R/S V2.0 introduced multi-source indicator levels and source-family confluence, but its cluster and neutral distances remained fixed percentages and its level library did not yet include observed market-structure levels.

V2.1 must add:

- ATR-adaptive clustering and neutral zones;
- confirmed Swing High/Low;
- Previous Week/Month High/Low;
- rolling 52W High/Low;
- explicit point-in-time/no-lookahead behavior;
- structural quality in Strength.

The main architecture risks are:

- using ATR as a price level instead of context;
- using a swing pivot before right-side confirmation exists;
- accidentally reading current partial week/month as previous period structure;
- historical calculations observing future bars;
- coupling structural providers to Indicator Engine;
- changing proximity ranking semantics.

## Decision

### 1. ATR14_D is CONTEXT only

ATR is read from Indicator Engine public SSOT:

```text
vw_Ticker_indicators
+
vw_Indicator_config
        ↓
ATR Provider
        ↓
MarketContext
```

ATR never creates `LevelCandidate`.

V2.1 uses ATR14_D as the primary volatility context for adaptive distance calculations.

### 2. Adaptive distance uses percent floors

```text
ATRPercent = ATR14_D / CurrentPrice

ClusterThresholdPct =
    max(MinClusterPct, ATRPercent × ATRClusterMultiplier)

NeutralThresholdPct =
    max(MinNeutralPct, ATRPercent × ATRNeutralMultiplier)
```

If ATR is unavailable for the requested historical date, the deterministic percent floors remain valid fallback thresholds.

### 3. Structural levels read raw OHLCV directly

```text
raw_stock_eod
     ↓
Structural Providers
     ↓
LevelCandidate[]
```

Structural providers do not create artificial technical-indicator configurations.

All structural candidates use:

```text
SourceRole     = LEVEL
SourceFamily   = MARKET_STRUCTURE
ValueSemantic  = PRICE_LEVEL
```

### 4. Point-in-time availability is explicit

`LevelCandidate` carries both:

```text
source_date
confirmed_at
```

The core invariant is:

```text
source_date <= as_of_date
confirmed_at <= as_of_date
```

Normalization rejects a future `confirmed_at`.

### 5. Swing pivots require right-side confirmation

For swing parameters `left=N`, `right=M`:

- `source_date` = pivot bar date;
- `confirmed_at` = date of the M-th right-side confirmation bar.

The pivot cannot participate in an earlier historical calculation.

### 6. Previous periods must be completed periods

Previous Week H/L excludes the current calendar/ISO week.

Previous Month H/L excludes the current calendar month.

### 7. 52W levels are rolling and point-in-time

52W High/Low uses only bars in the rolling 365-day window ending at `as_of_date`.

### 8. Structural quality changes Strength only

V2.1 adds structural-quality evidence based on MARKET_STRUCTURE source recency.

It does not change ranking.

Invariant remains:

```text
S1 = nearest eligible support
R1 = nearest eligible resistance
```

### 9. No DuckDB schema migration is required

V2.1 reuses:

- V2.0 `ValueSemantic/Unit` metadata;
- existing ATR14_D backfill;
- `raw_stock_eod`;
- existing Indicator Engine public views.

A read-only preflight SQL is provided:

```text
src/DuckDB/sql/rs_v2_1_preflight.sql
```

## Consequences

### Positive

- clustering adapts to ticker volatility;
- structural price behavior becomes first-class evidence;
- historical calculations have explicit no-lookahead protection;
- R/S remains source-agnostic;
- no new schema or duplicated indicator calculations are introduced;
- V2.0 MA-only and indicator-only regression modes remain available.

### Trade-offs

- default V2.1 performs additional raw OHLCV reads for structural providers;
- Strength scores can differ from V2.0 because structural evidence is added;
- Swing results depend on explicit left/right confirmation parameters;
- ATR adaptive thresholds may produce wider zones in high-volatility regimes.

## Validation

Minimum automated and local validation:

```text
tests/test_rs_ladder.py
tests/test_R_S_V2_1.md
src/DuckDB/sql/rs_v2_1_preflight.sql
```

Production rollout is allowed only after all point-in-time, adaptive-distance and NiceGUI smoke checks PASS.
