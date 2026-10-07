---
id: REQ-0037
title: R/S-based Averaging Down Strategy and Position Sizing
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

# REQ-0037 — R/S-based Averaging Down Strategy and Position Sizing

## Business Objective

Enable CherryStock to evaluate and support a disciplined averaging-down strategy in which investment capital is divided into multiple tranches and additional capital is deployed only when price reaches qualified support conditions and the original trade thesis remains valid.

The capability shall combine CherryStock R/S evidence with position sizing, risk limits and historical validation so averaging down is treated as a governed trading strategy rather than an unconditional rule to buy more whenever price falls.

## Background / Problem

A simple averaging-down approach can reduce average cost when price declines, but it can also concentrate capital into a deteriorating position. Fixed rules such as buying every -5%, -10% or -15% do not distinguish between a normal pullback into strong support and a structural breakdown.

CherryStock already has an R/S analytical workstream capable of identifying support/resistance levels and strength evidence. A strategy layer can use qualified support zones as potential staged-entry references while preserving an explicit invalidation boundary and total-position risk limit.

This requirement defines WHAT the strategy capability must achieve. Exact tranche formulas, score thresholds, sizing algorithms, optimization methods, persistence schemas and implementation topology belong to Solution Architecture and later calibration/backtest work.

## Stakeholders / Consumers

- CherryStock owner/operator.
- Trading-strategy research workflows.
- R/S analytical workflows.
- Position/risk-management workflows.
- Backtest and strategy-comparison consumers.
- Future trading UI and decision-support surfaces.

## Functional Requirements

1. CherryStock shall support a staged-entry / averaging-down strategy that divides a configurable maximum position budget into multiple tranches.
2. Additional tranches shall not be triggered solely because price has fallen by a fixed percentage.
3. The strategy shall support qualified Support levels/zones from the CherryStock R/S domain as candidate add-entry locations.
4. Each add-entry decision shall require the position/trade thesis to remain valid according to approved strategy conditions.
5. The strategy shall define an explicit invalidation/stop condition after which no additional averaging-down tranche may be opened.
6. The strategy shall enforce a maximum total capital allocation or position-risk limit for each ticker/position.
7. The strategy shall support non-equal tranche sizing, including the ability for later qualified entries to receive different capital weights than the initial entry.
8. The strategy shall calculate and expose the resulting weighted average entry price after each executed/simulated tranche.
9. The strategy shall expose remaining deployable capital and the number/status of unused tranches.
10. Candidate add-entry decisions shall preserve the R/S evidence used at decision time, including the relevant support identity/zone and available strength evidence.
11. The strategy shall distinguish between a qualified support test and a structural breakdown/invalidation event.
12. The strategy shall support configurable rules for whether a previously used support zone may be reused for another tranche.
13. The strategy shall support historical simulation/backtesting across multiple tranche-allocation and entry-policy configurations.
14. Backtesting shall compare the averaging-down strategy against appropriate baselines, including at minimum a non-averaging/single-entry alternative.
15. Backtest results shall expose return and risk outcomes rather than evaluating configurations only by final profit.
16. Historical evaluation shall use only R/S and market information available at each simulated decision timestamp.
17. The capability shall support analysis of how results vary by market regime, ticker characteristics and/or support-quality bands where sufficient data exists.
18. The strategy shall remain decision support/research until approved validation and production-activation gates are satisfied.

## Business Rules

1. Averaging down is conditional capital deployment, not an obligation to buy every decline.
2. A falling price alone is insufficient evidence for an additional tranche.
3. No new tranche may be added after the approved thesis-invalidation condition is met.
4. Total committed capital/risk must never exceed the configured position limit.
5. R/S strength is evidence for decision-making, not a guarantee that support will hold.
6. Tranche sizing and support qualification thresholds must be configurable/design-governed rather than embedded as permanent business truth.
7. Backtest optimization must not select a configuration solely from in-sample profitability.
8. Strategy evaluation must account for trading costs/slippage assumptions appropriate to the tested market.
9. Historical R/S evidence must be point-in-time correct; future recalculated strength or future support knowledge must not leak into past decisions.
10. A strategy configuration that improves average entry price but materially worsens drawdown, tail loss or capital concentration shall not automatically be considered superior.
11. Production activation requires independent validation and must not be implied by successful implementation alone.

