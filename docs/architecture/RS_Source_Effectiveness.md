# R/S V2.4 — Source Effectiveness & Indicator Promotion Architecture

- **Requirement:** REQ-0022
- **Status:** APPROVED_FOR_IMPLEMENTATION
- **Date:** 2026-09-02
- **Primary owner:** SolutionArchitect
- **Affected domains:** R/S Engine, Historical Evaluation, DuckDB, Indicator Governance, Testing

---

## 1. Context

R/S V2.3 already provides historical events, chronological TRAIN/VALIDATION/TEST, regime metrics, cross-ticker evaluation, ablation primitives, model versioning, model Promotion Gate and a golden benchmark.

V2.4 answers a narrower question:

> For a given ticker and source/config, does that source add out-of-sample predictive value after controlling for the current model, and is that evidence strong enough to approve future R/S integration?

Runtime Strength and Source Effectiveness remain separate concepts.

```text
Runtime Strength
    = confidence in a current R/S zone

Source Effectiveness
    = historical evidence that one source/config adds predictive value
      for a ticker/horizon after controlling for the current model
```

## 2. Proposed Architecture

```text
R/S Runtime Providers
      │
      ▼
Source Identity Contract
      │
      ├──────────────┐
      ▼              ▼
V2.3 Baseline     V2.3 Ablation
      │              │
      └──────┬───────┘
             ▼
 Source Effectiveness Engine
             │
   ┌─────────┼───────────┐
   ▼         ▼           ▼
 LEVEL    CONTEXT     CONFIRMATION
 lineage  marginal      marginal
   │         │           │
   └─────────┼───────────┘
             ▼
 Per-Ticker Effectiveness
             │
     ┌───────┴────────┐
     ▼                ▼
Recommendation   Source Promotion Gate
     │                │
     └───────┬────────┘
             ▼
       DuckDB Persistence
             │
             ▼
vw_RS_Source_Effectiveness
```

V2.4 never automatically mutates runtime registration, runtime weights or Indicator Engine metadata.

## 3. Stable Source Identity

New pure module:

```text
src/calcEngine/rsSourceIdentity.py
```

Examples:

```text
MA50_D                 → MA50_D
BB20_2_D:LOWER         → BB20_2_D:LOWER
RSI14_D                → RSI14_D
ATR14_D                → ATR14_D
SWING_HIGH_20260820    → SWING_HIGH
SWING_LOW_20260818     → SWING_LOW
VP_POC                 → VP_POC
VP_HVN_01              → VP_HVN
VP_LVN_01              → VP_LVN
VP_HVN_01_CONF         → VP_HVN
```

Unknown non-empty source codes normalize to uppercase exact codes. Blank source codes fail explicitly.

## 4. Research Source Filters

`build_level_ladder()` gains backward-compatible optional research filters:

```python
included_source_keys=None
excluded_source_keys=None
```

Rules:

- defaults preserve V2.3 runtime behavior;
- include/exclude use canonical source identity;
- the same filtering applies to LEVEL candidates, CONTEXT contexts and CONFIRMATION contexts;
- include and exclude sets may not overlap;
- filters are research/evaluation controls, not a production source switch.

Examples:

```python
# isolate MA50_D inside MA provider
enabled_sources=("MA",)
included_source_keys=("MA50_D",)

# full model minus MA50_D
excluded_source_keys=("MA50_D",)

# remove only RSI14_D confirmation
excluded_source_keys=("RSI14_D",)
```

## 5. V2.3 Evaluation Reproducibility Extension

`RSModelSpec` and `cal_rs_evaluation_run` record include/exclude source keys so source-config research produces a distinct deterministic model signature.

Additive columns:

```text
cal_rs_evaluation_run
+ IncludeSourceKeysJson
+ ExcludeSourceKeysJson
```

## 6. Source Effectiveness Engine

New module:

```text
src/calcEngine/rsSourceEffectiveness.py
```

Primary contracts:

```text
SourceEffectivenessPolicy
SourceEffectivenessRecord
SourcePromotionPolicy
SourcePromotionDecision
```

Supported scopes:

```text
SOURCE_CONFIG
SOURCE_FAMILY
```

Supported attribution modes:

```text
LEVEL_LINEAGE
MARGINAL_ONLY
FAMILY_ABLATION
```

