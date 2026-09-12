# SmartMoneyStrategy V1 — BUY / HOLD / SELL

- **Requirement:** [[../backlog/requirements/REQ-0026-smart-money-strategy|REQ-0026]]
- **Upstream model:** [[SmartMoneyScore|SmartMoneyScore V1]]
- **Public contract:** `"CherryMon"."main"."vw_Ticker_SmartMoney"`
- **Strategy output:** `TradeAction`
- **Status:** FUNCTIONALLY_VALIDATED

## Purpose

`SmartMoneyStrategy V1` converts the rich SmartMoneyScore state model into one simple downstream action:

```text
BUY
HOLD
SELL
```

The strategy does **not** replace `SmartMoneyScore`, `ConfidenceScore`, `MarketState` or component scores. It is a thin, deterministic interpretation layer so Screener, Chart, Dashboard and research consumers do not each invent a different BUY/HOLD/SELL mapping.

The strategy is technical classification only. It does not place orders, size positions, define stop-loss/take-profit, or represent personalized investment advice.

---

# 1. Output Contract

`TradeAction` is exposed directly by:

```text
"CherryMon"."main"."vw_Ticker_SmartMoney"
```

Allowed values:

```text
BUY
HOLD
SELL
```

Properties:

- non-NULL for every public Smart Money row;
- derived from the row's existing `DataQualityStatus` and primary `MarketState`;
- not persisted in `cal_smart_money_ticker_score`;
- not persisted in `cal_smart_money_factor_values`;
- does not alter the SmartMoney model/factor calculation;
- preserves the existing public grain `Ticker + Date + enabled ModelCode/ModelVersion`.

`TradeAction` is therefore a presentation/strategy contract over the existing Smart Money Source of Truth, not a second Source of Truth.

---

# 2. Rule Precedence

Strategy V1 uses the following deterministic precedence:

```text
1. DataQualityStatus != PASS
      → HOLD

2. MarketState = DISTRIBUTION
      → SELL

3. MarketState IN (
       ACCUMULATION,
       BREAKOUT,
       DEMAND_EXPANSION,
       SUPPLY_LOCK
   )
      → BUY

4. Everything else
      → HOLD
```

Equivalent SQL contract:

```sql
CASE
    WHEN DataQualityStatus <> 'PASS' THEN 'HOLD'
    WHEN MarketState = 'DISTRIBUTION' THEN 'SELL'
    WHEN MarketState IN (
        'ACCUMULATION',
        'BREAKOUT',
        'DEMAND_EXPANSION',
        'SUPPLY_LOCK'
    ) THEN 'BUY'
    ELSE 'HOLD'
END AS TradeAction
```

The quality gate is intentionally first. A bullish/bearish state with incomplete or low-confidence evidence does not emit an actionable BUY/SELL label in V1.

---

# 3. BUY

## Meaning

`BUY` means SmartMoneyScore V1 has classified the ticker into a **bullish participation/setup state** and the evidence quality has passed the current production gate.

It means:

```text
DataQualityStatus = PASS
AND
MarketState ∈ {
    ACCUMULATION,
    BREAKOUT,
    DEMAND_EXPANSION,
    SUPPLY_LOCK
}
```

It does **not** mean all four bullish states are simultaneously true. `MarketState` is one primary state after V1 precedence resolves competing evidence.

## BUY state conditions

### 3.1 ACCUMULATION → BUY

Purpose: detect multi-session accumulation before or during an emerging move.

Implemented state condition:

```text
AccumulationScore >= STATE_ACCUMULATION_THRESHOLD (65)
AND
AccumulationMemoryScore >= 60
```

Main evidence:

- persistent strong Close Location Value;
- Relative Strength versus VNINDEX;
- optional OBV/AD slope improvement;
- multi-session accumulation memory.

`AccumulationScore` raw evidence:

```text
AccumulationRaw = mean(
    CLV20,
    RS20 × 10,
    OBVSlope20,
    ADSlope20
)
```

At least 2 of the 4 evidence components must be available; the raw value is then normalized by same-date cross-sectional percentile.