## Scope

### In Scope

- Multi-tranche position budget.
- R/S-based candidate add-entry conditions.
- Conditional thesis-validity checks.
- Explicit invalidation/no-more-buy boundary.
- Maximum capital and position-risk constraints.
- Weighted average entry-price calculation.
- Remaining-capital/tranche state.
- Configurable tranche-allocation policies.
- Backtesting of staged-entry configurations.
- Comparison with non-averaging baseline.
- Return, drawdown and risk-oriented evaluation.
- Point-in-time R/S evidence integrity.
- Analysis by support quality and market context where practical.

### Out of Scope

- Automatic live order execution.
- Guaranteed-loss-recovery or guaranteed-profit behavior.
- Unlimited averaging down.
- Buying solely at fixed percentage declines without supporting strategy evidence.
- Prescribing the exact tranche percentages or exact R/S threshold in this requirement.
- Prescribing database schema, module/class layout, optimizer, backtest engine implementation or UI design before architecture approval.
- Changing the canonical R/S scoring methodology as part of this requirement.
- Production activation without independent strategy validation.

## Acceptance Criteria

### AC-01 — Multi-tranche budget

Given a configured maximum position budget,
When the strategy initializes a position,
Then it can represent multiple planned tranches whose maximum combined allocation does not exceed that budget.

### AC-02 — R/S-qualified add entry

Given an open position and unused capital,
When price declines,
Then an additional tranche is not generated solely from the decline percentage and requires an approved qualified support/thesis condition.

### AC-03 — Invalidation stops averaging

Given a position whose approved invalidation condition has been reached,
When the strategy evaluates another add entry,
Then no additional averaging-down tranche is permitted.

### AC-04 — Capital/risk ceiling

Given any sequence of qualified entries,
When a new tranche is evaluated,
Then the resulting total allocation/risk cannot exceed the configured position limit.

### AC-05 — Average price transparency

Given two or more executed/simulated tranches,
When position state is inspected,
Then CherryStock exposes each tranche and the resulting weighted average entry price.

### AC-06 — R/S evidence traceability

Given an averaging-down tranche is triggered,
When the historical decision is inspected,
Then the support/zone and relevant R/S evidence available at that decision timestamp can be identified.

### AC-07 — Breakdown distinction

Given price approaches or passes a support area,
When the strategy evaluates the event,
Then it can distinguish an approved support-entry condition from an invalidation/breakdown condition according to the designed policy.

### AC-08 — Configurable allocation

Given multiple valid strategy configurations,
When backtesting is performed,
Then tranche allocation is configurable and is not restricted to equal-sized capital slices.

### AC-09 — Baseline comparison

Given a historical test sample,
When an averaging-down configuration is evaluated,
Then its results can be compared with a defined non-averaging/single-entry baseline over equivalent data boundaries.

### AC-10 — Risk-aware evaluation

Given completed strategy backtests,
When results are reviewed,
Then they include both return and risk evidence sufficient to compare capital efficiency and downside behavior rather than profit alone.

### AC-11 — Point-in-time integrity

Given a historical decision timestamp,
When the strategy is replayed,
Then only R/S, price and contextual evidence available at or before that timestamp is used.

### AC-12 — Trading-cost inclusion

Given a multi-tranche backtest,
When performance is calculated,
Then approved transaction-cost/slippage assumptions are applied consistently to the strategy and comparison baseline.

### AC-13 — No automatic production claim

Given a configuration performs well in historical testing,
When the result is presented,
Then it remains a research/validation result until the independent production-activation criteria are satisfied.

