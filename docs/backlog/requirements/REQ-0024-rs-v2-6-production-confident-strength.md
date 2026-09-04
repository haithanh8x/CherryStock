---
id: REQ-0024
title: R/S V2.6 Production Confident Strength Integration
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

# REQ-0024 — R/S V2.6 Production Confident Strength Integration

## Business Objective

Promote the V2.5 historical-confidence capability into production only after shadow/OOS evidence demonstrates that it is sufficiently covered, stable and non-degrading.

V2.6 must provide production consumers with a historically validated confidence score for each current R/S level while preserving the meaning of the existing runtime Strength and the proximity-based S/R ranking contract.

The production outcome must answer:

> For this current R/S level and selected horizon, what is the production confidence after current market structure and validated historical source evidence are both considered?

## Background / Problem

V2.4 intentionally separates runtime Strength from historical Source Effectiveness.

V2.5 introduces HistoricalReliability and ConfidentStrength in shadow mode so the project can test whether historical evidence actually improves confidence quality without altering production behavior.

A production integration must not happen merely because the V2.5 formula exists. It must be gated by:

- adequate Source Effectiveness coverage;
- positive role-appropriate source evidence;
- non-negative TEST marginal evidence;
- temporal and regime stability;
- OOS comparison against CurrentStrength;
- explainable and auditable confidence adjustments.

V2.6 is the controlled productionization step after V2.5 meets the promotion-readiness gate.

## Stakeholders / Consumers

- R/S Engine owner.
- CherryStock R/S UI consumers.
- Quant/research workflow.
- Source/model governance workflow.
- Solution Architect.
- Test Engineer.
- Downstream analytics or alerting consumers that use R/S confidence.

## Functional Requirements

1. V2.6 production activation must require a successful, auditable V2.5 promotion-readiness decision.

2. V2.6 must not activate production ConfidentStrength if the relevant evidence universe contains only RESEARCH/DROP states.

3. V2.6 must preserve `CurrentStrength` as a separately available production field and concept.

4. V2.6 must expose `HistoricalReliability`, `EvidenceCoverage`, `ConfidenceAdjustment` and `ConfidentStrength` as separately inspectable production outputs.

5. ConfidentStrength must be used only from an explicitly selected HorizonBars context. V2.6 must not silently collapse H5/H10/H20/H40 evidence into one score.

6. If a consumer requires a single default horizon, that default must be explicit, configurable and governed; no hidden horizon default is allowed.

7. Production ConfidentStrength must use the same versioned confidence policy that passed V2.5 validation, unless a new policy version is separately validated.

8. Production results must be reproducible from:
   - current level inputs;
   - source lineage;
   - Source Effectiveness evidence version;
   - horizon;
   - confidence policy version.

9. V2.6 must fail safe when historical evidence is missing, stale or below minimum sufficiency:
   - CurrentStrength remains available;
   - historical confidence is marked UNASSESSED/INSUFFICIENT_EVIDENCE;
   - no unsupported positive uplift is applied.

10. `DROP` evidence must never create positive confidence uplift.

11. `RESEARCH` evidence must not be counted as confirmed positive evidence.

12. `UNASSESSED` evidence must remain neutral and visible rather than being converted to DROP.

13. Positive evidence must remain role-aware:
   - LEVEL positive states are CORE/SUPPORTING;
   - CONFIRMATION positive evidence follows the approved confirmation recommendation contract;
   - CONTEXT positive evidence follows the approved context recommendation contract.

14. The production confidence adjustment must be bounded and policy-controlled so that HistoricalReliability cannot create an unbounded change to CurrentStrength.

15. CurrentStrength and ConfidentStrength must each remain bounded to 0–100.

16. R/S rank semantics must remain unchanged:
   - S1 remains the nearest valid support;
   - R1 remains the nearest valid resistance;
   - Strength/ConfidentStrength must not reorder levels unless a future separately approved requirement changes ranking semantics.

