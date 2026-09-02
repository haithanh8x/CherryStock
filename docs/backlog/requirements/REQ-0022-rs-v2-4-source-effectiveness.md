---
id: REQ-0022
title: R/S V2.4 Source Effectiveness & Indicator Promotion Framework
status: READY_FOR_DESIGN
priority: P0
owner: BusinessAnalyst
primary_next_owner: SolutionArchitect
related:
  architecture: docs/architecture/RS_Ladder.md
  adr: docs/adr/ADR-007-rs-v2-3-evaluation-governance.md
  implementation:
  test:
  change_request:
---

# REQ-0022 — R/S V2.4 Source Effectiveness & Indicator Promotion Framework

## Business Objective

Provide a reproducible, point-in-time and out-of-sample framework to determine whether an R/S source, indicator configuration or source family actually adds predictive value for each stock before that source is approved for integration into the R/S Engine.

The framework must answer:

- Which source/config is effective for a specific ticker?
- Is the source effective standalone or only because it is correlated with existing sources?
- Does the source add incremental out-of-sample value after existing R/S evidence is already present?
- Is effectiveness stable across time horizons and market regimes?
- Should the source be classified as CORE, SUPPORTING, role-specific, RESEARCH or DROP?
- Does the evidence support global integration, ticker-selective research, or rejection?

## Background / Problem

R/S V2.0–V2.2 progressively added MA, Bollinger Bands, structural levels, ATR context, RSI confirmation and Volume Profile.

R/S V2.3 added historical evaluation, temporal split, regime metrics, ablation, model versioning and Promotion Gate governance.

The remaining gap is source-level attribution and promotion readiness.

A runtime Strength score answers:

> How confident is the engine in this level now?

It does not answer:

> Has this source historically added predictive value for this ticker after controlling for the rest of the model?

Using runtime Strength alone to decide whether an indicator belongs in the R/S Engine risks:

- circular validation;
- correlated-source double counting;
- global weights that hide ticker-specific differences;
- overfitting to TRAIN data;
- promoting sources that look good standalone but add no marginal value;
- promoting sources that improve aggregate metrics while degrading TEST or market regimes.

V2.4 must convert V2.3 historical evidence into a source-effectiveness and indicator/source-promotion decision framework.

## Stakeholders / Consumers

- R/S Engine owner.
- Indicator Management workflow.
- Solution Architect.
- Quant/research workflow.
- Test Engineer.
- CherryStock UI/analytics consumers.
- Future automated model/source governance workflows.

## Functional Requirements

1. The framework must calculate source effectiveness at least by:
   - ticker;
   - source/config key;
   - source family;
   - source role;
   - evaluation horizon.

2. The framework must distinguish:
   - runtime Strength;
   - historical Source Effectiveness;
   - model-level Promotion Gate.

3. LEVEL sources must support source-lineage effectiveness using historical events where the source actually contributed to a level.

4. CONTEXT and CONFIRMATION sources must not be falsely scored as price levels. Their effectiveness must be measured through marginal model contribution/ablation.

5. The framework must support standalone source evaluation when a source/config can be isolated.

6. The framework must support source-config ablation:
   - full baseline;
   - baseline minus one source/config.

7. The framework must support source-family ablation.

8. The framework must calculate out-of-sample marginal contribution using VALIDATION and TEST evidence.

9. The framework must calculate temporal stability between VALIDATION and TEST.

10. The framework must calculate regime stability across available market regimes.

11. The framework must expose per-ticker effectiveness rather than relying only on global averages.

12. The framework must support multiple evaluation horizons, including at least:
    - 5 bars;
    - 10 bars;
    - 20 bars;
    - 40 bars.

13. The framework must calculate an Effectiveness Score normalized to 0–100.

14. LEVEL-source effectiveness must include evidence from:
    - touch behavior;
    - hold behavior;
    - retest behavior;
    - directional edge;
    - temporal stability;
    - regime stability;
    - marginal contribution.

