# SmartMoneyStrategy V1 — Local Deployment & Validation Runbook

- **Requirement:** `REQ-0026`
- **Architecture:** `docs/architecture/SmartMoneyStrategy.md`
- **Upstream model:** `docs/architecture/SmartMoneyScore.md`
- **Python execution convention:** `docs/development/Python_Execution_Conventions.md`
- **Public contract:** `"CherryMon"."main"."vw_Ticker_SmartMoney"`
- **Strategy column:** `TradeAction`
- **Validation owner:** `TestEngineer`
- **Execution target:** local CherryStock repository + local CherryMon DuckDB
- **Status:** `FUNCTIONALLY_VALIDATED`

## 1. Objective

Validate that the local CherryStock environment has correctly deployed and can safely consume the SmartMoneyStrategy V1 mapping:

```text
BUY / HOLD / SELL
```

from the existing SmartMoney public view without changing SmartMoneyScore calculation semantics or historical persistence.

This runbook incorporates the execution lessons found during the first local validation on 2026-09-12, especially Python import/collection behavior and direct-script path bootstrapping.

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

- sync the latest `main` branch safely;
- verify required SmartMoneyStrategy files exist;
- verify Python import/collection contract before functional tests;
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
- refactoring unrelated code;
- changing repository-wide Python packaging beyond the approved execution convention.

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
.github/instructions/python.instructions.md
.github/instructions/database.instructions.md
docs/development/Python_Execution_Conventions.md
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

The historical execution issue export from the first validation is not a canonical instruction source. Reusable lessons belong in the Python execution convention and this runbook.

---

# 5. Python execution contract for this runbook

All commands below are executed from repository root:

```text
C:\Github\CherryStock
```

Canonical rules:

```text
pytest
    → run with python -m pytest from repository root
    → pytest config exposes src for production imports

direct script
    → python scripts\x.py
    → script must bootstrap repository path itself
    → no manual developer-specific PYTHONPATH required

python -c / python -
    → run from repository root
    → repository root is available to src.* imports
```

Do NOT make the runbook pass by setting an undocumented path such as:

```powershell
$env:PYTHONPATH="C:\Github\CherryStock"
```

If a canonical direct script still needs manual `PYTHONPATH`, classify it as an execution-contract defect and apply one focused fix to the script/config instead.

---

# 6. Rule under validation

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

# 7. Phase 0 — Define the single validation objective

The local agent must write this before executing commands:

```text
Objective: validate local deployment and real-data contract of SmartMoneyStrategy V1 TradeAction without changing strategy rules.

In scope:
- Python import/collection contract
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

# 8. Phase 1 — Sync repository safely

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
Test-Path docs\development\Python_Execution_Conventions.md
Test-Path docs\backlog\requirements\REQ-0026-smart-money-strategy.md
Test-Path tests\test_smart_money_strategy.py
Test-Path src\DuckDB\sql\smart_money_v1_schema.sql
Test-Path src\DuckDB\sql\smart_money_v1_preflight.sql
Test-Path scripts\run_smart_money_preflight.py
```

### PASS

All commands return `True` for the expected files.

### BLOCKED

Any required file is missing after successful `git pull --ff-only`.

Do not invent a replacement file.

---

# 9. Phase 2 — Python compile and pytest collection sanity

First verify interpreter and compile the runnable scripts:

```powershell
python --version
python -m py_compile scripts\run_smart_money.py
python -m py_compile scripts\run_smart_money_preflight.py
```

Then verify pytest can collect both SmartMoney test modules before treating any assertion failure as a functional regression:

```powershell
python -m pytest tests\test_smart_money_strategy.py --collect-only -q
python -m pytest tests\test_smart_money_integration.py --collect-only -q
```

### PASS

- compile commands exit `0`;
- both pytest modules collect successfully;
- no `ModuleNotFoundError` / `ImportError` occurs during collection.

### Collection/import failure

A collection error is NOT automatically a SmartMoney functional regression.

Classify as:

```text
Verdict: FAIL
Category: Python import/execution contract
Action: FIX ONCE
```

Use the finite diagnostic in Section 10. Apply at most one focused correction and rerun only the failed collection command once.

If collection still fails with the same cause:

```text
Verdict: FAIL
Action: STOP
```

Do not continue to functional tests.

---

# 10. Import/collection diagnostic — finite path

If Phase 2 reports `ModuleNotFoundError`, `ImportError` or pytest collection failure:

```text
Step 1: Read the first relevant traceback and identify the unresolved module.
Step 2: Check docs/development/Python_Execution_Conventions.md.
Step 3: Compare with ONE known-good neighboring test/script of the same invocation type.
Step 4: Check whether the failure is test import style, pytest path config, or direct-script bootstrap.
Step 5: Apply ONE focused correction.
Step 6: Rerun the exact failed collection/command ONCE.
Step 7: PASS or STOP.
```

Do not repeatedly run equivalent `Select-String`, grep, `sys.path` inspection or the same failing command without new evidence.

For tests, current preferred repository-root form is:

```python
from src.calcEngine.smartMoneyScore import refresh_smart_money_score
from src.cherrystock.infrastructure.database.repositories.smart_money_repository import (
    SmartMoneyRepository,
)
```

Pytest path configuration is owned by `pyproject.toml`. Do not introduce a user-specific shell `PYTHONPATH` workaround as the permanent fix.

---

# 11. Phase 3 — Focused strategy unit test

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

If the assertion failure is caused by the current strategy change:

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

# 12. Phase 4 — Nearest SmartMoney integration regression

