# R/S V2.0 Local Cross-check Runbook

## Target

Validate one objective only:

> R/S V2.0 uses MA + BB as LEVEL sources, RSI as CONFIRMATION, and source-family confluence without breaking proximity ranking.

## Scope

In scope:

- `src/calcEngine/levelLadder.py`
- `src/Chart/levelLadderChart.py`
- `src/webapp/NiceGUI_chart.py`
- Indicator semantic migration
- MWG real-data smoke test

Out of scope:

- ATR adaptive clustering (V2.1)
- Swing / Previous H-L / 52W levels (V2.1)
- Volume Profile (V2.2)
- historical calibration (V2.3)

## Preconditions

1. Checkout the merged V2.0 code.
2. ATR14 may already be onboarded/backfilled; V2.0 does not consume ATR.
3. CherryMon DuckDB is available locally.
4. MA, BB and RSI D/W/M configurations are enabled and backfilled.

## Step 1 — Run DuckDB migration

Execute this SQL file manually against CherryMon:

```text
src/DuckDB/sql/rs_v2_0_indicator_semantics.sql
```

Do not edit the SQL ad hoc while testing.

### PASS

The validation SELECTs at the end show at minimum:

```text
MA  VALUE    PRICE_LEVEL          PRICE

BB  LOWER    PRICE_LEVEL          PRICE
BB  MIDDLE   PRICE_LEVEL          PRICE
BB  UPPER    PRICE_LEVEL          PRICE
BB  WIDTH    VOLATILITY           PERCENT
BB  PERCENT  RATIO                RATIO

RSI VALUE    OSCILLATOR           INDEX
ATR VALUE    VOLATILITY_DISTANCE  PRICE
```

ATR row is expected only when ATR component metadata exists.

### FAIL

STOP if:

- migration fails;
- `vw_Indicator_config` does not expose `ValueSemantic` and `Unit`;
- MA/BB/RSI required semantics are null/wrong.

Do not continue to runtime testing.

## Step 2 — Refresh generated DB reference

Run the existing metadata export workflow used by CherryStock so these generated files reflect the migrated DB:

```text
docs/reference/DB_Metadata.md
docs/reference/dim_indicator.csv
docs/reference/dim_indicator_component.csv
docs/reference/dim_indicator_config.csv
```

PASS when `DB_Metadata.md` contains `ValueSemantic` and `Unit` under `dim_indicator_component` and `vw_Indicator_config`.

## Step 3 — Focused automated test

From repository root:

```powershell
python -m pytest tests/test_rs_ladder.py -v
```

### PASS

All tests PASS.

### FAIL

If a V2.0 assertion fails, record the exact assertion/error and STOP.

Do not investigate another feature.

## Step 4 — MA-only regression smoke

Run:

```powershell
python -c "from src.calcEngine.levelLadder import build_level_ladder; r=build_level_ladder('MWG', enabled_sources=('MA',)); print(r)"
```

PASS when:

- result returns without error;
- Support/Resistance ranks are ordered by proximity;
- no BB/RSI source appears.

## Step 5 — Default V2.0 real-data smoke

Run:

```powershell
python -c "from src.calcEngine.levelLadder import build_level_ladder; r=build_level_ladder('MWG'); print('date=',r.as_of_date,'price=',r.current_price); print('S=',[(x.rank,x.price,x.strength_score,x.source_count,x.source_family_count) for x in r.support_levels]); print('R=',[(x.rank,x.price,x.strength_score,x.source_count,x.source_family_count) for x in r.resistance_levels]); print('confirmations=',[(x.source_code,x.value) for x in r.confirmations])"
```

### PASS

Confirm all:

1. no runtime/database error;
2. sources contain MA and/or BB level candidates;
3. RSI appears only in `result.confirmations`;
4. each level satisfies `source_family_count <= source_count`;
5. S1 is nearest support below current price;
6. R1 is nearest resistance above current price;
7. `0 <= strength_score <= 100`.

## Step 6 — Semantic safety check

Run:

```powershell
python -c "from datetime import date; from src.calcEngine.levelLadder import CurrentPrice,LevelCandidate,build_level_ladder_from_data; c=CurrentPrice('MWG',date(2026,8,28),100); bad=LevelCandidate('MWG',95,'INDICATOR','RSI14_D','D','RSI',16,'RSI14_D','VALUE',date(2026,8,28),value_semantic='OSCILLATOR'); build_level_ladder_from_data(c,[bad])"
```

PASS only when the command fails clearly with:

```text
ValueSemantic=PRICE_LEVEL
```

## Step 7 — NiceGUI smoke

Open the existing CherryStock NiceGUI chart page and select the **R/S** tab.

PASS when:

- header shows V2.0 MA + Bollinger Bands / RSI confirmation;
- chart renders;
- Level Details contains source families;
- Refresh on MWG works;
- no stale V1 MA-only empty-state text appears.

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
BLOCKED    → record environment/dependency blocker and STOP
REGRESSION → revert V2.0 deployment and STOP
```
