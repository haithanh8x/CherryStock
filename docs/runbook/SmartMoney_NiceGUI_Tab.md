# SmartMoney NiceGUI Tab — Deployment & Focused Validation

- **UI entry:** `src/webapp/NiceGUI_chart.py`
- **Renderer:** `src/webapp/smart_money_tab.py`
- **State-flow model:** `src/webapp/smart_money_state_flow.py`
- **Public data contract:** `"CherryMon"."main"."vw_Ticker_SmartMoney"`
- **Model:** `SMART_MONEY_V1`
- **Validation owner:** `TestEngineer`

## 1. Purpose

Deploy the `SmartMoney` tab immediately after `R/S` in `NiceGUI_chart.py` and validate only the UI/read contract.

Expected tab order:

```text
... → Danh mục → R/S → SmartMoney → Vận Hành
```

This runbook does **not** recalculate SmartMoney and does **not** run historical initload. The historical SmartMoney rollout is an upstream prerequisite and remains independently governed by `SmartMoneyTradeActionConfidence_V1.md`.

---

## 2. UI contract

The tab reads only the latest available `SMART_MONEY_V1` date from:

```text
"CherryMon"."main"."vw_Ticker_SmartMoney"
```

Each `MarketState` is one block.

Canonical flow order:

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

The primary progression intentionally follows:

```text
ACCUMULATION
→ SUPPLY_LOCK
→ demand / fresh-flow expansion
→ BREAKOUT
→ MARKUP
→ DISTRIBUTION
```

`SELLING_CLIMAX`, `LIQUIDITY_DRYUP` and `NEUTRAL` remain explicit blocks so no current `MarketState` is hidden. Any future unknown state is appended after the canonical states instead of being dropped.

Each block must show:

```text
MarketState
state description
total distinct tickers
BUY count
HOLD count
SELL count
```

Below the summary, ticker rows are split into three explicit `TradeAction` subgroups in this order:

```text
BUY
HOLD
SELL
```

Each subgroup shows its own count and ticker list. Empty subgroups remain visible as `0 / Không có ticker`, so the action breakdown is explicit rather than inferred from missing UI.

Ticker order **inside each TradeAction subgroup**:

```text
TradeActionConfidenceScore DESC
Ticker ASC   # deterministic tie-break
```

Ticker rows show:

```text
Ticker
TradeAction
TradeActionConfidenceScore
SmartMoneyScore
ConfidenceScore
```

`TradeActionConfidenceScore` keeps full precision in the public view. The UI may display it rounded to two decimals; display rounding must not be written back to the model/view.

---

## 3. Preconditions

Before deployment:

```text
SmartMoney historical rollout: PASS / KEEP
vw_Ticker_SmartMoney exists
TradeAction exists
TradeActionConfidenceScore exists
latest SMART_MONEY_V1 snapshot is non-empty
```

Do not rerun historical initload merely to deploy this tab.

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
canonical MarketState block ordering
empty canonical blocks remain visible
BUY/HOLD/SELL counts match block total
BUY/HOLD/SELL subgroups are materialized explicitly
ticker ranking inside each subgroup is TradeActionConfidenceScore DESC
future unknown state is not dropped
duplicate ticker input is handled deterministically
```

Do not expand automatically to the full pytest suite.

---

## 7. Step 4 — Validate the real local snapshot

Run:

```powershell
python scripts\validate_smart_money_ui_snapshot.py
```

Required result starts with:

```text
SMART MONEY UI SNAPSHOT — PASS
```

The validator is read-only and checks:

```text
latest SMART_MONEY_V1 date exists
snapshot contains tickers
canonical block order is preserved
all snapshot tickers are represented exactly once in UI blocks
action counts sum to each block total
each BUY/HOLD/SELL subgroup count matches its rows
TradeActionConfidenceScore is descending inside each subgroup
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

Validate only these UI items:

```text
1. SmartMoney tab appears immediately after R/S and before Vận Hành.
2. Tab opens without exception.
3. Header shows latest SmartMoney date and total ticker count.
4. Nine canonical MarketState blocks appear in the documented order.
5. Every block shows total tickers and BUY/HOLD/SELL summary counts.
6. Every non-empty block contains explicit BUY/HOLD/SELL subgroup sections.
7. Tickers inside each subgroup are ordered by TradeActionConfidenceScore descending.
8. Refresh reloads the latest public-view snapshot.
9. Empty MarketStates render as an empty block, not as a missing block.
```

Do not judge Strategy quality from this visual smoke; this step validates rendering only.

Stop the NiceGUI process after the smoke check.

---

## 9. PASS / FAIL contract

PASS requires:

```text
focused compile PASS
focused unit test PASS
real snapshot validator PASS
SmartMoney tab placement PASS
SmartMoney tab render PASS
TradeAction subgroup render PASS
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
SMART MONEY NICEGUI TAB — DEPLOYMENT

HEAD: <sha>
Compile: PASS | FAIL
Focused state-flow test: PASS | FAIL
Snapshot validator: PASS | FAIL | BLOCKED
Snapshot date: <date>
Snapshot tickers: <count>
Tab order R/S -> SmartMoney -> Vận Hành: PASS | FAIL
Nine canonical blocks: PASS | FAIL
TradeAction subgroups: PASS | FAIL
Ticker confidence order per subgroup: PASS | FAIL
Refresh smoke: PASS | FAIL

Verdict: PASS | FAIL | BLOCKED
Action: KEEP | STOP
```

After the terminal verdict, STOP.

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

Those belong to their own contracts and are not evidence for whether the NiceGUI tab renders the already-validated public SmartMoney snapshot correctly.