15. CONTEXT/CONFIRMATION effectiveness must use a role-appropriate formula and must not fabricate touch/hold attribution.

16. The framework must apply break and complexity penalties where applicable.

17. The framework must generate a recommendation for each ticker/source/horizon.

18. Supported recommendations must include at least:
    - CORE;
    - SUPPORTING;
    - CONFIRM_ONLY;
    - CONTEXT_ONLY;
    - RESEARCH;
    - DROP.

19. Recommendations must respect the source's declared role. The framework must not silently reclassify a LEVEL source into CONTEXT or CONFIRMATION.

20. The framework must support a promotion decision for adding a source/config to R/S integration scope.

21. Promotion must require out-of-sample evidence, not TRAIN-only performance.

22. Promotion must distinguish:
    - global promotion readiness;
    - ticker-selective effectiveness;
    - rejection/research-only state.

23. A passing source-promotion gate must produce an approval/audit record only.

24. Source promotion must not automatically:
    - modify Indicator Engine metadata;
    - activate an indicator;
    - change R/S runtime source registry;
    - change runtime weights;
    - deploy a new production model.

25. Any real runtime integration following approval must require a separate implementation/release step.

26. The framework must persist effectiveness results for later comparison and audit.

27. The framework must expose a public read contract for the latest source-effectiveness result.

28. Evaluation/persistence workflows must be rerunnable without duplicate source-effectiveness records for the same run/key.

29. Existing V2.3 model evaluation and Promotion Gate must remain backward compatible.

30. V2.0–V2.3 runtime R/S behavior must remain unchanged unless a later explicit approved release changes it.

## Business Rules

1. Runtime Strength and Source Effectiveness are separate concepts.

2. Source Effectiveness is historical evidence, not a runtime R/S rank.

3. The primary promotion metric is incremental out-of-sample lift.

4. Standalone effectiveness alone is insufficient for promotion.

5. A source that is highly correlated with existing evidence may receive a high standalone score but low marginal contribution.

6. Source-family correlation must be evaluated explicitly.

7. TRAIN data may be used for research/calibration but cannot authorize promotion.

8. VALIDATION and TEST results must be reported separately.

9. Negative TEST lift blocks global promotion.

10. Material regime degradation blocks global promotion.

11. Ticker-specific strength does not imply global strength.

12. A source may be strong for a subset of tickers without qualifying for global promotion.

13. CONTEXT and CONFIRMATION sources are judged by marginal contribution, not by direct price-level hit metrics unless their semantics explicitly support price levels.

14. Source recommendations do not override SourceRole or ValueSemantic.

15. Promotion approval is governance metadata only.

16. Any concrete technical-indicator onboarding/modification after V2.4 approval remains owned by the Indicator Management workflow.

## Scope

### In Scope

- source/config effectiveness calculation;
- source-family effectiveness;
- ticker-level effectiveness;
- role-aware scoring;
- multi-horizon evaluation;
- source/config include/exclude research controls;
- source/family ablation;
- temporal/regime stability;
- marginal VALIDATION/TEST lift;
- complexity/break penalties;
- effectiveness recommendation;
- source-promotion gate;
- persistence and audit;
- public latest-effectiveness view;
- reproducible scripts;
- automated tests and production validation runbook.

### Out of Scope

- adding a new concrete technical indicator;
- changing indicator calculation formulas;
- activating/deactivating Indicator Engine configs;
- automatic alteration of R/S runtime weights;
- automatic runtime source registration;
- auto-deployment after promotion approval;
- ML/AI black-box optimization of source weights;
- intraday/tick-level R/S evaluation;
- replacing V2.3 model Promotion Gate.

## Acceptance Criteria

### AC-01 — Separation from runtime Strength

Given an R/S level with a runtime Strength score  
When source effectiveness is calculated  
Then the historical Effectiveness Score is produced independently and does not overwrite runtime Strength.

