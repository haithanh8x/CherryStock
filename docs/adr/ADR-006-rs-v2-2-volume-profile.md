# ADR-006 — R/S V2.2 Dedicated Volume Profile Domain

- **Status:** Accepted
- **Date:** 2026-09-02
- **Scope:** Support / Resistance Engine V2.2

## Context

R/S V2.1 added adaptive volatility and structural price levels. V2.2 adds volume-at-price evidence: Point of Control (POC), High Volume Nodes (HVN) and Low Volume Nodes (LVN).

CherryStock currently has daily OHLCV in `raw_stock_eod`, but does not have exchange tick-level or intraday price-by-volume distribution as a production SSOT.

The architecture must avoid:

- registering POC/HVN/LVN as generic technical indicators;
- pretending daily OHLCV contains exact intraday volume-at-price;
- recalculating the same profile twice for level and confirmation roles;
- allowing multiple Volume Profile nodes to inflate source-family confluence;
- introducing persistence/schema before V2.3 evaluation proves it is needed.

## Decision

### 1. Volume Profile is a dedicated domain

Volume Profile is calculated in:

```text
src/calcEngine/volumeProfile.py
```

It is not registered in:

```text
dim_indicator
dim_indicator_component
dim_indicator_config
```

The profile engine is pure calculation code and has no DuckDB/UI dependency.

### 2. V2.2 uses an explicit daily-OHLCV approximation

For each selected daily bar, volume is distributed uniformly across all configured price bins crossed by the bar's Low–High range.

This is a deterministic approximation.

It must not be described as tick-accurate Volume Profile.

A future intraday/tick provider may replace this data source without changing the R/S LevelCandidate contract.

### 3. POC/HVN/LVN are LEVEL sources

All profile nodes use:

```text
SourceRole    = LEVEL
SourceFamily  = VOLUME_STRUCTURE
ValueSemantic = PRICE_LEVEL
```

### 4. Volume confirmation is a separate confirmation family

The provider also emits confirmation contexts:

```text
SourceFamily   = VOLUME_CONFIRMATION
reference_price = node price
value           = normalized node density score
```

Confirmation contributes to Strength only when the reference price belongs to the evaluated zone.

### 5. One profile calculation per provider request

The Volume Profile adapter returns a `ProviderBundle` containing both levels and confirmations.

This prevents one calculation for LEVEL plus another calculation for CONFIRMATION.

### 6. Volume-family cap is enforced through family semantics

POC/HVN/LVN all belong to one `VOLUME_STRUCTURE` family.

Multiple profile nodes in one zone may increase lineage `source_count`, but increase `source_family_count` by at most one.

### 7. No DuckDB schema migration in V2.2

V2.2 consumes the existing:

```text
raw_stock_eod(Date, High, Low, Close, Volume)
```

No new persistence table/view is introduced.

Production validation uses:

```text
src/DuckDB/sql/rs_v2_2_preflight.sql
```

which is read-only.

## Consequences

### Positive

- keeps Indicator Engine semantics clean;
- provides POC/HVN/LVN without a new database model;
- keeps the R/S core source-agnostic;
- preserves point-in-time calculation;
- limits correlated volume evidence through family cap;
- allows future migration to intraday/tick Volume Profile.

### Trade-offs

- daily OHLCV profile is an approximation, not true tick-level volume-at-price;
- profile parameters materially affect node locations;
- default V2.2 performs additional calculation per request;
- persistence and formal ablation are deferred to V2.3.

## Validation

Required:

```text
python -m pytest tests/test_rs_ladder.py -v
src/DuckDB/sql/rs_v2_2_preflight.sql
tests/test_R_S_V2_2.md
```

Production rollout is allowed only after the V2.2 runbook returns PASS.
