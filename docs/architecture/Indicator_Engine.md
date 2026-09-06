# Indicator Engine Architecture

## Purpose
Architecture-facing entry point for CherryStock technical indicators.

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
- `dim_indicator_component`: output component mapping.
- `dim_indicator_config`: executable parameter + timeframe configuration.
- `vw_Indicator_config`: public configuration Single Source of Truth.
- `cal_indicator_values`: long-format internal persistence.
- `vw_Ticker_indicators`: downstream/public calculated indicator Single Source of Truth.

## Design principles
- New indicators are metadata/config-driven.
- Default production family contains Daily, Weekly and Monthly configs unless explicitly scoped otherwise.
- Adding an indicator must not require a new fact table or ALTER of a wide indicator fact schema.
- Downstream consumers should use `vw_Ticker_indicators` instead of internal persistence when possible.
- Historical initialization/backfill and idempotent incremental refresh are separate lifecycle concerns.
- `run.py` orchestrates; it should not contain one hard-coded calculation branch per indicator.

## Current detailed reference
During this refactor, the existing detailed operational/design document remains available at:

- `.github/agents/Instructions/Indicator_Engine.md`

The long-form content should be progressively migrated here when it is edited next. New architecture/design content belongs in this file; AI operational policy belongs in `.github/instructions/indicators.instructions.md`.

## Cumulative full-history indicators

Some library indicators are cumulative lines rather than finite-window transforms.
Their absolute value depends on the beginning of the input series, so a normal
checkpoint warmup would reset the baseline and make incremental output diverge
from a full historical backfill.

CherryStock records this execution trait centrally in
`src/calcEngine/indicatorRegistry.py`. The current full-history functions are:

| Indicator | Function | Required inputs | Production configs | Component semantic |
|---|---|---|---|---|
| OBV | `obv` | Close, Volume | OBV_D / OBV_W / OBV_M | CUMULATIVE_FLOW / VOLUME |
| AD Line | `ad` | High, Low, Close, Volume | AD_D / AD_W / AD_M | CUMULATIVE_FLOW / VOLUME |

During incremental refresh, `refresh_technical_indicators()` partitions normal
windowed configs from full-history cumulative configs. Windowed indicators keep
their configured warmup behavior; OBV/AD reload source history from inception
before calculating the requested checkpoint. Only checkpoint rows are replaced,
so the cumulative absolute level remains reproducible without forcing unrelated
indicators to calculate from full history.

Activation metadata:
`src/DuckDB/sql/indicator_obv_ad_activate.sql`

Targeted historical initialization:
`scripts/initload/init_reload_cal_indicator_values_obv_ad.py`

Validation:
`src/DuckDB/sql/indicator_obv_ad_preflight.sql`

## Related
- [[../../.github/instructions/indicators.instructions|Indicator Instructions]]
- [[../adr/ADR-002-indicator-source-of-truth|ADR-002 Indicator Source of Truth]]
- [[../00_HOME|Knowledge Home]]

---

## Component Value Semantics

Downstream domains may need to know whether an indicator component represents a price, oscillator, ratio or volatility distance without hard-coding indicator names.

`dim_indicator_component` therefore exposes generic semantic metadata:

```text
ValueSemantic
Unit
```

Initial values used by R/S V2.0:

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

These are generic Indicator Engine semantics, not R/S-specific configuration.

The public configuration SSOT `vw_Indicator_config` must expose both fields so downstream consumers do not need to join internal dimension tables directly.

Migration for existing CherryMon databases:

```text
src/DuckDB/sql/rs_v2_0_indicator_semantics.sql
```

