# vw_raw_stock_eod — Reference / Price Band / Limit Streak Runbook

## Migration notice

Independent reconciliation found that the current implementation is not safe as a
historical point-in-time market-limit SSOT because `raw_stock_eod` can be
back-adjusted after corporate actions.

The approved replacement architecture is:

```text
raw_stock_eod_astraded
-> cal_stock_market_limit_eod
-> vw_stock_market_limit_eod
-> vw_raw_stock_eod compatibility join
```

See:
- `docs/architecture/AsTraded_Market_Limit.md`
- `docs/adr/ADR-010-separate-adjusted-as-traded-market-limit.md`
- `docs/runbook/AsTraded_Market_Limit_Migration.md`

Until that migration passes independent validation, this runbook validates only the
legacy derived implementation. Do not promote historical LimitUp/Down from this path
to authoritative SmartMoney evidence.

## Purpose

Deploy and validate the enriched stock EOD public read contract:

```text
"CherryMon"."main"."vw_raw_stock_eod"
```

The change enriches canonical `raw_stock_eod` with:

```text
Market
ReferencePrice
CeilingPrice
FloorPrice
LimitUp
LimitUpStreak
LimitDown
LimitDownStreak
```

plus provenance / quality fields required by SmartMoneyScore.

Logical grain remains:

```text
Ticker + Date
```

The view MUST preserve one row for every `raw_stock_eod` row.

---

## Change scope

### Source tables

```text
raw_stock_eod
raw_stock_intraday
raw_stock_fa
```

### New public view

```text
vw_raw_stock_eod
```

### Definition

```text
src/DuckDB/sql/vw_raw_stock_eod.sql
```

### Validation

```text
src/DuckDB/sql/vw_raw_stock_eod_preflight.sql
tests/test_vw_raw_stock_eod.md
```

### Rebuild entry point

```text
scripts/initload/init_reload_vw_raw_stock_eod.py
```

### Dependent full-load workflows

These workflows drop/recreate the view automatically around destructive raw reloads:

```text
scripts/initload/init_reload_raw_eod_tables.py
scripts/initload/init_reload_raw_intraday_tables.py
scripts/initload/init_reload_raw_eod_raw_intraday.py
```

---

## Public column contract

Expected 22 columns:

| Group | Columns |
|---|---|
| Raw EOD | `Ticker, Date, Open, High, Low, Close, Volume, OpenInt` |
| Market lineage | `Market, Market_Source, Market_IsPointInTime` |
| Reference lineage | `ReferencePrice, ReferencePrice_Source, ReferencePrice_IsProxy` |
| Band quality | `PriceBandRate, PriceBandRuleQuality` |
| Price limits | `CeilingPrice, FloorPrice` |
| Limit state | `LimitUp, LimitUpStreak, LimitDown, LimitDownStreak` |

Price units remain identical to `raw_stock_eod`:

```text
thousand VND / share
```

---

## Standard-session rules implemented

| Market | ReferencePrice | Normal band | Quote unit |
|---|---|---:|---|
| HOSE | nearest previous Close | +/-7% | 10 / 50 / 100 VND by price level |
| HNX | nearest previous Close | +/-10% | 100 VND |
| UPCOM | nearest previous eligible weighted-average matched price | +/-15% | 100 VND |

Rule basis recorded in the architecture:

- VNX Decision 22/QD-HDTV dated 16/03/2026 — listed securities.
- VNX Decision 23/QD-HDTV dated 18/03/2026 — UPCOM.
- HOSE 2026 trading guide — normal band and HOSE quote units.

### Ceiling / Floor

```text
CeilingRaw = ReferencePrice * (1 + PriceBandRate)
FloorRaw   = ReferencePrice * (1 - PriceBandRate)

CeilingPrice = round DOWN to quote unit
FloorPrice   = round UP to quote unit
```

If rounding collapses a price limit to ReferencePrice, the one-quote-unit
adjustment defined by the implemented standard rule is applied.

---

## ReferencePrice behavior

### HOSE / HNX

```text
ReferencePrice = nearest previous available Close
ReferencePrice_Source = PREVIOUS_CLOSE_STANDARD_RULE
ReferencePrice_IsProxy = FALSE
```

This is a derived ordinary-session rule. Historical corporate-action adjustments
can still make the reconstructed value differ from the exchange-published
point-in-time value.

### UPCOM

UPCOM ReferencePrice is based conceptually on the previous eligible session's
weighted-average regular-lot continuous-matching price.

Current CherryStock Intraday data does not contain an explicit
regular-lot / odd-lot / negotiated flag. The implementation therefore uses the
best available compatible tick subset:

```text
OpenInt IN (1,2,3)
AND Volume >= 100
AND Volume % 100 = 0
```

and calculates:

```text
VWAP = SUM(TickPrice * TickVolume) / SUM(TickVolume)
```

Provenance:

```text
ReferencePrice_Source = UPCOM_INTRADAY_LOT100_VWAP_PROXY
ReferencePrice_IsProxy = TRUE
```

If a previous eligible Intraday reference cannot be resolved:

```text
ReferencePrice = NULL
ReferencePrice_Source = MISSING_PREVIOUS_REFERENCE
```

The system MUST NOT fabricate UPCOM ReferencePrice from EOD Close.

---

## Limit state semantics

### LimitUp

```text
LimitUp = TRUE
when daily Close == derived CeilingPrice
```

### LimitDown

```text
LimitDown = TRUE
when daily Close == derived FloorPrice
```

### Unknown

If ReferencePrice / CeilingPrice / FloorPrice cannot be resolved:

```text
LimitUp = NULL
LimitDown = NULL
```

Missing evidence MUST NOT be converted to `FALSE`.

### Streaks

```text
TRUE  -> previous streak + 1
FALSE -> 0
NULL  -> NULL
```

Example:

| Date | LimitUp | LimitUpStreak |
|---|---|---:|
| D1 | TRUE | 1 |
| D2 | TRUE | 2 |
| D3 | TRUE | 3 |
| D4 | FALSE | 0 |

The same contract applies to `LimitDownStreak`.

---

## Quality boundary

This view is a **derived standard-rule contract**.

It is NOT yet an exchange-published authoritative historical daily
Reference/Ceiling/Floor feed.

Known quality limitations:

1. `raw_stock_fa.Market` is a current snapshot, not point-in-time exchange history.
2. A ticker that historically moved between exchanges may inherit today's Market.
3. `raw_stock_eod` can be back-adjusted for corporate actions.
4. UPCOM Intraday does not explicitly prove regular-lot vs negotiated/odd-lot scope.
5. First trading day is not derived by the ordinary rule.
6. Trading resumption after long suspension is not derived by the ordinary rule.
7. Ex-right / dividend / bonus-share ReferencePrice adjustments require event data.
8. Other special-session exchange rules require an authoritative event/reference source.

Therefore normal supported rows expose:

```text
PriceBandRuleQuality = STANDARD_RULE_DERIVED
```

and SmartMoney MUST treat them as partial/derived evidence.

---

# Deployment Procedure

## Step 0 — Pull latest repository state

```powershell
git pull
```

Confirm:

```powershell
git status
```

Expected: no unintended local changes in the affected SQL/scripts.

---

## Step 1 — Check prerequisites

Required objects:

```text
"CherryMon"."main"."raw_stock_eod"
"CherryMon"."main"."raw_stock_intraday"
"CherryMon"."main"."raw_stock_fa"
```

Minimum required source columns:

### raw_stock_eod

```text
Ticker
Date
Open
High
Low
Close
Volume
OpenInt
```

### raw_stock_intraday

```text
Ticker
Date
Close
Volume
OpenInt
```

### raw_stock_fa

```text
Ticker
Date
Market
```

If a prerequisite is missing, stop with:

```text
Verdict: BLOCKED
Action: STOP
```

---

## Step 2 — Rebuild the view

Run:

```powershell
python scripts\initload\init_reload_vw_raw_stock_eod.py
```

Expected:

- SQL executes without DDL error;
- view exists;
- no source table is mutated;
- rerunning the command is idempotent because the definition uses
  `CREATE OR REPLACE VIEW`.

---

## Step 3 — Run the read-only preflight

Execute:

```text
src/DuckDB/sql/vw_raw_stock_eod_preflight.sql
```

Validation sequence:

1. View exists.
2. Public schema has 22 columns.
3. View row count equals `raw_stock_eod`.
4. Duplicate `Ticker + Date` groups = 0.
5. Market mapping distribution is reviewed.
6. Standard band mapping is:
   - HOSE = 0.07
   - HNX = 0.10
   - UPCOM = 0.15
7. `CeilingPrice >= ReferencePrice >= FloorPrice`.
8. HNX/UPCOM derived prices align to 100 VND quote units.
9. TRUE LimitUp rows close at CeilingPrice.
10. TRUE LimitDown rows close at FloorPrice.
11. LimitUp/Down streak semantics are consistent.
12. UPCOM ReferencePrice provenance is reviewed.
13. Recent derived limit events are manually spot-checked.

---

## Step 4 — Targeted manual checks

Use a small sample from all three markets.

Recommended sample classes:

```text
HOSE normal session
HNX normal session
UPCOM with Intraday reference available
one LimitUp case
one LimitDown case
one multi-day LimitUpStreak
one multi-day LimitDownStreak
one MISSING_PREVIOUS_REFERENCE case
```

For each sample inspect:

```sql
SELECT
    "Ticker",
    "Date",
    "Market",
    "Close",
    "ReferencePrice",
    "ReferencePrice_Source",
    "ReferencePrice_IsProxy",
    "PriceBandRate",
    "PriceBandRuleQuality",
    "CeilingPrice",
    "FloorPrice",
    "LimitUp",
    "LimitUpStreak",
    "LimitDown",
    "LimitDownStreak"
FROM "CherryMon"."main"."vw_raw_stock_eod"
WHERE "Ticker" = '<TICKER>'
ORDER BY "Date" DESC
LIMIT 30;
```

