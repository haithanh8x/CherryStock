# ADR-009 — SmartMoneyScore State-Aware Scoring and Data Contracts

- **Status:** Accepted
- **Date:** 2026-09-05
- **Requirement:** REQ-0025
- **Scope:** Ticker-level SmartMoneyScore V1

## Context

CherryStock needs to detect where high-quality money flow is appearing at ticker level.

A fixed Price × Volume score is insufficient because the same liquidity behavior has different meanings in different states:

```text
high liquidity + strong close  → demand expansion candidate
high liquidity + weak close    → distribution candidate
low liquidity + weak price     → lack of demand candidate
low liquidity + strong price
+ prior accumulation           → supply lock candidate
```

Current `raw_stock_eod` exposes OHLCV but does not contain exact Trading Value, market-limit/reference prices, MarketCap or FreeFloat.

The design must remain useful with current data while not pretending missing evidence exists.

## Decision

### 1. Smart Money is a separate analytical domain

Smart Money factors and scores do not become technical indicators inside `cal_indicator_values`.

The Smart Money domain may consume technical indicators through the existing public SSOT:

`vw_Ticker_indicators`.

This avoids redefining Indicator Engine semantics or coupling Smart Money model versioning to indicator persistence.

### 2. Factor evidence is separate from final score

Internal persistence is split into:

```text
cal_smart_money_factor_values
cal_smart_money_ticker_score
```

Factor values are long-form and auditable.

The final score table stores one ticker/date/model result.

Downstream consumers use:

`vw_Ticker_SmartMoney`.

### 3. SmartMoneyScore is state-aware

The engine detects a primary market state before selecting positive factor weights.

V1 states include:

```text
ACCUMULATION
BREAKOUT
DEMAND_EXPANSION
SUPPLY_LOCK
MARKUP
DISTRIBUTION
LIQUIDITY_DRYUP
SELLING_CLIMAX
NEUTRAL
```

Different states use different weight profiles.

A single immutable global weighted formula is rejected.

### 4. SmartMoneyScore and ConfidenceScore are independent

`SmartMoneyScore` measures strength/direction of Smart Money behavioral evidence.

`ConfidenceScore` measures trustworthiness of that conclusion based on:

- data completeness;
- factor coverage;
- source quality;
- liquidity/history adequacy;
- benchmark availability;
- exact vs proxy evidence;
- illiquidity/price-impact risk.

A high SmartMoneyScore with low Confidence is a valid result.

### 5. Missing evidence is not negative evidence

Factor semantics are:

```text
0     = observed weak/negative evidence
NULL  = unavailable/not calculable
```

When optional positive factors are unavailable, state weights are renormalized over available factors if minimum coverage is satisfied.

Confidence is reduced for missing evidence.

### 6. Current Trading Value is a proxy, not a fact

Until an authoritative Trading Value source is added:

```text
LiquidityValue = Close * Volume
SourceQuality = PROXY
```

This value is used only as a relative-liquidity proxy.

It must not be presented as official exchange Trading Value.

### 7. Exact limit-up is not guessed

Current `raw_stock_eod` lacks authoritative Reference/Ceiling/Floor fields.

Therefore exact:

```text
IsLimitUp
LimitUpStreak
LimitUpScore
```

remain unavailable unless an authoritative market-limit source is connected.

The engine may still detect Supply Lock using price persistence, Close strength, relative strength, liquidity compression and accumulation memory.

A guessed exchange ceiling percentage is not persisted as fact.

### 8. Supply Lock is conjunctive

Liquidity compression alone cannot generate Supply Lock.

Supply Lock requires combined positive price/strength evidence and low Distribution evidence, with accumulation memory and exact limit-up evidence acting as confirmations when available.

### 9. Accumulation has memory

Accumulation evidence decays rather than disappearing immediately.

A versioned exponential-memory model is used in V1.

Incremental calculation must reproduce full-history results for the same model/config.

### 10. Distribution is an explicit penalty

Distribution is modeled as negative evidence and can reduce final SmartMoneyScore.

It is not represented merely as absence of inflow.

### 11. Weights and thresholds are configuration-owned

Model definitions, factor definitions, state-specific weights and thresholds are stored in versioned Smart Money metadata.

V1 does not build a generic user-defined rule DSL.

The code owns state semantics; configuration owns parameter values.

### 12. Public Smart Money SSOT is a view

Downstream users should consume:

`vw_Ticker_SmartMoney`.

Internal `cal_*` tables are persistence/audit contracts and are not the preferred consumer API.

## Consequences

### Positive

- consecutive strong-price/low-volume cases can remain high Smart Money candidates through Supply Lock semantics;
- weak low-volume stocks are not automatically treated as bullish;
- Distribution becomes explicitly visible;
- missing market-limit data does not silently create false negatives;
- exact vs proxy data quality is auditable;
- historical scoring can be versioned and reproduced;
- future sector/group aggregation gets a stable ticker-level contract;
- new factors can be added without ALTER of a wide factor-value fact table.

### Trade-offs

- V1 score is a behavioral proxy, not proof of institutional investor identity;
- current lack of exact Trading Value reduces precision;
- current lack of exact market-limit data prevents exact limit-up evidence;
- state detection and configuration require calibration/backtesting;
- cross-sectional percentile normalization depends on adequate universe coverage;
- factor correlation may still require later weight calibration.

## Alternatives Considered

### One global weighted formula

Rejected because low volume has different meaning across states and the formula would systematically under-score Supply Lock.

### Store Smart Money as Indicator Engine components

Rejected because Smart Money is a composite market-state model with its own model/config/version lifecycle, not a single technical indicator calculation.

### Set missing factors to zero

Rejected because missing evidence is not evidence of weakness.

### Guess limit-up from daily return percentages

Rejected because exchange/reference rules and corporate-action rounding can make this inaccurate and current source metadata is insufficient for an authoritative classification.

### Store all component scores as physical columns only

Rejected because adding/removing factors would force wide-schema churn and duplicate semantics.

The public view may pivot selected factors for convenience while long-form factor persistence remains canonical internally.

## Migration

Additive objects are defined in:

[[../architecture/SmartMoneyScore|SmartMoneyScore Architecture]].

Implementation should create Smart Money `dim_*`, `cal_*` and `vw_Ticker_SmartMoney` without altering existing OHLCV or Indicator Engine public contracts.

## Validation

Required validation includes:

- factor formula unit tests;
- no-look-ahead tests;
- Supply Lock low-volume scenario;
- Distribution scenario;
- missing-factor renormalization;
- Confidence degradation for proxy/illiquid cases;
- exact limit-up unavailable when source is absent;
- historical/incremental convergence;
- idempotent persistence;
- transaction rollback;
- public view contract.

## Status

```text
APPROVED_FOR_IMPLEMENTATION
```
