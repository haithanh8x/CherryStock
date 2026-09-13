# SmartMoney NiceGUI Tab — MarketState Flow + MA200 Split Deployment

- **Status:** ACTIVE
- **UI entry:** `src/webapp/NiceGUI_chart.py`
- **Renderer:** `src/webapp/smart_money_tab.py`
- **Snapshot query:** `src/webapp/smart_money_snapshot_query.py`
- **State-flow model:** `src/webapp/smart_money_state_flow.py`
- **Snapshot validator:** `scripts/validate_smart_money_ui_snapshot.py`
- **Focused tests:** `tests/test_smart_money_state_flow.py`, `tests/test_smart_money_snapshot_query.py`
- **SmartMoney source:** `"CherryMon"."main"."vw_Ticker_SmartMoney"`
- **Close source:** `"CherryMon"."main"."vw_Ticker_OHLC_D"`
- **Indicator values:** `"CherryMon"."main"."vw_Ticker_indicators"`
- **Indicator config SSOT:** `"CherryMon"."main"."vw_Indicator_config"`
- **MA200 config:** `MA200_D` / `VALUE`
- **Model:** `SMART_MONEY_V1`
- **Validation owner:** `TestEngineer`

## 1. Objective

Deploy the SmartMoney tab presentation change without modifying SmartMoney scoring/state logic.

Required UI behavior:

```text
1. Remove the label: "Tickers · TradeActionConfidenceScore ↓".
2. Remove the MarketState total shown on the far right of each detail block header.
3. In the top "SmartMoney State Flow" box:
   - show total ticker count beside each MarketState;
   - make each MarketState a link to its corresponding detail block.
4. In each MarketState detail block:
   - left column: Close >= MA200;
   - right column: Close < MA200.
```

The global latest-snapshot ticker total below the SmartMoney header remains visible. Only the duplicate per-MarketState total on the right side of each detail header is removed.

This is a UI/read-only deployment. Do not recalculate SmartMoneyScore and do not run SmartMoney historical initload.

---

## 2. Correct data contract

The previous draft incorrectly assumed `vw_Ticker_indicators` was wide-format with `Close` and `MA200` columns. That assumption is invalid.

The actual Indicator Engine public contract is **long format**:

```text
Ticker
Date
ConfigId
ComponentCode
Value
IndicatorCode
Timeframe
WarmupBars
```

Therefore the UI snapshot must resolve the two comparison values from their canonical sources:

```text
Close
  <- "CherryMon"."main"."vw_Ticker_OHLC_D".Close

MA200
  <- "CherryMon"."main"."vw_Ticker_indicators".Value
  JOIN "CherryMon"."main"."vw_Indicator_config"
       ON ConfigId + ComponentCode
  WHERE ConfigCode = 'MA200_D'
    AND ComponentCode = 'VALUE'
    AND ConfigIsEnabled = TRUE
    AND IndicatorIsActive = TRUE
    AND ComponentIsActive = TRUE
```

Join grain:

```text
Ticker + Date
```

The shared implementation is centralized in:

```text
src/webapp/smart_money_snapshot_query.py
```

Both NiceGUI and the real snapshot validator must use this same query builder so their contracts cannot drift.

No new wide-format view is required. No schema migration is required. Do not hard-code a `ConfigId`; resolve MA200 through `ConfigCode='MA200_D'`.

MA200 classification:

```text
Close >= MA200   -> left column
Close <  MA200   -> right column
Close/MA200 NULL -> MA200 N/A line below the two columns
```

`MA200 N/A` preserves ticker coverage for incomplete history without falsely assigning a ticker to either side.

---

## 3. MarketState flow contract

Canonical order remains:

```text
1. ACCUMULATION
2. SUPPLY_LOCK
3. DEMAND_EXPANSION
4. BREAKOUT
5. MARKUP
6. DISTRIBUTION
7. SELLING_CLIMAX
8. LIQUIDITY_DRYUP
9. NEUTRAL
```

Unknown future states are appended after the canonical states.

Top flow rendering example:

```text
ACCUMULATION · 62 -> SUPPLY LOCK · 39 -> DEMAND EXPANSION · 18 -> ...
```

Each flow item is an in-page link to a stable anchor such as:

```text
#smart-money-state-accumulation
#smart-money-state-supply-lock
```

---

## 4. Detail block contract

Header:

```text
[stage] MARKET STATE [BUY/HOLD/SELL count badge(s)]
        description
```

The old right-side element must be absent:

```text
<number>
tickers
```

The old label must also be absent:

```text
Tickers · TradeActionConfidenceScore ↓
```

Detail body:

```text
+---------------------------+---------------------------+
| >= MA200 · <count>        | < MA200 · <count>         |
| ticker sequence           | ticker sequence           |
+---------------------------+---------------------------+
| MA200 N/A · <count> ...   | only when required        |
+-------------------------------------------------------+
```

Ticker ordering inside each bucket:

```text
TradeActionConfidenceScore DESC
Ticker ASC
```

First two tickers in each bucket remain bold as presentation-only emphasis.

