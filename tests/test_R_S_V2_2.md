# R/S V2.2 Local Cross-check Runbook

## Objective

Validate one release objective:

> R/S V2.2 adds deterministic daily-OHLCV Volume Profile POC/HVN/LVN and volume confirmation without breaking V2.1 adaptive, point-in-time or proximity-ranking contracts.

## Scope

In scope:
- Volume Profile Engine
- POC / HVN / LVN LEVEL sources
- VOLUME_STRUCTURE family cap
- volume confirmation
- 120-bar configurable profile window
- historical point-in-time behavior
- V2.1 regression
- NiceGUI V2.2 smoke

Out of scope:
- persisted Volume Profile tables
- tick/intraday volume-at-price
- V2.3 historical ablation/calibration

## Step 1 — DuckDB preflight

Run read-only:

```text
src/DuckDB/sql/rs_v2_2_preflight.sql
```

PASS when:
- MWG has at least 30 positive-volume eligible bars;
- default latest-120 window is available;
- no invalid High/Low in benchmark window;
- TotalVolume > 0;
- PriceHigh > PriceLow.

No DDL/data migration is required.

## Step 2 — Focused pytest

```powershell
python -m pytest tests/test_rs_ladder.py -v
```

PASS when all V2.0/V2.1 regressions and V2.2 profile tests pass.

## Step 3 — V2.1 compatibility smoke

```powershell
python -c "from datetime import date; from src.calcEngine.levelLadder import build_level_ladder; r=build_level_ladder('MWG',as_of_date=date(2026,8,28),enabled_sources=('MA','BB','SWING','PREVIOUS_HL','52W_HL','ATR','RSI')); print([(x.rank,x.price,x.strength_score) for x in r.support_levels]); print([(x.rank,x.price,x.strength_score) for x in r.resistance_levels])"
```

PASS when VOLUME_STRUCTURE does not appear and V2.1 invariants remain valid.

## Step 4 — Volume Profile provider smoke

```powershell
python -c "from datetime import date; from src.calcEngine.levelLadder import build_level_ladder; r=build_level_ladder('MWG',as_of_date=date(2026,8,28),enabled_sources=('VOLUME_PROFILE',)); print('S=',[(x.rank,x.price,[s.source_code for s in x.sources]) for x in r.support_levels]); print('R=',[(x.rank,x.price,[s.source_code for s in x.sources]) for x in r.resistance_levels]); print('CONF=',[(x.source_code,x.value,x.reference_price) for x in r.confirmations])"
```

PASS when:
- VP_POC exists;
- zero or more VP_HVN_* / VP_LVN_* exist depending on profile shape;
- every level source family = VOLUME_STRUCTURE;
- confirmations use VOLUME_CONFIRMATION;
- confirmation reference_price corresponds to profile node price.

## Step 5 — Default V2.2 MWG smoke

```powershell
python -c "from datetime import date; from src.calcEngine.levelLadder import build_level_ladder; r=build_level_ladder('MWG',as_of_date=date(2026,8,28)); print('price=',r.current_price,'cluster=',r.cluster_threshold_pct_used,'neutral=',r.neutral_threshold_pct_used); print('S=',[(x.rank,x.price,x.strength_score,x.source_count,x.source_family_count,[s.source_code for s in x.sources]) for x in r.support_levels]); print('R=',[(x.rank,x.price,x.strength_score,x.source_count,x.source_family_count,[s.source_code for s in x.sources]) for x in r.resistance_levels]); print('VP_CONF=',[(x.source_code,x.value,x.reference_price) for x in r.confirmations if x.source_family=='VOLUME_CONFIRMATION'])"
```

PASS criteria:
1. runtime completes;
2. POC/HVN/LVN may enter LEVEL zones;
3. all Volume Profile level candidates are VOLUME_STRUCTURE;
4. multiple Volume Profile nodes still contribute one source family per zone;
5. volume confirmations never become LEVEL candidates;
6. ATR remains context only;
7. RSI remains momentum confirmation only;
8. S1/R1 remain proximity-ranked;
9. Strength remains [0,100];
10. all source_date/confirmed_at <= as_of_date.

## Step 6 — Point-in-time Volume Profile

Run at two historical dates:

```powershell
python -c "from datetime import date; from src.calcEngine.levelLadder import build_level_ladder; [print(d,[(x.rank,x.price,[s.source_code+':'+str(s.source_date) for s in x.sources if s.source_family=='VOLUME_STRUCTURE']) for x in build_level_ladder('MWG',as_of_date=d).support_levels]) for d in (date(2026,7,31),date(2026,8,28))]"
```

PASS when no Volume Profile source_date exceeds each requested date.

## Step 7 — NiceGUI smoke

Open CherryStock → R/S.

PASS when:
- header shows V2.2 Volume Profile;
- chart renders;
- Families may include VOLUME_STRUCTURE;
- sources may include VP_POC / VP_HVN / VP_LVN;
- Refresh MWG works;
- no stale V2.1 empty-state/header remains.

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
BLOCKED    → record blocker and STOP
REGRESSION → revert V2.2 rollout and STOP
```
