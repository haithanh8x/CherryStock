# Runbook — REQ-0033 Active Ticker ZigZag + Price Movement Initial Load

- Requirement: REQ-0033
- Architecture: docs/architecture/Active_Ticker_Movement_Initload.md
- Universe SSOT: "CherryMon"."main"."vw_Ticker_Active"
- ZigZag config: ZZ_D_5_MVP
- Price Movement config: PM_ZZ_D_V2
- Final validation owner: TestEngineer

## 1. Objective

Initial-load the validated movement chain for the complete active ticker universe:

~~~text
vw_Ticker_Active
    ↓
ZigZag
    ↓
Price Movement
    ↓
MovementContext (derived automatically)
~~~

This runbook does not add the workflow to run.py.

## 2. Phase 0 — Sync Branch and Protect Unrelated Local Changes

~~~powershell
cd C:\Github\CherryStock
git status --short
git fetch origin
git switch feature/active-ticker-movement-initload
git pull origin feature/active-ticker-movement-initload
~~~

If unrelated local changes exist, keep them untouched and do not include them in validation commits.

## 3. Phase 1 — Focused Tests

Run:

~~~powershell
python -m pytest tests\test_active_ticker_movement_initload.py tests\test_zigzag_engine.py tests\test_price_movement_zigzag.py tests\test_movement_context_v1.py -v
~~~

Expected:

- bulk orchestration tests PASS;
- existing ZigZag tests PASS;
- existing Price Movement tests PASS;
- existing MovementContext tests PASS.

If any selected test fails, STOP and report the first objective failure.

## 4. Phase 2 — Universe Prerequisite

Verify the exact user-requested universe:

~~~sql
SELECT
    COUNT(DISTINCT UPPER(TRIM(CAST(Ticker AS VARCHAR)))) AS ActiveTickerCount
FROM "CherryMon"."main"."vw_Ticker_Active"
WHERE Ticker IS NOT NULL
  AND TRIM(CAST(Ticker AS VARCHAR)) <> '';

SELECT *
FROM "CherryMon"."main"."vw_Ticker_Active"
ORDER BY Ticker
LIMIT 20;
~~~

Then verify OHLC coverage:

~~~sql
WITH active AS (
    SELECT DISTINCT UPPER(TRIM(CAST(Ticker AS VARCHAR))) AS Ticker
    FROM "CherryMon"."main"."vw_Ticker_Active"
    WHERE Ticker IS NOT NULL
      AND TRIM(CAST(Ticker AS VARCHAR)) <> ''
)
SELECT a.Ticker
FROM active a
LEFT JOIN "CherryMon"."main"."vw_Ticker_OHLC_D" o
    ON o.Ticker = a.Ticker
GROUP BY a.Ticker
HAVING COUNT(o.Date) = 0
ORDER BY a.Ticker;
~~~

Expected for a clean full rollout: zero rows.

If active tickers lack OHLC, record them before continuing. The final validator will treat them as failures.

## 5. Phase 3 — Small Canary

Run MWG + one additional active ticker with normal history:

~~~powershell
python scripts\initload\init_reload_zigzag_price_movement_active.py --ticker MWG --ticker FPT
~~~

Expected:

- both ZigZag stages OK;
- Price Movement is OK when confirmed swings exist;
- no hard failures.

If FPT is not in the active universe locally, choose another ticker shown by Phase 2. Do not bypass the active-universe check.

## 6. Phase 4 — Deterministic 20-Ticker Canary

~~~powershell
python scripts\initload\init_reload_zigzag_price_movement_active.py --limit 20
~~~

Expected:

~~~text
failure_count: 0
~~~

A ticker may legitimately show PriceMovementStatus = SKIPPED_NO_CONFIRMED_SWING when ZigZag
has no confirmed swing yet.

Any FAILED* status must be investigated before full rollout.

## 7. Phase 5 — Full Active Universe Initial Load

Create the canonical evidence directory:

~~~powershell
$evidence = "docs\reference\data\price_movement\active"
~~~

Run:

~~~powershell
python scripts\initload\init_reload_zigzag_price_movement_active.py --evidence-dir $evidence
~~~

Default behavior:

