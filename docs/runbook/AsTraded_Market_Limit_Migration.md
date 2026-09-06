# As-Traded Market-Limit Migration Runbook

- **Status:** DESIGN_READY_NOT_EXECUTABLE_UNTIL_IMPLEMENTED
- **Architecture:** [[../architecture/AsTraded_Market_Limit|As-Traded Market Limit Architecture]]
- **ADR:** [[../adr/ADR-010-separate-adjusted-as-traded-market-limit|ADR-010]]

## Purpose

Migrate historical Reference/Ceiling/Floor/LimitUp/LimitDown calculations away from
adjusted `raw_stock_eod` and onto a point-in-time as-traded market-data contract.

This runbook is the operational procedure to execute **after implementation artifacts
exist and have reached `IMPLEMENTED_PENDING_VALIDATION`**.

Do not execute this runbook against the current repository state until the target
implementation files named below have been delivered.

---

# Target Objects

Expected target data flow:

```text
raw_stock_eod_astraded
        ↓
cal_stock_market_limit_eod
        ↓
vw_stock_market_limit_eod
        ↓
vw_raw_stock_eod compatibility join
        ↓
SmartMoney MarketLimitAdapter
```

Expected target contracts:

```text
raw_stock_eod          -> adjusted analytical history
raw_stock_eod_astraded -> point-in-time/as-traded history
```

---

# Expected Implementation Artifacts

Implementation may adjust exact filenames to current repository patterns, but the
runbook MUST be updated before execution if paths differ.

Expected:

```text
src/DuckDB/sql/stock_market_limit_schema.sql
src/DuckDB/sql/vw_stock_market_limit_eod.sql
src/DuckDB/sql/vw_raw_stock_eod.sql
src/DuckDB/sql/stock_market_limit_preflight.sql

scripts/initload/init_reload_raw_stock_eod_astraded.py
scripts/initload/init_reload_cal_stock_market_limit_eod.py

tests/test_stock_market_limit_eod.py
tests/test_stock_market_limit_eod.md
```

Expected application components:

```text
AsTradedStockEODAdapter
MarketLimitResolver
SmartMoney MarketLimitAdapter -> vw_stock_market_limit_eod
```

---

# Deployment Preconditions

Before deployment, all conditions must be true:

1. Implementation state is `IMPLEMENTED_PENDING_VALIDATION`.
2. The selected source is verified to be as-traded / point-in-time.
3. Price unit is confirmed as thousand VND/share after normalization.
4. Source historical values do not retroactively back-adjust after a corporate action.
5. Source provides point-in-time Market or equivalent daily market identity.
6. UPCOM ReferencePrice is either:
   - directly supplied by a trusted provider; or
   - derived from explicit eligible regular-lot continuous-matching VWAP evidence.
7. Current `raw_stock_eod` remains unchanged and continues to serve analytical use.
8. Backup/recovery strategy for the local DuckDB exists.

If any prerequisite fails:

```text
Verdict: BLOCKED
Action: STOP
```

---

# Phase 0 — Sync repository

```powershell
git pull
git status
```

Confirm no unintended local changes in the migration scope.

---

# Phase 1 — Create additive market-limit storage

Execute the delivered schema migration using the approved CherryMon SQL path.

Expected objects:

```text
raw_stock_eod_astraded
cal_stock_market_limit_eod
```

Verify:

- object existence;
- business keys;
- column types;
- no destructive change to `raw_stock_eod`.

Expected business keys:

```text
raw_stock_eod_astraded:
Ticker + Date + SourceCode

cal_stock_market_limit_eod:
Ticker + Date
```

---

# Phase 2 — Full as-traded backfill

Run the delivered full-load wrapper, expected shape:

```powershell
python scripts\initload\init_reload_raw_stock_eod_astraded.py
```

Validate source-level quality:

```text
row count > 0
duplicate Ticker+Date+SourceCode = 0
Ticker/Date coverage is plausible
Market coverage is plausible
price unit is correct
Close is as-traded, not adjusted
```

## Corporate-action proof

Use at least one known corporate-action ticker/date sequence.

Compare:

```text
raw_stock_eod.Close
vs
raw_stock_eod_astraded.Close
vs
external historical as-traded source
```

Expected:

- analytical adjusted Close may differ;
- as-traded Close must match the point-in-time external source;
- later corporate actions must not rewrite earlier as-traded Close.

If this fails:

```text
Verdict: FAIL
Action: STOP
```

Do not continue to market-limit backfill.

---

# Phase 3 — Resolve historical market limits

Run the delivered resolver/initload wrapper, expected shape:

```powershell
python scripts\initload\init_reload_cal_stock_market_limit_eod.py
```

Expected resolution priority:

```text
AUTHORITATIVE
    ↓
VALIDATED_PROVIDER
    ↓
DERIVED_AS_TRADED
    ↓
PARTIAL / UNAVAILABLE
```

Explicitly forbidden:

```text
fallback to adjusted raw_stock_eod.Close
```

---

# Phase 4 — Market-limit preflight

Run the delivered read-only preflight.

Validate:

1. one final row per `Ticker + Date`;
2. `ReferencePrice <= CeilingPrice`;
3. `ReferencePrice >= FloorPrice`;
4. TRUE `LimitUp` means `AsTradedClose == CeilingPrice`;
5. TRUE `LimitDown` means `AsTradedClose == FloorPrice`;
6. unavailable evidence remains NULL;
7. direct provider values preserve source provenance;
8. HOSE/HNX ordinary derivation uses previous as-traded Close;
9. UPCOM never falls back to previous EOD Close;
10. special-session UNKNOWN does not silently use ordinary rules;
11. streaks are verified-session aware;
12. no adjusted analytical Close is referenced by market-limit calculation.

