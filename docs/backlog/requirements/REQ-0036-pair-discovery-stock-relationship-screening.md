---
id: REQ-0036
title: Pair Discovery and Stock Relationship Screening
status: READY_FOR_DESIGN
priority: P1
owner: BusinessAnalyst
primary_next_owner: SolutionArchitect
related:
  architecture:
  adr:
  implementation:
  test:
  change_request:
---

# REQ-0036 — Pair Discovery and Stock Relationship Screening

## Business Objective

Enable CherryStock to discover economically and statistically meaningful stock pairs across the active equity universe without performing expensive full-depth analysis on every possible pair.

The capability shall use a coarse-to-fine screening process so inexpensive filters reduce the candidate universe before rolling relationship, lead/lag and long-run relationship analysis is performed. The outcome is a ranked, explainable candidate-pair watchlist suitable for deeper research and future pair-oriented trading analysis while keeping daily compute and runtime practical.

## Background / Problem

A universe of N stocks produces N×(N-1)/2 unique pairs. Running full rolling correlation, lead/lag analysis, market-neutral analysis, cointegration and related tests for every pair would spend compute on many pairs with weak data quality or little economic/statistical relevance.

CherryStock therefore needs a Pair Discovery layer before deep pair analysis. Screening must be computationally cheaper than the downstream tests, preserve enough candidates to avoid an overly narrow search, and make the reasons for promotion/rejection observable.

This requirement defines WHAT the discovery and screening capability must achieve. Exact algorithms, thresholds, matrix libraries, persistence schemas, scheduling topology and optimization techniques belong to Solution Architecture and implementation.

## Stakeholders / Consumers

- CherryStock owner/operator.
- Research and pair-analysis workflows.
- Daily analytical pipeline.
- Future pair scanner/watchlist UI.
- Future strategy/backtest consumers, subject to separate production requirements.

## Functional Requirements

1. CherryStock shall support discovery of candidate stock pairs from an eligible active-stock universe.
2. The discovery process shall exclude stocks that do not satisfy defined minimum data-quality and tradability eligibility rules before pair generation.
3. The process shall support economic/contextual screening, including sector or other approved relationship metadata, to reduce implausible pair comparisons where appropriate.
4. The process shall compute a low-cost statistical similarity/correlation screening layer across the remaining universe.
5. The screening layer shall support ranking candidates per stock rather than requiring full-depth analysis of every possible pair.
6. CherryStock shall support retaining a bounded Top-K or otherwise bounded candidate set per stock using an approved screening policy.
7. Candidate promotion shall be explainable through observable screening inputs and scores rather than an opaque pass/fail result.
8. Promoted candidates shall be eligible for progressively more expensive analysis, including:
   - rolling relationship stability;
   - lead/lag relationship;
   - market/sector-adjusted relationship where applicable;
   - long-run/cointegration analysis where applicable.
9. Expensive deep-analysis stages shall run only on candidates that survive the required upstream screening gates.
10. The process shall avoid duplicate logical pairs such as treating A-B and B-A as two independent pair identities unless direction is explicitly relevant to a downstream metric.
11. Daily operation shall support reusing prior computation/state where appropriate so unchanged historical data does not require unnecessary full-history recomputation.
12. The system shall expose enough run statistics to identify the number of stocks/pairs entering and surviving each screening stage.
13. The system shall produce a ranked pair-candidate output containing enough evidence for a user or downstream workflow to understand why the pair is considered interesting.
14. Pair discovery shall remain analytically separate from an automated BUY/SELL execution decision.
15. The design shall support future expansion from two-stock analysis to market-wide pair scanning without requiring all deep statistical methods to execute across the full raw pair universe.

## Business Rules

