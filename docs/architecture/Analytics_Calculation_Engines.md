# CherryStock Analytics & Calculation Engines

- **Status:** DRAFT_PENDING_ARCHIFY_RENDER
- **Owner:** `.github/agents/SolutionArchitect.agent.md`
- **Parent:** `docs/architecture/CherryStock_High_Level.md` → **Analytics & Calculation Engines**
- **Archify source:** `docs/architecture/diagrams/cherrystock-analytics-calculation-engines.architecture.json`
- **Generated HTML:** `docs/architecture/generated/CherryStock_Analytics_Calculation_Engines.html`
- **Mapped repository revision:** `cec702c6788a75f6f430be11dc3055c955dc4e0c`

## Purpose

This document drills down the **Analytics & Calculation Engines** component from the CherryStock high-level architecture. It separates three runtime concerns that are grouped together at system level:

1. the transactional **daily calculation pipeline**;
2. the read/on-demand **R/S Runtime Ladder** path;
3. the independent **monthly R/S historical research/effectiveness** path.

REQ-0027 now uses an isolated **ZigZag Swing Engine MWG MVP** as the segmentation foundation. The MVP is manual and intentionally remains outside the canonical daily pipeline until MWG pivot validation is accepted.

## Navigation Contract

`CherryStock_High_Level.html` is the root/main architecture map. The high-level node with stable Archify id `analytics` drills down to this generated detail page:

```text
CherryStock_High_Level.html
        │
        │ double-click: Analytics & Calculation Engines
        ▼
CherryStock_Analytics_Calculation_Engines.html
        │
        └─ ← High Level
```

The mapping is configuration-driven in:

```text
docs/architecture/diagrams/cherrystock-archify-navigation.json
```

and is injected after every Archify delivery by:

```text
scripts/customize_archify_navigation.py
```

Both generated files live in the same `docs/architecture/generated/` directory, so navigation uses relative HTML links and works when opened locally as files as well as when hosted as static artifacts.

## Detailed Flow

```text
Validated DuckDB analytics inputs
        │
        ▼
SyncWritePipelineService / shared DuckDBUnitOfWork
        │
        ├─ 1. Composite Index Engine
        │       └─> cal_Indexes
        │           └─> blocking stage DQ
        │
        ├─ 2. Trend & Moving Average
        │       └─> cal_Trends
        │           └─> blocking stage DQ
        │
        ├─ 3. Technical Indicator Engine
        │       └─> cal_indicator_values
        │           └─> vw_Ticker_indicators + vw_Indicator_config
        │               └─> blocking stage DQ
        │
        └─ 4. SmartMoneyScore Engine
                └─> cal_smart_money_factor_values
                    + cal_smart_money_ticker_score
                    └─> vw_Ticker_SmartMoney
                        └─> blocking stage DQ

Indicator public contracts + market/price inputs
        │
        ▼
R/S Runtime Ladder
levels → normalize → cluster → classify → strength → rank
        │
        ▼
LevelLadderResult
        │
        ▼
Web / Chart / Screener consumers

runMonthly.py
        │
        ▼
R/S V2.4 Full Evaluation
        │
        ├─ baseline evaluation
        ├─ source/family ablation
        ├─ Source Effectiveness
        └─ Source Promotion Gate
        │
        ▼
cal_rs_source_effectiveness_run
cal_rs_source_effectiveness
sys_rs_source_promotion_audit
vw_RS_Source_Effectiveness
```

## 1. Daily Analytics Order

The authoritative implemented daily order is owned by `SyncWritePipelineService.run()`. ZigZag is not part of this order during the MWG MVP:

```text
Composite Index
→ Trend / Moving Average
→ Technical Indicators
→ SmartMoneyScore
```

The ordering is orchestration order, not an assertion that each engine consumes every prior engine's persistence output. Each engine resolves its own required input contracts from the shared DuckDB transaction context.

All daily calculation writes participate in the same `DuckDBUnitOfWork` opened by `run.py`. Blocking Data Quality failure before commit rolls back the daily write set.

### Composite Index Engine

**Implementation:** `src/calcEngine/calcIndexes.py`

Primary inputs:

```text
raw_index_eod        → VNINDEX base/reference value
raw_lstTicker        → ticker universe
raw_stock_fa         → Shares Float
raw_stock_eod        → ticker Close history
```

Current calculation:

```text
calculate_VNINDEX_NOT_VIN()
→ capitalization-weighted composite index
→ divisor adjustment when constituent/share structure changes
→ cal_Indexes
```

Current persisted key/identity:

```text
INDEX_NAME = VNINDEX_NOT_VIN
Date
```

Daily DQ validates the calculated `cal_Indexes` series after persistence.

### Trend & Moving Average Engine

**Implementation:** `src/calcEngine/calc_fv_Trend.py`

Inputs:

```text
raw_lstTicker.status = 'Y'
raw_stock_eod.Close
```

Outputs:

```text
MA20
MA50
MA100
MA200
MA20_W
MA50_W
MA20_M
MA50_M
```

Persistence:

```text
cal_Trends
PK: Ticker / Date
```

The implementation loads enough history to preserve long-window calculations and only limits the rows being upserted by the checkpoint window.

### Technical Indicator Engine

**Implementation:** `src/calcEngine/calcIndicators.py`

Architecture contract: `docs/architecture/Indicator_Engine.md`.

Core contract:

```text
raw_stock_eod
      +
dim_indicator
dim_indicator_component
dim_indicator_config
      ↓
vw_Indicator_config
      ↓
refresh_technical_indicators()
      ↓
cal_indicator_values
      ↓
vw_Ticker_indicators
```

`cal_indicator_values` is internal long-format persistence. `vw_Ticker_indicators` is the downstream calculated-value SSOT and `vw_Indicator_config` is the public configuration SSOT.

Normal finite-window indicators use configured warmup/checkpoint behavior. Cumulative full-history indicators such as OBV and AD reload history from inception so incremental calculation preserves the same cumulative baseline as historical backfill.

### ZigZag Swing Engine — MWG MVP

**Status:** implemented for manual MWG validation; not part of run.py.

**Architecture contract:** docs/architecture/ZigZag_Engine.md.

**Requirement / decisions:** REQ-0027 / ADR-012 / ADR-013.

MVP path:

    vw_Ticker_OHLC_D (MWG only)
            ↓
    O(n) percentage-reversal ZigZag
            ↓
    cal_zigzag_pivot
    cal_zigzag_current_leg
            ↓
    vw_Ticker_ZigZag_Pivots
    vw_Ticker_ZigZag_Swings
    vw_Ticker_ZigZag_Current

The ZigZag engine uses High/Low for candidate extrema and Close for 5% reversal confirmation.
It has no ATR dependency and stores PivotDate separately from ConfirmedAtDate.

The previous Price Movement daily persistence/ATR segmentation implementation was rolled back.
Higher-level magnitude/velocity/persistence work is deferred until the MWG ZigZag gate is accepted.

### SmartMoneyScore Engine

**Implementation:** `src/calcEngine/smartMoneyScore.py`

Architecture contract: `docs/architecture/SmartMoneyScore.md`.

Core analytical stages:

```text
MarketData / Benchmark / optional Indicator / MarketLimit evidence
        ↓
SmartMoney Feature Engine
        ↓
cal_smart_money_factor_values
        ↓
Normalization
        ↓
State Detection
        ↓
State-Aware Scoring
        ↓
Confidence
        ↓
cal_smart_money_ticker_score
        ↓
vw_Ticker_SmartMoney
```

SmartMoney is a separate analytical domain, not an Indicator Engine subtype. When indicator evidence is required it consumes public Indicator Engine contracts rather than directly coupling to `cal_indicator_values`.

REQ-0027 V1 does not change SmartMoneyScore inputs or weights. Any future consumption of Price Movement public contracts by SmartMoney requires its own approved requirement/design change.

## 2. R/S Runtime Ladder — Read / On-Demand Path

**Implementation:** `src/calcEngine/levelLadder.py`

Architecture contract: `docs/architecture/RS_Ladder.md`.

The R/S Runtime Ladder is intentionally separated from the daily transactional calculation order. It resolves current price and candidate level sources when requested and builds a chart/domain result:

```text
PriceProvider
→ LevelSourceProvider
→ LevelNormalizer
→ LevelClusterEngine
→ LevelClassifier
→ LevelStrengthEngine
→ LevelRanker
→ LadderBuilder
→ LevelLadderResult
```

Key public input contracts include:

```text
raw_stock_eod
vw_Ticker_indicators
vw_Indicator_config
```

The runtime ladder does not duplicate Indicator Engine calculations and does not treat `cal_indicator_values` as its downstream public contract.

## 3. Monthly R/S V2.4 Historical Research Path

**Entry point:** `runMonthly.py`

**Orchestration:** `src/Orchestrator/rs_v2_4_full_evaluation.py`

**Calculation modules:**

```text
src/calcEngine/rsEvaluation.py
src/calcEngine/rsSourceEffectiveness.py
src/calcEngine/rsSourceIdentity.py
```

The monthly runner currently invokes one configured job: **R/S V2.4 Full Source Effectiveness Evaluation**.

V2.4 evaluates current R/S provider behavior through reproducible baseline vs ablation runs:

```text
R/S Runtime Providers
      ↓
Stable Source Identity
      ├─> V2.3 Baseline
      └─> V2.3 Ablation
               ↓
       Source Effectiveness
               ↓
       per-ticker recommendation
               ↓
       Source Promotion Gate
```

Persistence:

```text
cal_rs_source_effectiveness_run
cal_rs_source_effectiveness
sys_rs_source_promotion_audit
vw_RS_Source_Effectiveness
```

V2.4 is research/governance. It does **not** automatically mutate runtime provider registration, Indicator metadata or production runtime weights.

## Calculation Boundary Summary

| Path | Trigger | Main calculation | Persistence / Output | Transaction relationship |
| --- | --- | --- | --- | --- |
| Composite Index | daily | `calculate_VNINDEX_NOT_VIN()` | `cal_Indexes` | shared daily UoW |
| Trend / MA | daily | `cal_Moving_Average()` | `cal_Trends` | shared daily UoW |
| Indicator Engine | daily | `refresh_technical_indicators()` | `cal_indicator_values` → `vw_Ticker_indicators` | shared daily UoW |
| ZigZag Swing Engine | manual MWG MVP | O(n) 5% reversal pivot segmentation | `cal_zigzag_pivot`, `cal_zigzag_current_leg` → three public views | separate manual UoW; not in run.py |
| SmartMoneyScore | daily | `refresh_smart_money_score()` | factor + score tables → `vw_Ticker_SmartMoney` | shared daily UoW |
| R/S Runtime Ladder | on demand / consumer | `build_level_ladder()` family | `LevelLadderResult` | read/calculation path, separate from daily writer |
| R/S V2.4 Evaluation | monthly/manual | baseline + ablation + effectiveness | `cal_rs_source_effectiveness*`, audit + public view | separate monthly research run |

## Archify Artifact Pair

Typed source:

```text
docs/architecture/diagrams/cherrystock-analytics-calculation-engines.architecture.json
```

Generated HTML:

```text
docs/architecture/generated/CherryStock_Analytics_Calculation_Engines.html
```

Preferred validation/render command:

```powershell
.\scripts\render_archify_analytics.ps1
```

The shared repository renderer performs:

```text
showcase validation
→ Archify delivery
→ CherryStock typography/font picker
→ CherryStock drill-down/back navigation
```

Until the command above succeeds and the generated HTML is committed, this drill-down remains `DRAFT_PENDING_ARCHIFY_RENDER` under the repository artifact synchronization contract.

## Related Architecture

- `docs/architecture/CherryStock_High_Level.md`
- `docs/architecture/Data_Architecture.md`
- `docs/architecture/Indicator_Engine.md`
- `docs/architecture/ZigZag_Engine.md`
- `docs/architecture/Price_Movement_Character.md`
- `docs/architecture/SmartMoneyScore.md`
- `docs/architecture/RS_Ladder.md`
- `docs/architecture/RS_Source_Effectiveness.md`
- `docs/runbook/Daily_Data_Pipeline.md`

## ADR

- `ADR-012` owns the stateful analytics domain boundary; `ADR-013` owns the ZigZag segmentation decision and MWG-first rollout.
- No new ADR is required for the pre-existing calculation-engine drill-down itself.