---

## 5. Step 1 — Safe sync

From repository root:

```powershell
git status --short
git pull --ff-only origin main
git log -1 --oneline
```

Unexpected local changes:

```text
Verdict: BLOCKED
Action: STOP
```

---

## 6. Step 2 — Minimum compile

Run:

```powershell
python -m py_compile src\webapp\NiceGUI_chart.py src\webapp\smart_money_tab.py src\webapp\smart_money_snapshot_query.py src\webapp\smart_money_state_flow.py scripts\validate_smart_money_ui_snapshot.py
```

Required:

```text
exit=0
```

Any syntax/import parse failure:

```text
Verdict: FAIL
Action: STOP
```

---

## 7. Step 3 — Minimum focused tests

Run only:

```powershell
python -m pytest tests\test_smart_money_state_flow.py tests\test_smart_money_snapshot_query.py -q
```

Expected:

```text
5 passed
```

The four state-flow tests prove:

```text
canonical MarketState order
stable anchor ids
Close == MA200 -> >= MA200
Close > MA200 -> >= MA200
Close < MA200 -> < MA200
missing MA200 is not misclassified
bucket counts reconcile to MarketState total
confidence ordering is preserved per bucket
unknown MarketState is appended
duplicate ticker input keeps strongest confidence row
```

The snapshot-query contract test additionally creates a minimal DuckDB fixture with the **real long-format indicator schema** and proves:

```text
Close is read from vw_Ticker_OHLC_D
MA200 is read from vw_Ticker_indicators.Value
MA200 is selected through vw_Indicator_config ConfigCode='MA200_D'
MA50_D or other MA rows are not substituted
query binds successfully without i.Close / i.MA200 assumptions
```

Do not automatically expand to the full pytest suite.

---

## 8. Step 4 — Real local snapshot validator

Run:

```powershell
python scripts\validate_smart_money_ui_snapshot.py
```

Required first line:

```text
SMART MONEY UI SNAPSHOT — PASS
```

The validator is read-only and uses the exact same snapshot query as NiceGUI.

It verifies:

```text
latest SMART_MONEY_V1 snapshot exists
one latest date only
canonical state prefix is preserved
all tickers are represented exactly once
TradeAction counts reconcile to MarketState total
>= MA200 + < MA200 + MA200 N/A = MarketState total
all >= MA200 rows satisfy Close >= MA200
all < MA200 rows satisfy Close < MA200
all MA200 N/A rows have missing Close or MA200
confidence ordering and ticker sequence agree
```

Expected per-state evidence:

```text
01. ACCUMULATION: total=... >=MA200=... <MA200=... NA=... BUY=...
```

If the validator reports a missing canonical public view (`vw_Ticker_OHLC_D`, `vw_Ticker_indicators`, or `vw_Indicator_config`), classify as `BLOCKED`. Do not create an ad-hoc wide indicator view as a repair action.

---

## 9. Step 5 — Visual smoke

Run:

```powershell
python src\webapp\NiceGUI_chart.py
```

Open the existing endpoint, normally:

```text
http://127.0.0.1:8081
```

Validate only:

```text
1. SmartMoney tab opens without exception.
2. "Tickers · TradeActionConfidenceScore ↓" is absent everywhere.
3. Per-MarketState total on the far right of detail headers is absent.
4. SmartMoney State Flow shows a total beside every MarketState.
5. Clicking each MarketState flow item jumps to the matching detail block.
6. Each non-empty MarketState has two columns on desktop:
   left >= MA200, right < MA200.
7. Responsive narrow layout may stack the two columns vertically.
8. Ticker counts match validator output.
9. MA200 N/A tickers appear below the grid, not in either MA200 bucket.
10. BUY/HOLD/SELL badges remain beside MarketState.
11. Refresh rebuilds flow counts, links and MA200 buckets from latest snapshot.
```

Stop the NiceGUI process after smoke check.

---

## 10. Deployment result contract

Return:

```text
SMART MONEY NICEGUI — MA200 FLOW DEPLOYMENT

HEAD: <sha>
Compile: PASS | FAIL
Focused tests: PASS | FAIL
Snapshot query contract: PASS | FAIL
Snapshot validator: PASS | FAIL | BLOCKED
Snapshot date: <date>
Snapshot tickers: <count>
Old ticker heading removed: PASS | FAIL
Detail-header right total removed: PASS | FAIL
State Flow totals: PASS | FAIL
State Flow anchor navigation: PASS | FAIL
>= MA200 bucket: PASS | FAIL
< MA200 bucket: PASS | FAIL
MA200 N/A coverage: PASS | FAIL
Refresh smoke: PASS | FAIL

Verdict: PASS | FAIL | BLOCKED
Action: KEEP | STOP
```

After terminal verdict, STOP.

---

## 11. Deliberately skipped validation

Do not run for this deployment:

```text
SmartMoney historical initload
smart_money_v1_preflight.sql
run.py daily pipeline
OOS/backtest evaluation
full pytest suite
```

Those validate different contracts and do not provide additional evidence for this presentation change.
