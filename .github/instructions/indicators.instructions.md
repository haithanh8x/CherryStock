---
applyTo: "src/calcEngine/**/*.py,scripts/*indicator*.py,src/DuckDB/**/*indicator*.sql"
---

# Indicator Engine Instructions

This file owns operational rules for onboarding, calculating and validating technical indicators.

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
The current detailed operational reference remains at:
- `.github/agents/Instructions/Indicator_Engine.md`

The architecture-facing entry point is:
- `docs/architecture/Indicator_Engine.md`

When those documents are consolidated later, `docs/architecture/Indicator_Engine.md` should become the specification owner and this file should remain only operational AI/developer policy.