### AC-02 — Per-ticker output

Given historical evaluation data for multiple tickers  
When source effectiveness is calculated  
Then a distinct effectiveness result is available for each ticker/source/horizon combination.

### AC-03 — Source-config granularity

Given a provider containing multiple stable source/config keys  
When a source/config is evaluated  
Then it can be included or excluded without dropping the entire provider.

### AC-04 — LEVEL lineage attribution

Given a LEVEL source present in historical R/S event lineage  
When effectiveness is calculated  
Then touch/hold/retest/directional-edge metrics are derived only from events containing that canonical source key.

### AC-05 — Role-aware CONTEXT behavior

Given a CONTEXT source such as ATR  
When effectiveness is calculated  
Then no direct price-level touch/hold score is fabricated and the result is driven by marginal model contribution and stability.

### AC-06 — Role-aware CONFIRMATION behavior

Given a CONFIRMATION source such as RSI  
When effectiveness is calculated  
Then no direct price-level source attribution is fabricated and the result is driven by marginal contribution and stability.

### AC-07 — VALIDATION marginal lift

Given baseline and ablation runs using the same dataset/horizon  
When effectiveness is calculated  
Then VALIDATION quality delta is stored separately.

### AC-08 — TEST marginal lift

Given baseline and ablation runs using the same dataset/horizon  
When effectiveness is calculated  
Then TEST quality delta is stored separately.

### AC-09 — Negative TEST protection

Given a source with positive TRAIN/VALIDATION evidence but negative TEST marginal lift beyond policy tolerance  
When promotion is evaluated  
Then global promotion is rejected.

### AC-10 — Temporal stability

Given VALIDATION and TEST source evidence  
When effectiveness is calculated  
Then temporal stability is normalized to 0–1.

### AC-11 — Regime stability

Given source evidence across multiple regimes  
When effectiveness is calculated  
Then regime stability is normalized to 0–1 and material regime degradation is visible.

### AC-12 — Multi-horizon support

Given horizons 5, 10, 20 and 40 bars  
When effectiveness runs are executed  
Then results remain separately identifiable by horizon.

### AC-13 — Effectiveness Score bounds

Given any valid source-effectiveness result  
When the score is calculated  
Then EffectivenessScore is between 0 and 100 inclusive.

### AC-14 — LEVEL recommendation

Given a LEVEL source with strong OOS effectiveness and positive marginal lift  
When recommendation is generated  
Then the result can be CORE or SUPPORTING according to policy thresholds.

### AC-15 — Confirmation recommendation

Given a CONFIRMATION source meeting its role-aware thresholds  
When recommendation is generated  
Then the recommendation is CONFIRM_ONLY and does not convert it into a LEVEL source.

### AC-16 — Context recommendation

Given a CONTEXT source meeting its role-aware thresholds  
When recommendation is generated  
Then the recommendation is CONTEXT_ONLY.

### AC-17 — Drop recommendation

Given a source with weak effectiveness or materially negative TEST lift  
When recommendation is generated  
Then recommendation is DROP or RESEARCH according to policy.

### AC-18 — Family correlation control

Given multiple source configs from the same family  
When family effectiveness is evaluated  
Then the framework can compare source-level lift with family-level lift and does not treat the configs as independent families.

### AC-19 — Global promotion gate

Given effectiveness evidence across enough tickers  
When the source-promotion gate is evaluated  
Then global approval requires minimum ticker coverage, positive-ticker ratio, OOS lift, stability and complexity constraints.

### AC-20 — Ticker-selective outcome

Given a source that is strong on some tickers but does not meet global breadth requirements  
When promotion is evaluated  
Then the outcome can explicitly remain ticker-selective/research-only rather than being globally promoted.

### AC-21 — No automatic Indicator Engine mutation

Given a source-promotion decision of approved  
When the decision is applied  
Then no Indicator Engine dimension/config metadata is changed automatically.

### AC-22 — No automatic R/S runtime mutation

