# SmartMoneyStrategy V1 — Local Deployment & Validation Runbook

- **Requirement:** `REQ-0026`
- **Architecture:** `docs/architecture/SmartMoneyStrategy.md`
- **Upstream model:** `docs/architecture/SmartMoneyScore.md`
- **Public contract:** `"CherryMon"."main"."vw_Ticker_SmartMoney"`
- **Strategy column:** `TradeAction`
- **Validation owner:** `TestEngineer`
- **Execution target:** local CherryStock repository + local CherryMon DuckDB
- **Status before local validation:** `IMPLEMENTED_PENDING_VALIDATION`

## 1. Objective

Validate that the local CherryStock environment has correctly deployed and can safely consume the SmartMoneyStrategy V1 mapping:

```text
BUY / HOLD / SELL
```

from the existing SmartMoney public view without changing SmartMoneyScore calculation semantics or historical persistence.

The local agent MUST end with exactly one terminal verdict:

```text
PASS
FAIL
BLOCKED
REGRESSION
```

and one terminal action:

```text
KEEP
FIX ONCE
REVERT
STOP
```

After a terminal verdict, STOP. Do not automatically investigate another hypothesis.

---

# 2. Scope

## In scope

- sync the latest `main` branch;
- verify required SmartMoneyStrategy files exist;
- run focused strategy tests;
- run the nearest SmartMoney integration regression test;
- execute the normal SmartMoney schema/incremental path so the local view is recreated with `TradeAction`;
- run read-only SmartMoney preflight;
- verify `TradeAction` values and mapping against real local data;
- refresh generated DuckDB metadata after the local view change;
- record a finite TestEngineer verdict.

## Out of scope

- changing BUY/HOLD/SELL business rules;
- recalibrating SmartMoneyScore weights or thresholds;
- full SmartMoney historical initload unless a separate requirement explicitly asks for it;
- OOS/effectiveness research;
- changing `MarketState` rules;
- changing `ConfidenceScore` or `DataQualityStatus` rules;
- adding position sizing, stop loss, take profit or order execution;
- refactoring unrelated code.

---

# 3. Why full historical initload is NOT required

`TradeAction` is not persisted in:

```text
cal_smart_money_ticker_score
cal_smart_money_factor_values
```

It is derived by the public view:

```text
vw_Ticker_SmartMoney
```

Therefore recreating the view immediately exposes `TradeAction` for all already-persisted historical SmartMoney rows.

Do NOT run:

```powershell
python scripts\initload\init_reload_smart_money_score.py
```

for this strategy-only rollout unless another failure proves that historical SmartMoney persistence itself is invalid.

---

# 4. Mandatory context for the local agent

Before execution, read only this context set:

```text
.github/copilot-instructions.md
.github/agents/CherryMon.agent.md
.github/agents/TestEngineer.agent.md
.github/instructions/testing.instructions.md
.github/instructions/database.instructions.md
docs/backlog/requirements/REQ-0026-smart-money-strategy.md
docs/architecture/SmartMoneyStrategy.md
docs/architecture/SmartMoneyScore.md
docs/runbook/SmartMoneyStrategy_V1.md
src/DuckDB/sql/smart_money_v1_schema.sql
src/DuckDB/sql/smart_money_v1_preflight.sql
tests/test_smart_money_strategy.py
tests/test_smart_money_integration.py
```

Do not scan unrelated repository areas.

---

# 5. Rule under validation

The public view must expose exactly this deterministic strategy mapping:

```sql
CASE
    WHEN DataQualityStatus <> 'PASS' THEN 'HOLD'
    WHEN MarketState = 'DISTRIBUTION' THEN 'SELL'
    WHEN MarketState IN (
        'ACCUMULATION',
        'BREAKOUT',
        'DEMAND_EXPANSION',
        'SUPPLY_LOCK'
    ) THEN 'BUY'
    ELSE 'HOLD'
END AS TradeAction
```

Expected semantics:

| Condition | Expected `TradeAction` |
|---|---|
| `DataQualityStatus <> PASS` | `HOLD` |
| `PASS + DISTRIBUTION` | `SELL` |
| `PASS + ACCUMULATION` | `BUY` |
| `PASS + BREAKOUT` | `BUY` |
| `PASS + DEMAND_EXPANSION` | `BUY` |
| `PASS + SUPPLY_LOCK` | `BUY` |
| `PASS + MARKUP` | `HOLD` |
| `PASS + LIQUIDITY_DRYUP` | `HOLD` |
| `PASS + SELLING_CLIMAX` | `HOLD` |
| `PASS + NEUTRAL` | `HOLD` |

The local production dataset is NOT required to contain all three actions on the latest date. The synthetic focused test owns complete branch coverage.

---

# 6. Phase 0 — Define the single validation objective

The local agent must write this before executing commands:

```text
Objective: validate local deployment and real-data contract of SmartMoneyStrategy V1 TradeAction without changing strategy rules.

In scope:
- schema/view deployment
- focused tests
- integration regression
- read-only real-data verification
- metadata refresh

Out of scope:
- strategy redesign
- SmartMoneyScore recalibration
- full historical initload
```

Stop condition:

```text
PASS / FAIL / BLOCKED / REGRESSION + KEEP / FIX ONCE / REVERT / STOP
```

---

# 7. Phase 1 — Sync repository safely

Run from the CherryStock repository root in PowerShell.

```powershell
git status --short
```

### Expected

No unexpected local modifications.

### If output is non-empty

Do NOT discard, reset, stash or overwrite user work automatically.

Return:

```text
Verdict: BLOCKED
Action: STOP
Reason: working tree contains uncommitted changes; safe sync cannot be guaranteed.
```

If clean, continue:

```powershell
git fetch origin
git checkout main
git pull --ff-only origin main
git log -1 --oneline
```

Then verify the expected files:

```powershell
Test-Path docs\architecture\SmartMoneyStrategy.md
Test-Path docs\runbook\SmartMoneyStrategy_V1.md
Test-Path docs\backlog\requirements\REQ-0026-smart-money-strategy.md
Test-Path tests\test_smart_money_strategy.py
Test-Path src\DuckDB\sql\smart_money_v1_schema.sql
Test-Path src\DuckDB\sql\smart_money_v1_preflight.sql
```

### PASS

All commands return `True` for the expected files.

### BLOCKED

Any required file is missing after successful `git pull --ff-only`.

Do not invent a replacement file.

---

# 8. Phase 2 — Python/import sanity

Run:

```powershell
python --version
python -m py_compile scripts\run_smart_money.py
python -m py_compile scripts\run_smart_money_preflight.py
```

### PASS

All commands exit code `0`.

### FAIL

Compilation/import error in a file touched by this strategy rollout.

Allowed repair budget: at most one focused repair before retest.

Do not rerun an unchanged failing command.

---

# 9. Phase 3 — Focused strategy unit test

Run the narrowest strategy test first:

```powershell
python -m pytest tests\test_smart_money_strategy.py -v
```

This test must cover at minimum:

```text
PASS + bullish state      -> BUY
PASS + DISTRIBUTION       -> SELL
PASS + neutral/non-action -> HOLD
WARNING/INVALID           -> HOLD
only BUY/HOLD/SELL values
```

### PASS

All tests in `tests/test_smart_money_strategy.py` pass.

### FAIL

If the failure is caused by the current strategy change:

```text
Action: FIX ONCE
```

One focused fix is allowed, followed by one retest.

If the same behavior still fails after the focused repair:

```text
Verdict: FAIL
Action: STOP
```

Do not continue to integration or real-data execution.

---

# 10. Phase 4 — Nearest SmartMoney integration regression

Run:

```powershell
python -m pytest tests\test_smart_money_integration.py -v
```

This is the nearest persistence/public-view regression boundary. It checks schema bootstrap, SmartMoney calculation persistence, public view readability and incremental/full convergence behavior on the synthetic DuckDB fixture.