Run:

```powershell
python -m pytest tests\test_smart_money_integration.py -v
```

This is the nearest persistence/public-view regression boundary. It checks schema bootstrap, SmartMoney calculation persistence, public view readability and incremental/full convergence behavior on the synthetic DuckDB fixture.

### PASS

All integration tests pass.

### REGRESSION

Only classify `REGRESSION` when the module collected and executed successfully, and a previously valid SmartMoney persistence/incremental behavior now fails because of the current change.

On regression:

```text
Verdict: REGRESSION
Action: STOP
```

Do not broaden into unrelated SmartMoney refactoring.

---

# 13. Phase 5 — Deploy/recreate the local public view through the normal path

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

# 14. Phase 6 — Read-only SmartMoney preflight

Run directly from repository root:

```powershell
python scripts\run_smart_money_preflight.py
```

The script now owns its repository-path bootstrap. The command MUST NOT require a manual developer-specific `PYTHONPATH`.

If the command fails only because repository code cannot be imported, classify that as a direct-script execution-contract failure and follow Section 10 once. Do not workaround it by permanently setting a local absolute `PYTHONPATH`.

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

# 15. Phase 7 — Real local data drill-down

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

# 16. Phase 8 — Refresh generated DB metadata

After the local database view has been successfully recreated and validated, export generated metadata from repository root:

```powershell
python -c "from src.Ults import DuckLib; DuckLib.exportDuckDB_metadata()"
```

`python -c` from repository root has different import-path behavior from directly executing a file under `scripts/`. Do not use its success as proof that every `python scripts\x.py` command is correctly bootstrapped; direct scripts own their own path setup.

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

# 17. Phase 9 — Optional daily pipeline smoke

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

# 18. Acceptance criteria for local TestEngineer

Local validation is PASS only when all applicable criteria below pass:

1. repository sync is clean and safe;
2. both SmartMoney pytest modules collect without import error;
3. strategy unit test passes;
4. nearest SmartMoney integration test passes;
5. normal SmartMoney runner successfully recreates/deploys the view;
6. direct preflight runner works without manual developer-specific `PYTHONPATH`;
7. public view contains `TradeAction`;
8. `TradeAction` is never NULL;
9. `TradeAction` contains only `BUY`, `HOLD`, `SELL`;
10. quality gate maps every non-PASS row to `HOLD`;
11. PASS + `DISTRIBUTION` maps to `SELL`;
12. PASS + `ACCUMULATION/BREAKOUT/DEMAND_EXPANSION/SUPPLY_LOCK` maps to `BUY`;
13. all other PASS states map to `HOLD`;
14. `TradeActionMappingMismatch = 0` on the full local public view;
15. existing SmartMoney duplicate/range/factor-evidence contracts remain valid;
16. generated DB metadata exports successfully and includes `TradeAction`.

---

# 19. Failure handling and retry budget

## Working tree dirty

```text
Verdict: BLOCKED
Action: STOP
```

Do not auto-reset/stash user changes.

## Pytest collection/import failure

Do not classify it as regression before the test body executes.

```text
Verdict: FAIL
Category: Python import/execution contract
Action: FIX ONCE
```

Follow Section 10. One focused correction + one collection retry.

If still failing with the same cause:

```text
Verdict: FAIL
Action: STOP
```

## Focused strategy assertion fails

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

Only after successful collection/execution:

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

## Direct preflight script import fails

Treat missing repository bootstrap as a script defect, not an environment workaround opportunity.

Do not permanently solve it with:

```powershell
$env:PYTHONPATH="<developer-specific absolute path>"
```

Apply one focused script/bootstrap fix or STOP.

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
- this runbook defaults to one focused repair for the strategy/import execution change;
- no automatic second hypothesis;
- no unrelated cleanup/refactor;
- do not repeat equivalent grep/Select-String/sys.path probes after the import convention has been established.

---

# 20. Rollback boundary

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

# 21. Required local-agent result format

The local agent MUST finish with this exact evidence structure:

```text
SMART MONEY STRATEGY V1 — LOCAL VALIDATION

Objective:
Validate TradeAction BUY/HOLD/SELL on local CherryMon.

Repository:
Branch: main
HEAD: <sha>
Working tree before run: CLEAN | DIRTY

Python/import sanity:
Compile run_smart_money.py: PASS | FAIL
Compile run_smart_money_preflight.py: PASS | FAIL
Strategy test collection: PASS | FAIL
Integration test collection: PASS | FAIL
Manual PYTHONPATH required: NO | YES

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

# 22. Historical execution issue handling

Execution issues found during one validation run are evidence, not a new Source of Truth.

Reusable lessons must be promoted into:

```text
docs/development/Python_Execution_Conventions.md
.github/instructions/python.instructions.md
docs/runbook/SmartMoneyStrategy_V1.md
```

Non-obvious historical context that remains useful belongs under:

```text
docs/development/implementation-notes/**
```

Do not leave postmortem/issue-export documents under `tests/**` after their reusable rules have been incorporated. `tests/*.md` is reserved for finite test execution material.

---

# 23. After PASS — closure/revalidation handoff

REQ-0026 and SmartMoneyStrategy were functionally validated locally on 2026-09-12.

Future executions of this runbook are revalidation runs. They must return the evidence format above and stop after the terminal verdict.

Do not change strategy thresholds or mapping during revalidation.

---

# 24. STOP

After returning the terminal verdict and evidence, STOP.

Do not continue into OOS research, SmartMoneyScore calibration, R/S work, chart work or any other task without a new explicit request.