1. Screening is a candidate-discovery mechanism, not proof of a causal relationship between two stocks.
2. Price-level correlation alone shall not be treated as sufficient evidence of a relationship; return-based or otherwise approved stationary/normalized measures shall be used for statistical screening.
3. A high raw correlation caused primarily by broad market or sector movement shall not automatically be interpreted as a stock-specific relationship.
4. Candidate ranking must not be presented as a guaranteed trading opportunity.
5. Missing or insufficient history must be represented as ineligible/unassessed rather than silently converted to a weak relationship score.
6. Screening thresholds and Top-K limits must be configurable or design-governed rather than embedded as permanent business truth.
7. Deep-analysis results must preserve the analysis window and data boundary used so future data cannot leak into historical evaluation/backtests.
8. Daily recomputation should favor incremental/reusable calculation when it preserves analytical equivalence and data integrity.
9. The initial capability should prioritize practical compute reduction and explainability over unnecessary algorithmic complexity.
10. ANN/vector-search acceleration is optional and must not be required for the initial capability unless architecture benchmarks show a material need.

## Scope

### In Scope

- Eligible stock-universe definition for pair discovery.
- Data-quality/liquidity/tradability screening.
- Sector/economic-context filtering where approved.
- Fast return-based similarity/correlation screening.
- Bounded candidate ranking such as Top-K per stock.
- Progressive candidate funnel.
- Rolling relationship stability for promoted candidates.
- Lead/lag analysis for promoted candidates.
- Market/sector-adjusted relationship analysis where applicable.
- Cointegration/long-run relationship testing for the final candidate subset where applicable.
- Pair score/ranking and explainable pair watchlist output.
- Stage-by-stage funnel metrics and compute/runtime observability.
- Incremental/reusable daily computation requirements.

### Out of Scope

- Automated order execution.
- Treating correlation as causation.
- Guaranteed profitability claims.
- Exhaustive deep analysis of every possible pair as the normal daily path.
- Mandatory ANN/FAISS/HNSW implementation in the first version.
- Prescribing exact database schemas, Python modules, libraries, worker topology or mathematical thresholds before architecture approval.
- Final pair-trading entry/exit/risk rules; these require a separate strategy requirement and validation.
- Production activation of a pair strategy without independent out-of-sample/backtest validation.

## Acceptance Criteria

### AC-01 — Eligible universe screening

Given the active stock universe,
When pair discovery starts,
Then stocks failing the approved minimum history/data-quality/tradability criteria are excluded or marked ineligible before deep pair analysis.

### AC-02 — Candidate reduction

Given an eligible universe containing multiple possible pairs,
When the fast screening stages complete,
Then the number of pairs promoted to deep analysis is lower than the raw unique-pair count and the funnel reports counts for each stage.

### AC-03 — Return-based screening

Given synchronized price histories for two eligible stocks,
When statistical screening is performed,
Then the screening relationship is not based solely on correlation of untransformed trending price levels.

### AC-04 — Bounded candidate set

Given a stock with many possible peers,
When fast similarity screening completes,
Then CherryStock can retain a bounded ranked candidate set according to the approved screening policy without requiring deep analysis of every peer.

### AC-05 — Explainable promotion

Given a pair is promoted,
When its discovery result is inspected,
Then the user can identify the relevant screening evidence such as eligibility/context, similarity/correlation measure, analysis window and candidate rank/score.

### AC-06 — Progressive deep analysis

Given a pair fails a required upstream screening gate,
When the discovery pipeline proceeds,
Then downstream expensive tests for that pair are skipped unless an explicit override/research mode is used.

### AC-07 — Unique pair identity

Given stocks A and B,
When pair candidates are materialized,
Then A-B and B-A do not create duplicate logical pair records except for explicitly directional lead/lag outputs.

### AC-08 — Incremental daily operation

Given a prior successful discovery run and one new daily data boundary,
When the next daily run executes,
Then the design supports reuse/incremental update of eligible computations where analytically valid rather than requiring unconditional full-history recomputation.

### AC-09 — Deep relationship evidence

Given a pair reaches the final candidate stage,
When deep analysis is available,
Then its output can distinguish short/medium-horizon co-movement from lead/lag and long-run relationship evidence instead of collapsing all evidence into one correlation number.

### AC-10 — Compute observability

Given a completed discovery run,
When the operator reviews run metadata,
Then the system exposes candidate counts by stage and sufficient duration/compute indicators to identify expensive stages and evaluate screening effectiveness.

### AC-11 — Historical integrity

