# ADR-004 — R/S V2.0 Source Semantics and Provider Boundary

- **Status:** Accepted
- **Date:** 2026-09-01
- **Scope:** Support / Resistance Engine V2.0, Indicator Engine public metadata contract

## Context

R/S V1 consumes MA values from the Indicator Engine public views and hard-codes MA as the only source. V2.0 introduces Bollinger Band price levels and RSI confirmation while preserving the rule that technical indicators are calculated once by Indicator Engine and reused downstream.

The main risks are:

- treating non-price indicator outputs as price levels;
- coupling R/S core calculation directly to indicator-specific SQL;
- counting correlated sources as independent confluence;
- duplicating indicator calculation inside the R/S domain;
- losing explainability about source role and source family.

## Decision

### 1. Indicator Engine remains the technical-indicator source of truth

R/S reads:

- `vw_Ticker_indicators` — calculated value SSOT;
- `vw_Indicator_config` — configuration/component metadata SSOT.

R/S does not read `cal_indicator_values` directly when the public views satisfy the contract.

### 2. Indicator Providers are R/S adapters, not database objects

`MAProvider`, `BBProvider`, and `RSIProvider` translate generic Indicator Engine rows into R/S canonical contracts.

```text
vw_Ticker_indicators + vw_Indicator_config
                 ↓
          Indicator Providers
                 ↓
LevelCandidate / ConfirmationContext
                 ↓
              R/S Core
```

### 3. Generic indicator component semantics belong in Indicator Engine metadata

Add nullable columns to `dim_indicator_component`:

- `ValueSemantic`
- `Unit`

The public `vw_Indicator_config` view exposes both columns.

Initial semantic assignments:

| Indicator | Component | ValueSemantic | Unit |
|---|---|---|---|
| MA | VALUE | PRICE_LEVEL | PRICE |
| BB | LOWER/MIDDLE/UPPER | PRICE_LEVEL | PRICE |
| BB | WIDTH | VOLATILITY | PERCENT |
| BB | PERCENT | RATIO | RATIO |
| RSI | VALUE | OSCILLATOR | INDEX |
| ATR | VALUE | VOLATILITY_DISTANCE | PRICE |

These fields are generic indicator metadata. No R/S-specific `UseForRS` flag is added to `dim_indicator`.

### 4. R/S owns SourceRole and SourceFamily

V2.0 roles:

- MA → LEVEL / TREND_AVERAGE
- BB LOWER/MIDDLE/UPPER → LEVEL / VOLATILITY_BAND
- RSI → CONFIRMATION / MOMENTUM_CONFIRMATION

Only `LEVEL + PRICE_LEVEL` values may enter normalization/clustering.

### 5. Confluence uses source-family diversity

`source_count` remains for lineage/explainability, but Strength confluence uses unique `source_family_count` with saturation instead of treating every source as independent evidence.

### 6. RSI confirmation never changes proximity rank

S1/R1 are still nearest eligible support/resistance zones. RSI may change Strength/confidence only.

## Consequences

### Positive

- R/S core is source-agnostic and easier to extend.
- BB WIDTH/PERCENT and RSI cannot accidentally become price levels.
- Indicator calculations are not duplicated.
- Source-family correlation is explicitly controlled.
- UI/AI can explain both source count and family count.
- The same semantic metadata can be reused by other downstream domains.

### Trade-offs

- Existing DuckDB environments require one metadata migration before V2.0 runtime is enabled.
- `vw_Indicator_config` public contract gains two columns.
- Strength values are not numerically identical to V1 because confluence semantics change from raw source count to family diversity.

## Migration

Run:

```text
src/DuckDB/sql/rs_v2_0_indicator_semantics.sql
```

against CherryMon before running R/S V2.0 with default sources.

After migration, refresh generated DB references with the existing metadata export workflow.

## Validation

Minimum:

```powershell
python -m pytest tests/test_rs_ladder.py -v
```

Then execute the local production-data runbook:

```text
tests/test_R_S_V2_0.md
```