---

# Phase 5 — Regression reconciliation

Use three test groups.

## Group A — Random market sample

Minimum:

```text
5 HOSE
5 HNX
5 UPCOM
```

Prefer a mix of:

- normal sessions;
- no-trade/low-liquidity sessions;
- varied price levels / quote units.

Reconcile against TradingView and/or another market-data source.

## Group B — Limit events

Minimum:

```text
3 LimitUp
3 LimitDown
2 multi-session LimitUp streaks
1 multi-session LimitDown streak
```

Verify:

```text
AsTradedClose
ReferencePrice
CeilingPrice
FloorPrice
LimitUp
LimitDown
Streak
```

## Group C — Corporate-action regressions

Minimum:

```text
AGG-type ex-right/back-adjustment case
at least 2 additional corporate-action examples
```

Core assertion:

```text
Later adjustment of raw_stock_eod
MUST NOT change
historical cal_stock_market_limit_eod
```

---

# Phase 6 — Full vs incremental convergence

Run a bounded incremental refresh over a date window that overlaps the full backfill.

Compare logical keys:

```text
Ticker + Date
```

Expected:

- same ReferencePrice;
- same CeilingPrice/FloorPrice;
- same LimitUp/Down;
- same streaks;
- same quality/source classification.

Any divergence is FAIL.

---

# Phase 7 — Public-view cutover

Create/replace:

```text
vw_stock_market_limit_eod
```

Then change:

```text
vw_raw_stock_eod
```

to a compatibility join:

```text
raw_stock_eod
LEFT JOIN vw_stock_market_limit_eod
USING (Ticker, Date)
```

Validation:

- adjusted OHLCV still comes from `raw_stock_eod`;
- market-limit fields come only from `vw_stock_market_limit_eod`;
- no previous-close market-limit derivation remains inside `vw_raw_stock_eod`;
- row count remains equal to `raw_stock_eod`;
- existing public column names/order are preserved where required.

---

# Phase 8 — SmartMoney cutover

Change SmartMoney `MarketLimitAdapter` to read:

```text
vw_stock_market_limit_eod
```

Quality mapping:

```text
AUTHORITATIVE      -> highest confidence
VALIDATED_PROVIDER -> high confidence
DERIVED_AS_TRADED  -> partial confidence
PARTIAL            -> reduced confidence
UNAVAILABLE        -> factor NULL
```

Explicitly verify:

```text
NULL LimitUp != FALSE
```

SmartMoney SupplyLock must continue to work when LimitUp evidence is unavailable.

---

# Phase 9 — Refresh generated metadata

After local DB cutover succeeds:

```powershell
python -c "from src.Ults import DuckLib; DuckLib.exportDuckDB_metadata()"
```

Confirm generated metadata includes:

```text
raw_stock_eod_astraded
cal_stock_market_limit_eod
vw_stock_market_limit_eod
vw_raw_stock_eod
```

Do not hand-edit generated metadata before runtime.

---

# Phase 10 — Independent TestEngineer validation

TestEngineer must execute the focused integration/regression plan.

Required terminal output:

```text
As-Traded Market-Limit Migration
--------------------------------
As-traded source: PASS | FAIL
Corporate-action stability: PASS | FAIL
Market identity: PASS | WARNING | FAIL
ReferencePrice: PASS | WARNING | FAIL
Ceiling/Floor: PASS | WARNING | FAIL
LimitUp/Down: PASS | WARNING | FAIL
Streaks: PASS | WARNING | FAIL
UPCOM semantics: PASS | WARNING | FAIL
Full/incremental convergence: PASS | FAIL
Public compatibility view: PASS | FAIL
SmartMoney adapter: PASS | WARNING | FAIL

Verdict: PASS | FAIL | BLOCKED | REGRESSION
Action: KEEP | REVERT | FIX ONCE | STOP
```

Only TestEngineer may issue final PASS.

---

# Rollback

## Before public cutover

If backfill/validation fails:

```text
leave existing public consumers unchanged
disable new market-limit pipeline
STOP
```

Do not mutate `raw_stock_eod`.

## After public cutover

Preferred rollback:

1. disable SmartMoney LimitUp factor;
2. point/restore `vw_raw_stock_eod` to a safe compatibility state;
3. keep limit fields NULL if necessary;
4. do NOT re-enable historical adjusted-Close derivation as a production fallback.

The old adjusted-Close derivation may remain in Git history for diagnosis, but should
not be restored as the authoritative market-limit path.

---

# Stop Conditions

Stop immediately when:

- the source proves to be adjusted rather than as-traded;
- price units cannot be resolved;
- corporate-action stability fails;
- UPCOM semantics require an unsupported guess;
- full/incremental results diverge;
- continuing would require fallback to adjusted `raw_stock_eod`.

---

# Final success criteria

Migration is complete only when:

```text
Adjusted analytics
    stays on raw_stock_eod

As-traded market limits
    stay on raw_stock_eod_astraded
    -> cal_stock_market_limit_eod
    -> vw_stock_market_limit_eod

vw_raw_stock_eod
    is join-only for market-limit fields

SmartMoney
    consumes vw_stock_market_limit_eod

corporate actions
    do not rewrite historical limit evidence
```
