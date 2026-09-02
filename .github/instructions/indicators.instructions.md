---
applyTo: "src/calcEngine/**/*.py,scripts/*indicator*.py,src/DuckDB/**/*indicator*.sql"
---

# Indicator Engine Instructions

This file defines mandatory operational rules for onboarding, calculating and validating technical indicators.

Canonical knowledge:
- `docs/architecture/Indicator_Engine.md`
- `docs/adr/ADR-002-indicator-source-of-truth.md`
- generated metadata under `docs/reference/`

## Agent routing
- Concrete indicator onboarding, configuration, activation, repair, backfill, deactivation or deletion → `.github/agents/Indicator_Management.agent.md`.
- Broad Indicator Engine architecture or cross-module redesign → `.github/agents/SolutionArchitect.agent.md`.
- Clear supporting code change that preserves the approved Indicator Engine contract and is not an indicator lifecycle operation → `.github/agents/GeneralCoding.agent.md`.
- Materially unclear indicator business requirement → `.github/agents/BusinessAnalyst.agent.md`.
- Independent validation → `.github/agents/TestEngineer.agent.md`.

Indicator lifecycle ownership has priority over General Coding. A broad redesign has Solution Architect ownership. General Coding may implement approved supporting changes and must end with `IMPLEMENTED_PENDING_VALIDATION`.

## Source-of-Truth contracts
- `dim_indicator`: indicator master definition.
- `dim_indicator_component`: output component contract.
- `dim_indicator_config`: executable config by parameters/timeframe.
- `vw_Indicator_config`: configuration Single Source of Truth.
- `cal_indicator_values`: internal long-format calculated persistence.
- `vw_Ticker_indicators`: public/calculated indicator Single Source of Truth for downstream consumers.

Downstream code should not read `cal_indicator_values` directly when `vw_Ticker_indicators` satisfies the use case.

## Generated configuration context
Before analyzing or changing indicator metadata, use the generated reference set:
- `docs/reference/DB_Metadata.md` for table/view structure and column contracts;
- `docs/reference/dim_indicator.parquet` for master definitions;
- `docs/reference/dim_indicator_component.parquet` for output components;
- `docs/reference/dim_indicator_config.parquet` for active executable configurations.

Load structure first, then current Parquet values. Join the dimension snapshots by `IndicatorCode`; do not treat the Markdown schema as evidence of current row values.

## Naming
Indicator output convention:

```text
<INDICATOR><PERIOD>_<TIMEFRAME>
```

Timeframes:
- `D` Daily
- `W` Weekly
- `M` Monthly

Examples: `MA20_D`, `MA50_W`, `RSI14_M`.

## Adding or changing an indicator
Follow this sequence:
1. Discovery/pre-check current metadata and library support.
2. Upsert `dim_indicator`.
3. Upsert `dim_indicator_component`.
4. Upsert `dim_indicator_config`.
5. Default production config family includes D/W/M unless requirement explicitly says otherwise.
6. Verify `vw_Indicator_config` exposes the complete executable configuration.
7. Run targeted smoke calculation.
8. Run historical initialization/backfill for the new/changed config family.
9. Validate calculated persistence and `vw_Ticker_indicators` output.
10. Ensure incremental `refresh_technical_indicators()` continues to discover enabled configs without hard-coded indicator branches.

Do not mark onboarding complete if metadata, backfill or validation fails.

## Configuration rules
- `RequiredInputs` must match runtime/library function inputs.
- `ParameterSchema` and config `Parameters` must agree.
- Every active multi-output indicator must have complete component mapping.
- `WarmupBars` must be sufficient for the indicator lookback.
- Prefer targeted `config_ids` backfill when onboarding one family; do not recompute unrelated indicators without reason.
- Reruns must not create duplicates for the logical key.

## Engine rules
- Primary library integrations must resolve through the project registry (`src/calcEngine/indicatorRegistry.py`) rather than hard-coded dispatch in `run.py`.
- New indicators should be config-driven.
- Avoid altering wide fact schemas just to add an indicator when the long-format engine supports it.
- Do not create one table per indicator.

## Validation
At minimum verify:
- D/W/M family completeness;
- active components and output mapping;
- non-empty output after warmup when source history is sufficient;
- numeric/value validity;
- uniqueness of logical key;
- no unintended changes to unrelated config IDs;
- rerun/idempotency behavior;
- public view exposes expected columns/records.

## Architecture reference
The canonical architecture-facing entry point is:
- `docs/architecture/Indicator_Engine.md`

The legacy detailed operational reference remains at:
- `.github/agents/Instructions/Indicator_Engine.md`

Do not add new architecture content to this instruction file. Update the canonical document or an ADR when the approved contract changes.