# SmartMoneyStrategy V1 — Local Deployment & Validation Runbook

- **Requirement:** `REQ-0026`
- **Architecture:** `docs/architecture/SmartMoneyStrategy.md`
- **Upstream model:** `docs/architecture/SmartMoneyScore.md`
- **Python execution convention:** `docs/development/Python_Execution_Conventions.md`
- **Public contract:** `"CherryMon"."main"."vw_Ticker_SmartMoney"`
- **Strategy outputs:** `TradeAction`, `TradeActionConfidenceScore`
- **Validation owner:** `TestEngineer`
- **Execution target:** local CherryStock repository + local CherryMon DuckDB
- **Status before this validation:** `IMPLEMENTED_PENDING_VALIDATION`

## 1. Objective

Validate local deployment of SmartMoneyStrategy V1 with both public strategy outputs:

```text
TradeAction                 = BUY / HOLD / SELL
TradeActionConfidenceScore  = 0..100
```

without changing SmartMoneyScore persistence or historical factor/score calculations.

The local agent MUST finish with exactly one verdict:

```text
PASS
FAIL
BLOCKED
REGRESSION
```

and one action:

```text
KEEP
FIX ONCE
REVERT
STOP
```

After a terminal verdict, STOP.

---

# 2. Scope

## In scope

- safely sync latest `main`;
- verify Python import/collection contract;
- run focused strategy unit test;
- run nearest SmartMoney integration regression;
- recreate local Smart Money public view through the normal runner;
- validate `TradeAction` mapping;
- validate `TradeActionConfidenceScore` range, upstream-confidence cap and quality gate;
- run read-only preflight;
- inspect real local action/confidence distribution;
- export generated DB metadata;
- produce finite TestEngineer evidence.

## Out of scope

- changing BUY/HOLD/SELL state mapping;
- changing the documented 60/40 confidence blend during validation;
- SmartMoney factor/state threshold recalibration;
- predictive win-probability research;
- position sizing / stop loss / take profit / order execution;
- full SmartMoney historical initload unless separate evidence proves persistence invalid;
- unrelated refactor.

---

# 3. Persistence boundary

Neither strategy field is persisted in:

```text
cal_smart_money_ticker_score
cal_smart_money_factor_values
```

Both are derived by:

```text
vw_Ticker_SmartMoney
```

Therefore recreating the view exposes the new field for already-persisted historical rows.

Do NOT run a full historical SmartMoney initload merely to add `TradeActionConfidenceScore`.

---

# 4. Mandatory context

Read only the smallest relevant set:

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

---

# 5. Python execution contract

Run all commands from repository root:

```text
C:\Github\CherryStock
```

Rules:

```text
pytest
    → python -m pytest ...
    → use --collect-only before classifying an integration failure as behavioral regression

direct script
    → python scripts\x.py
    → script must bootstrap repository path itself
    → do not require developer-specific PYTHONPATH

python -c / python -
    → execute from repository root
```

Do not make a canonical command pass by adding an undocumented absolute-path `PYTHONPATH`.

---

# 6. Strategy contracts under validation

## 6.1 TradeAction

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
END
```

## 6.2 TradeActionConfidenceScore

Hard invariants:

```text
non-NULL
0 <= TradeActionConfidenceScore <= 100
TradeActionConfidenceScore <= ConfidenceScore
DataQualityStatus != PASS → TradeActionConfidenceScore = 0
```

PASS rows use:

```text
CandidateActionConfidence
    = 0.60 * ConfidenceScore
    + 0.40 * StateEvidenceStrength

TradeActionConfidenceScore
    = min(ConfidenceScore, CandidateActionConfidence)