## 7. LEVEL Effectiveness Formula

LEVEL sources use direct historical event lineage plus baseline-vs-ablation marginal lift.

Default positive components:

```text
Hold Rate                25%
Touch Rate               15%
Retest Rate              10%
Directional Edge         20%
Temporal Stability       10%
Regime Stability         10%
Marginal Contribution    10%
                         ----
                         100%
```

Penalties:

```text
Break Penalty
Complexity Penalty
```

Directional edge normalization:

```text
DirectionalEdgeScore
= clamp(0.5 + DirectionalEdgePct / 20, 0, 1)
```

Marginal contribution normalization:

```text
MeanOOSLift = (ValidationLift + TestLift) / 2
MarginalScore = clamp(0.5 + MeanOOSLift / 0.05, 0, 1)
```

## 8. CONTEXT / CONFIRMATION Effectiveness

CONTEXT and CONFIRMATION are not price levels and must not receive fabricated touch/hold/retest metrics.

Marginal metric is role-aware:

```text
CONTEXT
    → LEVEL_QUALITY lift
      because context can alter clustering / neutral-zone geometry

CONFIRMATION
    → STRENGTH_BRIER lift
      because confirmation may change Strength without changing S1/R1 geometry
```

`STRENGTH_BRIER` uses touched events and evaluates whether `Strength / 100` predicts the probability that the touched level holds. This prevents a confirmation-only indicator such as RSI from being incorrectly judged as zero-value merely because level prices/ranks do not move.

Role-aware marginal-only score:

```text
Validation Lift Score    35%
Test Lift Score          35%
Temporal Stability       15%
Regime Stability         15%
                         ----
                         100%
```

Recommendations remain role preserving:

```text
CONTEXT       → CONTEXT_ONLY / RESEARCH / DROP
CONFIRMATION  → CONFIRM_ONLY / RESEARCH / DROP
```

## 9. Temporal and Regime Stability

LEVEL temporal stability:

```text
1 - clamp(abs(ValidationQuality - TestQuality) / 0.10, 0, 1)
```

Marginal-only temporal stability:

```text
1 - clamp(abs(ValidationLift - TestLift) / 0.05, 0, 1)
```

Regime stability:

```text
RegimeRange = max(RegimeQualityOrLift) - min(RegimeQualityOrLift)
RegimeStability = 1 - clamp(RegimeRange / 0.20, 0, 1)
```

If fewer than two usable regimes exist, RegimeStability is NULL and the score re-normalizes over available evidence. Promotion breadth checks remain separate.

## 10. Recommendation Contract

LEVEL defaults:

```text
CORE
  score >= 75
  validation lift >= +0.01
  test lift >= 0
  sufficient OOS samples

SUPPORTING
  score >= 65
  test lift >= 0

RESEARCH
  score >= 55 or insufficient breadth

DROP
  score < 55 or materially negative TEST lift
```

CONFIRMATION and CONTEXT use role-specific CONFIRM_ONLY / CONTEXT_ONLY recommendations instead of being converted into LEVEL sources.

## 11. Source Promotion Gate

Promotion is cross-ticker governance. It is not the same as a per-ticker recommendation.

Default policy:

```text
min_tickers                 = 3
min_positive_ticker_ratio   = 0.60
min_effectiveness_score     = 65
min_validation_lift         = +0.01
min_test_lift               = 0.00
min_temporal_stability      = 0.70
min_regime_stability        = 0.60
max_complexity_delta        = 0.15
max_negative_test_lift      = -0.01
```

Outcomes:

```text
APPROVED_FOR_INTEGRATION
TICKER_SELECTIVE
RESEARCH
REJECTED
```

Even with an explicit apply action, V2.4 writes governance/audit metadata only. It MUST NOT alter indicator dimensions/configs, provider registry, runtime source set, Strength weights or production deployment.

Concrete indicator lifecycle changes remain owned by Indicator Management.

## 12. Persistence Model

V2.4 adds:

```text
cal_rs_source_effectiveness_run
cal_rs_source_effectiveness
sys_rs_source_promotion_audit
vw_RS_Source_Effectiveness
```

`cal_rs_source_effectiveness_run` grain:

```text
EffectivenessRunId
```

`cal_rs_source_effectiveness` grain:

```text
EffectivenessRunId / Ticker / ScopeType / SourceKey / HorizonBars
```

