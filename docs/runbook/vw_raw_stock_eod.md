# vw_raw_stock_eod Deployment Runbook

## Purpose

Create and validate `"CherryMon"."main"."vw_raw_stock_eod"`, the enriched stock
EOD read contract for:

- current exchange classification;
- ReferencePrice;
- CeilingPrice / FloorPrice;
- LimitUp / LimitDown;
- LimitUpStreak / LimitDownStreak.

The view preserves `raw_stock_eod` at one row per `Ticker + Date`.

## Current rules implemented

Standard-session rules:

| Market | ReferencePrice | Normal band | Quote unit |
|---|---|---:|---|
| HOSE | nearest previous Close | +/-7% | 10 / 50 / 100 VND by price level |
| HNX | nearest previous Close | +/-10% | 100 VND |
| UPCOM | nearest previous eligible weighted-average matched price | +/-15% | 100 VND |

Ceiling is rounded down and Floor is rounded up to the applicable quote unit.

Rule basis:
- VNX Decision 22/QD-HDTV dated 16/03/2026 for listed securities.
- VNX Decision 23/QD-HDTV dated 18/03/2026 for UPCOM.
- HOSE 2026 trading guide for ordinary +/-7% band and quote units.

## Quality boundary

This is a **derived standard-rule contract**, not an exchange-published official
daily reference/ceiling/floor feed.

Known limitations:

1. `raw_stock_fa.Market` is a current snapshot and is not point-in-time exchange history.
2. `raw_stock_eod` can be corporate-action adjusted historically.
3. `raw_stock_intraday` does not expose an explicit negotiated/odd-lot flag.
4. First-trading-day, long-suspension/resumption and ex-right/corporate-action
   special price-band rules are not silently guessed.

The view exposes provenance/quality fields so consumers can lower confidence.

## Step 0 — Pull latest code

```powershell
git pull
```

Expected files:

```text
src/DuckDB/sql/vw_raw_stock_eod.sql
src/DuckDB/sql/vw_raw_stock_eod_preflight.sql
scripts/initload/init_reload_vw_raw_stock_eod.py
```

## Step 1 — Rebuild the view

```powershell
python scripts\initload\init_reload_vw_raw_stock_eod.py
```

Prerequisites:

```text
raw_stock_eod
raw_stock_intraday
raw_stock_fa
```

The full EOD, full Intraday and combined raw reload scripts automatically
drop/recreate this dependent view around destructive raw-table rebuilds.

## Step 2 — Run preflight

Execute:

```text
src/DuckDB/sql/vw_raw_stock_eod_preflight.sql
```

Validate:

1. view exists;
2. 22-column public contract;
3. row count equals `raw_stock_eod`;
4. unique `Ticker + Date`;
5. market mapping distribution;
6. standard band rates;
7. ceiling/reference/floor ordering;
8. HNX/UPCOM 100-VND quote alignment;
9. LimitUp/LimitDown match Close against derived limits;
10. streak consistency;
11. UPCOM reference lineage coverage;
12. recent limit events for manual spot-check.

## Step 3 — SmartMoney readiness

SmartMoney may consume:

```text
ReferencePrice
CeilingPrice
FloorPrice
LimitUp
LimitUpStreak
LimitDown
LimitDownStreak
```

with:

```text
DataQuality = PARTIAL / DERIVED_STANDARD_RULE
```

until an authoritative daily market-limit source is available.

Do not promote this contract to `EXACT` merely because the SQL preflight passes.

## Terminal verdict

```text
vw_raw_stock_eod
----------------
Schema: PASS | FAIL
Key uniqueness: PASS | FAIL
Row preservation: PASS | FAIL
Market mapping: PASS | WARNING | FAIL
ReferencePrice: PASS | WARNING | FAIL
Price bands: PASS | WARNING | FAIL
Limit flags: PASS | FAIL
Streaks: PASS | FAIL
UPCOM lineage: PASS | WARNING | FAIL

Verdict: PASS | WARNING | FAIL | BLOCKED
Action: KEEP | INVESTIGATE | FIX ONCE | STOP
```

A PASS validates the implemented derived contract. It does not convert derived
reference/price-limit data into an authoritative exchange feed.