### PASS

All integration tests pass.

### REGRESSION

Any previously valid SmartMoney persistence/incremental behavior fails because of the strategy rollout.

On regression:

```text
Verdict: REGRESSION
Action: STOP
```

Do not broaden into unrelated SmartMoney refactoring.

---

# 11. Phase 5 — Deploy/recreate the local public view through the normal path

Use the normal SmartMoney operational runner rather than ad-hoc `duckdb.connect()` calls.

Run:

```powershell
python scripts\run_smart_money.py --days 15
```

The runner performs:

```text
DuckDBUnitOfWork
    ↓
execute smart_money_v1_schema.sql
    ↓
CREATE OR REPLACE vw_Ticker_SmartMoney
    ↓
bounded SmartMoney incremental refresh
    ↓
COMMIT
```

`TradeAction` is derived by the recreated public view. Existing historical persisted score rows immediately inherit the new public column.

### Expected output

A summary containing:

```text
status = OK
score_rows_upserted > 0
factor_rows_upserted > 0
```

Exact counts depend on current local data and requested checkpoint window.

### Failure behavior

The runner uses the project UnitOfWork. A write failure must not be bypassed with an ad-hoc direct DuckDB writer.

If it fails:

```text
Verdict: FAIL or BLOCKED
Action: STOP
```

Capture the exact exception and command. Do not run full initload automatically.

---

# 12. Phase 6 — Read-only SmartMoney preflight

Run:

```powershell
python scripts\run_smart_money_preflight.py
```

The runner executes `src/DuckDB/sql/smart_money_v1_preflight.sql` statement-by-statement using read-only DuckDB access.

For SmartMoneyStrategy specifically, verify the output includes these contracts:

```text
TradeAction distribution query executes successfully
InvalidTradeAction = 0
TradeActionMappingMismatch = 0
```

Also preserve all upstream SmartMoney preflight expectations:

```text
no duplicate score keys
no duplicate factor keys
score/confidence ranges valid
FactorCoverage range valid
supported MarketState values only
public view readable
all score rows have factor evidence
```

### PASS

The preflight reaches the end without `STOPPED at statement ...` and all zero-violation checks are zero.

### FAIL

Any of these is non-zero:

```text
InvalidTradeAction
TradeActionMappingMismatch
DuplicateScoreKeys
DuplicateFactorKeys
ScoreRowsWithoutFactors
```

or any existing SmartMoney range/integrity contract is violated.

---

# 13. Phase 7 — Real local data drill-down

Run this PowerShell block exactly from repository root:

```powershell
@'
from src.Ults.DuckLib import DuckDBManager

with DuckDBManager(read_only=True) as con:
    print("=== Latest SmartMoney date ===")
    latest = con.sql('''
        SELECT MAX(Date) AS LatestDate
        FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
    ''').df()
    print(latest.to_string(index=False))

    print("\n=== Latest-date TradeAction / state / quality distribution ===")
    distribution = con.sql('''
        WITH latest AS (
            SELECT MAX(Date) AS Date
            FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
        )
        SELECT
            v.TradeAction,
            v.MarketState,
            v.DataQualityStatus,
            COUNT(*) AS Rows
        FROM "CherryMon"."main"."vw_Ticker_SmartMoney" AS v
        INNER JOIN latest AS d ON d.Date = v.Date
        GROUP BY v.TradeAction, v.MarketState, v.DataQualityStatus
        ORDER BY v.TradeAction, Rows DESC, v.MarketState
    ''').df()
    print(distribution.to_string(index=False))

    print("\n=== Strategy violation counts ===")
    violations = con.sql('''
        SELECT
            SUM(CASE
                WHEN TradeAction IS NULL
                  OR TradeAction NOT IN ('BUY','HOLD','SELL')
                THEN 1 ELSE 0
            END) AS InvalidTradeAction,
            SUM(CASE
                WHEN TradeAction <>
                    CASE
                        WHEN DataQualityStatus <> 'PASS' THEN 'HOLD'
                        WHEN MarketState = 'DISTRIBUTION' THEN 'SELL'
                        WHEN MarketState IN (
                            'ACCUMULATION',
                            'BREAKOUT',
                            'DEMAND_EXPANSION',
                            'SUPPLY_LOCK'
                        ) THEN 'BUY'
                        ELSE 'HOLD'
                    END
                THEN 1 ELSE 0
            END) AS TradeActionMappingMismatch
        FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
    ''').df()
    print(violations.to_string(index=False))

    print("\n=== Recent sample ===")
    sample = con.sql('''
        SELECT
            Ticker,
            Date,
            SmartMoneyScore,
            ConfidenceScore,
            MarketState,
            DataQualityStatus,
            TradeAction
        FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
        WHERE Ticker IN ('MWG','FPT','HPG')
        ORDER BY Date DESC, Ticker
        LIMIT 30
    ''').df()
    print(sample.to_string(index=False))
'@ | python -
```