Given a source-promotion decision of approved  
When the decision is applied  
Then no R/S runtime registry, source set or production weight is changed automatically.

### AC-23 — Auditability

Given a source-promotion decision  
When it is persisted  
Then baseline/ablation evidence, policy, score, recommendation, reasons and decision timestamp are auditable.

### AC-24 — Idempotency

Given the same effectiveness run ID and source/ticker/horizon keys  
When persistence is rerun  
Then no duplicate result rows are created.

### AC-25 — Public read contract

Given persisted source-effectiveness results  
When a consumer queries the public latest-effectiveness contract  
Then the latest record per ticker/source/horizon is available without reading internal implementation tables directly.

### AC-26 — V2.3 compatibility

Given the V2.3 baseline and golden benchmark  
When V2.4 is introduced with no approved source deployed  
Then V2.3 runtime outputs and invariants remain unchanged.

### AC-27 — Bounded promotion

Given a promotion gate dry-run  
When it returns approved  
Then approval remains non-deploying until a separate implementation/release occurs.

### AC-28 — Reproducibility

Given the same historical dataset, policy, source filters and run IDs  
When the analysis is rerun  
Then source-effectiveness outputs are deterministic.

## Non-functional Requirements

- Performance:
  - reuse persisted V2.3 events/metrics wherever possible;
  - avoid recalculating full historical ladders when a persisted compatible run can be reused;
  - persist effectiveness results in batch.

- Reliability:
  - fail clearly on incompatible baseline/ablation dataset, horizon or split;
  - no silent fallback from OOS evidence to TRAIN-only decisions.

- Security:
  - no new credential or secret requirements.

- Observability:
  - all source-promotion decisions must persist reasons/policy/evidence identifiers;
  - scripts must print deterministic summary/result IDs.

- Compatibility:
  - V2.0–V2.3 runtime behavior remains backward compatible;
  - V2.3 model Promotion Gate remains available unchanged.

## Dependencies

- R/S V2.3 historical evaluation events/metrics.
- V2.3 model version registry and evaluation run persistence.
- Existing SourceRole / SourceFamily / ValueSemantic contracts.
- Existing Indicator Engine SSOT for indicator config identity.
- DuckDB migration capability for new V2.4 persistence/read view.

## Constraints

- GitHub Markdown remains engineering SSOT.
- DuckDB DDL is generated in repository and executed externally.
- MCP may remain read-only for DDL.
- Promotion approval must not bypass Indicator Management for concrete technical-indicator lifecycle changes.
- No future data may influence historical source generation.

## Assumptions

- V2.3 production migration and validation remain PASS.
- Historical event lineage is sufficient for direct LEVEL-source attribution.
- CONTEXT/CONFIRMATION roles require ablation-based attribution.
- A later approved runtime integration may use V2.4 output but is not part of this requirement.

## Open Questions

None blocking.

Policy thresholds are configurable architecture parameters and may be calibrated after initial implementation without changing the core business rules.

## Risks

- insufficient per-ticker TEST sample sizes;
- correlated source configs overstating standalone quality;
- regime sparsity;
- dynamic structural source codes requiring canonicalization;
- confusing source promotion with production deployment;
- excessive historical reruns if existing V2.3 evidence is not reused.

## Suggested Routing

- Architecture required: Yes
- Primary next owner: SolutionArchitect
- Domain instructions:
  - database.instructions.md
  - indicators.instructions.md
  - testing.instructions.md
- Validation owner: TestEngineer

## Handoff

```text
REQUIREMENT HANDOFF
Requirement ID: REQ-0022
Outcome: Define R/S V2.4 Source Effectiveness & Indicator Promotion Framework
Status: READY_FOR_DESIGN
Primary next owner: SolutionArchitect
Material: docs/backlog/requirements/REQ-0022-rs-v2-4-source-effectiveness.md
Open questions: None blocking
Acceptance criteria count: 28
```
