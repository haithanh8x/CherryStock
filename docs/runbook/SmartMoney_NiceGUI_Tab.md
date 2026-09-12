# SmartMoney NiceGUI Tab — Vertical MarketState Deployment

- **UI entry:** `src/webapp/NiceGUI_chart.py`
- **Renderer:** `src/webapp/smart_money_tab.py`
- **State-flow model:** `src/webapp/smart_money_state_flow.py`
- **Public data contract:** `"CherryMon"."main"."vw_Ticker_SmartMoney"`
- **Model:** `SMART_MONEY_V1`
- **Validation owner:** `TestEngineer`

## 1. Purpose

Deploy the `SmartMoney` tab immediately after `R/S` with a compact vertical flow:

```text
... → Danh mục → R/S → SmartMoney → Vận Hành
```

Each `MarketState` occupies one **full-width block** and blocks are stacked vertically in canonical flow order.

This is an **UI/read-only deployment**. Do not recalculate SmartMoney and do not rerun historical initload. The historical SmartMoney rollout remains independently governed by `SmartMoneyTradeActionConfidence_V1.md`.

---

## 2. UI contract

The tab reads only the latest available `SMART_MONEY_V1` snapshot from:

```text
"CherryMon"."main"."vw_Ticker_SmartMoney"
```

Canonical vertical block order:

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

Any future unknown `MarketState` is appended after these nine canonical states rather than silently dropped.

### 2.1 MarketState block layout

Every MarketState block must be:

```text
full width
one block per row
vertical ordering only
```

Header contract:

```text
[stage] MARKET_STATE  [TradeAction count badge(s)]                 <total tickers>
        state description
```

Examples:

```text
01  ACCUMULATION  [BUY 75]                                        75 tickers
02  SUPPLY LOCK   [HOLD 1]                                         1 ticker
```

There are **no BUY/HOLD/SELL subgroups below the MarketState**.

TradeAction is summarized beside `MarketState` instead:

```text
BUY <count>
HOLD <count>
SELL <count>
```

Only actions with count greater than zero are rendered. This preserves exceptional cases such as a normally-BUY MarketState containing a `HOLD` ticker because of upstream data-quality rules, without splitting the ticker list into multiple sections.

An empty MarketState remains visible and uses:

```text
NO TICKER
```

### 2.2 Ticker sequence contract

All tickers in one MarketState share a **single sequence**, regardless of TradeAction.

Ordering:

```text
TradeActionConfidenceScore DESC
Ticker ASC  # deterministic tie-break
```

Rendering:

```text
**MCH, VC3**, CTR, CTF, ...
```

Rules:

```text
tickers are separated by ", "
first two tickers are bold
remaining tickers use normal weight
one ticker only -> that ticker is bold
empty state -> no sequence, show empty-state message
```

The ticker string does not display subgroup headings and does not reorder by TradeAction.

`TradeActionConfidenceScore` remains full precision in the public view. The UI ordering uses the original numeric value; bold formatting and comma-separated rendering are presentation-only.

---

## 3. Preconditions

Required upstream state:

```text
SmartMoney historical rollout: PASS / KEEP
vw_Ticker_SmartMoney exists
TradeAction exists
TradeActionConfidenceScore exists
latest SMART_MONEY_V1 snapshot is non-empty
```

Do not rerun historical initload merely to deploy this UI layout.

---

## 4. Step 1 — Safe sync

From repository root:

```powershell
git status --short
```

If unexpected local changes exist:

```text
Verdict: BLOCKED
Action: STOP
```

If clean:

```powershell
git fetch origin
git checkout main
git pull --ff-only origin main
git log -1 --oneline
```

---

## 5. Step 2 — Compile focused UI files

Run:

```powershell
python -m py_compile src\webapp\NiceGUI_chart.py
python -m py_compile src\webapp\smart_money_tab.py
python -m py_compile src\webapp\smart_money_state_flow.py
python -m py_compile scripts\validate_smart_money_ui_snapshot.py
```

Any compile error:

```text
Verdict: FAIL
Action: STOP
```

---

## 6. Step 3 — Focused state-flow unit test