```

StateEvidenceStrength:

| MarketState | Evidence strength |
|---|---|
| ACCUMULATION | min(AccumulationScore, AccumulationMemoryScore) |
| BREAKOUT | min(FreshFlowScore, RelativeLiquidityScore, RelativeStrengthScore) |
| DEMAND_EXPANSION | min(RelativeLiquidityScore, LiquidityAccelerationScore, RelativeStrengthScore) |
| SUPPLY_LOCK | min(SupplyLockScore, AccumulationMemoryScore) |
| DISTRIBUTION | DistributionScore |
| MARKUP | min(TrendScore, RelativeStrengthScore) |
| SELLING_CLIMAX | min(DistributionScore, RelativeLiquidityScore) |
| LIQUIDITY_DRYUP | ConfidenceScore |
| NEUTRAL | ConfidenceScore |

For states with explicit required public factors, missing required factor evidence must yield action confidence `0`.

Do not interpret this score as future-return probability.

---

# 7. Phase 0 — Define objective

Before execution write:

```text
Objective: validate local TradeAction and TradeActionConfidenceScore public contracts without changing strategy rules or SmartMoney persistence.
```

Stop condition:

```text
PASS / FAIL / BLOCKED / REGRESSION
+
KEEP / FIX ONCE / REVERT / STOP
```

---

# 8. Phase 1 — Safe repository sync

```powershell
git status --short
```

If non-empty, do not reset/stash/discard automatically:

```text
Verdict: BLOCKED
Action: STOP
```

If clean:

```powershell
git fetch origin
git checkout main
git pull --ff-only origin main
git log -1 --oneline
```

Verify:

```powershell
Test-Path docs\architecture\SmartMoneyStrategy.md
Test-Path docs\runbook\SmartMoneyStrategy_V1.md
Test-Path docs\backlog\requirements\REQ-0026-smart-money-strategy.md
Test-Path tests\test_smart_money_strategy.py
Test-Path tests\test_smart_money_integration.py
Test-Path src\DuckDB\sql\smart_money_v1_schema.sql
Test-Path src\DuckDB\sql\smart_money_v1_preflight.sql
```

All must be `True`.

---

# 9. Phase 2 — Compile and collection sanity

```powershell
python --version
python -m py_compile scripts\run_smart_money.py
python -m py_compile scripts\run_smart_money_preflight.py
python -m pytest tests\test_smart_money_strategy.py tests\test_smart_money_integration.py --collect-only -q
```

A collection/import failure is an execution-contract FAIL, not automatically a strategy regression.

Diagnostic path:

```text
1. Read first relevant traceback.
2. Identify unresolved module/import.
3. Compare with docs/development/Python_Execution_Conventions.md and one known-good neighbor.
4. Apply one focused correction.
5. Retest once.
6. Same failure without new evidence → STOP.
```

---

# 10. Phase 3 — Focused strategy test

```powershell
python -m pytest tests\test_smart_money_strategy.py -v
```

The test must prove at minimum:

```text
PASS bullish states → BUY
PASS DISTRIBUTION → SELL
PASS management/neutral states → HOLD
WARNING/INVALID → HOLD
WARNING/INVALID action confidence → 0
confidence values are deterministic
0 <= action confidence <= 100
action confidence <= upstream ConfidenceScore
```

One focused repair is allowed if the failure belongs directly to this implementation.

If the same focused behavior still fails after repair:

```text
Verdict: FAIL
Action: STOP
```

---

# 11. Phase 4 — Integration regression

First collection was already validated in Phase 2.

Run:

```powershell
python -m pytest tests\test_smart_money_integration.py -v
```

This checks SmartMoney persistence/public-view/incremental behavior on synthetic DuckDB data.

If existing behavior breaks because of this public-view extension:

```text
Verdict: REGRESSION
Action: STOP
```

Do not broaden into unrelated SmartMoney refactoring.

---

# 12. Phase 5 — Recreate local public view

Use the normal operational path:

```powershell
python scripts\run_smart_money.py --days 15
```

Expected flow:

```text
DuckDBUnitOfWork
→ execute smart_money_v1_schema.sql
→ CREATE OR REPLACE vw_Ticker_SmartMoney
→ bounded incremental SmartMoney refresh
→ COMMIT
```

Expected summary includes:

```text
status = OK
```

and normal score/factor upsert counts appropriate to local data.

If the runner fails, capture exact command/exception/HEAD/config context and STOP. Do not bypass project transaction policy with ad-hoc direct writes.

---

# 13. Phase 6 — Read-only preflight

```powershell
python scripts\run_smart_money_preflight.py
```

Required strategy checks:

```text
InvalidTradeAction = 0
TradeActionMappingMismatch = 0
InvalidTradeActionConfidenceScore = 0
TradeActionConfidenceAboveEvidence = 0
NonPassTradeActionConfidenceMismatch = 0
```

Also preserve upstream integrity:

```text
DuplicateScoreKeys = 0
DuplicateFactorKeys = 0
ScoreRowsWithoutFactors = 0
score/confidence/coverage ranges valid
supported MarketState values only
```

Any non-zero strategy confidence violation is FAIL.

---

# 14. Phase 7 — Real local data drill-down

Run from repository root:

```powershell
@'
from src.Ults.DuckLib import DuckDBManager

