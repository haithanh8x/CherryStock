# Runbook — REQ-0032 MovementContext V1

- Requirement: REQ-0032
- Architecture: docs/architecture/Movement_Context_V1.md
- ADR: ADR-017
- Initial validation ticker: MWG
- Final validation owner: TestEngineer

## 1. Objective

Apply and independently validate MovementContext V1 on the local CherryMon DuckDB.

MovementContext must:

- derive confirmed history from `vw_Ticker_Movement_Profile`;
- derive provisional current-leg context from `vw_Ticker_ZigZag_Current`;
- use `vw_Ticker_OHLC_D` only to count current-leg trading intervals;
- expose `vw_Ticker_Movement_Context`;
- remain independent of R/S and SmartMoney;
- leave `run.py` unchanged.

## 2. Main Artifacts

```text
docs/backlog/requirements/REQ-0032-movement-context-v1.md
docs/architecture/Movement_Context_V1.md
docs/adr/ADR-017-movement-context-as-price-behavior-contract.md
src/DuckDB/sql/movement_context_v1_schema.sql
scripts/initload/init_movement_context_v1.py
scripts/validate_movement_context_mwg.py
tests/test_movement_context_v1.py
```

## 3. Phase 0 — Sync the GitHub Branch

Run exactly:

```powershell
cd C:\Github\CherryStock
git status
git fetch origin
git switch feature/movement-context-v1
git pull origin feature/movement-context-v1
```

If unrelated local modifications exist, STOP and report BLOCKED. Do not overwrite them.

## 4. Phase 1 — Focused Automated Tests

Run:

```powershell
python -m pytest tests\test_movement_context_v1.py tests\test_price_movement_zigzag.py -v
```

PASS requires all selected tests to pass.

If FAIL:

1. capture the exact first failing assertion/error;
2. do not broaden scope;
3. report FAIL to the implementation owner;
4. STOP.

Do not run the migration after a focused-test failure.

## 5. Phase 2 — Prerequisite Check

MovementContext requires existing MWG upstream data.

Run:

```sql
SELECT
    Ticker,
    AsOfConfirmedAtDate,
    ConfirmedSwingCount,
    LastSwingDirection,
    LastSwingPct,
    MovementCharacter
FROM "CherryMon"."main"."vw_Ticker_Movement_Profile"
WHERE Ticker = 'MWG'
  AND PriceMovementConfigCode = 'PM_ZZ_D_V2';

SELECT
    Ticker,
    AsOfDate,
    Direction,
    StartPivotDate,
    CurrentMovePct,
    Status
FROM "CherryMon"."main"."vw_Ticker_ZigZag_Current"
WHERE Ticker = 'MWG'
  AND ConfigCode = 'ZZ_D_5_MVP';
```

Required:

- exactly one MWG movement profile row;
- ZigZag current row may exist or be absent;
- absence of current row is allowed and should later produce `PROFILE_ONLY`.

If the movement profile is absent, STOP with BLOCKED and run the REQ-0031 Price Movement runbook first.

## 6. Phase 3 — Apply Additive MovementContext Schema

Run:

```powershell
python scripts\initload\init_movement_context_v1.py
```

Expected:

```text
schema: applied
mwg_context_rows: 1
MovementContext V1 committed; DuckDB metadata exported.
```

This step:

- creates/seeds `dim_movement_context_config`;
- creates/replaces `vw_Ticker_Movement_Context`;
- does not backfill a calculated context table;
- refreshes `docs/reference/DB_Metadata.md` from the actual local DB.

If the command fails, report FAIL and STOP. Do not retry unchanged SQL.

## 7. Phase 4 — Independent MWG Validation

Run:

```powershell
python scripts\validate_movement_context_mwg.py
```

PASS requires:

```text
context_rows: 1
profile_rows: 1
structural_errors: 0
MOVEMENT CONTEXT VALIDATION: PASS
```

The validator independently checks:

- TrendRegime equals MovementCharacter;
- TypicalSwingPct / TypicalSwingBars / TypicalMoveSpeed map to profile medians;
- same-direction LastSwingTypicalPct;
- LastSwingExtentRatio formula;
- allowed LastSwingState;
- allowed TrendQuality;
- CurrentTradingBars from canonical OHLC dates;
- CurrentMoveSpeedPctPerBar formula;
- CurrentMoveSpeedRatio formula;
- no SmartMoney/R/S dependency in the schema contract.

