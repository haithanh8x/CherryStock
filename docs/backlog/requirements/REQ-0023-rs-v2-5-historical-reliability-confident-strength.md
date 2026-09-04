---
id: REQ-0023
title: R/S V2.5 Historical Reliability & Confident Strength Shadow Evaluation
status: READY_FOR_DESIGN
priority: P0
owner: BusinessAnalyst
primary_next_owner: SolutionArchitect
related:
  architecture: docs/architecture/RS_Ladder.md; docs/architecture/RS_Source_Effectiveness.md
  adr: docs/adr/ADR-008-rs-v2-4-source-effectiveness-promotion.md
  implementation:
  test:
  change_request:
---

# REQ-0023 — R/S V2.5 Historical Reliability & Confident Strength Shadow Evaluation

## Business Objective

Extend the R/S framework so that each current Support/Resistance level can be assessed not only by its runtime `CurrentStrength`, but also by historical out-of-sample evidence of the source lineage that created or confirmed that level.

V2.5 must create an auditable historical-confidence layer that answers:

> Given the sources contributing to this current R/S level, how much historical evidence exists that those sources have been effective for this ticker and horizon, and should that evidence increase, decrease, or leave unchanged our confidence in the current Strength?

V2.5 is a shadow/research release. It must measure and validate the value of historical confidence without changing production R/S ranking, source selection, runtime Strength calculation, or production decision behavior.

## Background / Problem

R/S V2.4 provides `vw_RS_Source_Effectiveness`, which contains historical source/config evidence by ticker and horizon, including:

- EffectivenessScore;
- Recommendation;
- Validation/Test sample counts;
- Validation/Test marginal lift;
- TemporalStability;
- RegimeStability;
- lineage outcome metrics where semantically valid.

However, V2.4 intentionally keeps Source Effectiveness separate from runtime `build_level_ladder()`. A current level can therefore have a high `CurrentStrength` even when its contributing sources have weak, unstable, insufficient or negative historical evidence.

The inverse is also possible: a level may have only moderate current structural strength but be formed by sources with strong and stable historical evidence for that ticker/horizon.

The remaining gap is a level-level historical reliability layer that combines current source lineage with V2.4 evidence while preserving the existing runtime contract.

V2.5 must close this evidence gap in shadow mode before any production behavior is changed.

## Stakeholders / Consumers

- R/S Engine owner.
- Quant/research workflow.
- Source Effectiveness governance workflow.
- Solution Architect.
- Test Engineer.
- CherryStock UI/analytics consumers.
- Future R/S decision-support and model-governance workflows.

## Functional Requirements

1. V2.5 must preserve three separate concepts:
   - `CurrentStrength`: runtime strength of the current level;
   - `HistoricalReliability`: historical evidence quality of the current level's contributing sources;
   - `ConfidentStrength`: a historical-evidence-adjusted confidence score derived from CurrentStrength and HistoricalReliability.

2. V2.5 must not overwrite or rename the existing `CurrentStrength` contract.

3. Historical reliability must be calculated at current R/S level granularity and remain traceable to:
   - ticker;
   - as-of date;
   - level rank;
   - level type;
   - source lineage;
   - evaluation horizon.

4. Historical reliability must use the latest completed public Source Effectiveness contract and must not depend on incomplete effectiveness runs.

5. Matching between current level lineage and historical evidence must use canonical `SourceKey` identity.

6. V2.5 must support at least the canonical horizons:
   - H5;
   - H10;
   - H20;
   - H40.

7. Horizon-specific evidence must remain separate. V2.5 must not silently merge H5/H10/H20/H40 into one confidence score.

8. LEVEL sources may use their V2.4 historical lineage and marginal evidence.

9. CONTEXT and CONFIRMATION sources must retain their V2.4 role semantics and must not be treated as direct price-level lineage when they are not price-level sources.

10. Source-level historical reliability must consider, where available and semantically applicable:
    - EffectivenessScore;
    - Recommendation;
    - ValidationEventCount;
    - TestEventCount;
    - ValidationMarginalLift;
    - TestMarginalLift;
    - TemporalStability;
    - RegimeStability;
    - lineage outcome evidence for LEVEL sources.

11. Recommendation must act as evidence classification, not as a substitute for the underlying metrics.

12. For LEVEL sources:
    - `CORE` and `SUPPORTING` are positive historical-evidence states;
    - `RESEARCH` means evidence is insufficient or not yet strong enough for positive production confidence;
    - `DROP` means current evidence does not support positive confidence and may justify a negative confidence adjustment.