Result fields include attribution mode, OOS samples, LEVEL metrics when applicable, validation/test quality, marginal lifts, temporal/regime stability, complexity delta, score, recommendation and evidence JSON.

`sys_rs_source_promotion_audit` stores decision evidence/policy/reasons but is never a hot runtime configuration switch.

## 13. Public Read SSOT

Public latest-effectiveness contract:

```text
vw_RS_Source_Effectiveness
```

It exposes the latest COMPLETED effectiveness row per:

```text
Ticker / ScopeType / SourceKey / HorizonBars
```

Consumers should use the view rather than internal cal_* tables.

## 14. Multi-Horizon Strategy

Canonical research horizons:

```text
5, 10, 20, 40 trading bars
```

Each horizon keeps separate baseline/ablation/effectiveness evidence. V2.4 does not average horizons into a runtime weight.

## 14.1 How Historical Evaluation Actually Works

Historical evaluation is not a daily live prediction loop. It is a point-in-time backtest over selected historical snapshots.

The canonical flow is:

```text
historical trading dates
        ↓
select snapshot dates using snapshot_step
        ↓
build R/S ladder using information available at that snapshot only
        ↓
observe future market bars over H5 / H10 / H20 / H40
        ↓
label historical outcomes
        ↓
aggregate thousands of events
        ↓
derive historical rates / quality / source effectiveness
```

### Snapshot cadence

With:

```text
snapshot_step = 5
```

the evaluator does not rebuild the ladder on every trading date.

Conceptually:

```text
D1
D2
D3
D4
D5
D6
D7
...

sampled snapshots:

D1
D6
D11
D16
...
```

Warm-up filtering is applied after this sampling step. If a sampled date does not have enough point-in-time history for an enabled provider, that sampled date is skipped; the cadence is not rebased.

### Meaning of H5 / H10 / H20 / H40

```text
H5  = evaluate the next 5 market trading bars
H10 = evaluate the next 10 market trading bars
H20 = evaluate the next 20 market trading bars
H40 = evaluate the next 40 market trading bars
```

These are trading bars, not calendar days.

Approximate interpretation:

```text
H5  ≈ very short term
H10 ≈ short term
H20 ≈ roughly one trading month
H40 ≈ roughly two trading months
```

The horizons are not four different R/S models. They are four future observation windows applied to the same point-in-time R/S signal.

### Example

Assume this historical snapshot:

```text
Ticker       MWG
Snapshot     2026-05-04
CurrentPrice 58
S1           55
R1           62
```

The ladder is calculated using only data available on or before 2026-05-04.

For H20, the evaluator then observes the next 20 trading bars and asks questions such as:

```text
Did price touch S1 or R1?
If touched, did the level hold?
Did price break through the level?
If broken, was there a retest?
After the interaction, did price move in the expected direction?
```

The same historical snapshot can be evaluated independently under H5, H10, H20 and H40.

### Event labels

At event level, evaluation records concepts such as:

```text
Ticker
AsOfDate
LevelRank
LevelType
HorizonBars
Touched
Held
Broken
Retested
DirectionalEdgePct
Strength
Source lineage
Regime
Temporal split
```

For example:

```text
MWG / 2026-05-04 / R1 / H20
Touched = TRUE
Held    = TRUE
Broken  = FALSE
Retested= FALSE
```

Another event may be:

```text
MWG / 2026-05-19 / S1 / H20
Touched = TRUE
Held    = FALSE
Broken  = TRUE
Retested= TRUE
```

### Historical rates

After many historical events have been labeled, the evaluator aggregates them into empirical rates such as:

```text
Touch Rate
Hold Rate
Break Rate
Retest Rate
Directional Edge
LEVEL_QUALITY
STRENGTH_BRIER
```

Illustrative example:

```text
historical resistance events = 1,000

Touch Rate                  = 42%
Hold Rate given touch       = 68%
Break Rate given touch      = 32%
Retest Rate given break     = 47%
```

This can be interpreted as historical empirical evidence, for example:

```text
P_historical(Break | Touch, horizon=H20) ≈ 32%
```

### Historical rate is not the same as a current predictive probability

V2.4 does not currently claim:

```text
MWG current R1 = 62
Probability of breaking R1 within H20 = 27%
```