## 8. Phase 5 — Direct SQL Review

Run:

```sql
SELECT
    MovementContextConfigCode,
    Ticker,
    ContextAsOfDate,
    ContextStatus,
    TrendRegime,
    TrendQuality,
    TypicalSwingPct,
    TypicalSwingBars,
    TypicalMoveSpeedPctPerBar,
    LastSwingDirection,
    LastSwingPct,
    LastSwingTypicalPct,
    LastSwingExtentRatio,
    LastSwingState,
    CurrentLegDirection,
    CurrentMovePct,
    CurrentTradingBars,
    CurrentMoveSpeedPctPerBar,
    CurrentMoveSpeedRatio,
    CurrentMoveSpeedState
FROM "CherryMon"."main"."vw_Ticker_Movement_Context"
WHERE Ticker = 'MWG'
  AND MovementContextConfigCode = 'MC_PM_ZZ_D_V1';
```

For the currently committed MWG profile, the confirmed portion should reconcile approximately to:

```text
TrendRegime           MIXED
TrendQuality          MODERATE_HIGH
LastSwingDirection    DOWN
LastSwingPct          -9.62%
LastSwingTypicalPct   ~9.86%
LastSwingExtentRatio  ~0.98
LastSwingState        TYPICAL_DOWN_SWING
```

Current-leg fields depend on the latest local ZigZag snapshot and are expected to change over time.

## 9. Phase 6 — Idempotency

Run the migration a second time:

```powershell
python scripts\initload\init_movement_context_v1.py
python scripts\validate_movement_context_mwg.py
```

PASS requires:

- still one enabled `MC_PM_ZZ_D_V1` config;
- still one MWG context row for the config;
- validation remains PASS;
- no duplicate config rows.

## 10. Phase 7 — Daily Pipeline Regression

Run:

```powershell
python -m pytest tests\test_sync_write_pipeline_service.py -v
```

PASS requires no regression.

REQ-0032 does not authorize editing `run.py`.

## 11. Phase 8 — Archify Validation

Because REQ-0032 changes the Movement public-contract description, validate the analytics architecture:

```powershell
.\scripts\render_archify_analytics.ps1 -NoOpen
```

PASS requires the current Archify showcase validation to return `ok=true` and the generated HTML to be synchronized.

If Archify fails only on visualization/layout:

- do not modify MovementContext runtime semantics;
- report the exact Archify failure;
- mark architecture visualization BLOCKED;
- STOP.

Do not hand-edit generated HTML.

## 12. Phase 9 — Review Generated DB Metadata

After Phase 3, confirm `docs/reference/DB_Metadata.md` contains:

```text
main.dim_movement_context_config
main.vw_Ticker_Movement_Context
```

Do not hand-edit DB_Metadata.md. It must come from `exportDuckDB_metadata()`.

## 13. Local Model Output Format

Return exactly this compact verdict:

```text
TEST VERDICT
Objective: REQ-0032 MovementContext V1
Validation depth: INTEGRATION VALIDATION

Focused tests:
PASS | FAIL | BLOCKED

Migration:
PASS | FAIL | BLOCKED

MWG validator:
PASS | FAIL | BLOCKED

Idempotency:
PASS | FAIL | BLOCKED

Daily pipeline regression:
PASS | FAIL | BLOCKED

Archify:
PASS | FAIL | BLOCKED

DB metadata refresh:
PASS | FAIL | BLOCKED

Verdict:
PASS | FAIL | BLOCKED | REGRESSION

Action:
KEEP | FIX_ONCE | REVERT | STOP

Evidence:
- <short evidence>

Residual risk:
- thresholds are heuristic/research until strategy effectiveness is evaluated
```

## 14. STOP Rule

If all gates PASS:

```text
Verdict: PASS
Action: KEEP
STOP
```

If one functional gate fails:

```text
Verdict: FAIL or REGRESSION
Action: FIX_ONCE or REVERT
STOP
```

Do not continue into Strategy, R/S, SmartMoney or unrelated refactoring.