13. For non-LEVEL roles, role-specific positive recommendations such as `CONFIRM_ONLY` and `CONTEXT_ONLY` must be respected according to their declared SourceRole.

14. Missing source-effectiveness evidence must be classified as `UNASSESSED`; missing evidence must never be interpreted as `DROP`.

15. V2.5 must calculate `EvidenceCoverage` for each current level/horizon so consumers can distinguish:
    - high reliability with broad evidence;
    - high reliability derived from sparse evidence;
    - insufficiently assessed source lineage.

16. HistoricalReliability must be normalized to a bounded 0–100 scale.

17. ConfidentStrength must be normalized to a bounded 0–100 scale.

18. The method used to combine source evidence into HistoricalReliability and to combine HistoricalReliability with CurrentStrength must be deterministic, versioned and policy-configurable.

19. Historical evidence may increase or decrease ConfidentStrength relative to CurrentStrength, but an unassessed or insufficient-evidence state must not create an artificial positive uplift.

20. V2.5 must expose the confidence adjustment separately so that users can explain:
    - current strength;
    - historical reliability;
    - evidence coverage;
    - adjustment direction/magnitude;
    - resulting ConfidentStrength.

21. V2.5 must retain source-level explainability sufficient to identify which sources:
    - contributed positive evidence;
    - were unassessed;
    - were RESEARCH;
    - were DROP;
    - drove a material confidence adjustment.

22. V2.5 must support a deterministic level confidence classification suitable for research/analytics, including at least:
    - `STRONG`;
    - `VALID`;
    - `CAUTION`;
    - `UNASSESSED`.

23. A negative-evidence state may additionally expose `REJECT` or an equivalent explicit negative classification if approved during architecture design.

24. V2.5 must run in shadow mode:
    - production `build_level_ladder()` behavior remains unchanged;
    - S1/S2/S3 and R1/R2/R3 ranking remains unchanged;
    - runtime source set remains unchanged;
    - CurrentStrength remains unchanged;
    - no current level is hidden or promoted because of HistoricalReliability;
    - no indicator/source configuration is automatically mutated.

25. Shadow output must be queryable and auditable for historical comparison between CurrentStrength and ConfidentStrength.

26. V2.5 evaluation must compare CurrentStrength-only performance with ConfidentStrength performance using out-of-sample TEST evidence.

27. V2.5 validation must include at least:
    - calibration quality;
    - hold/break discrimination;
    - temporal stability;
    - regime stability;
    - multi-horizon behavior;
    - evidence coverage.

28. V2.5 must report whether ConfidentStrength improves, preserves or degrades the agreed evaluation metrics relative to CurrentStrength.

29. V2.5 must support repeatable evaluation without changing production runtime behavior.

30. V2.5 completion must produce evidence sufficient to make a controlled V2.6 production-promotion decision.

## Business Rules

1. CurrentStrength answers: "How strong does this level look now?"

2. HistoricalReliability answers: "How trustworthy have the sources behind this level been historically for this ticker and horizon?"

3. ConfidentStrength answers: "How much confidence should be assigned to CurrentStrength after historical evidence is considered?"

4. HistoricalReliability is not a forecast probability.

5. Historical hold/break rates are supporting evidence and must not be presented as a calibrated current probability unless a later approved model explicitly calibrates them as such.

6. Source Effectiveness and runtime Strength remain separate evidence domains even when combined into ConfidentStrength.

7. No source with only `RESEARCH` evidence may be treated as confirmed positive evidence.

8. A `DROP` recommendation must never increase ConfidentStrength.

9. `UNASSESSED` evidence must never be interpreted as positive or negative evidence.

10. Evidence sufficiency must be visible separately from reliability quality.

11. A high HistoricalReliability score with low EvidenceCoverage must not be presented as high-confidence evidence.

12. Horizon semantics are future trading bars, not calendar days.

13. V2.5 is shadow-only and cannot authorize a runtime behavior change by itself.

14. Promotion from V2.5 to V2.6 requires explicit evidence-based gating.

15. If the evaluated source universe contains only RESEARCH/DROP evidence for the relevant role and ticker/horizon coverage, V2.5 may continue collecting shadow evidence but must not authorize V2.6 production integration.

## V2.5 → V2.6 Promotion Readiness Gate

V2.5 must generate a promotion-readiness assessment. V2.6 production integration is eligible only when all mandatory conditions below are met for the agreed production evaluation scope:

1. Source-effectiveness evidence includes positive promoted states, not only RESEARCH/DROP.
2. EvidenceCoverage is at least 70%.
3. At least 60% of assessed source contribution weight is supported by positive role-appropriate recommendations:
   - LEVEL: CORE or SUPPORTING;
   - CONFIRMATION: role-approved positive confirmation state;
   - CONTEXT: role-approved positive context state.
4. Average TEST marginal lift for the evidence used by the level-confidence model is non-negative.
5. TemporalStability is at least 0.70.
6. RegimeStability is at least 0.60.
7. Material DROP evidence must not be used to create a positive uplift.
8. ConfidentStrength must show no material out-of-sample degradation against CurrentStrength on the agreed primary validation metrics.
9. Any production promotion decision must be explicit and auditable.

Thresholds are initial governance defaults for V2.5 readiness and must be policy-configurable and versioned. Changing them requires an explicit governed change.

## Scope

### In Scope

- current-level historical reliability;
- source-lineage-to-effectiveness matching;
- role-aware historical evidence;
- multi-horizon reliability;
- evidence sufficiency and coverage;
- source-level explainability;
- HistoricalReliability 0–100;
- ConfidentStrength 0–100;
- confidence adjustment;
- shadow decision classification;
- shadow persistence/read contract;
- OOS comparison against CurrentStrength;
- V2.5-to-V2.6 promotion-readiness evidence;
- reproducible evaluation and validation.

### Out of Scope

- replacing CurrentStrength in production;
- changing `rank_levels()`;
- changing S1/S2/S3 or R1/R2/R3 ranking semantics;
- changing runtime source/provider registration;
- adding or deleting technical indicators;
- changing Indicator Engine calculation formulas;
- automatic source promotion;
- automatic runtime weight mutation;
- hiding current R/S levels based on historical evidence;
- calibrated future probability forecasting;
- black-box ML optimization of confidence weights;
- V2.6 production activation.

## Acceptance Criteria

### AC-01 — CurrentStrength remains unchanged

Given the same ticker, as-of date and runtime inputs  
When V2.5 shadow confidence is enabled  
Then the existing CurrentStrength value and R/S rank output are identical to the V2.4 runtime result.

### AC-02 — Separate confidence concepts

Given a current R/S level  
When V2.5 produces its shadow result  
Then CurrentStrength, HistoricalReliability and ConfidentStrength are separately identifiable.

### AC-03 — Canonical source matching

Given a current level with canonical source lineage  
When historical evidence is resolved  
Then only matching canonical SourceKeys are attributed to that level.

### AC-04 — Horizon separation

Given effectiveness evidence for H5/H10/H20/H40  
When level confidence is calculated  
Then each horizon has a separately identifiable HistoricalReliability and ConfidentStrength result.

### AC-05 — Latest completed effectiveness only

Given completed and incomplete Source Effectiveness runs  
When V2.5 resolves evidence  
Then incomplete runs do not contribute to the shadow confidence result.

### AC-06 — Missing evidence is UNASSESSED

Given a current level containing a source with no matching historical effectiveness evidence  
When V2.5 evaluates the level  
Then that source is reported as UNASSESSED and is not treated as DROP.

### AC-07 — EvidenceCoverage

Given a current level whose lineage is only partially represented by historical evidence  
When V2.5 evaluates the level  
Then EvidenceCoverage is less than 100% and the unassessed portion is explainable.

### AC-08 — RESEARCH is not confirmed positive evidence

Given a source whose Recommendation is RESEARCH  
When level reliability is calculated  
Then that source cannot be counted as CORE/SUPPORTING positive evidence.

### AC-09 — DROP cannot uplift confidence

Given a source whose Recommendation is DROP  
When ConfidentStrength is calculated  
Then that source cannot increase ConfidentStrength relative to otherwise equivalent evidence.

### AC-10 — Role-aware semantics

Given LEVEL, CONTEXT and CONFIRMATION sources contributing to runtime evidence  
When historical reliability is calculated  
Then each role uses its approved V2.4 evidence semantics and no false price-level lineage is fabricated for non-LEVEL roles.

### AC-11 — Bounded scores

Given any valid V2.5 level-confidence result  
When scores are produced  
Then HistoricalReliability and ConfidentStrength are each between 0 and 100 inclusive.

### AC-12 — Explainable adjustment

Given ConfidentStrength differs from CurrentStrength  
When the result is inspected  
Then the confidence adjustment and contributing source evidence can explain the direction of the change.

### AC-13 — Insufficient evidence cannot create uplift

Given evidence coverage or sufficiency is below policy requirements  
When shadow confidence is calculated  
Then the level is marked insufficient/UNASSESSED and no unsupported positive confidence uplift is produced.