### PASS criteria

The output must show:

```text
InvalidTradeAction = 0
TradeActionMappingMismatch = 0
```

Every displayed action must be one of:

```text
BUY
HOLD
SELL
```

Do not fail the run merely because one of BUY/HOLD/SELL is absent on the latest trading date. Market conditions may legitimately produce only a subset.

---

# 14. Phase 8 — Refresh generated DB metadata

After the local database view has been successfully recreated and validated, export generated metadata:

```powershell
python -c "from src.Ults import DuckLib; DuckLib.exportDuckDB_metadata()"
```

Then confirm the generated metadata knows the new public column:

```powershell
Select-String -Path docs\reference\DB_Metadata.md -Pattern "vw_Ticker_SmartMoney"
Select-String -Path docs\reference\DB_Metadata.md -Pattern "TradeAction"
```

### PASS

`DB_Metadata.md` contains `TradeAction` under the local `vw_Ticker_SmartMoney` structure.

### Important

`docs/reference/DB_Metadata.md` is generated evidence of the local physical database. Do not hand-edit it to make this check pass.

If metadata export fails after the database validation already passed, report the export failure explicitly. Do not claim full local closure until generated reference export succeeds.

---

# 15. Phase 9 — Optional daily pipeline smoke

This phase is optional for strategy-only validation because `TradeAction` does not change orchestration.

Run `run.py` only when the operator explicitly wants a full daily pipeline smoke or when there is evidence that schema recreation through the daily pipeline differs from `scripts/run_smart_money.py`.

Do NOT automatically run the full daily pipeline merely for extra confidence.

If explicitly required:

```powershell
python run.py
```

Expected ordering remains:

```text
Technical Indicators + DQ
→ ensure SmartMoney schema
→ SmartMoney incremental refresh
→ SmartMoney DQ
→ COMMIT
→ exportDuckDB_metadata()
```

---

# 16. Acceptance criteria for local TestEngineer

Local validation is PASS only when all applicable criteria below pass:

1. repository sync is clean and safe;
2. strategy unit test passes;
3. nearest SmartMoney integration test passes;
4. normal SmartMoney runner successfully recreates/deploys the view;
5. public view contains `TradeAction`;
6. `TradeAction` is never NULL;
7. `TradeAction` contains only `BUY`, `HOLD`, `SELL`;
8. quality gate maps every non-PASS row to `HOLD`;
9. PASS + `DISTRIBUTION` maps to `SELL`;
10. PASS + `ACCUMULATION/BREAKOUT/DEMAND_EXPANSION/SUPPLY_LOCK` maps to `BUY`;
11. all other PASS states map to `HOLD`;
12. `TradeActionMappingMismatch = 0` on the full local public view;
13. existing SmartMoney duplicate/range/factor-evidence contracts remain valid;
14. generated DB metadata exports successfully and includes `TradeAction`.

---

# 17. Failure handling and retry budget

## Working tree dirty

```text
Verdict: BLOCKED
Action: STOP
```

Do not auto-reset/stash user changes.