with DuckDBManager(read_only=True) as con:
    latest = con.sql('''
        SELECT MAX(Date) AS LatestDate
        FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
    ''').df()
    print("=== Latest SmartMoney date ===")
    print(latest.to_string(index=False))

    distribution = con.sql('''
        WITH latest AS (
            SELECT MAX(Date) AS Date
            FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
        )
        SELECT
            v.TradeAction,
            v.MarketState,
            v.DataQualityStatus,
            COUNT(*) AS Rows,
            ROUND(MIN(v.TradeActionConfidenceScore), 2) AS MinActionConfidence,
            ROUND(AVG(v.TradeActionConfidenceScore), 2) AS AvgActionConfidence,
            ROUND(MAX(v.TradeActionConfidenceScore), 2) AS MaxActionConfidence
        FROM "CherryMon"."main"."vw_Ticker_SmartMoney" AS v
        INNER JOIN latest AS d ON d.Date = v.Date
        GROUP BY v.TradeAction, v.MarketState, v.DataQualityStatus
        ORDER BY v.TradeAction, Rows DESC, v.MarketState
    ''').df()
    print("\n=== Latest action/state/confidence distribution ===")
    print(distribution.to_string(index=False))

    violations = con.sql('''
        SELECT
            SUM(CASE
                WHEN TradeAction IS NULL
                  OR TradeAction NOT IN ('BUY','HOLD','SELL')
                THEN 1 ELSE 0
            END) AS InvalidTradeAction,
            SUM(CASE
                WHEN TradeActionConfidenceScore IS NULL
                  OR TradeActionConfidenceScore < 0
                  OR TradeActionConfidenceScore > 100
                THEN 1 ELSE 0
            END) AS InvalidTradeActionConfidenceScore,
            SUM(CASE
                WHEN TradeActionConfidenceScore > ConfidenceScore + 0.000001
                THEN 1 ELSE 0
            END) AS TradeActionConfidenceAboveEvidence,
            SUM(CASE
                WHEN DataQualityStatus <> 'PASS'
                 AND ABS(TradeActionConfidenceScore) > 0.000001
                THEN 1 ELSE 0
            END) AS NonPassTradeActionConfidenceMismatch
        FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
    ''').df()
    print("\n=== Strategy confidence violations ===")
    print(violations.to_string(index=False))

    sample = con.sql('''
        SELECT
            Ticker,
            Date,
            SmartMoneyScore,
            ConfidenceScore,
            MarketState,
            DataQualityStatus,
            TradeAction,
            TradeActionConfidenceScore
        FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
        WHERE Ticker IN ('MWG','FPT','HPG')
        ORDER BY Date DESC, Ticker
        LIMIT 30
    ''').df()
    print("\n=== Recent sample ===")
    print(sample.to_string(index=False))