Do not convert a discrepancy around a known special session into an automatic SQL
repair. First classify whether the date is outside the ordinary-rule scope.

---

## Step 5 — Refresh generated DB metadata

Only after the local database has successfully rebuilt the view:

```powershell
python -c "from src.Ults import DuckLib; DuckLib.exportDuckDB_metadata()"
```

Confirm `docs/reference/DB_Metadata.md` contains:

```text
main.vw_raw_stock_eod
```

Do not hand-edit generated metadata ahead of runtime.

---

# Full-load behavior

The following scripts already protect this dependent view:

```text
init_reload_raw_eod_tables.py
init_reload_raw_intraday_tables.py
init_reload_raw_eod_raw_intraday.py
```

Their expected order is:

```text
DROP dependent views
        ↓
rebuild raw source table(s)
        ↓
verify prerequisites
        ↓
CREATE / REPLACE dependent views
```

This prevents destructive table reloads from leaving an invalid dependent view.

---

# SmartMoneyScore Handoff

SmartMoney `MarketLimitAdapter` may consume:

```text
Market
ReferencePrice
ReferencePrice_Source
ReferencePrice_IsProxy
PriceBandRate
PriceBandRuleQuality
CeilingPrice
FloorPrice
LimitUp
LimitUpStreak
LimitDown
LimitDownStreak
```

Current quality mapping:

```text
STANDARD_RULE_DERIVED
    -> PARTIAL / DERIVED_STANDARD_RULE

ReferencePrice_IsProxy = TRUE
    -> additional Confidence penalty

MISSING_INPUT
    -> Limit evidence unavailable / NULL
```

The following is explicitly prohibited:

```text
STANDARD_RULE_DERIVED -> EXACT
UPCOM_INTRADAY_LOT100_VWAP_PROXY -> AUTHORITATIVE
NULL LimitUp -> FALSE
```

SupplyLock can still calculate from non-limit factors when limit evidence is
unavailable.

---

# Rollback

The change is additive and does not mutate `raw_stock_eod`.

## Operational rollback

If the new view blocks downstream work:

```sql
DROP VIEW IF EXISTS "CherryMon"."main"."vw_raw_stock_eod";
```

Then keep SmartMoney MarketLimitAdapter disabled/unavailable until the issue is
resolved.

Do NOT alter or delete:

```text
raw_stock_eod
raw_stock_intraday
raw_stock_fa
```

as part of rollback.

## Code rollback

Use normal Git history to revert the change commit(s). Do not manually rewrite
historical raw data to compensate for a view calculation problem.

---

# Failure Handling

## BLOCKED

Examples:

- required raw table missing;
- required source column missing;
- database unavailable;
- view cannot compile because local schema differs from repository contract.

Action:

```text
STOP
```

## FAIL

Examples:

- duplicate `Ticker + Date`;
- row preservation fails;
- LimitUp/Down TRUE values do not match derived price limit;
- streak logic violates TRUE/FALSE/NULL contract.

Action:

```text
FIX ONCE
```

Only one controlled repair should be attempted before returning to TestEngineer.

## WARNING

Examples:

- historical Market is not point-in-time;
- UPCOM ReferencePrice is proxy;
- missing previous UPCOM Intraday reference;
- known special-session/corporate-action dates.

Action:

```text
INVESTIGATE / KEEP with quality penalty
```

A WARNING does not justify relabeling derived data as exact.

---

# Terminal Verdict

Use exactly this execution summary:

```text
vw_raw_stock_eod
----------------
Schema: PASS | FAIL
Key uniqueness: PASS | FAIL
Row preservation: PASS | FAIL
Market mapping: PASS | WARNING | FAIL
ReferencePrice: PASS | WARNING | FAIL
Price bands: PASS | WARNING | FAIL
LimitUp/Down: PASS | WARNING | FAIL
Limit streaks: PASS | WARNING | FAIL
UPCOM lineage: PASS | WARNING | FAIL
SmartMoney contract: PASS | WARNING | FAIL

Verdict: PASS | WARNING | FAIL | BLOCKED
Action: KEEP | INVESTIGATE | FIX ONCE | STOP
```

A `PASS` means the **derived standard-rule implementation** is validated.

It does NOT mean the values are an authoritative exchange-published historical
Reference/Ceiling/Floor feed.

---

## Related materials

- `docs/architecture/Data_Architecture.md`
- `docs/architecture/SmartMoneyScore.md`
- `docs/backlog/requirements/REQ-0025-smart-money-score.md`
- `scripts/initload/README.md`
- `tests/test_vw_raw_stock_eod.md`
- `.github/instructions/database.instructions.md`
- `.github/agents/TestEngineer.agent.md`