## Focused strategy test fails

One focused repair is allowed only when the failure directly belongs to the strategy rollout.

```text
Fix attempt 1
→ rerun the same focused test once
```

If still failing:

```text
Verdict: FAIL
Action: STOP
```

## Integration regression

```text
Verdict: REGRESSION
Action: STOP
```

Do not rewrite the SmartMoney engine during this runbook.

## Local DB runner fails

Capture:

```text
command
exception
current HEAD
local DB path/config context
```

Then STOP. Do not bypass project connection/transaction policy.

## Preflight mapping mismatch

If:

```text
TradeActionMappingMismatch > 0
```

classify as:

```text
Verdict: FAIL
Action: STOP
```

because the public contract does not match the approved deterministic strategy.

## Retry governance

- never rerun the same failing command unchanged;
- maximum two total repair attempts for the same defect under repository governance;
- this runbook defaults to one focused repair for the strategy change;
- no automatic second hypothesis;
- no unrelated cleanup/refactor.

---

# 18. Rollback boundary

SmartMoneyStrategy V1 is additive at the public-view contract layer.

The rollout does not add persisted `TradeAction` data and does not mutate upstream OHLCV/indicator Sources of Truth.

If strategy validation fails:

1. STOP further rollout;
2. do not run full historical initload automatically;
3. do not delete SmartMoney factor/score persistence;
4. preserve the exact failing evidence;
5. if an explicit rollback is approved, revert the strategy implementation commit(s) and recreate `vw_Ticker_SmartMoney` from the reverted schema through the normal SmartMoney runner;
6. rerun only the focused validation required to prove rollback correctness.

Do not manually edit production DuckDB objects outside the repository-owned SQL path.

---

# 19. Required local-agent result format

The local agent MUST finish with this exact evidence structure:

```text
SMART MONEY STRATEGY V1 — LOCAL VALIDATION

Objective:
Validate TradeAction BUY/HOLD/SELL on local CherryMon.

Repository:
Branch: main
HEAD: <sha>
Working tree before run: CLEAN | DIRTY

Focused strategy test:
Command: python -m pytest tests\test_smart_money_strategy.py -v
Result: PASS | FAIL
Tests: <passed>/<total>

Integration regression:
Command: python -m pytest tests\test_smart_money_integration.py -v
Result: PASS | FAIL | REGRESSION

Local deployment:
Command: python scripts\run_smart_money.py --days 15
Result: PASS | FAIL | BLOCKED
Summary status: <value>
Score rows upserted: <value>
Factor rows upserted: <value>

Preflight:
Command: python scripts\run_smart_money_preflight.py
Result: PASS | FAIL
InvalidTradeAction: <value>
TradeActionMappingMismatch: <value>
DuplicateScoreKeys: <value>
DuplicateFactorKeys: <value>
ScoreRowsWithoutFactors: <value>

Real-data verification:
Latest SmartMoney date: <date>
Latest BUY rows: <count or not present>
Latest HOLD rows: <count or not present>
Latest SELL rows: <count or not present>

Metadata export:
Result: PASS | FAIL
TradeAction present in DB_Metadata.md: YES | NO

Verdict: PASS | FAIL | BLOCKED | REGRESSION
Action: KEEP | FIX ONCE | REVERT | STOP
```

Do not claim PASS based only on static review or GitHub CI. This runbook requires execution against the local CherryMon database.

---

# 20. After PASS — closure handoff

After a real local TestEngineer PASS, the local agent should provide the evidence above to the repository owner.

Only then may the requirement/documentation closure be updated to reflect real local validation, for example:

```text
REQ-0026: DONE
SmartMoneyStrategy status: FUNCTIONALLY_VALIDATED
```

when the repository owner/normal workflow permits that state transition.

Do not change strategy thresholds or mapping during closure.

---

# 21. STOP

After returning the terminal verdict and evidence, STOP.

Do not continue into OOS research, SmartMoneyScore calibration, R/S work, chart work or any other task without a new explicit request.