Run only:

```powershell
python -m pytest tests\test_smart_money_state_flow.py -q
```

PASS proves:

```text
canonical MarketState ordering
empty canonical states remain represented
all ticker rows are globally ranked inside MarketState
TradeAction counts still reconcile to MarketState total
no action_rows/subgroup contract remains
ticker sequence is comma-separated
first two confidence-ranked tickers are bold
future unknown MarketState is not dropped
duplicate ticker input is handled deterministically
```

Do not expand automatically to the full pytest suite.

---

## 7. Step 4 — Validate real local snapshot

Run:

```powershell
python scripts\validate_smart_money_ui_snapshot.py
```

Required first line:

```text
SMART MONEY UI SNAPSHOT — PASS
```

The validator is read-only and checks:

```text
latest SMART_MONEY_V1 date exists
snapshot is non-empty
canonical MarketState prefix is preserved
all snapshot tickers are represented exactly once
TradeAction summary counts equal each MarketState total
MarketState rows are TradeActionConfidenceScore DESC
ticker sequence matches the row ranking exactly
first two ticker symbols are bolded in the rendered sequence
```

This step does not write to DuckDB.

---

## 8. Step 5 — Start NiceGUI and visual smoke

Run:

```powershell
python src\webapp\NiceGUI_chart.py
```

Open the existing NiceGUI endpoint, normally:

```text
http://127.0.0.1:8081
```

Validate only:

```text
1. SmartMoney remains immediately after R/S and before Vận Hành.
2. Tab opens without exception.
3. Header shows latest snapshot date and total ticker count.
4. Nine canonical MarketState blocks appear in documented order.
5. Every MarketState block spans full available width.
6. Blocks are stacked vertically, one block per row.
7. BUY/HOLD/SELL subgroup sections are absent.
8. Non-zero TradeAction badge(s) appear beside MarketState name.
9. Tickers are shown as one comma-separated string per MarketState.
10. First two ticker symbols are bold.
11. Ticker order follows TradeActionConfidenceScore descending.
12. Refresh reloads the same/latest public-view snapshot correctly.
13. Empty MarketStates remain visible.
```

Do not judge strategy quality from this smoke test; this validates presentation only.

Stop the NiceGUI process after the smoke check.

---

## 9. PASS / FAIL contract

PASS requires:

```text
focused compile PASS
focused unit test PASS
real snapshot validator PASS
SmartMoney tab placement PASS
full-width vertical block layout PASS
TradeAction-beside-MarketState layout PASS
flat comma-separated ticker sequence PASS
confidence ordering PASS
refresh smoke PASS
```

If any item fails:

```text
Verdict: FAIL | BLOCKED
Action: STOP
```

Do not rerun SmartMoney historical initload as a UI repair action.

---

## 10. Required result

Return only:

```text
SMART MONEY NICEGUI TAB — VERTICAL LAYOUT DEPLOYMENT

HEAD: <sha>
Compile: PASS | FAIL
Focused state-flow test: PASS | FAIL
Snapshot validator: PASS | FAIL | BLOCKED
Snapshot date: <date>
Snapshot tickers: <count>
Tab order R/S -> SmartMoney -> Vận Hành: PASS | FAIL
Nine canonical blocks: PASS | FAIL
Full-width vertical blocks: PASS | FAIL
TradeAction beside MarketState: PASS | FAIL
No TradeAction subgroups: PASS | FAIL
Comma-separated ticker sequence: PASS | FAIL
Top-two ticker emphasis: PASS | FAIL
Ticker confidence order per MarketState: PASS | FAIL
Refresh smoke: PASS | FAIL

Verdict: PASS | FAIL | BLOCKED
Action: KEEP | STOP
```

After terminal verdict, STOP.

---

## 11. Deliberately skipped validation

This UI deployment does not run:

```text
SmartMoney historical initload
smart_money_v1_preflight.sql
SmartMoney integration regression
full pytest suite
run.py daily pipeline
OOS/backtest evaluation
```

Those belong to separate contracts and do not provide additional evidence for this NiceGUI presentation change.
