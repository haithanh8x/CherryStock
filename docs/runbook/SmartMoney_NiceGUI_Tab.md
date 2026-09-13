# SmartMoney NiceGUI Tab — MarketState Flow + MA200 Split Deployment

- **Status:** ACTIVE
- **UI entry:** `src/webapp/NiceGUI_chart.py`
- **Renderer:** `src/webapp/smart_money_tab.py`
- **State-flow model:** `src/webapp/smart_money_state_flow.py`
- **Snapshot validator:** `scripts/validate_smart_money_ui_snapshot.py`
- **Focused unit test:** `tests/test_smart_money_state_flow.py`
- **SmartMoney source:** `"CherryMon"."main"."vw_Ticker_SmartMoney"`
- **MA200 source:** `"CherryMon"."main"."vw_Ticker_indicators"`
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

## 2. Data contract

The latest `SMART_MONEY_V1` cross-section is read from:

```text
"CherryMon"."main"."vw_Ticker_SmartMoney"
```

`Close` and `MA200` are joined read-only from:

```text
"CherryMon"."main"."vw_Ticker_indicators"
```

Join key:

```text
Ticker + Date
```

No SmartMoney schema migration is required.

MA200 classification:

```text
Close >= MA200  -> left column
Close <  MA200  -> right column
Close/MA200 NULL -> MA200 N/A line below the two columns
```

`MA200 N/A` exists only to preserve ticker coverage for newly listed or otherwise incomplete indicator history. Such a ticker must not be falsely classified into either MA200 side.

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

Each flow item is an in-page link to a stable anchor:

```text
#smart-money-state-accumulation
#smart-money-state-supply-lock
...
```

Clicking a flow item must navigate to the corresponding detail block.

---

## 4. Detail block contract

Header:

```text
[stage] MARKET STATE [BUY/HOLD/SELL count badge(s)]
        description
```

The following old right-side element must be absent:

```text
<number>
tickers
```

The following old label must also be absent:

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

Ticker ordering inside each bucket remains:

```text
TradeActionConfidenceScore DESC
Ticker ASC  # deterministic tie-break
```

First two tickers in each bucket remain bold as a presentation-only emphasis.

---

## 5. Preconditions

From repository root:

```powershell
git status --short
git checkout main
git pull --ff-only origin main
python --version
```

Required local data objects:

```text
vw_Ticker_SmartMoney
vw_Ticker_indicators
```

Required latest indicator columns:

```text
Ticker
Date
Close
MA200
```

If either view is unavailable, classify deployment validation as `BLOCKED` rather than changing the UI contract.

---

## 6. Minimum test — syntax

Run:

```powershell
python -m py_compile src\webapp\smart_money_state_flow.py
python -m py_compile src\webapp\smart_money_tab.py
python -m py_compile scripts\validate_smart_money_ui_snapshot.py
```

PASS criteria:

```text
all three commands exit 0
```

Any syntax/import parse failure:

```text
Verdict: FAIL
Action: STOP
```

---

## 7. Minimum test — focused unit test

Run only:

```powershell
python -m pytest tests\test_smart_money_state_flow.py -q
```

Expected:

```text
4 passed
```

This focused test proves:

```text
canonical MarketState order is preserved
stable anchor ids are generated
Close == MA200 belongs to >= MA200
Close > MA200 belongs to >= MA200
Close < MA200 belongs to < MA200
missing MA200 is not misclassified
bucket counts reconcile to MarketState total
confidence ordering is preserved per bucket
unknown future MarketState is appended
duplicate ticker input keeps the strongest confidence row
```

Do not automatically expand to the full pytest suite for this UI change.

---

## 8. Minimum test — real snapshot validator

Run:

```powershell
python scripts\validate_smart_money_ui_snapshot.py
```

Required first line:

```text
SMART MONEY UI SNAPSHOT — PASS
```

The validator is read-only and verifies:

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

Expected per-state evidence format:

```text
01. ACCUMULATION: total=... >=MA200=... <MA200=... NA=... BUY=...
```

---

## 9. Visual smoke

Start NiceGUI:

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
6. Each non-empty MarketState detail block has two columns on desktop:
   left >= MA200, right < MA200.
7. Responsive narrow layout may stack the two columns vertically.
8. Ticker counts in the two MA200 buckets match the validator output.
9. Any MA200 N/A ticker appears below the grid, not inside either MA200 bucket.
10. BUY/HOLD/SELL badges remain beside the MarketState name.
11. Refresh rebuilds flow counts, links and detail buckets from the latest snapshot.
```

Stop the NiceGUI process after the smoke check.

---

## 10. Deployment result contract

Return:

```text
SMART MONEY NICEGUI — MA200 FLOW DEPLOYMENT

HEAD: <sha>
Compile: PASS | FAIL
Focused unit test: PASS | FAIL
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

Those validate different contracts and are not required to prove this presentation change.