## Non-functional Requirements

- Explainability: Every add/no-add/invalidation decision must be attributable to observable strategy and R/S evidence.
- Reproducibility: Strategy configuration, data boundary and relevant R/S version/evidence must be recoverable for a historical run.
- Risk safety: The strategy must enforce bounded capital exposure and prevent further averaging after invalidation.
- Performance: Backtest design should permit practical comparison of multiple configurations without requiring unnecessary recomputation of unchanged market/R/S history.
- Compatibility: The capability shall consume existing CherryStock R/S outputs without redefining R/S Source of Truth.
- Observability: Backtests shall expose tranche usage, entry locations, average-cost evolution and relevant return/risk metrics.

## Dependencies

- Existing CherryStock R/S level/zone and strength evidence.
- Point-in-time historical R/S data suitable for leakage-safe backtesting.
- Canonical adjusted price history and trading-calendar boundaries.
- Existing/future strategy backtest framework.
- Position/risk-management contract.
- Transaction-cost/slippage assumptions for strategy evaluation.
- Solution Architecture definition for strategy state, entry/invalidation contracts and backtest integration.
- Independent TestEngineer/OOS validation before production activation.

## Constraints

- GitHub repository remains the CherryStock engineering Single Source of Truth.
- This requirement shall not prescribe exact tranche percentages, exact R/S score thresholds, persistence schema or implementation topology before architecture approval.
- Averaging down must remain bounded by explicit capital/risk limits.
- No averaging is allowed after the approved invalidation condition.
- Historical testing must prevent look-ahead leakage from future R/S recalculation or future market data.
- Optimization must preserve out-of-sample governance and avoid selecting parameters solely from in-sample maximum return.

## Assumptions

- CherryStock R/S can provide support/zone evidence usable by downstream strategy logic.
- Multiple staged entries can be represented in the future strategy/position model.
- Daily/EOD data is sufficient for an initial research version unless architecture determines intraday confirmation is required.
- The first version is intended for research and decision support rather than automated execution.

## Open Questions

- Which R/S evidence should qualify a support zone for an add entry?
- Should the current production visibility threshold be reused, or should averaging-down qualification have an independently calibrated threshold?
- How many tranches should the initial strategy support?
- Which allocation families should be tested: equal, increasing, decreasing or risk-normalized?
- Should tranche size depend on support strength, distance, volatility or remaining risk budget?
- What exactly constitutes thesis invalidation for the initial strategy?
- Should an add entry require support confirmation/reversal evidence rather than price merely entering the zone?
- Which benchmark strategies and risk metrics form the production-promotion gate?
- Which market regimes/ticker groups require separate calibration?
- What OOS/walk-forward evidence is required before the strategy can influence production trade actions?

These are architecture/calibration decisions and do not block requirement readiness.

## Risks

- Averaging down can amplify losses when the underlying thesis is wrong or the market enters a persistent downtrend.
- Backtests can overstate performance if historical R/S levels are reconstructed with future information.
- Increasing tranche sizes at lower prices can create concentrated tail risk.
- Excessive parameter search can overfit tranche counts, support thresholds and allocation ratios.
- Strong historical support scores may behave differently across market regimes.
- Transaction costs and repeated entries may materially reduce apparent improvements from lower average cost.
- A strategy optimized for win rate may hide worse drawdown or loss severity.
- Tight invalidation may prevent useful staged entries, while loose invalidation may permit destructive averaging.

## Suggested Routing

- Architecture required: Yes
- Primary next owner: SolutionArchitect
- Domain instructions: trading/backtest, R/S, database, python, testing and archify instructions as applicable
- Validation owner: TestEngineer

## Handoff

```text
Status: READY_FOR_DESIGN
Primary next owner: SolutionArchitect
Acceptance criteria count: 13
Blocking questions: None; listed open questions are design/calibration decisions.
```