Memory:

```text
AccumulationMemory_t
≈ 0.90 × AccumulationMemory_(t-1)
 + 0.10 × AccumulationScore_t
```

Interpretation: Strategy V1 treats confirmed accumulation as an early BUY/setup action rather than waiting exclusively for the breakout day.

### 3.2 BREAKOUT → BUY

Purpose: detect fresh participation pushing price with abnormal liquidity and relative strength.

Implemented state condition:

```text
FreshFlowScore >= STATE_BREAKOUT_THRESHOLD (70)
AND
RelativeLiquidityScore >= 70
AND
RelativeStrengthScore >= 60
```

Fresh Flow raw formula:

```text
FreshFlowRaw =
    (CLV + 2 × Return5 + 1.5 × RS5)
    × ln(1 + max(RVAL20, 0))
```

Then:

```text
FreshFlowScore = same-date cross-sectional percentile(FreshFlowRaw)
```

Key confirmation:

```text
new participation
+ strong close/short-term price impulse
+ abnormal current liquidity
+ strength versus VNINDEX
```

### 3.3 DEMAND_EXPANSION → BUY

Purpose: detect broadening demand before/without requiring the stricter FreshFlow breakout threshold.

Implemented state condition:

```text
RelativeLiquidityScore >= 70
AND
LiquidityAccelerationScore >= 65
AND
RelativeStrengthScore >= 55
```

Supporting formulas:

```text
RVAL20 = TradingValue / ALV20

LiquidityAccelerationRaw = ALV5 / ALV20

ALV5  = MA5(TradingValue)
ALV20 = MA20(TradingValue)
```

The raw liquidity measures are normalized cross-sectionally for the same trading date.

Interpretation: current participation is elevated, the recent liquidity baseline is accelerating, and price strength remains better than the benchmark/universe context.

### 3.4 SUPPLY_LOCK → BUY

Purpose: identify a bullish shortage of available supply after prior accumulation, even when current volume is not expanding.

Implemented state condition:

```text
SupplyLockScore >= STATE_SUPPLY_LOCK_THRESHOLD (70)
AND
AccumulationMemoryScore >= 60
```

`SupplyLockScore` is a conjunctive/geometric composite of available evidence:

```text
AccumulationMemory
CloseStrength
RelativeStrength
Trend
LiquidityCompression
```

At least 4/5 components are required. The composite is then penalized by Distribution evidence:

```text
SupplyLockScore
= GeometricComposite(...)
  × (1 - DistributionScore / 100)
```

Interpretation:

```text
prior accumulation remains present
+ price/RS/trend stay strong
+ available supply/liquidity contracts
+ distribution remains low
```

Low volume alone never produces a bullish Supply Lock conclusion.

---

# 4. HOLD

## Meaning

`HOLD` means **Strategy V1 does not emit a new BUY or SELL action** for the row.

Important semantic boundary:

- if the ticker is already held, `HOLD` can be interpreted as no strategy-driven change;
- if the ticker is not held, `HOLD` should be read as `WAIT / NO NEW ACTION`;
- it is not a guarantee that an investor should literally keep an existing position.

## HOLD condition A — evidence quality is not PASS

```text
DataQualityStatus != PASS
→ HOLD
```

Current SmartMoneyScore V1 quality contract:

```text
INVALID
  if SmartMoneyScore is NULL

PASS
  if ConfidenceScore >= 60
  AND FactorCoverage >= 0.80

WARNING
  otherwise
```

Therefore a technically bullish `MarketState` cannot emit `BUY` when its supporting evidence has only WARNING/INVALID quality.

## HOLD condition B — MARKUP

Implemented MARKUP state:

```text
TrendScore >= STATE_MARKUP_THRESHOLD (65)
AND
RelativeStrengthScore >= 60
```

Strategy interpretation:

`MARKUP` describes an existing positive trend/strength phase. V1 maps it to HOLD rather than repeatedly generating a fresh BUY each day after the initial setup/participation phase.

## HOLD condition C — LIQUIDITY_DRYUP