'@ | python -
```

PASS requires all four displayed violation counts = `0`.

The latest trading date does not need to contain all BUY/HOLD/SELL labels.

---

# 15. Phase 8 — Metadata refresh

Only after local schema/view deployment and validation succeeds:

```powershell
python -c "from src.Ults import DuckLib; DuckLib.exportDuckDB_metadata()"
```

Confirm:

```powershell
Select-String -Path docs\reference\DB_Metadata.md -Pattern "vw_Ticker_SmartMoney"
Select-String -Path docs\reference\DB_Metadata.md -Pattern "TradeAction"
Select-String -Path docs\reference\DB_Metadata.md -Pattern "TradeActionConfidenceScore"
```

`docs/reference/DB_Metadata.md` is generated evidence. Never hand-edit it to make this validation pass.

---

# 16. Optional daily pipeline smoke

Not required by default because this is an additive derived-view change.

Run only if explicitly requested or evidence suggests the daily orchestration path differs:

```powershell
python run.py
```

Do not run the full daily pipeline merely for extra confidence.

---

# 17. Acceptance criteria

Local PASS requires:

1. repository sync clean/safe;
2. compile and pytest collection pass;
3. focused strategy test pass;
4. integration regression pass;
5. normal SmartMoney runner recreates public view;
6. `TradeAction` remains non-NULL BUY/HOLD/SELL only;
7. action mapping remains exact;
8. `TradeActionConfidenceScore` is non-NULL and `0..100`;
9. action confidence never exceeds upstream `ConfidenceScore`;
10. non-PASS rows have action confidence `0`;
11. focused tests prove deterministic formula values for representative states;
12. upstream duplicate/range/factor-evidence contracts remain valid;
13. metadata export includes `TradeActionConfidenceScore`.

---

# 18. Failure handling

## Dirty working tree

```text
Verdict: BLOCKED
Action: STOP
```

## Collection/import failure

One focused import/bootstrap fix, then one retest. Do not repeat unchanged grep/search/command loops.

## Focused strategy formula failure

```text
Action: FIX ONCE
```

Retest only the focused strategy test. Same defect after repair → FAIL/STOP.

## Integration behavior regression

```text
Verdict: REGRESSION
Action: STOP
```

## Local DB runner failure

Capture command, exception, HEAD and DB path/config context. STOP. Do not switch to an ad-hoc writer.

## Preflight confidence violation

Any of:

```text
InvalidTradeActionConfidenceScore > 0
TradeActionConfidenceAboveEvidence > 0
NonPassTradeActionConfidenceMismatch > 0
```

means:

```text
Verdict: FAIL
Action: STOP
```

---

# 19. Rollback boundary

The change is additive at the public-view layer.

If validation fails:

1. stop rollout;
2. do not delete SmartMoney score/factor persistence;
3. do not run full historical initload automatically;
4. preserve failing evidence;
5. if rollback is approved, revert the strategy view commit(s);
6. recreate the view through the normal SmartMoney runner;
7. rerun only the focused rollback validation.

---

# 20. Required local-agent result format

```text
SMART MONEY STRATEGY V1 — LOCAL VALIDATION

Repository:
Branch: main
HEAD: <sha>
Working tree before run: CLEAN | DIRTY

Collection:
Result: PASS | FAIL

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

Preflight:
Command: python scripts\run_smart_money_preflight.py
Result: PASS | FAIL
InvalidTradeAction: <value>
TradeActionMappingMismatch: <value>
InvalidTradeActionConfidenceScore: <value>
TradeActionConfidenceAboveEvidence: <value>
NonPassTradeActionConfidenceMismatch: <value>
DuplicateScoreKeys: <value>
DuplicateFactorKeys: <value>
ScoreRowsWithoutFactors: <value>

Real-data verification:
Latest SmartMoney date: <date>
Latest BUY rows: <count or not present>
Latest HOLD rows: <count or not present>
Latest SELL rows: <count or not present>
BUY avg action confidence: <value or not present>
HOLD avg action confidence: <value or not present>
SELL avg action confidence: <value or not present>

Metadata export:
Result: PASS | FAIL
TradeAction present: YES | NO
TradeActionConfidenceScore present: YES | NO

Verdict: PASS | FAIL | BLOCKED | REGRESSION
Action: KEEP | FIX ONCE | REVERT | STOP
```

Do not claim local PASS from GitHub CI alone.

---

# 21. Closure

After real local TestEngineer PASS, evidence may support returning REQ-0026 and SmartMoneyStrategy to:

```text
FUNCTIONALLY_VALIDATED
```

Do not alter strategy mapping or confidence formula during closure.

After terminal verdict, STOP.
