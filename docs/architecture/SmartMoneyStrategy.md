# SmartMoneyStrategy V1 — BUY / HOLD / SELL

- **Requirement:** [[../backlog/requirements/REQ-0026-smart-money-strategy|REQ-0026]]
- **Upstream model:** [[SmartMoneyScore|SmartMoneyScore V1]]
- **Public contract:** `"CherryMon"."main"."vw_Ticker_SmartMoney"`
- **Strategy outputs:** `TradeAction`, `TradeActionConfidenceScore`
- **Status:** IMPLEMENTED_PENDING_VALIDATION

## Purpose

`SmartMoneyStrategy V1` converts the rich SmartMoneyScore state model into a simple downstream action:

```text
BUY
HOLD
SELL
```

and exposes a companion confidence score:

```text
TradeActionConfidenceScore: 0..100
```

The strategy does **not** replace `SmartMoneyScore`, upstream `ConfidenceScore`, `MarketState` or component factor scores. It is a deterministic interpretation layer so Screener, Chart, Dashboard and research consumers do not each invent different BUY/HOLD/SELL semantics.

The strategy is a technical classification contract only. It does not place orders, size positions, define stop-loss/take-profit, or represent personalized investment advice.

`TradeActionConfidenceScore` is **not** a probability that a trade will win. It measures how well the current strategy action is supported by upstream evidence quality and the weakest factor directly confirming the current state.

---

# 1. Public Output Contract

The public view exposes:

```text
"CherryMon"."main"."vw_Ticker_SmartMoney"
```

with additive strategy fields:

```text
TradeAction
TradeActionConfidenceScore
```

`TradeAction` allowed values:

```text
BUY
HOLD
SELL
```

`TradeActionConfidenceScore` contract:

```text
0 <= TradeActionConfidenceScore <= 100
TradeActionConfidenceScore <= ConfidenceScore
```

Both fields are derived at read time. They are not persisted in:

```text
cal_smart_money_ticker_score
cal_smart_money_factor_values
```

The existing public grain remains:

```text
Ticker + Date + enabled ModelCode/ModelVersion
```

No second Smart Money Source of Truth is introduced.

---

# 2. TradeAction Rule Precedence

Strategy V1 uses deterministic precedence:

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

The quality gate is first. A bullish/bearish state with incomplete or low-confidence evidence cannot emit BUY/SELL.

---

# 3. Why Action Confidence Is Separate

Three different concepts must remain separate:

```text
SmartMoneyScore
    = overall Smart Money signal strength after state-aware weighting/penalty

ConfidenceScore
    = trustworthiness/completeness of the upstream SmartMoney conclusion

TradeActionConfidenceScore
    = confidence that the derived BUY/HOLD/SELL classification is sufficiently supported
```

A high `SmartMoneyScore` does not automatically imply a high action confidence.

A high `TradeActionConfidenceScore` does not imply future return or win probability.

Important invariant:

```text
TradeActionConfidenceScore <= ConfidenceScore
```

The strategy layer may reduce confidence when state-confirming factors are weak; it may never increase confidence beyond the upstream evidence-quality ceiling.

---

# 4. TradeActionConfidenceScore Formula

## 4.1 Quality gate

If:

```text
DataQualityStatus != PASS
```

then:

```text
TradeAction = HOLD
TradeActionConfidenceScore = 0
```

This is a safety HOLD, not a validated directional/management action.

## 4.2 PASS rows

For PASS rows, derive a `StateEvidenceStrength` from the weakest directly confirming public factor.

The weakest factor is intentional: one very strong factor must not hide another condition that is only marginal.

| MarketState | StateEvidenceStrength |
|---|---|
| `ACCUMULATION` | `min(AccumulationScore, AccumulationMemoryScore)` |
| `BREAKOUT` | `min(FreshFlowScore, RelativeLiquidityScore, RelativeStrengthScore)` |
| `DEMAND_EXPANSION` | `min(RelativeLiquidityScore, LiquidityAccelerationScore, RelativeStrengthScore)` |
| `SUPPLY_LOCK` | `min(SupplyLockScore, AccumulationMemoryScore)` |
| `DISTRIBUTION` | `DistributionScore` |
| `MARKUP` | `min(TrendScore, RelativeStrengthScore)` |
| `SELLING_CLIMAX` | `min(DistributionScore, RelativeLiquidityScore)` |
| `LIQUIDITY_DRYUP` | `ConfidenceScore` |
| `NEUTRAL` | `ConfidenceScore` |

For states with an explicit factor list, if any required public factor is NULL:

```text
TradeActionConfidenceScore = 0
```

This exposes a state/factor consistency problem rather than silently assigning high confidence.

## 4.3 Blend and cap

For a valid PASS row:

```text
CandidateActionConfidence
    = 0.60 * ConfidenceScore
    + 0.40 * StateEvidenceStrength

TradeActionConfidenceScore
    = min(ConfidenceScore, CandidateActionConfidence)
```