17. V2.6 must not automatically:
   - activate/deactivate Indicator Engine configs;
   - add/remove provider sources;
   - alter source-promotion audit outcomes;
   - change SourceRole;
   - change SourceFamily;
   - deploy a different indicator formula.

18. Production UI/analytics consumers must be able to distinguish CurrentStrength from ConfidentStrength and must not relabel ConfidentStrength as historical probability.

19. Production output must expose enough evidence metadata to explain why ConfidentStrength is above, below or equal to CurrentStrength.

20. Production output must expose the selected horizon and evidence coverage beside ConfidentStrength or through an equivalent inspectable detail contract.

21. V2.6 must provide deterministic confidence states including at least:
   - STRONG;
   - VALID;
   - CAUTION;
   - UNASSESSED;
   - and an explicit negative state such as REJECT when the approved policy requires it.

22. A low-coverage level must not be presented with the same confidence semantics as a high-coverage level even when their raw HistoricalReliability values are equal.

23. Production integration must preserve V2.4/V2.5 source-effectiveness governance and must not bypass Source Promotion Gate evidence.

24. V2.6 must support ongoing periodic re-evaluation as new Source Effectiveness evidence is produced.

25. A change in Source Effectiveness evidence may change future ConfidentStrength results, but the evidence/run/policy version used for each produced result must remain traceable.

26. V2.6 must support rollback/fallback to CurrentStrength-only production behavior without requiring deletion of historical effectiveness data.

27. V2.6 must include regression protection comparing production candidate behavior against the V2.4 CurrentStrength baseline.

28. V2.6 must not be considered complete until independent validation demonstrates no material production regression on the agreed OOS metrics and operational performance.

## Business Rules

1. V2.6 is a production confidence layer, not a replacement definition for CurrentStrength.

2. CurrentStrength remains the runtime structural/confluence score.

3. HistoricalReliability remains historical source-evidence quality.

4. ConfidentStrength is the production confidence score after the approved historical adjustment is applied.

5. ConfidentStrength is not automatically a probability of Hold, Break, price target or future return.

6. Production confidence is horizon-specific.

7. No hidden cross-horizon averaging is permitted.

8. Production uplift requires validated positive historical evidence.

9. Insufficient evidence can preserve or reduce confidence but cannot create unsupported positive confidence.

10. DROP evidence can only be neutral/negative to confidence according to the approved policy.

11. Ranking remains price-proximity/geometry based and independent of confidence score.

12. The V2.5 policy version that passes OOS validation is the starting V2.6 production policy.

13. Policy changes after production require versioning, regression validation and an explicit release/change record.

14. Source Effectiveness remains the historical evidence SSOT; production consumers must not query internal persistence tables when a public contract exists.

15. A production fallback path to CurrentStrength-only behavior is mandatory.

## V2.6 Production Entry Gate

Production activation is allowed only if V2.5 evidence demonstrates all of the following for the approved production scope:

1. EvidenceCoverage >= 70%.
2. Positive role-appropriate recommendation weight >= 60% of assessed source contribution weight.
3. Average TEST marginal lift >= 0.
4. TemporalStability >= 0.70.
5. RegimeStability >= 0.60.
6. Material DROP evidence is not used to produce positive uplift.
7. ConfidentStrength does not materially degrade the agreed primary OOS calibration/discrimination metrics versus CurrentStrength.
8. The candidate passes independent regression validation.
9. Runtime performance remains within the approved operational budget.
10. A rollback/fallback procedure is validated.
11. The production policy version and evidence basis are recorded.

If any mandatory condition fails, V2.6 production activation must remain blocked while V2.5 shadow evaluation may continue.

## Scope

### In Scope

- production exposure of HistoricalReliability;
- production EvidenceCoverage;
- production ConfidenceAdjustment;
- production horizon-specific ConfidentStrength;
- production confidence classification;
- role-aware historical evidence;
- fail-safe handling for missing/insufficient evidence;
- explainability;
- versioned policy/evidence lineage;
- UI/analytics read contract;
- regression validation;
- operational fallback;
- ongoing periodic evidence refresh.

