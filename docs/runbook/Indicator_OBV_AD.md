# OBV + AD Line Activation and Historical Initload Runbook

## Purpose

Activate `OBV` and `AD` (Accumulation/Distribution Line), create complete D/W/M
indicator config families, backfill their full historical values, and validate the
public `vw_Ticker_indicators` contract before SmartMoneyScore consumes them.

## Scope

Affected indicator configs:

```text
OBV_D
OBV_W
OBV_M
AD_D
AD_W
AD_M
```

Unrelated indicator configs MUST NOT be recalculated by this runbook.

## Preconditions

1. Repository is on the intended branch and up to date.
2. CherryMon DuckDB is available in write mode.
3. `raw_stock_eod` and `raw_lstTicker` are populated.
4. Indicator Engine baseline objects already exist:
   - `dim_indicator`
   - `dim_indicator_component`
   - `dim_indicator_config`
   - `cal_indicator_values`
   - `vw_Indicator_config`
   - `vw_Ticker_indicators`
5. Python environment has the repository dependencies including `pandas-ta-classic`.

## Step 0 — Pull latest code

```powershell
git pull
```

Expected files include:

```text
src/DuckDB/sql/indicator_obv_ad_activate.sql
scripts/initload/init_reload_cal_indicator_values_obv_ad.py
src/DuckDB/sql/indicator_obv_ad_preflight.sql
```

## Step 1 — PHASE 1: Activate metadata

Execute:

```text
src/DuckDB/sql/indicator_obv_ad_activate.sql
```

Use the approved CherryMon DuckDB SQL execution path/MCP. The SQL is idempotent.

Expected metadata:

| Indicator | Function | RequiredInputs | Configs |
|---|---|---|---|
| OBV | `obv` | Close, Volume | OBV_D / OBV_W / OBV_M |
| AD | `ad` | High, Low, Close, Volume | AD_D / AD_W / AD_M |

Expected component contract for both:

```text
ComponentCode = VALUE
ValueSemantic = CUMULATIVE_FLOW
Unit          = VOLUME
IsPrimary     = TRUE
IsActive      = TRUE
```

Stop if:
- either definition is missing;
- either indicator remains inactive;
- any D/W/M config is missing or disabled;
- RequiredInputs differ from the contract above.

## Step 2 — PHASE 2: Targeted historical initload

Run:

```powershell
.\.venv\Scripts\python.exe scripts\initload\init_reload_cal_indicator_values_obv_ad.py
```

The script performs:

```text
resolve ConfigId dynamically
        ↓
MWG smoke refresh
        ↓
full historical backfill
        ↓
OBV_D/W/M + AD_D/W/M only
```

Expected:
- smoke `records_upserted > 0`;
- full backfill `records_upserted > 0`;
- each of the six configs has non-zero output coverage;
- transaction commits successfully.

### Cumulative-history rule

OBV and AD are cumulative indicators. Incremental calculation must read source
history from inception so the cumulative baseline matches a full historical run.
Only the target checkpoint rows are replaced.

This behavior is implemented in:

```text
src/calcEngine/indicatorRegistry.py
src/calcEngine/calcIndicators.py
```

Do not replace this with a short fixed warmup window.

## Step 3 — PHASE 3: Read-only validation

Execute:

```text
src/DuckDB/sql/indicator_obv_ad_preflight.sql
```

Validate all sections:

1. active master definitions + exact RequiredInputs;
2. one active `VALUE` component per indicator;
3. complete enabled D/W/M config families;
4. non-zero historical output coverage;
5. zero duplicate logical keys;
6. zero unexpected components;
7. numeric `OBV_D` and `AD_D` rows visible for MWG through `vw_Ticker_indicators`.

## Step 4 — SmartMoneyScore readiness check

SmartMoneyScore consumes technical indicator evidence through:

```text
vw_Ticker_indicators
```

For V1:

```text
OBV_D -> optional accumulation evidence
AD_D  -> optional accumulation/distribution evidence
```

SmartMoneyScore MUST NOT read `cal_indicator_values` directly when the public
view satisfies the contract.

## Terminal verdict

Use exactly one terminal outcome:

```text
OBV + AD Line Deployment
------------------------
Metadata: PASS | FAIL
Smoke: PASS | FAIL
Historical initload: PASS | FAIL
D/W/M coverage: PASS | FAIL
Duplicate keys: PASS | FAIL
Public view: PASS | FAIL

Verdict: PASS | FAIL | BLOCKED
Action: KEEP | FIX ONCE | STOP
```

Rules:
- `PASS` -> KEEP and allow SmartMoneyScore to consume `OBV_D` / `AD_D`.
- `FAIL` -> identify one failing condition and perform at most one controlled repair.
- `BLOCKED` -> stop; do not mark the indicators production-ready.
- Never convert missing output into a successful verdict.

## Related material

- `docs/architecture/Indicator_Engine.md`
- `docs/architecture/SmartMoneyScore.md`
- `.github/agents/Indicator_Management.agent.md`
- `.github/instructions/indicators.instructions.md`
- `scripts/initload/README.md`
