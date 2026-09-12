# SmartMoney TradeActionConfidence V1 — Minimal Local Rollout

- **Requirement:** `REQ-0026`
- **Architecture:** `docs/architecture/SmartMoneyStrategy.md`
- **Public view:** `"CherryMon"."main"."vw_Ticker_SmartMoney"`
- **New field:** `TradeActionConfidenceScore`
- **Validation owner:** `TestEngineer`
- **Goal:** deploy the additive view field locally with minimum sufficient validation.

## 1. Scope

This runbook validates only the `TradeActionConfidenceScore` public-view extension.

In scope:

- sync latest `main`;
- recreate the Smart Money public view through the normal runner;
- verify the new field and four critical invariants on the local CherryMon database;
- refresh generated DB metadata;
- return one finite verdict.

Out of scope:

- full SmartMoney historical initload;
- SmartMoneyScore recalibration;
- full integration/regression suite;
- full `smart_money_v1_preflight.sql` execution;
- full `run.py` daily pipeline;
- OOS/backtest/effectiveness research;
- changing BUY/HOLD/SELL or confidence formulas.

GitHub CI owns formula/unit regression for this change. Local validation owns deployment against the actual local CherryMon database.

---

## 2. PASS contract

`TradeActionConfidenceScore` must satisfy all of these:

```text
1. field exists and public view returns rows
2. 0 <= TradeActionConfidenceScore <= 100
3. TradeActionConfidenceScore <= ConfidenceScore
4. DataQualityStatus != PASS -> TradeActionConfidenceScore = 0
5. TradeAction remains BUY / HOLD / SELL only
```

The field is derived by the public view and is not persisted into `cal_smart_money_ticker_score`.

---

## 3. Step 1 — Safe sync

Run from repository root:

```powershell
git status --short
```

If the working tree contains unexpected local changes:

```text
Verdict: BLOCKED
Action: STOP
```

Do not reset, stash or overwrite user work automatically.

If clean:

```powershell
git fetch origin
git checkout main
git pull --ff-only origin main
git log -1 --oneline
```

---

## 4. Step 2 — Recreate the view through the normal runner

Run only a one-day bounded refresh; schema execution recreates the view before the incremental calculation:

```powershell
python scripts\run_smart_money.py --days 1
```

PASS when the runner completes successfully.

Do not run historical initload for this extension. `TradeActionConfidenceScore` is a derived view column, so existing historical SmartMoney rows receive it immediately after `CREATE OR REPLACE VIEW`.

If the runner fails:

```text
Verdict: FAIL | BLOCKED
Action: STOP
```

Capture the exact exception. Do not bypass the repository runner with ad-hoc DuckDB writes.

---

## 5. Step 3 — One focused read-only validation

Run exactly from repository root:

```powershell
@'
from src.Ults.DuckLib import DuckDBManager

with DuckDBManager(read_only=True) as con:
    result = con.sql('''
        SELECT
            COUNT(*) AS Rows,
            MAX(Date) AS LatestDate,
            SUM(CASE
                WHEN TradeActionConfidenceScore IS NULL
                  OR TradeActionConfidenceScore < 0
                  OR TradeActionConfidenceScore > 100
                THEN 1 ELSE 0
            END) AS InvalidRange,
            SUM(CASE
                WHEN TradeActionConfidenceScore > ConfidenceScore + 0.000001
                THEN 1 ELSE 0
            END) AS AboveUpstreamConfidence,
            SUM(CASE
                WHEN DataQualityStatus <> 'PASS'
                 AND ABS(TradeActionConfidenceScore) > 0.000001
                THEN 1 ELSE 0
            END) AS NonPassConfidenceMismatch,
            SUM(CASE
                WHEN TradeAction IS NULL
                  OR TradeAction NOT IN ('BUY','HOLD','SELL')
                THEN 1 ELSE 0
            END) AS InvalidTradeAction
        FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
    ''').df()
    print(result.to_string(index=False))

    print("\n=== Latest action-confidence sample ===")
    sample = con.sql('''
        WITH latest AS (
            SELECT MAX(Date) AS Date
            FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
        )
        SELECT
            Ticker,
            Date,
            MarketState,
            TradeAction,
            ConfidenceScore,
            TradeActionConfidenceScore
        FROM "CherryMon"."main"."vw_Ticker_SmartMoney" v
        INNER JOIN latest l ON l.Date = v.Date
        ORDER BY TradeActionConfidenceScore DESC, Ticker
        LIMIT 20
    ''').df()
    print(sample.to_string(index=False))
'@ | python -
```

### PASS

Required result:

```text
Rows > 0
InvalidRange = 0
AboveUpstreamConfidence = 0
NonPassConfidenceMismatch = 0
InvalidTradeAction = 0
```

The latest-date sample is observational only. Do not fail because BUY, HOLD or SELL is absent on the latest trading date.

### FAIL

If any violation count is non-zero:

```text
Verdict: FAIL
Action: STOP
```

Do not continue into unrelated diagnosis in this runbook.

---

## 6. Step 4 — Refresh generated metadata

Only after Step 3 passes:

```powershell
python -c "from src.Ults import DuckLib; DuckLib.exportDuckDB_metadata()"
Select-String -Path docs\reference\DB_Metadata.md -Pattern "TradeActionConfidenceScore"
```

PASS when generated metadata contains the new field.

Do not hand-edit `docs/reference/DB_Metadata.md`.

---

## 7. Optional focused pytest — only when needed

Do **not** run pytest by default when the pulled GitHub commit already has green SmartMoney CI and no local strategy code was modified.

Run this only when:

- CI is not green/available; or
- local strategy/schema/test code was modified after pull.

```powershell
python -m pytest tests\test_smart_money_strategy.py -q
```

Do not escalate automatically to `tests/test_smart_money_integration.py` or the repository-wide suite.

---

## 8. Required result

Return only:

```text
SMART MONEY ACTION CONFIDENCE — MINIMAL LOCAL VALIDATION

HEAD: <sha>
View deployment: PASS | FAIL | BLOCKED
Rows: <count>
LatestDate: <date>
InvalidRange: <count>
AboveUpstreamConfidence: <count>
NonPassConfidenceMismatch: <count>
InvalidTradeAction: <count>
Metadata TradeActionConfidenceScore: YES | NO
Optional pytest: NOT_RUN | PASS | FAIL

Verdict: PASS | FAIL | BLOCKED
Action: KEEP | STOP
```

PASS requires:

```text
view deployment PASS
all four violation counts = 0
metadata contains TradeActionConfidenceScore
```

After the terminal verdict, STOP.

---

## 9. Deliberately skipped validation

For this additive derived-view field, the following are intentionally not part of the default local gate:

```text
full historical initload
full SmartMoney preflight
SmartMoney integration regression
full daily pipeline
full test suite
OOS/backtest evaluation
```

Those are only required when their own code/contracts change or separate evidence indicates a regression beyond this view extension.
