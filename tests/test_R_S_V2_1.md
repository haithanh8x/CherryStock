# R/S V2.1 Local Cross-check Runbook

## Objective

Validate one release objective:

> R/S V2.1 adds ATR-adaptive clustering/neutral distance and point-in-time structural levels without breaking V2.0 ranking, semantic safety or UI behavior.

## Scope

In scope:

- ATR14_D context
- adaptive cluster threshold
- adaptive neutral threshold
- Swing High / Low
- Previous Week High / Low
- Previous Month High / Low
- 52W High / Low
- point-in-time / no-lookahead
- structural quality contribution
- MA/BB/RSI V2.0 regression
- NiceGUI V2.1 smoke

Out of scope:

- Volume Profile / POC / HVN / LVN (V2.2)
- historical ablation / calibration (V2.3)
- persistence tables / vw_Ticker_RS

## Step 1 — DuckDB preflight

Run manually:

```text
src/DuckDB/sql/rs_v2_1_preflight.sql
```

PASS when:

- ATR14_D exists;
- IndicatorCode=ATR;
- Timeframe=D;
- ComponentCode=VALUE;
- ValueSemantic=VOLATILITY_DISTANCE;
- Unit=PRICE;
- config/indicator/component active;
- ATR calculated values are positive and available for MWG benchmark;
- raw_stock_eod has sufficient ~52W history and usable High/Low.

No database migration is required for V2.1.

## Step 2 — Focused pytest

```powershell
python -m pytest tests/test_rs_ladder.py -v
```

PASS when all V2.0 + V2.1 tests pass.

STOP on first reproducible regression.

## Step 3 — V2.0 compatibility smoke

MA-only:

```powershell
python -c "from src.calcEngine.levelLadder import build_level_ladder; r=build_level_ladder('MWG', as_of_date=__import__('datetime').date(2026,8,28), enabled_sources=('MA',)); print([(x.rank,x.price,x.strength_score) for x in r.support_levels]); print([(x.rank,x.price,x.strength_score) for x in r.resistance_levels])"
```

PASS when:

- only MA sources exist;
- S1/R1 remain proximity ranked;
- no ATR/structural source appears.

## Step 4 — ATR adaptive smoke

```powershell
python -c "from datetime import date; from src.calcEngine.levelLadder import build_level_ladder; r=build_level_ladder('MWG',as_of_date=date(2026,8,28),enabled_sources=('MA','BB','ATR','RSI')); print('contexts=',[(x.source_code,x.value,x.source_date) for x in r.market_contexts]); print('cluster=',r.cluster_threshold_pct_used,'neutral=',r.neutral_threshold_pct_used)"
```

PASS when:

- ATR14_D appears in market_contexts;
- cluster threshold >= 0.01;
- neutral threshold >= 0.003;
- thresholds are deterministic for same as_of_date.

## Step 5 — Structural provider smoke

```powershell
python -c "from datetime import date; from src.calcEngine.levelLadder import build_level_ladder; r=build_level_ladder('MWG',as_of_date=date(2026,8,28),enabled_sources=('SWING','PREVIOUS_HL','52W_HL')); print('S=',[(x.rank,x.price,[(s.source_code,s.source_date,s.confirmed_at) for s in x.sources]) for x in r.support_levels]); print('R=',[(x.rank,x.price,[(s.source_code,s.source_date,s.confirmed_at) for s in x.sources]) for x in r.resistance_levels])"
```

PASS when:

- structural source codes are present;
- all sources satisfy `source_date <= 2026-08-28`;
- all sources satisfy `confirmed_at <= 2026-08-28`;
- Previous Week/Month levels come from completed prior periods;
- no future bar is used.

## Step 6 — Default V2.1 smoke

```powershell
python -c "from datetime import date; from src.calcEngine.levelLadder import build_level_ladder; r=build_level_ladder('MWG',as_of_date=date(2026,8,28)); print('price=',r.current_price,'cluster=',r.cluster_threshold_pct_used,'neutral=',r.neutral_threshold_pct_used); print('S=',[(x.rank,x.price,x.strength_score,x.source_count,x.source_family_count,[s.source_code for s in x.sources]) for x in r.support_levels]); print('R=',[(x.rank,x.price,x.strength_score,x.source_count,x.source_family_count,[s.source_code for s in x.sources]) for x in r.resistance_levels]); print('ATR=',[(x.source_code,x.value) for x in r.market_contexts]); print('RSI=',[(x.source_code,x.value) for x in r.confirmations])"
```

PASS criteria:

1. runtime completes without error;
2. ATR14_D is context only;
3. RSI is confirmation only;
4. MA/BB and structural sources may create LEVEL candidates;
5. `source_family_count <= source_count`;
6. S1 is nearest eligible support;
7. R1 is nearest eligible resistance;
8. all Strength scores are in [0,100];
9. all structural `confirmed_at <= as_of_date`;
10. cluster/neutral thresholds match ATR-adaptive formula.

## Step 7 — Historical point-in-time comparison

Run default V2.1 for at least two historical dates, for example:

```powershell
python -c "from datetime import date; from src.calcEngine.levelLadder import build_level_ladder; [print(d,[(x.rank,x.price,[s.source_code for s in x.sources]) for x in build_level_ladder('MWG',as_of_date=d).support_levels]) for d in (date(2026,7,31),date(2026,8,28))]"
```

PASS when the older result contains no source whose source/confirmation date belongs to the future relative to that older date.

## Step 8 — NiceGUI smoke

Open CherryStock NiceGUI → R/S.

PASS when:

- header shows V2.1 ATR adaptive + structural sources;
- Min Cluster % control is present;
- Refresh MWG works;
- notification shows actual cluster/neutral percentages;
- Families can include MARKET_STRUCTURE;
- chart and Level Details render normally;
- no V2.0 stale empty-state text remains.

## Final Verdict

Use exactly one:

```text
PASS
FAIL
BLOCKED
REGRESSION
```

Action:

```text
PASS       → KEEP and STOP
FAIL       → record exact failure and STOP
BLOCKED    → record dependency/environment blocker and STOP
REGRESSION → revert V2.1 rollout and STOP
```