Then round to 2 decimals.

Why 60/40:

- `ConfidenceScore` remains the dominant evidence-quality input;
- state evidence can reduce confidence when the weakest confirming factor is weaker;
- the upstream confidence cap prevents strategy confidence from becoming more optimistic than the model's own evidence quality.

`LIQUIDITY_DRYUP` currently falls back to `ConfidenceScore` because `LiquidityCompressionScore`, one of the state trigger inputs, is not exposed as a public factor column. This limitation is explicit rather than reconstructed from unrelated public fields.

---

# 5. BUY States

`BUY` requires:

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

## ACCUMULATION → BUY

State condition:

```text
AccumulationScore >= 65
AND
AccumulationMemoryScore >= 60
```

Main evidence:

- persistent strong Close Location Value;
- Relative Strength versus VNINDEX;
- optional OBV/AD slope improvement;
- multi-session accumulation memory.

Approximate accumulation raw evidence:

```text
AccumulationRaw = mean(
    CLV20,
    RS20 × 10,
    OBVSlope20,
    ADSlope20
)
```

Action-confidence evidence strength:

```text
min(AccumulationScore, AccumulationMemoryScore)
```

## BREAKOUT → BUY

State condition:

```text
FreshFlowScore >= 70
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

Action-confidence evidence strength:

```text
min(
    FreshFlowScore,
    RelativeLiquidityScore,
    RelativeStrengthScore
)
```

## DEMAND_EXPANSION → BUY

State condition:

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

Action-confidence evidence strength:

```text
min(
    RelativeLiquidityScore,
    LiquidityAccelerationScore,
    RelativeStrengthScore
)
```

## SUPPLY_LOCK → BUY

State condition:

```text
SupplyLockScore >= 70
AND
AccumulationMemoryScore >= 60
```

`SupplyLockScore` is a conjunctive/geometric composite of available evidence including accumulation memory, close strength, Relative Strength, Trend and liquidity compression, penalized by Distribution evidence.

Action-confidence evidence strength:

```text
min(SupplyLockScore, AccumulationMemoryScore)
```

---

# 6. SELL State

`SELL` requires:

```text
DataQualityStatus = PASS
AND
MarketState = DISTRIBUTION
```

Distribution state condition:

```text
DistributionScore >= 70
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

Action-confidence evidence strength:

```text
DistributionScore
```

Because `DISTRIBUTION` has highest MarketState precedence, an otherwise bullish ticker can still resolve to SELL if distribution dominates and quality is PASS.

---

# 7. HOLD States

`HOLD` means no new BUY/SELL action from Strategy V1. For a ticker not already held, consumers may read it as `WAIT / NO NEW ACTION`.

## Non-PASS quality

```text
DataQualityStatus != PASS
→ TradeAction = HOLD
→ TradeActionConfidenceScore = 0
```

Current upstream quality contract:

```text
INVALID
  if SmartMoneyScore is NULL

PASS
  if ConfidenceScore >= 60
  AND FactorCoverage >= 0.80

WARNING
  otherwise
```

## MARKUP

State condition:

```text
TrendScore >= 65
AND
RelativeStrengthScore >= 60
```

V1 treats this as an already-running trend rather than repeatedly emitting new BUY entries.

Action-confidence evidence strength:

```text
min(TrendScore, RelativeStrengthScore)
```

## LIQUIDITY_DRYUP

State condition:

```text
LiquidityCompressionScore >= 75
AND
RelativeStrengthScore < 55
```

Because public view does not expose `LiquidityCompressionScore`, action confidence currently equals upstream `ConfidenceScore` for PASS rows.

## SELLING_CLIMAX

State condition:

```text
DistributionScore >= 60
AND
RelativeLiquidityScore >= 80
AND
Return1 < 0
```

The state can mean continuing risk or capitulation/exhaustion, so V1 does not infer automatic SELL or bottom-fishing BUY.

Action-confidence evidence strength uses the public confirming factors:

```text
min(DistributionScore, RelativeLiquidityScore)
```

The already-persisted `MarketState` supplies the `Return1 < 0` part of the classification.

## NEUTRAL

No stronger supported state condition is satisfied.

For a PASS `NEUTRAL` row:

```text
TradeAction = HOLD
TradeActionConfidenceScore = ConfidenceScore
```

---

# 8. Action Matrix

| DataQualityStatus | Primary MarketState | TradeAction | Action-confidence evidence |
|---|---|---|---|
| not `PASS` | any | `HOLD` | `0` |
| `PASS` | `ACCUMULATION` | `BUY` | min Accumulation + Memory |
| `PASS` | `BREAKOUT` | `BUY` | min FreshFlow + RelativeLiquidity + RS |
| `PASS` | `DEMAND_EXPANSION` | `BUY` | min RelativeLiquidity + LiquidityAcceleration + RS |
| `PASS` | `SUPPLY_LOCK` | `BUY` | min SupplyLock + Memory |
| `PASS` | `MARKUP` | `HOLD` | min Trend + RS |
| `PASS` | `DISTRIBUTION` | `SELL` | DistributionScore |
| `PASS` | `LIQUIDITY_DRYUP` | `HOLD` | upstream ConfidenceScore |
| `PASS` | `SELLING_CLIMAX` | `HOLD` | min Distribution + RelativeLiquidity |
| `PASS` | `NEUTRAL` | `HOLD` | upstream ConfidenceScore |