1. read all tickers from vw_Ticker_Active;
2. run ZigZag for all selected tickers;
3. commit/rollback each ticker independently;
4. run Price Movement only after successful ZigZag;
5. clear stale Price Movement for zero-swing tickers;
6. continue across failures;
7. exit non-zero if hard failures exist.

Expected aggregate:

~~~text
active_ticker_count: <N>
zigzag_ok: <N>
zigzag_failed: 0
price_movement_failed: 0
failure_count: 0
~~~

price_movement_skipped_no_confirmed_swing may be greater than zero.

## 8. Phase 6 — Full Structural Validator

Run:

~~~powershell
python scripts\validate_movement_active.py --evidence-dir $evidence
~~~

PASS requires:

~~~text
validation_failures: 0
ACTIVE TICKER MOVEMENT VALIDATION: PASS
~~~

Validator gates:

- active universe is non-empty;
- every active ticker has OHLC;
- every active ticker with OHLC has exactly one ZigZag current row;
- ZigZag swing count equals Price Movement swing count per eligible ticker;
- every ticker with ZigZag swings has exactly one Movement Profile;
- zero-swing tickers have no stale Price Movement rows.

## 9. Phase 7 — Direct Coverage SQL

### ZigZag current coverage

~~~sql
WITH active AS (
    SELECT DISTINCT UPPER(TRIM(CAST(Ticker AS VARCHAR))) AS Ticker
    FROM "CherryMon"."main"."vw_Ticker_Active"
)
SELECT
    COUNT(*) AS ActiveTickers,
    COUNT(z.Ticker) AS ZigZagCurrentCovered
FROM active a
LEFT JOIN (
    SELECT DISTINCT Ticker
    FROM "CherryMon"."main"."vw_Ticker_ZigZag_Current"
    WHERE ConfigCode = 'ZZ_D_5_MVP'
) z
ON z.Ticker = a.Ticker;
~~~

### ZigZag ↔ Price Movement parity

~~~sql
WITH zz AS (
    SELECT Ticker, COUNT(*) AS ZigZagSwings
    FROM "CherryMon"."main"."vw_Ticker_ZigZag_Swings"
    WHERE ConfigCode = 'ZZ_D_5_MVP'
    GROUP BY Ticker
),
pm AS (
    SELECT Ticker, COUNT(*) AS PriceMovementSwings
    FROM "CherryMon"."main"."vw_Ticker_Price_Movement_Swings"
    WHERE PriceMovementConfigCode = 'PM_ZZ_D_V2'
      AND ZigZagConfigCode = 'ZZ_D_5_MVP'
    GROUP BY Ticker
)
SELECT
    zz.Ticker,
    zz.ZigZagSwings,
    COALESCE(pm.PriceMovementSwings, 0) AS PriceMovementSwings
FROM zz
LEFT JOIN pm USING (Ticker)
WHERE zz.ZigZagSwings <> COALESCE(pm.PriceMovementSwings, 0)
ORDER BY zz.Ticker;
~~~

Expected: zero rows.

### Movement Profile coverage

~~~sql
SELECT
    COUNT(DISTINCT Ticker) AS ProfileTickerCount,
    COUNT(*) AS ProfileRows
FROM "CherryMon"."main"."vw_Ticker_Movement_Profile"
WHERE PriceMovementConfigCode = 'PM_ZZ_D_V2'
  AND ZigZagConfigCode = 'ZZ_D_5_MVP';
~~~

For this config there should be one row per eligible ticker.

## 10. Phase 8 — MovementContext Downstream Check

No MovementContext backfill is needed.

~~~sql
SELECT
    COUNT(DISTINCT Ticker) AS ContextTickerCount,
    COUNT(*) AS ContextRows
FROM "CherryMon"."main"."vw_Ticker_Movement_Context"
WHERE PriceMovementConfigCode = 'PM_ZZ_D_V2'
  AND ZigZagConfigCode = 'ZZ_D_5_MVP';
~~~

Spot-check:

~~~sql
SELECT
    Ticker,
    ContextStatus,
    TrendRegime,
    TrendQuality,
    LastSwingState,
    CurrentLegDirection,
    CurrentMoveSpeedState
FROM "CherryMon"."main"."vw_Ticker_Movement_Context"
WHERE PriceMovementConfigCode = 'PM_ZZ_D_V2'
ORDER BY Ticker
LIMIT 50;
~~~