unless a dedicated calibrated predictive layer is added.

Current V2.4 outputs are primarily:

```text
historical event outcomes
historical conditional rates
quality metrics
source marginal lift
source effectiveness
promotion evidence
```

Therefore:

```text
historical empirical rate
    !=
calibrated per-level forecast probability
```

A future probability-calibration layer could use the historical event dataset to produce current-level forecasts such as:

```text
P(Break R1 within H20)
P(Hold S1 within H10)
P(Retest after break within H20)
```

but that is outside the current V2.4 contract.

### Why the largest horizon reserves future bars

To label an H40 snapshot correctly, the evaluator needs 40 later trading bars.

Therefore:

```text
latest raw data date
    !=
latest safe evaluation snapshot date
```

The monthly orchestrator chooses an evaluation end that leaves enough future bars for the largest requested horizon.

Example:

```text
evaluation snapshot date
2026-07-03
        ↓
40 later market trading bars
        ↓
latest observed market date
2026-08-28
```

This avoids immature/censored outcome labels and look-ahead leakage.


## 14.2 Decision Playbook — Six Evidence-Driven Decision Scenarios

The public decision surface is:

```text
"CherryMon"."main"."vw_RS_Source_Effectiveness"
```

The view answers questions about **historical source effectiveness** at this grain:

```text
Ticker / ScopeType / SourceKey / HorizonBars
```

Decision rules below use the current V2.4 default policy unless explicitly marked as a future/research use case.

Important interpretation boundary:

```text
Source Effectiveness
    = evidence about whether a source/config/family historically adds value

Runtime Strength
    = current quality/confidence score of an R/S level

Horizon Probability
    = calibrated probability for a current R/S level over a future horizon
      (not implemented in V2.4)
```

Therefore this view can directly support source-governance decisions, but it must not be interpreted as a direct probability forecast for the current S1/R1.

### Common evidence fields

The following fields are used repeatedly across the six decision scenarios:

| Field | Decision meaning |
|---|---|
| `Ticker` | which symbol the evidence applies to |
| `ScopeType` | whether the evidence is for one config/source or a whole family |
| `SourceKey` | canonical source/config identity |
| `SourceFamily` | broader source family |
| `SourceRole` | LEVEL / CONTEXT / CONFIRMATION |
| `HorizonBars` | future evaluation window in trading bars |
| `AttributionMode` | how contribution was attributed |
| `MarginalMetric` | LEVEL_QUALITY or STRENGTH_BRIER |
| `LineageEventCount` | historical lineage coverage for LEVEL sources |
| `ValidationEventCount` | validation OOS sample size |
| `TestEventCount` | final test OOS sample size |
| `TouchRate` | historical fraction of LEVEL events touched within the horizon |
| `HoldRateGivenTouch` | historical hold rate conditional on touch |
| `BreakRateGivenTouch` | historical break rate conditional on touch |
| `RetestRateGivenBreak` | historical retest rate conditional on break |
| `DirectionalEdgePct` | average favorable move minus average adverse move |
| `ValidationQuality` | role-aware baseline quality on VALIDATION |
| `TestQuality` | role-aware baseline quality on TEST |
| `ValidationMarginalLift` | baseline minus ablation quality on VALIDATION |
| `TestMarginalLift` | baseline minus ablation quality on TEST |
| `TemporalStability` | stability between VALIDATION and TEST |
| `RegimeStability` | stability across market regimes |
| `ComplexityDelta` | additional model complexity attributable to the source |
| `EffectivenessScore` | composite 0-100 source-effectiveness score |
| `Recommendation` | per-ticker/source/horizon decision label |
| `EvidenceJson` | regime evidence and policy used for the score |
| `CompletedAt` | timestamp of the latest completed evidence row |

Default sample thresholds:

```text
ValidationEventCount >= 20
TestEventCount       >= 10
```

Default positive evidence thresholds used by source promotion:

```text
EffectivenessScore      >= 65
ValidationMarginalLift  >= +0.01
TestMarginalLift        >= 0.00
TemporalStability       >= 0.70
RegimeStability         >= 0.60
ComplexityDelta         <= 0.15
```

A material negative TEST result is:

```text
TestMarginalLift < -0.01
```

and should be treated as strong negative evidence.

---

### Scenario 1 — Decide whether to keep, research or remove one indicator/source config

