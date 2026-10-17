# Indicator Engine Architecture

## Purpose

Canonical architecture entry point for CherryStock technical indicators. This document owns **how the Indicator Engine is structured**. Mandatory execution constraints live in `.github/instructions/indicators.instructions.md`; the repeatable lifecycle procedure lives in `.github/skills/indicator-onboarding/SKILL.md`.

## Active full-history AFL producer (October 2026)

The canonical **daily calculation path** now runs AmiBroker's saved
`Export_Indicator.apx` and its `Export_Indicator.afl` (D/W/M) after the core
EOD source-sync transaction commits. Python handles COM export, wide CSV staging,
quality checks and atomic full replacement of `cal_indicator_values`. All
indicators are calculated by AFL, not `pandas-ta-classic` in the daily path.

The daily operator needs only to maintain the AmiBroker AFL/APX and execute
`run.py` (or `scripts/sync_amibroker_indicator_full.py`). The existing
three `dim_indicator*` tables **remain physically present**, because the
current `cal_indicator_values` schema uses a numeric `ConfigId` and
R/S, SmartMoney and public views still join metadata. The loader now
populates any missing indicator/config/component rows automatically,
preserving existing ConfigIds and downstream queries. Manual metadata
onboarding is no longer required for columns already present in the AFL contract.

The previous `refresh_technical_indicators()` Python engine is retained
for historical/test compatibility but is not the daily producer. Its
incremental backfill and metadata-driven calculations are the **legacy path**.
Do not run both producers concurrently.

The full history is imported in a dedicated transaction: after validation,
DELETE all rows and INSERT the complete new set. Any failed check rolls back
the old fact and metadata changes. Source AFL CSV is a wide intermediate
format; persistence stays long-format.

See `docs/runbook/AFL_Indicator_Full_Refresh.md` for setup, D/W/M semantics,
safety gates and daily commands.

## Core flow

```text
raw_stock_eod
      ↓
dim_indicator
      ↓
dim_indicator_component
      ↓
dim_indicator_config (D/W/M)
      ↓
vw_Indicator_config          ← Configuration SSOT
      ↓
refresh_technical_indicators()
      ↓
cal_indicator_values         ← internal persistence
      ↓
vw_Ticker_indicators         ← Calculated Value SSOT
      ↓
CherryMon / Screener / Score / Chart / API / ML
```

## Responsibilities

- `dim_indicator`: indicator master definition and library/runtime contract.
- `dim_indicator_component`: output component mapping and semantic metadata.
- `dim_indicator_config`: executable parameters + timeframe configuration.
- `vw_Indicator_config`: public configuration Single Source of Truth.
- `cal_indicator_values`: long-format internal calculated persistence.
- `vw_Ticker_indicators`: downstream/public calculated indicator Single Source of Truth.

Primary logical key of calculated persistence:

```text
Ticker + Date + ConfigId + ComponentCode
```

## Design principles

- New indicators are metadata/config-driven.
- Default production family contains Daily, Weekly and Monthly configs unless explicitly scoped otherwise.
- Adding an indicator does not require a new fact table or ALTER of a wide indicator fact schema.
- Downstream consumers should use `vw_Ticker_indicators` instead of internal persistence when possible.
- Historical initialization/backfill and idempotent incremental refresh are separate lifecycle concerns.
- `run.py` orchestrates; it should not contain one hard-coded calculation branch per indicator.
- Library/function resolution belongs in the registry/config model.
- Config IDs are generated persistence identities; stable behavior should be addressed through indicator/config codes and metadata.

## Agent Harness ownership

```text
Agent
  .github/agents/Indicator_Management.agent.md
  owns lifecycle outcome

Instruction
  .github/instructions/indicators.instructions.md
  owns mandatory invariants/safety

Skill
  .github/skills/indicator-onboarding/SKILL.md
  owns Discover → Metadata → Backfill → Validate procedure

Docs
  this file + ADR-002
  own architecture and rationale

Tools
  CherryMon/DuckDB MCP + focused Python wrappers
  provide execution capability

Verification
  TestEngineer + tests/queries
  owns independent verdict
```

The historical long-form pre-hierarchy reference is retained only for migration archaeology at:

```text
docs/reference/Indicator_Engine_Legacy_Reference.md
```

Do not add new operational procedure or architecture ownership to that reference.

## Lifecycle architecture

The canonical lifecycle is:

```text
DISCOVER
  ↓
METADATA / CONFIG
  dim_indicator
  dim_indicator_component
  dim_indicator_config
  ↓
HISTORICAL INITIALIZATION / BACKFILL
  refresh_technical_indicators()
  ↓
PUBLIC/FACT VALIDATION
  cal_indicator_values
  vw_Ticker_indicators
  ↓
INCREMENTAL DAILY/WEEKLY/MONTHLY REFRESH
```

The detailed bounded execution steps are intentionally kept in the `indicator-onboarding` Skill rather than duplicated here.

## Cumulative full-history indicators

Some indicators are cumulative lines rather than finite-window transforms. Their absolute value depends on the beginning of the input series, so a normal checkpoint warmup can reset the baseline and make incremental output diverge from a full historical backfill.

CherryStock records this execution trait centrally in `src/calcEngine/indicatorRegistry.py`. Current full-history functions include:

| Indicator | Function | Required inputs | Production configs | Component semantic |
|---|---|---|---|---|
| OBV | `obv` | Close, Volume | OBV_D / OBV_W / OBV_M | CUMULATIVE_FLOW / VOLUME |
| AD Line | `ad` | High, Low, Close, Volume | AD_D / AD_W / AD_M | CUMULATIVE_FLOW / VOLUME |

During incremental refresh, `refresh_technical_indicators()` partitions ordinary windowed configs from full-history cumulative configs. Windowed indicators keep configured warmup behavior; cumulative indicators reload source history from inception before calculation of the requested checkpoint. Only checkpoint output rows are replaced, preserving reproducible cumulative absolute levels without forcing unrelated indicators through full-history calculation.

Related implementation/material:

```text
src/DuckDB/sql/indicator_obv_ad_activate.sql
scripts/initload/init_reload_cal_indicator_values_obv_ad.py
src/DuckDB/sql/indicator_obv_ad_preflight.sql
```

## Component value semantics

Downstream domains may need to know whether an indicator component represents a price, oscillator, ratio or volatility distance without hard-coding indicator names.

`dim_indicator_component` exposes generic semantic metadata:

```text
ValueSemantic
Unit
```

Current examples:

| Indicator | Component | ValueSemantic | Unit |
|---|---|---|---|
| MA | VALUE | PRICE_LEVEL | PRICE |
| BB | LOWER | PRICE_LEVEL | PRICE |
| BB | MIDDLE | PRICE_LEVEL | PRICE |
| BB | UPPER | PRICE_LEVEL | PRICE |
| BB | WIDTH | VOLATILITY | PERCENT |
| BB | PERCENT | RATIO | RATIO |
| RSI | VALUE | OSCILLATOR | INDEX |
| ATR | VALUE | VOLATILITY_DISTANCE | PRICE |

These are generic Indicator Engine semantics, not R/S-specific configuration. `vw_Indicator_config` should expose them so downstream consumers do not need to join internal dimension tables directly.

Migration for existing CherryMon databases:

```text
src/DuckDB/sql/rs_v2_0_indicator_semantics.sql
```

## Related

- `docs/adr/ADR-002-indicator-source-of-truth.md`
- `.github/instructions/indicators.instructions.md`
- `.github/skills/indicator-onboarding/SKILL.md`
- `.github/agents/Indicator_Management.agent.md`
- `docs/00_HOME.md`
