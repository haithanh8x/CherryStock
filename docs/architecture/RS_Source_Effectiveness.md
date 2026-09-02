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