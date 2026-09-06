# vw_raw_stock_eod Validation

Validation owner: TestEngineer.

## Objective

Validate the derived standard-session market-limit contract without claiming that
derived values are an authoritative exchange feed.

## Execute

1. Rebuild:
   `python scripts/initload/init_reload_vw_raw_stock_eod.py`
2. Run:
   `src/DuckDB/sql/vw_raw_stock_eod_preflight.sql`

## Required evidence

- row preservation vs `raw_stock_eod`;
- zero duplicate `Ticker + Date` keys;
- HOSE/HNX/UPCOM band-rate mapping;
- quote-unit alignment;
- LimitUp/LimitDown consistency with Close;
- streak consistency;
- UPCOM proxy/reference coverage;
- spot-check recent limit events against an external official market page when practical.

## Terminal format

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

Expected implementation state before independent validation:
`IMPLEMENTED_PENDING_VALIDATION`.