**Business question**

> Does one concrete source/config such as MA50_D, BB20_2_D:LOWER, RSI14_D or VP_POC add enough historical value to remain a candidate for the R/S model?

**Primary filter**

```sql
ScopeType = 'SOURCE_CONFIG'
AND SourceKey = <candidate source>
```

**Primary columns**

```text
SourceRole
AttributionMode
MarginalMetric
ValidationEventCount
TestEventCount
ValidationMarginalLift
TestMarginalLift
TemporalStability
RegimeStability
EffectivenessScore
Recommendation
ComplexityDelta
```

For a `LEVEL` source, also inspect:

```text
LineageEventCount
TouchRate
HoldRateGivenTouch
BreakRateGivenTouch
RetestRateGivenBreak
DirectionalEdgePct
```

**Decision pattern**

Strong candidate:

```text
ValidationEventCount >= 20
TestEventCount       >= 10
EffectivenessScore   >= 75                 # strong LEVEL evidence
ValidationLift       >= +0.01
TestLift             >= 0
TemporalStability    high, preferably >= 0.70
RegimeStability      high, preferably >= 0.60
Recommendation       = CORE
```

Useful but secondary:

```text
EffectivenessScore >= 65
TestMarginalLift   >= 0
Recommendation     = SUPPORTING
```

For role-preserving non-LEVEL sources:

```text
CONFIRMATION → CONFIRM_ONLY
CONTEXT      → CONTEXT_ONLY
```

Research only:

```text
Recommendation = RESEARCH
OR insufficient OOS sample
OR score/lift is promising but regime breadth is weak
```

Removal candidate:

```text
Recommendation = DROP
OR TestMarginalLift < -0.01
OR repeated negative TEST lift across horizons/tickers
```

**Example**

```text
Ticker                  MWG
SourceKey               MA50_D
ScopeType               SOURCE_CONFIG
SourceRole              LEVEL
HorizonBars             20
ValidationEventCount    34
TestEventCount          18
ValidationMarginalLift  +0.028
TestMarginalLift        +0.017
TemporalStability       0.82
RegimeStability         0.73
EffectivenessScore      79.6
Recommendation          CORE
```

Decision:

```text
KEEP as a strong integration candidate for MWG/H20.
Do not interpret 79.6 as 79.6% probability.
```

---

### Scenario 2 — Decide whether an entire source family is still worth keeping

**Business question**

> Does an entire family such as TREND_AVERAGE, VOLATILITY_BAND, MARKET_STRUCTURE or VOLUME_STRUCTURE add enough value to justify its complexity?

**Primary filter**

```sql
ScopeType = 'SOURCE_FAMILY'
AND SourceFamily = <candidate family>
```

Typical attribution:

```text
AttributionMode = FAMILY_ABLATION
```

**Primary columns**

```text
SourceFamily
HorizonBars
ValidationEventCount
TestEventCount
ValidationMarginalLift
TestMarginalLift
TemporalStability
RegimeStability
ComplexityDelta
EffectivenessScore
Recommendation
EvidenceJson
```

For LEVEL families, also inspect historical geometry metrics when present:

```text
TouchRate
HoldRateGivenTouch
BreakRateGivenTouch
RetestRateGivenBreak
DirectionalEdgePct
```

**Decision logic**

Keep the family as strategically useful when:

```text
family ablation makes the model worse
→ ValidationMarginalLift > 0
→ TestMarginalLift       >= 0

and evidence is stable:
→ TemporalStability >= 0.70
→ RegimeStability   >= 0.60
```

Question the family when:

```text
ValidationMarginalLift ≈ 0
TestMarginalLift       ≈ 0
ComplexityDelta         is material
```

This means the family may be adding moving parts without adding measurable OOS value.

Strong removal/research signal:

```text
TestMarginalLift < -0.01
```

because removing the family improves TEST quality.

**Important**

A family can be weak globally while one config inside it is useful for selected tickers. Therefore:

```text
SOURCE_FAMILY weak
    does not automatically imply
every SOURCE_CONFIG in that family must be deleted
```

Always cross-check Scenario 1 before removing a family from research scope.

---

### Scenario 3 — Build ticker-specific source profiles

**Business question**

> Which indicators/sources work best for MWG versus FPT, HPG, VIC, etc.?

