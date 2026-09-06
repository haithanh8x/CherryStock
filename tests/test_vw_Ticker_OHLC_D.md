# vw_Ticker_OHLC_D Validation

## Objective

Validate the daily public OHLC + transaction-flow view after creation.

## Definition

`src/DuckDB/sql/vw_Ticker_OHLC_D.sql`

## Rebuild

```powershell
python scripts\initload\init_reload_vw_Ticker_OHLC_D.py
```

Full EOD/Intraday init reload scripts also recreate the view automatically.

## Preflight

Run:

`src/DuckDB/sql/vw_Ticker_OHLC_D_preflight.sql`

PASS requires:

- view exists;
- expected 16-column contract exists;
- duplicate `Ticker + Date` groups = 0;
- no negative flow/value metrics;
- `TradingValue >= BuyUp + SellDown + ATO + ATC`;
- zero-volume EOD-only days expose zero flow/value;
- positive-volume days without Intraday coverage expose NULL flow/value.

The OI=3 timestamp distribution and `UNCLASSIFIED_OI3` bucket are informational.
Do not change ATO/ATC rules only because unclassified OI=3 exists; inspect source
timestamps and market/session semantics first.

## Flow semantics

- `OpenInt=1` -> SellDown
- `OpenInt=2` -> BuyUp
- `OpenInt=3` + 09:00-09:15 -> ATO
- `OpenInt=3` + 14:30-14:45 -> ATC
- other `OpenInt=3` -> remains only in TradingValue

## Terminal result

```text
vw_Ticker_OHLC_D
----------------
Schema: PASS | FAIL
Key uniqueness: PASS | FAIL
Value quality: PASS | FAIL
Missing-data semantics: PASS | FAIL
OI=3 auction classification: PASS | WARNING | FAIL

Verdict: PASS | WARNING | FAIL
Action: KEEP | INVESTIGATE | FIX ONCE | STOP
```