The context view should reflect newly created profiles dynamically.

## 11. Phase 9 — Idempotency

Capture aggregate counts:

~~~sql
SELECT COUNT(*) FROM "CherryMon"."main"."cal_zigzag_pivot";
SELECT COUNT(*) FROM "CherryMon"."main"."cal_zigzag_current_leg";
SELECT COUNT(*) FROM "CherryMon"."main"."cal_price_movement_swing";
SELECT COUNT(*) FROM "CherryMon"."main"."cal_price_movement_profile";
~~~

Run the full initial load again unchanged:

~~~powershell
python scripts\initload\init_reload_zigzag_price_movement_active.py
python scripts\validate_movement_active.py
~~~

Expected:

- no duplicates;
- same structural coverage;
- validator PASS;
- business row counts remain stable for unchanged source data.

CalculatedAt timestamps may change and are not business-value idempotency failures.

## 12. Phase 10 — Daily Pipeline Regression

~~~powershell
python -m pytest tests\test_sync_write_pipeline_service.py -v
~~~

Expected: PASS.

Confirm no REQ-0033 integration exists in run.py.

## 13. Phase 11 — Evidence Review and Commit

Generated files:

~~~text
docs/reference/data/price_movement/active/
  Active_Ticker_Movement_Initload_Detail.csv
  Active_Ticker_Movement_Initload_Summary.json
  Active_Ticker_Movement_Validation_Coverage.csv
  Active_Ticker_Movement_Validation_Summary.json
~~~

Review failures/skips before commit.

Only after full PASS:

~~~powershell
git add docs\reference\data\price_movement\active
git commit -m "validation: add active ticker movement initial-load evidence"
git push origin feature/active-ticker-movement-initload
~~~

Do not commit unrelated local files or database files.

## 14. TestEngineer Verdict Format

~~~text
TEST VERDICT
Objective: REQ-0033 Active Ticker ZigZag + Price Movement Initial Load
Validation depth: FULL-UNIVERSE INTEGRATION VALIDATION

Focused tests:
PASS | FAIL | BLOCKED

Universe/OHLC prerequisite:
PASS | FAIL | BLOCKED

Canary:
PASS | FAIL | BLOCKED

Full ZigZag load:
PASS | FAIL | BLOCKED

Full Price Movement load:
PASS | FAIL | BLOCKED

Structural validator:
PASS | FAIL | BLOCKED

MovementContext downstream:
PASS | FAIL | BLOCKED

Idempotency:
PASS | FAIL | BLOCKED

Daily pipeline regression:
PASS | FAIL | BLOCKED

Verdict:
PASS | FAIL | BLOCKED | REGRESSION

Action:
KEEP | FIX_ONCE | REVERT | STOP

Evidence:
- active_ticker_count=<N>
- zigzag_ok=<N>
- price_movement_ok=<N>
- skipped_no_confirmed_swing=<N>
- validation_failures=<N>

Residual risk:
- fixed 5% ZigZag remains the active baseline; volatility-aware promotion is separate
~~~

## 15. STOP Rule

On full PASS:

~~~text
Verdict: PASS
Action: KEEP
STOP
~~~

Do not merge a failed full-universe rollout and do not add it to run.py as part of REQ-0033.


## 16. Validation Closure — 2026-09-22

~~~text
Focused tests:              PASS (24/24)
Universe/OHLC prerequisite: PASS (349/349)
Canary MWG+FPT:             PASS (2/2)
Canary first 20:            PASS (20/20)
Full ZigZag load:           PASS (349/349)
Full Price Movement load:   PASS (349/349)
Structural validator:       PASS (validation_failures=0)
MovementContext downstream: PASS (349/349)
Idempotency:                PASS
Daily pipeline regression:  PASS (3/3)
run.py unchanged:           PASS

Verdict: PASS
Action: KEEP
~~~

Stable business row counts after unchanged rerun:

~~~text
cal_zigzag_pivot              154795
cal_zigzag_current_leg           349
cal_price_movement_swing      154446
cal_price_movement_profile       349
~~~

Validation evidence commit:

~~~text
7e872c1b5b51834e8cec8f847bf6658fa03e9167
~~~

REQ-0033 is closed. Daily/incremental production integration belongs to a new requirement.