Implemented state condition:

```text
LiquidityCompressionScore >= STATE_DRYUP_THRESHOLD (75)
AND
RelativeStrengthScore < 55
```

Liquidity compression alone has no bullish meaning. Because RS is weak in this state rule, V1 does not promote it to BUY.

## HOLD condition D — SELLING_CLIMAX

Implemented state condition:

```text
DistributionScore >= 60
AND
RelativeLiquidityScore >= 80
AND
Return1 < 0
```

A selling climax can represent continuing risk or late-stage capitulation/exhaustion. V1 therefore does not infer an automatic SELL or bottom-fishing BUY from this state alone.

## HOLD condition E — NEUTRAL

No stronger supported state condition is satisfied.

```text
MarketState = NEUTRAL
→ HOLD
```

---

# 5. SELL

## Meaning

`SELL` means the primary Smart Money state is `DISTRIBUTION` and the evidence quality passes the production gate.

Condition:

```text
DataQualityStatus = PASS
AND
MarketState = DISTRIBUTION
```

Implemented Distribution state:

```text
DistributionScore >= STATE_DISTRIBUTION_THRESHOLD (70)
```

Distribution raw evidence:

```text
Participation = max(RVAL20 - 1, 0)

DistributionRaw =
    Participation
    × [
        0.40 × max(-CLV, 0)
      + 0.35 × max(-Return5, 0) × 10
      + 0.25 × max(-RS20, 0) × 10
      ]
```

Then:

```text
DistributionScore =
same-date cross-sectional percentile(DistributionRaw)
```

This looks for the dangerous combination:

```text
participation/liquidity high
+ Close weak / near Low
+ short-term return weak
+ Relative Strength deteriorating
```

`DISTRIBUTION` has the highest MarketState precedence in SmartMoneyScore V1. A ticker that also satisfies a lower-precedence bullish state can therefore still finish as `DISTRIBUTION`, which maps to `SELL` when quality is PASS.

---

# 6. Action Matrix

| DataQualityStatus | Primary MarketState | TradeAction | Strategy meaning |
|---|---|---|---|
| not `PASS` | any | `HOLD` | Evidence quality insufficient for BUY/SELL |
| `PASS` | `ACCUMULATION` | `BUY` | Early accumulation/setup confirmed |
| `PASS` | `BREAKOUT` | `BUY` | Fresh flow + abnormal liquidity + RS confirmed |
| `PASS` | `DEMAND_EXPANSION` | `BUY` | Demand/liquidity expanding with strength |
| `PASS` | `SUPPLY_LOCK` | `BUY` | Prior accumulation + strong price/RS + supply contraction |
| `PASS` | `MARKUP` | `HOLD` | Trend already in progress; manage rather than re-trigger entry |
| `PASS` | `DISTRIBUTION` | `SELL` | High-participation weak price behavior / distribution |
| `PASS` | `LIQUIDITY_DRYUP` | `HOLD` | Low liquidity without enough bullish confirmation |
| `PASS` | `SELLING_CLIMAX` | `HOLD` | Capitulation ambiguous; no automatic action |
| `PASS` | `NEUTRAL` | `HOLD` | No actionable Smart Money state |

---

# 7. Important Fields by Action

## BUY evidence

The most useful fields when `TradeAction='BUY'` are:

| Field | Why it matters |
|---|---|
| `MarketState` | Identifies which BUY setup generated the action |
| `SmartMoneyScore` | Overall positive Smart Money evidence after Distribution penalty |
| `ConfidenceScore` | Trustworthiness of the conclusion |
| `FreshFlowScore` | Fresh money/price participation, especially BREAKOUT |
| `RelativeLiquidityScore` | Current abnormal liquidity |
| `LiquidityAccelerationScore` | Recent liquidity expansion |
| `RelativeStrengthScore` | Strength versus VNINDEX |
| `AccumulationScore` | Current accumulation evidence |
| `AccumulationMemoryScore` | Persistence of prior accumulation |
| `SupplyLockScore` | Bullish supply contraction evidence |
| `DistributionScore` | Contradictory/negative evidence to monitor |