Given a historical evaluation boundary,
When pair discovery or downstream analysis is replayed,
Then only information available at that boundary is used for eligibility, scoring and promotion.

### AC-12 — No trading claim

Given a pair receives a high relationship/discovery score,
When the result is presented,
Then it is identified as a research/watchlist candidate and not automatically represented as a BUY/SELL instruction.

## Non-functional Requirements

- Performance: Normal daily pair discovery must materially reduce expensive pair-level analyses relative to running the full deep-analysis stack on all raw pairs; measurable targets shall be established from baseline benchmarks during design.
- Scalability: The design shall remain practical as the active equity universe grows and shall permit later acceleration if benchmarks justify it.
- Explainability: Screening and promotion reasons must be inspectable.
- Reproducibility: Analysis windows, data boundaries and relevant configuration/version information must be recoverable for research and validation.
- Reliability: Re-running the same completed data boundary shall not create duplicate logical candidates or inconsistent pair identities.
- Observability: Stage counts and timings must be available to evaluate both analytical selectivity and compute cost.
- Compatibility: The capability shall integrate with existing CherryStock daily data and analytics contracts without making pair discovery a new market-data Source of Truth.

## Dependencies

- Canonical adjusted/synchronized stock price and return-capable history.
- Active ticker/universe contract.
- Sector/industry or other approved classification metadata where contextual filtering is used.
- Existing daily pipeline/data-quality boundaries.
- Solution Architecture definition for candidate identity, screening contracts, computation boundaries and persistence.
- Testing/OOS governance for any later trading-strategy use.

## Constraints

- GitHub repository remains the CherryStock engineering Single Source of Truth.
- The requirement must not prescribe a specific matrix library, ANN engine, schema, class/module layout or worker topology before architecture approval.
- Deep analysis must not be run across all raw pairs by default when cheaper upstream gates can reject candidates.
- Screening must preserve timestamp/data-boundary integrity for future backtesting.
- Runtime optimization must not silently change analytical meaning without validation.

## Assumptions

- Daily/EOD data is sufficient for the initial pair-discovery capability.
- The initial CherryStock equity universe is small enough that a vectorized fast-screening stage is likely practical, subject to benchmark validation.
- Sector/economic metadata is available or can be mapped from an approved source.
- Pair discovery is initially a research/watchlist capability, not an execution engine.
- More advanced approximate-nearest-neighbor acceleration can be introduced later if measured scale/latency warrants it.

## Open Questions

- What minimum history, liquidity and missing-data criteria define the eligible universe?
- Should contextual screening be strictly same-sector initially, or allow approved cross-sector economic relationships?
- Which horizons should contribute to the fast similarity screen?
- Should candidate selection use Top-K per stock, a global score threshold, or a hybrid policy?
- What candidate-reduction ratio and daily runtime should be the initial performance target?
- Which deep-analysis stages run daily versus on a slower cadence?
- What evidence should compose the final Pair Discovery/Relationship Score?
- When should market/sector-neutral analysis be mandatory?
- What benchmark would justify introducing ANN/vector search?

These are architecture/calibration decisions and do not block requirement readiness.

## Risks

- Over-aggressive filtering may discard economically meaningful pairs before deep analysis.
- Weak filtering may preserve too many candidates and fail to reduce compute materially.
- Correlation can change by market regime and may create unstable candidate rankings.
- Multiple-window/multiple-lag searches can create false discoveries if downstream validation is weak.
- Sector classification can miss valid cross-sector supply-chain or macro relationships.
- Incremental optimization can create drift from full recomputation if numerical/state boundaries are not validated.
- A composite Pair Score can become misleading if its components and interpretation are not transparent.
- Future strategy work may overfit candidate-selection thresholds unless OOS governance is preserved.

## Suggested Routing

- Architecture required: Yes
- Primary next owner: SolutionArchitect
- Domain instructions: database.instructions.md; python.instructions.md; testing.instructions.md; archify.instructions.md as applicable
- Validation owner: TestEngineer

## Handoff

```text
Status: READY_FOR_DESIGN
Primary next owner: SolutionArchitect
Acceptance criteria count: 12
Blocking questions: None; listed open questions are design/calibration decisions.
```
