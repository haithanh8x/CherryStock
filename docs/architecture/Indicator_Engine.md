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

## Related
- [[../../.github/instructions/indicators.instructions|Indicator Instructions]]
- [[../adr/ADR-002-indicator-source-of-truth|ADR-002 Indicator Source of Truth]]
- [[../00_HOME|Knowledge Home]]