## HOLD management

Important fields:

```text
MarketState
SmartMoneyScore
ConfidenceScore
TrendScore
RelativeStrengthScore
AccumulationMemoryScore
DistributionScore
```

HOLD should be monitored for transition into a new actionable state, especially:

```text
ACCUMULATION / SUPPLY_LOCK → BREAKOUT
MARKUP → DISTRIBUTION
WARNING → PASS
```

## SELL risk

Primary fields:

```text
MarketState = DISTRIBUTION
DistributionScore
RelativeLiquidityScore
RelativeStrengthScore
SmartMoneyScore
ConfidenceScore
```

A SELL label should always be explainable through the Distribution state and evidence quality rather than being inferred from a low SmartMoneyScore alone.

---

# 8. Public View Construction

The existing score/factor persistence remains authoritative:

```text
cal_smart_money_ticker_score
        +
cal_smart_money_factor_values
        +
dim_smart_money_model
        ↓
vw_Ticker_SmartMoney
        ↓
TradeAction = CASE(DataQualityStatus, MarketState)
```

No strategy persistence is introduced in V1.

This has three consequences:

1. historical rows automatically receive a deterministic `TradeAction` when the view definition is refreshed;
2. SmartMoney full/incremental score convergence is unaffected because action is not part of persistence;
3. downstream consumers can still drill from action into the original state/factors.

---

# 9. Examples

### Example A — confirmed breakout

```text
MarketState             = BREAKOUT
DataQualityStatus       = PASS
FreshFlowScore          = 86
RelativeLiquidityScore  = 91
RelativeStrengthScore   = 73

TradeAction             = BUY
```

### Example B — strong state but weak evidence quality

```text
MarketState             = BREAKOUT
DataQualityStatus       = WARNING
SmartMoneyScore         = 84
ConfidenceScore         = 48

TradeAction             = HOLD
```

The quality gate prevents an apparently strong directional score from becoming an actionable BUY.

### Example C — markup

```text
MarketState             = MARKUP
DataQualityStatus       = PASS
TrendScore              = 82
RelativeStrengthScore   = 75

TradeAction             = HOLD
```

The trend is already in progress; V1 does not repeatedly trigger BUY on every MARKUP day.

### Example D — distribution

```text
MarketState             = DISTRIBUTION
DataQualityStatus       = PASS
DistributionScore       = 88
RelativeLiquidityScore  = 92

TradeAction             = SELL
```

---

# 10. Validation Contract

Focused validation must prove:

1. `TradeAction` is always one of `BUY/HOLD/SELL`.
2. non-PASS data quality always returns HOLD.
3. each of the four BUY states returns BUY under PASS quality.
4. DISTRIBUTION returns SELL under PASS quality.
5. MARKUP, LIQUIDITY_DRYUP, SELLING_CLIMAX and NEUTRAL return HOLD under PASS quality.
6. existing score/factor persistence schema is unchanged.
7. repeated execution of `smart_money_v1_schema.sql` remains idempotent.

Implementation validation artifacts:

```text
src/DuckDB/sql/smart_money_v1_preflight.sql
tests/test_smart_money_strategy.py
```

---

# 11. Versioning and Change Control

Strategy V1 intentionally reuses existing `SMART_MONEY_V1 / 1.0.0` score outputs because it does not change factor/state calculations.

`TradeAction` mapping itself is an explicit strategy contract. Future material changes such as:

- changing which state means BUY/SELL;
- adding STRONG_BUY / REDUCE / WATCH;
- adding position-aware entry/exit lifecycle;
- adding stop/target/position sizing;
- changing the quality gate;

must be documented and versioned rather than silently rewriting the historical meaning of the strategy.

The upstream SmartMoneyScore architecture remains owned by:

[[SmartMoneyScore|SmartMoneyScore Architecture]]

The requirement boundary between score and strategy is:

- REQ-0025: calculate explainable Smart Money score/state/confidence;
- REQ-0026: interpret validated primary state as BUY/HOLD/SELL for downstream consumption.