### AC-14 — Shadow-only behavior

Given V2.5 is running in production data flow  
When shadow calculations complete  
Then no production rank, runtime source set, CurrentStrength, indicator metadata or source-promotion state is mutated.

### AC-15 — OOS comparison

Given a valid historical TEST evaluation set  
When CurrentStrength and ConfidentStrength are compared  
Then the evaluation reports their relative calibration and hold/break discrimination without using TRAIN-only evidence as final proof.

### AC-16 — Temporal and regime reporting

Given sufficient TEST evidence across time and regimes  
When V2.5 validation is run  
Then temporal and regime stability of ConfidentStrength are reported separately.

### AC-17 — Promotion blocked with only RESEARCH/DROP

Given the relevant evaluated source evidence contains only RESEARCH and/or DROP recommendations  
When V2.5 promotion readiness is evaluated  
Then V2.6 production promotion is not approved.

### AC-18 — Promotion readiness thresholds

Given a V2.5 candidate that meets the configured coverage, positive-evidence, TEST lift, temporal-stability and regime-stability thresholds  
When promotion readiness is evaluated  
Then the result explicitly records whether the candidate is eligible for V2.6 design/production approval.

### AC-19 — Repeatability

Given the same source-effectiveness snapshot, current-level inputs and confidence-policy version  
When V2.5 is rerun  
Then the resulting shadow confidence values are deterministic.

### AC-20 — Auditability

Given any V2.5 ConfidentStrength result  
When a reviewer inspects it  
Then the source evidence version, horizon, coverage and adjustment rationale can be reconstructed.

## Non-functional Requirements

- Performance: Shadow confidence calculation must not materially degrade interactive R/S UI response time; architecture must allow precomputation/caching or bounded reads if required.
- Reliability: Missing or stale effectiveness evidence must fail safe to CurrentStrength/UNASSESSED behavior rather than silently invent confidence.
- Security: No new external credentials or write access to Indicator Engine metadata is required.
- Observability: Runs and promotion-readiness decisions must be traceable by policy/version and evaluation evidence.
- Compatibility: Existing V2.4 runtime R/S outputs must remain backward compatible while V2.5 is in shadow mode.

## Dependencies

- REQ-0022 — R/S V2.4 Source Effectiveness & Indicator Promotion Framework.
- `vw_RS_Source_Effectiveness` with adequate source/ticker/horizon coverage.
- Existing V2.4 canonical source identity.
- Existing CurrentStrength and R/S level lineage.
- Historical V2.3/V2.4 evaluation events and TEST/OOS evidence.
- V2.5 architecture/ADR before implementation.
- Independent Test Engineer validation before promotion readiness can be accepted.

## Constraints

- V2.5 must not alter production ranking or runtime Strength behavior.
- No missing evidence may be silently treated as DROP.
- No TRAIN-only result may authorize production promotion.
- No Source Promotion Gate approval may automatically modify runtime behavior.
- Confidence policy and thresholds must be explicit, versioned and auditable.

## Assumptions

- Current R/S levels expose stable canonical source lineage.
- V2.4 Source Effectiveness remains the authoritative historical source-evidence contract.
- H5/H10/H20/H40 remain canonical horizons for this release.
- Source Effectiveness coverage will improve as monthly/full evaluations run.
- The first V2.5 implementation is deterministic and policy-driven rather than ML/AI black-box optimization.

## Open Questions

- None blocking requirement design. Exact score aggregation formula, source contribution weighting and bounded adjustment policy are architecture decisions and must be validated empirically before production promotion.

## Risks

- Sparse effectiveness coverage can make a high score appear more certain than the underlying evidence supports.
- Correlated sources can double-count historical confidence if source/family evidence is aggregated incorrectly.
- Using Recommendation alone without underlying metrics can over-simplify uncertainty.
- A fixed confidence formula may work for one horizon/regime and degrade another.
- Runtime latency may increase if effectiveness evidence is resolved synchronously without a suitable read contract.
- Premature production use can convert research evidence into false confidence.
- Policy thresholds may need recalibration as sample coverage grows.

## Suggested Routing

- Architecture required: Yes
- Primary next owner: SolutionArchitect
- Domain instructions: database.instructions.md; indicators.instructions.md; testing.instructions.md
- Validation owner: TestEngineer

## Handoff

```text
Status: READY_FOR_DESIGN
Primary next owner: SolutionArchitect
Acceptance criteria count: 20
Blocking questions: None
```