### Out of Scope

- changing S1/R1 proximity-based ranking;
- automatic removal of R/S levels;
- automatic source onboarding/deletion;
- technical-indicator formula changes;
- replacing Source Promotion Gate;
- TRAIN-only production promotion;
- converting historical rates into calibrated probabilities without a separate approved requirement;
- ML black-box dynamic weighting;
- intraday confidence unless separately designed and approved;
- automatic trading decisions.

## Acceptance Criteria

### AC-01 — V2.5 gate is mandatory

Given a V2.6 production candidate  
When no passing V2.5 promotion-readiness decision exists  
Then production ConfidentStrength activation is blocked.

### AC-02 — Only RESEARCH/DROP blocks promotion

Given the relevant source evidence contains only RESEARCH and/or DROP recommendations  
When production eligibility is evaluated  
Then V2.6 is not activated.

### AC-03 — CurrentStrength preserved

Given V2.6 is active  
When an R/S level is returned  
Then CurrentStrength remains separately available and retains its original meaning.

### AC-04 — Production confidence fields

Given a production R/S level with sufficient evidence  
When the level is consumed  
Then HistoricalReliability, EvidenceCoverage, ConfidenceAdjustment and ConfidentStrength are available as distinct outputs.

### AC-05 — Explicit horizon

Given production historical confidence is requested  
When ConfidentStrength is resolved  
Then the HorizonBars used is explicit and inspectable.

### AC-06 — No silent cross-horizon merge

Given different confidence values for H5/H10/H20/H40  
When a consumer requests one horizon  
Then evidence from other horizons is not silently averaged into the selected result.

### AC-07 — Insufficient evidence fallback

Given evidence coverage/sufficiency falls below production policy  
When the current level is evaluated  
Then CurrentStrength remains available, the historical state is marked insufficient/UNASSESSED and no positive confidence uplift is applied.

### AC-08 — DROP cannot uplift

Given a contributing source has DROP evidence  
When production confidence is calculated  
Then that evidence cannot increase ConfidentStrength.

### AC-09 — RESEARCH is not promoted evidence

Given a contributing source has RESEARCH evidence  
When the production positive-evidence ratio is calculated  
Then that source is not counted as CORE/SUPPORTING confirmed positive evidence.

### AC-10 — Bounded scores

Given any production result  
When CurrentStrength and ConfidentStrength are exposed  
Then both remain within 0–100 inclusive.

### AC-11 — Rank unchanged

Given identical current market inputs  
When V2.6 is enabled versus CurrentStrength-only mode  
Then S1/S2/S3 and R1/R2/R3 rank ordering remains unchanged.

### AC-12 — Explainable adjustment

Given ConfidentStrength differs from CurrentStrength  
When a user or test inspects the level detail  
Then the horizon, coverage and source evidence driving the adjustment are traceable.

### AC-13 — No Indicator Engine mutation

Given V2.6 produces positive confidence evidence  
When the result is applied  
Then no Indicator Engine metadata/configuration is automatically changed.

### AC-14 — No runtime source mutation

Given a source is CORE/SUPPORTING  
When V2.6 calculates confidence  
Then the source status alone does not automatically add/remove runtime providers or source configs.

### AC-15 — Promotion thresholds enforced

Given any V2.5 production candidate fails one or more mandatory V2.6 entry thresholds  
When activation is evaluated  
Then production activation is blocked.

### AC-16 — OOS non-degradation

Given a candidate production confidence policy  
When evaluated on the approved TEST/OOS scope  
Then it must meet the approved non-degradation criterion versus CurrentStrength before activation.

### AC-17 — Temporal/regime gate

Given temporal or regime stability is below the production threshold  
When activation is evaluated  
Then the candidate is blocked from production.

### AC-18 — Evidence version traceability

Given any production ConfidentStrength result  
When audited  
Then the Source Effectiveness evidence version/run and confidence policy version can be identified.

### AC-19 — Repeatability