---

# 9. Interpretation Guidelines

Recommended downstream interpretation:

```text
TradeAction
    = what the strategy says now

TradeActionConfidenceScore
    = how strongly/reliably that action is supported now
```

Examples:

```text
BUY  + 82
    stronger validated BUY evidence

BUY  + 62
    BUY still valid, but weaker/closer-to-threshold evidence

HOLD + 0
    safety HOLD caused by WARNING/INVALID quality

HOLD + 85
    validated no-new-action / management state

SELL + 88
    strong validated distribution classification
```

Do not use arbitrary global execution thresholds such as `BUY only if confidence >= 80` unless a separate backtest/research requirement validates that policy.

---

# 10. Public View Construction

Persistence remains authoritative:

```text
cal_smart_money_ticker_score
        +
cal_smart_money_factor_values
        +
dim_smart_money_model
        ↓
vw_Ticker_SmartMoney
        ↓
TradeAction
TradeActionConfidenceScore
```

No strategy persistence is introduced.

Consequences:

1. historical persisted rows automatically receive both strategy fields when the view definition is refreshed;
2. no full historical SmartMoney initload is required for this additive view change;
3. score/factor full-vs-incremental convergence is unaffected;
4. downstream consumers can drill from action confidence into the exact state and factor evidence.

---

# 11. Examples

## Confirmed BREAKOUT

```text
ConfidenceScore         = 85
MarketState             = BREAKOUT
DataQualityStatus       = PASS
FreshFlowScore          = 90
RelativeLiquidityScore  = 88
RelativeStrengthScore   = 80

StateEvidenceStrength   = 80
Candidate               = 0.60*85 + 0.40*80 = 83
TradeAction             = BUY
TradeActionConfidence   = 83
```

## Strong state but WARNING quality

```text
MarketState             = BREAKOUT
DataQualityStatus       = WARNING
ConfidenceScore         = 58

TradeAction             = HOLD
TradeActionConfidence   = 0
```

## Distribution stronger than upstream evidence confidence

```text
ConfidenceScore         = 86
MarketState             = DISTRIBUTION
DistributionScore       = 92
DataQualityStatus       = PASS

Candidate               = 88.4
Cap                     = ConfidenceScore = 86
TradeAction             = SELL
TradeActionConfidence   = 86
```

The strategy cannot claim 88.4 confidence when the upstream model only trusts the evidence at 86.

---

# 12. Validation Contract

Focused validation must prove:

1. `TradeAction` is always one of `BUY/HOLD/SELL`.
2. non-PASS data quality always returns HOLD.
3. each of the four BUY states returns BUY under PASS quality.
4. DISTRIBUTION returns SELL under PASS quality.
5. MARKUP, LIQUIDITY_DRYUP, SELLING_CLIMAX and NEUTRAL return HOLD under PASS quality.
6. `TradeActionConfidenceScore` is non-NULL and in `0..100`.
7. `TradeActionConfidenceScore <= ConfidenceScore` for every public row.
8. non-PASS rows return `TradeActionConfidenceScore = 0`.
9. explicit state factor formulas produce deterministic expected confidence values.
10. missing required public factor evidence returns action confidence `0`.
11. existing score/factor persistence schema remains unchanged.
12. repeated execution of `smart_money_v1_schema.sql` remains idempotent.

Implementation validation artifacts:

```text
src/DuckDB/sql/smart_money_v1_preflight.sql
tests/test_smart_money_strategy.py
docs/runbook/SmartMoneyStrategy_V1.md
```

---

# 13. Versioning and Change Control

This additive field reuses existing `SMART_MONEY_V1 / 1.0.0` upstream score outputs because it does not change factor/state calculations or existing `TradeAction` values.

It does change the public strategy contract, so the confidence formula is documented explicitly and must not be silently modified later.

Future material changes such as:

- changing BUY/SELL state mapping;
- changing the 60/40 action-confidence blend;
- changing the upstream-confidence cap;
- adding STRONG_BUY / REDUCE / WATCH;
- adding predictive win probability;
- adding position-aware entry/exit lifecycle;
- adding stop/target/position sizing;

must be versioned/documented rather than silently rewriting historical strategy semantics.

Requirement boundary:

- REQ-0025: calculate explainable Smart Money score/state/upstream confidence;
- REQ-0026: interpret validated primary state as BUY/HOLD/SELL and expose strategy confidence for downstream consumption.