The view is already per ticker, so it can reveal that one source is useful for one symbol but not another.

**Primary grouping**

```text
group by:
    Ticker
    SourceKey
    HorizonBars
```

**Primary columns**

```text
Ticker
SourceKey
SourceFamily
SourceRole
HorizonBars
ValidationEventCount
TestEventCount
TestMarginalLift
TemporalStability
RegimeStability
EffectivenessScore
Recommendation
```

**Decision pattern**

Ticker-specific positive source:

```text
for a given Ticker:
    EffectivenessScore >= 65
    ValidationMarginalLift >= +0.01
    TestMarginalLift >= 0
    TemporalStability >= 0.70
    RegimeStability >= 0.60
    sufficient OOS sample
```

Ticker-specific weak source:

```text
for that Ticker:
    Recommendation in (RESEARCH, DROP)
    or TestMarginalLift < 0
```

**Example**

```text
MA50_D / H20

MWG:
    Score     78
    TestLift +0.025
    CORE

FPT:
    Score     67
    TestLift +0.006
    SUPPORTING

HPG:
    Score     51
    TestLift -0.018
    DROP
```

Decision:

```text
Do not assume MA50_D has one universal quality level.
It may be:
    strong for MWG,
    supporting for FPT,
    harmful for HPG.
```

This scenario is the foundation for a future Adaptive Indicator Engine.

**Governance boundary**

V2.4 does not automatically change provider registration by ticker. The view supplies evidence only.

---

### Scenario 4 — Research evidence-based weights for future Strength scoring

**Business question**

> Instead of treating every source as equally informative, can historical effectiveness be used to propose better source weights when calculating current R/S Strength?

This is a **future/research use case**, not current V2.4 runtime behavior.

V2.4 explicitly does not automatically mutate runtime Strength weights.

**Candidate input columns**

```text
Ticker
SourceKey
SourceFamily
SourceRole
HorizonBars
EffectivenessScore
ValidationMarginalLift
TestMarginalLift
TemporalStability
RegimeStability
ComplexityDelta
Recommendation
```

For LEVEL sources, additional evidence:

```text
HoldRateGivenTouch
BreakRateGivenTouch
DirectionalEdgePct
```

**Candidate eligibility rule before a source is allowed to influence a future weight**

```text
ValidationEventCount >= 20
TestEventCount       >= 10
TestMarginalLift     >= 0
Recommendation       not in (RESEARCH, DROP)
```

Prefer sources with:

```text
high EffectivenessScore
high TestMarginalLift
high TemporalStability
high RegimeStability
low ComplexityDelta
```

**Illustrative research transformation only**

A future weighting layer might derive a normalized research weight from:

```text
EffectivenessScore
× OOS marginal contribution
× temporal stability
× regime stability
```

For example conceptually:

```text
RawWeight
    = ScoreFactor
    × LiftFactor
    × StabilityFactor
```

followed by normalization across sources contributing to the same current R/S zone.

This formula is intentionally not part of V2.4 production contract yet.

**Decision**

```text
Use Source Effectiveness to nominate/compare candidate weights.
Do not directly write EffectivenessScore into runtime Strength.
Do not interpret EffectivenessScore as probability.
Require a separate architecture decision + regression validation before changing Strength weighting.
```

---

### Scenario 5 — Provide training features for a future Horizon Probability model

**Business question**

> Can historical source-effectiveness evidence help estimate P(Hold), P(Break) or P(Retest) for a current R/S level over a specific horizon?

Yes as **input evidence**, but V2.4 does not currently provide calibrated current-level probabilities.

**Relevant columns**

Identity/context:

```text
Ticker
SourceKey
SourceFamily
SourceRole
HorizonBars
```

Historical behavior features for LEVEL sources:

```text
TouchRate
HoldRateGivenTouch
BreakRateGivenTouch
RetestRateGivenBreak
DirectionalEdgePct
```

Reliability features:

```text
ValidationEventCount
TestEventCount
ValidationQuality
TestQuality
ValidationMarginalLift
TestMarginalLift
TemporalStability
RegimeStability
EffectivenessScore
Recommendation
```

Potential current-state features must come from the runtime R/S ladder, not this view:

```text
current LevelPrice
current LevelType / Rank
current Strength
distance from current price
current source lineage
current regime/context
level age/lifecycle when implemented
```

