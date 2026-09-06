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
- expected 18-column contract exists;
- duplicate `Ticker + Date` groups = 0;
- Intraday dates use exact tick-derived TradingValue in integer VND;
- positive-volume EOD dates without Intraday use `((High + Low + Close) / 3) * Volume * 1000`, rounded to BIGINT;
- `TradingValue_Source` and `TradingValue_IsProxy` match provenance;
- zero-volume EOD-only days expose TradingValue=0 and `NO_TRADE`;
- proxy TradingValue rows do not fabricate BuyUp/SellDown/ATO/ATC flow fields;
- `TradingValue >= BuyUp + SellDown + ATO + ATC` on `INTRADAY_TICK` rows.

## TradingValue provenance

- `INTRADAY_TICK` -> `SUM(tick Close * tick Volume * 1000)`, `IsProxy=FALSE`.
- `EOD_TYPICAL_PRICE_PROXY` -> `((High + Low + Close) / 3) * Volume * 1000`, `IsProxy=TRUE`.
- `NO_TRADE` -> `0`, `IsProxy=FALSE`.
- `MISSING_INPUT` -> NULL TradingValue when positive-volume EOD has incomplete H/L/C.

## Flow semantics

- `OpenInt=1` -> SellDown
- `OpenInt=2` -> BuyUp
- `OpenInt=3` + 09:00-09:20 -> ATO
- `OpenInt=3` + 14:30-14:50 -> ATC
- other `OpenInt=3` -> remains only in tick-based TradingValue

Auction windows were verified against raw_stock_intraday `OpenInt=3` tick
timestamps: matching results publish after the 09:15/14:45 session closes, so
auction ticks legitimately land up to 09:20:00 and 14:50:00 respectively.

## Terminal result

```text
vw_Ticker_OHLC_D
----------------
Schema: PASS | FAIL
Key uniqueness: PASS | FAIL
TradingValue provenance: PASS | FAIL
Proxy formula: PASS | FAIL
Flow quality: PASS | FAIL
OI=3 auction classification: PASS | WARNING | FAIL

Verdict: PASS | WARNING | FAIL
Action: KEEP | INVESTIGATE | FIX ONCE | STOP
```