Given unchanged market inputs, effectiveness evidence, horizon and policy version  
When the production calculation is repeated  
Then the result is deterministic.

### AC-20 — Fallback

Given historical-confidence data is unavailable or the feature is disabled  
When R/S is requested  
Then the system can return to CurrentStrength-only behavior without corrupting R/S output.

### AC-21 — Regression protection

Given V2.6 implementation is ready for release  
When regression validation is run  
Then V2.4 baseline ladder behavior remains compatible except for the explicitly added confidence outputs.

### AC-22 — Operational performance

Given the agreed production workload  
When V2.6 confidence is enabled  
Then runtime performance remains within the approved operational budget.

### AC-23 — Ongoing refresh

Given a newer completed Source Effectiveness evidence set becomes available  
When the periodic confidence refresh is executed  
Then future results may use the newer evidence while prior results remain auditable to their original version.

### AC-24 — Rollback readiness

Given V2.6 must be rolled back  
When the rollback procedure is executed  
Then CurrentStrength-only production behavior can be restored without deleting V2.4/V2.5 historical evidence.

## Non-functional Requirements

- Performance: Production confidence must not materially degrade interactive R/S response time; the architecture must define and validate an operational latency budget.
- Reliability: Missing/stale evidence must fail safe and must never silently fabricate positive confidence.
- Security: No additional external credential or privileged Indicator Engine mutation is required.
- Observability: Production confidence policy, evidence version, horizon, coverage and fallback events must be observable.
- Compatibility: Existing CurrentStrength and proximity-based rank semantics remain backward compatible.
- Recoverability: A tested fallback to CurrentStrength-only behavior is mandatory.
- Auditability: Each production confidence result must be reconstructable from versioned inputs and policy.

## Dependencies

- REQ-0023 — R/S V2.5 Historical Reliability & Confident Strength Shadow Evaluation.
- Passing V2.5 promotion-readiness evidence.
- REQ-0022 / V2.4 Source Effectiveness evidence.
- Adequate `vw_RS_Source_Effectiveness` source/ticker/horizon coverage.
- Approved V2.6 architecture/ADR.
- Independent Test Engineer validation.
- Explicit Change Request/release approval before production activation.

## Constraints

- Production activation is prohibited without V2.5 gate evidence.
- CurrentStrength cannot be silently replaced.
- LevelRank semantics cannot change in this requirement.
- Source/indicator lifecycle cannot be mutated by confidence scoring.
- Policy/evidence lineage must be versioned.
- No hidden horizon aggregation is permitted.
- A safe fallback path is mandatory.

## Assumptions

- V2.5 provides deterministic shadow confidence results and auditable evidence.
- V2.4 Source Effectiveness remains available as the historical evidence SSOT.
- Current R/S source lineage remains stable/canonical.
- H5/H10/H20/H40 remain supported production research horizons.
- The production policy will initially remain deterministic and explainable.

## Open Questions

- None blocking architecture design. Exact UI placement, operational latency budget, confidence-adjustment cap and any default consumer horizon must be decided during Solution Architecture and validated before production activation.

## Risks

- Production confidence can be over-trusted if users confuse it with calibrated probability.
- Sparse or stale source evidence can produce misleading confidence unless fail-safe rules are enforced.
- A confidence formula optimized on one period may degrade under new regimes.
- Source correlation can inflate reliability unless family-level evidence is respected.
- Runtime latency may increase if evidence resolution is not designed efficiently.
- Downstream consumers may accidentally replace CurrentStrength semantics rather than use the new field explicitly.
- Evidence updates can cause score drift and require strong version traceability.
- Production rollout without fallback would create avoidable operational risk.

## Suggested Routing

- Architecture required: Yes
- Primary next owner: SolutionArchitect
- Domain instructions: database.instructions.md; chart.instructions.md; indicators.instructions.md; testing.instructions.md
- Validation owner: TestEngineer

## Handoff

```text
Status: READY_FOR_DESIGN
Primary next owner: SolutionArchitect
Acceptance criteria count: 24
Blocking questions: None
```