**Correct modeling boundary**

Historical rate:

```text
HoldRateGivenTouch = 0.72
```

means:

```text
72% of historical touched events in this evidence cohort held
```

It does **not** mean:

```text
P(current R1 holds over H20) = 72%
```

A future calibration model must combine current-level features with historical evidence and validate calibration out of sample.

**Candidate outputs of the future layer**

```text
P(Touch current R1 within H)
P(Hold current R1 | Touch, H)
P(Break current R1 | Touch, H)
P(Retest | Break, H)
```

where H can be any configured research horizon, including future choices such as H60/H250, provided the historical evaluator has enough future outcome bars.

---

### Scenario 6 — Support an actual current R/S trading decision

**Business question**

> When the current ladder shows S1/R1, how should a user combine current Strength and historical source-effectiveness evidence to decide whether the level deserves attention?

This scenario requires combining two different evidence layers:

```text
Current R/S Ladder
    +
vw_RS_Source_Effectiveness
```

**Current ladder supplies**

```text
Ticker
current S/R level price
LevelRank: S1/S2/R1/R2/...
current Strength
current source lineage
current SourceFamily composition
current market context
```

**Source-effectiveness view supplies**

```text
for each contributing SourceKey / SourceFamily / HorizonBars:

EffectivenessScore
Recommendation
TestMarginalLift
TemporalStability
RegimeStability

and for LEVEL sources:
TouchRate
HoldRateGivenTouch
BreakRateGivenTouch
RetestRateGivenBreak
DirectionalEdgePct
```

**Evidence pattern for a higher-confidence current level**

A current R/S level deserves more confidence when several independent contributing sources have:

```text
Recommendation in:
    CORE
    SUPPORTING
    CONFIRM_ONLY
    CONTEXT_ONLY

TestMarginalLift >= 0
TemporalStability >= 0.70
RegimeStability   >= 0.60
sufficient OOS samples
```

and LEVEL contributors also show favorable historical behavior:

```text
HoldRateGivenTouch relatively high
BreakRateGivenTouch relatively low
DirectionalEdgePct > 0
```

**Evidence pattern for caution**

```text
current Strength is high
BUT
major contributing sources have:
    DROP / RESEARCH
    negative TestMarginalLift
    poor TemporalStability
    poor RegimeStability
    insufficient OOS sample
```

Interpretation:

```text
The current geometric/confluence Strength may be high,
but historical evidence for the underlying sources is weak or unstable.
```

This is a reason to reduce confidence, not a direct sell/buy rule.

**Illustrative decision matrix**

| Current Strength | Source evidence | Interpretation |
|---|---|---|
| High | Strong/stable OOS evidence | strongest research-supported R/S case |
| High | Weak/negative source evidence | structurally strong now, historically questionable |
| Medium | Strong source evidence | may deserve attention despite moderate current confluence |
| Low | Strong source evidence | source historically useful, but current level geometry is weak |
| Low | Weak source evidence | lowest-priority level |

**Critical boundary**

The view must not be used alone to generate:

```text
BUY
SELL
exact stop loss
exact target
current Hold/Break probability
```

until the relevant runtime decision/calibration layer exists.

---

### Decision summary

The six decision scenarios map to the view as follows:

| # | Decision | Primary Scope | Most important fields | Directly supported by V2.4? |
|---|---|---|---|---|
| 1 | Keep/drop one indicator config | SOURCE_CONFIG | Score, Recommendation, Val/Test Lift, Stability, sample | YES |
| 2 | Keep/drop a source family | SOURCE_FAMILY | Family Ablation Lift, Stability, Complexity, Score | YES |
| 3 | Ticker-specific source selection | per Ticker + SOURCE_CONFIG | Score, Test Lift, Recommendation, Stability | YES as evidence; no auto-runtime mutation |
| 4 | Source weighting for Strength | SOURCE_CONFIG/FAMILY | Score, Lift, Stability, Complexity | RESEARCH INPUT ONLY |
| 5 | Horizon Probability | per Ticker/Source/Horizon | historical rates + reliability fields | TRAINING INPUT ONLY; no calibrated probability yet |
| 6 | Current R/S decision support | current ladder + view | Strength + source lineage + effectiveness evidence | PARTIAL; decision-support evidence only |

