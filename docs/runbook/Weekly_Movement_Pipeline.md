# Runbook — REQ-0036 Weekly Movement Pipeline

> This runbook is intentionally published on `main` so a local validation agent can pull the operational instructions before switching to the implementation branch.

- Requirement: REQ-0036
- Architecture: docs/architecture/Weekly_Movement_Pipeline.md
- ADR: ADR-020
- Implementation branch: feature/weekly-movement-pipeline
- Validation owner: TestEngineer

## 1. Objective

Validate the transition:

~~~text
BEFORE
run.py → core daily → Movement (~60 minutes)

AFTER
run.py → core daily only

runWeekly.py
→ full-universe ZigZag + Price Movement
→ MovementContext freshness
~~~

## 2. Phase 0 — Sync Implementation Branch

The runbook itself is available from `main`, but REQ-0036 code is still isolated on the feature branch until validation passes.

~~~powershell
cd C:\Github\CherryStock
git status --short
git fetch origin
git switch feature/weekly-movement-pipeline
git pull origin feature/weekly-movement-pipeline
~~~

Preserve unrelated local changes.

## 3. Phase 1 — Compile + Focused Tests

~~~powershell
python -m compileall run.py runWeekly.py src\cherrystock\application\services\movement_weekly_pipeline.py scripts\validate_weekly_movement.py

python -m pytest tests\test_movement_weekly_pipeline.py tests\test_run_daily_movement_integration.py tests\test_movement_context_v1.py tests\test_active_ticker_movement_initload.py tests\test_zigzag_engine.py tests\test_price_movement_zigzag.py tests\test_sync_write_pipeline_service.py -v
~~~

PASS requires all selected tests PASS.

## 4. Phase 2 — Apply Additive MovementContext View Update

~~~powershell
python scripts\initload\init_movement_context_v1.py
~~~

This recreates the derived public view with additive freshness fields:

~~~text
LatestOHLCDate
MovementAgeTradingDays
MovementFreshnessStatus
~~~

No historical backfill is required.

## 5. Phase 3 — Confirm Daily Runner Is Movement-Free

~~~powershell
python -m pytest tests\test_run_daily_movement_integration.py -v
~~~

Expected:

~~~text
run.py does not invoke Movement
runWeekly.py owns full-universe Movement
~~~

Run the normal daily entry point when safe:

~~~powershell
python run.py
~~~

There should be no:

~~~text
[daily] ▶ Incremental ZigZag + Price Movement
~~~

Daily should end after core pipeline + metadata export.

## 6. Phase 4 — Weekly Canary

~~~powershell
python scripts\initload\init_reload_zigzag_price_movement_active.py --ticker MWG --ticker FPT
python scripts\validate_movement_active.py
~~~

Expected: PASS.

## 7. Phase 5 — Full Weekly Run

~~~powershell
python runWeekly.py
~~~

Expected aggregate:

~~~text
active_ticker_count: <N>
zigzag_failed: 0
price_movement_failed: 0
failure_count: 0
~~~

Runtime may remain near one historical full Movement execution (~60 minutes). This is expected.

## 8. Phase 6 — Structural Validation

~~~powershell
python scripts\validate_movement_active.py
~~~

Expected:

~~~text
validation_failures: 0
ACTIVE TICKER MOVEMENT VALIDATION: PASS
~~~

## 9. Phase 7 — Weekly Freshness Validation

~~~powershell
$evidence = "docs\reference\data\price_movement\weekly"
python scripts\validate_weekly_movement.py --evidence-dir $evidence
~~~

Immediately after the weekly run normally expect:

~~~text
stale_count: 0
validation_failures: 0
WEEKLY MOVEMENT VALIDATION: PASS
~~~

`max_movement_age_trading_days` must be <= 5.

## 10. Phase 8 — Freshness Semantics

~~~sql
SELECT
    Ticker,
    ContextAsOfDate,
    LatestOHLCDate,
    MovementAgeTradingDays,
    MovementFreshnessStatus
FROM "CherryMon"."main"."vw_Ticker_Movement_Context"
WHERE PriceMovementConfigCode = 'PM_ZZ_D_V2'
ORDER BY MovementAgeTradingDays DESC, Ticker
LIMIT 50;
~~~

Expected:

~~~text
0     FRESH
1..5  AGING
>5    STALE
~~~

## 11. Phase 9 — On-Demand Repair Regression

~~~powershell
python scripts\run_daily_movement.py --ticker MWG --force
python scripts\run_daily_movement.py --ticker MWG --dry-run
~~~

Expected after force:

~~~text
MWG = UP_TO_DATE
Selected=False
~~~

The existing script name is retained for backward compatibility. It is now a manual/on-demand entry point, not part of normal daily scheduling.

## 12. Phase 10 — Idempotency

REQ-0033 already proved full-universe business-row idempotency for the same underlying runner. REQ-0036 therefore validates idempotency with a bounded MWG/FPT rerun instead of paying for a second full ~60-minute universe run.

Capture ticker-local counts:

~~~sql
SELECT Ticker, COUNT(*) AS RowCount
FROM "CherryMon"."main"."vw_Ticker_ZigZag_Pivots"
WHERE ConfigCode = 'ZZ_D_5_MVP'
  AND Ticker IN ('MWG', 'FPT')
GROUP BY Ticker
ORDER BY Ticker;

SELECT Ticker, COUNT(*) AS RowCount
FROM "CherryMon"."main"."vw_Ticker_Price_Movement_Swings"
WHERE PriceMovementConfigCode = 'PM_ZZ_D_V2'
  AND Ticker IN ('MWG', 'FPT')
GROUP BY Ticker
ORDER BY Ticker;
~~~

Rerun the bounded canary:

~~~powershell
python scripts\initload\init_reload_zigzag_price_movement_active.py --ticker MWG --ticker FPT
~~~

Expected:

- ticker-local business row counts remain stable;
- no duplicates;
- structural validator remains PASS;
- freshness remains valid.

Do **not** run a second full-universe weekly execution solely for idempotency unless the focused canary exposes a mismatch.

## 13. Phase 11 — Monthly Regression

~~~powershell
python -m py_compile runMonthly.py
git diff main -- runMonthly.py
~~~

Expected: no REQ-0036 changes to runMonthly.py.

## 14. Phase 12 — Archify

~~~powershell
.\scripts\render_archify_cherrystock.ps1 -NoOpen
.\scripts\render_archify_analytics.ps1 -NoOpen
~~~

PASS requires both showcase validations `ok=true`. High-level runtime entry points must include weekly, and the analytics diagram must show Movement as weekly/manual rather than daily post-commit.

## 15. Evidence Commit

After PASS:

~~~powershell
git add docs\reference\data\price_movement\weekly
git add docs\architecture\generated\CherryStock_High_Level.html
git add docs\architecture\generated\CherryStock_Analytics_Calculation_Engines.html
git add docs\reference\DB_Metadata.md
git commit -m "validation: add weekly Movement pipeline evidence"
git push origin feature/weekly-movement-pipeline
~~~

Do not commit unrelated local files.

## 16. TestEngineer Verdict

~~~text
TEST VERDICT
Objective: REQ-0036 Weekly Full-Universe Movement Pipeline
Validation depth: WEEKLY PRODUCTION INTEGRATION

Compile/focused tests:
PASS | FAIL | BLOCKED

MovementContext migration:
PASS | FAIL | BLOCKED

Daily Movement removal:
PASS | FAIL | BLOCKED

Weekly canary:
PASS | FAIL | BLOCKED

Full weekly run:
PASS | FAIL | BLOCKED

Structural validator:
PASS | FAIL | BLOCKED

Freshness validator:
PASS | FAIL | BLOCKED

On-demand repair:
PASS | FAIL | BLOCKED

Idempotency:
PASS | FAIL | BLOCKED

Monthly regression:
PASS | FAIL | BLOCKED

Archify:
PASS | FAIL | BLOCKED

Verdict:
PASS | FAIL | BLOCKED | REGRESSION

Action:
KEEP | FIX_ONCE | REVERT | STOP

Evidence:
- active_ticker_count=<N>
- zigzag_failed=0
- price_movement_failed=0
- stale_count=0
- max_movement_age_trading_days<=5
- daily runner movement invocation=0

Residual risk:
- weekly current-leg lag up to five trading sessions
~~~

## 17. STOP Rule

PASS → KEEP → STOP.

Do not optimize ZigZag algorithm or change Movement thresholds during validation.