### Recommended evidence priority

When fields conflict, use this order:

```text
1. TEST evidence
2. sufficient OOS sample
3. Validation/Test consistency
4. regime stability
5. marginal lift
6. composite EffectivenessScore
7. historical touch/hold/break/retest statistics
8. TRAIN evidence only as background
```

Do not promote a source merely because `EffectivenessScore` is high if the TEST evidence is materially negative or sample size is insufficient.



## 15. Performance and Operational Strategy

1. Reuse persisted V2.3 evaluation events/metrics.
2. Do not recalculate a compatible baseline unnecessarily.
3. Run source-config ablations only for candidates being investigated.
4. Load run events set-wise.
5. Compute per-ticker effectiveness in memory.
6. Persist results in one short writer transaction.
7. Read latest results through the public view.

### Monthly full evaluation

Canonical operational service:

~~~text
src/Orchestrator/rs_v2_4_full_evaluation.py
~~~

Stable CLI entry point:

~~~text
scripts/run_rs_v2_4_full_evaluation.py
~~~

The CLI wrapper delegates to the Orchestrator service; it contains no duplicated R/S calculation/business logic.

The monthly orchestrator:

~~~text
resolve eligible ticker universe
        ↓
reserve future outcome bars
        ↓
baseline × H5/H10/H20/H40
        ↓
source-config ablation/effectiveness
        ↓
source-family ablation/effectiveness
        ↓
Source Promotion Gate dry-run
        ↓
vw_RS_Source_Effectiveness
~~~

Rules:

- full evaluation is a research/governance workload, not a daily runtime workload;
- default cadence is monthly, with event-driven reruns after material source/model changes;
- the latest raw market date is reserved for outcome observation; the evaluation end must leave enough later trading bars for the largest requested horizon;
- one compatible baseline per horizon is reused across source/family ablations;
- deterministic run IDs plus metadata compatibility checks provide resumable execution;
- SOURCE_CONFIG LEVEL evaluation requires observable baseline lineage;
- SOURCE_FAMILY ablation removes the full discovered family membership;
- promotion defaults to dry-run and never changes runtime weights/providers.

Operational procedure:

~~~text
docs/runbook/RS_V2_4_Monthly_Full_Evaluation.md
~~~

## 16. Failure / Blocking Rules

BLOCK when baseline and ablation datasets, horizons or split contracts are incompatible; a required run is not COMPLETED; required OOS splits are absent; or a LEVEL source cannot be found in lineage.

Insufficient regime breadth or sample size yields RESEARCH rather than silent TRAIN-only approval.

## 17. Compatibility

With no include/exclude source filters, V2.4 preserves V2.3 runtime behavior and golden outputs.

The V2.3 model Promotion Gate remains unchanged. V2.4 introduces a separate Source Promotion Gate.

## 18. Migration

Generate additive/idempotent migration:

```text
src/DuckDB/sql/rs_v2_4_source_effectiveness.sql
```

Execute outside read-only MCP using:

```text
scripts/run_rs_v2_4_migration.py
```

## 19. Validation Strategy

Unit tests cover canonical identity, filters, role-aware scoring, score bounds, temporal/regime stability, negative TEST protection, recommendations, global/ticker-selective promotion and persistence dataframe contracts.

Regression requires V2.3 golden benchmark and existing R/S tests to remain PASS when research filters are not supplied.

Integration validation covers baseline/ablation compatibility, effectiveness persistence, public view, idempotency and promotion dry-run.

## 20. ADR

**Required** because V2.4 introduces stable source identity, research filters in the R/S API, a source-specific promotion governance layer, new persistence/public SSOT and an explicit non-deploying approval boundary.

ADR:

```text
docs/adr/ADR-008-rs-v2-4-source-effectiveness-promotion.md
```

## 21. Implementation Handoff

```text
DESIGN HANDOFF
Requirement: REQ-0022
Outcome: R/S V2.4 Source Effectiveness & Indicator Promotion Framework
Status: APPROVED_FOR_IMPLEMENTATION
Primary next owner: GeneralCoding
Architecture: docs/architecture/RS_Source_Effectiveness.md
ADR: docs/adr/ADR-008-rs-v2-4-source-effectiveness-promotion.md
Database migration: required, additive/idempotent, generated only
Validation owner: TestEngineer
```