---
id: REQ-0027
title: Price Movement Characterization and Swing Profile
status: READY_FOR_DESIGN
priority: P1
owner: BusinessAnalyst
primary_next_owner: SolutionArchitect
related:
  architecture: docs/architecture/Price_Movement_Character.md
  adr: docs/adr/ADR-012-price-movement-character-as-separate-analytics-domain.md
  implementation:
  test:
  change_request:
---

# REQ-0027 — Price Movement Characterization and Swing Profile

## Business Objective

CherryStock must be able to characterize **how a ticker moves**, not only whether price is currently up or down.

The required outcome is to distinguish at least these business dimensions:

1. **Magnitude** — how large the current/typical move is;
2. **Velocity** — how quickly the move occurs;
3. **Persistence** — how steadily price travels in one direction versus oscillating/noising;
4. **Swing profile** — how large and how long the ticker's historical up/down swings normally are;
5. **Current-relative-to-history context** — whether the current move is ordinary or exceptional for that same ticker.

This capability is intended to support chart interpretation, screening, later Smart Money/strategy features and research without conflating a fast volatile spike with a durable trend.

## Background / Problem

A simple return such as `+30%` does not describe the path taken to achieve the move. Two tickers can have the same return while exhibiting materially different behavior:

- one can rise steadily over many sessions with shallow pullbacks;
- another can jump rapidly with large reversals and high path noise.

Likewise, a fixed market-wide threshold such as `10%` does not mean the same thing for a low-volatility ticker and a naturally volatile ticker.

The requirement therefore needs both **swing/event history** and **trend-quality/path metrics**, with comparison primarily against the ticker's own historical behavior.

## Stakeholders / Consumers

- CherryStock user / analyst;
- Screener and ranking features;
- Chart/UI consumers;
- future SmartMoneyScore / SmartMoneyStrategy research;
- future portfolio/risk analytics;
- TestEngineer for deterministic historical and incremental validation.

## Functional Requirements

1. The system shall identify directional price swings and distinguish **confirmed historical swings** from the **currently developing/provisional swing**.
2. For each confirmed swing, the system shall expose direction, start/end points, percentage magnitude and duration in trading bars; calendar duration may also be exposed for interpretation.
3. The system shall calculate a swing velocity measure so that equal-sized moves occurring over different durations can be distinguished.
4. The system shall provide volatility-relative context so that price movement magnitude can be compared with the ticker's normal price variability.
5. The system shall maintain a historical up-swing and down-swing profile per ticker, including at minimum median and upper-percentile magnitude and duration statistics when sufficient history exists.
6. The system shall compare the current/provisional move with prior **same-direction** confirmed swings of the same ticker and expose its historical percentile/rank where statistically meaningful.
7. The system shall quantify trend persistence/smoothness using path-based evidence so that a steady trend is distinguishable from a noisy move with the same endpoint return.
8. Persistence evidence shall include at minimum directional efficiency, regression/trend fit quality and adverse pullback/excursion; directional-day consistency may be included as supporting evidence.
9. The system shall expose separate `Magnitude`, `Velocity` and `Persistence` measures/scores rather than collapsing them into one opaque score.
10. The system shall derive an explainable movement-character label from direction plus the separate dimensions, including neutral/insufficient-data behavior.
11. The system shall make historical swing details and current movement characterization available through stable consumer read contracts.
12. The system shall support historical backfill and daily incremental refresh with deterministic results for confirmed history.
13. Historical evaluation shall be point-in-time safe: no future-confirmed pivot information may leak into an earlier as-of date.
14. The system shall preserve enough provenance/config identity to reproduce how a swing or movement classification was produced.

## Business Rules

1. **Magnitude is not persistence.** A large move is not automatically a durable trend.
2. **Velocity is not persistence.** A very fast move may be highly volatile/noisy.
3. Historical comparison is primarily ticker-relative and direction-relative; an up swing is compared with prior up swings and a down swing with prior down swings.
4. Confirmed historical swings are immutable for a given algorithm/config version once their reversal confirmation is known; the current swing remains provisional and may move/repaint until confirmed.
5. Provisional swing values must be explicitly marked and must not be represented as confirmed historical facts.
6. Historical profiles and percentiles must use only information that was available as of the relevant date for research/backtest outputs.
7. When history is insufficient, percentile/character outputs must return an explicit insufficient-data state rather than fabricated zero/default meaning.
8. Volatility normalization shall not replace raw percentage magnitude; both absolute and normalized interpretations must remain available.
9. Price-path characterization alone must not assert Smart Money intent, accumulation, distribution or capitulation. Those interpretations belong to downstream models that combine additional evidence.
10. V1 targets adjusted analytical daily price history. Intraday and weekly/monthly swing models are not required for initial delivery.

## Scope

### In Scope

- Daily ticker price movement characterization;
- ZigZag/swing-like directional segmentation with confirmed vs provisional semantics;
- raw swing magnitude and trading-bar duration;
- swing velocity;
- volatility-normalized movement magnitude;
- ticker-specific historical swing distributions/percentiles;
- path efficiency / trend quality / persistence metrics;
- adverse pullback/excursion within a move;
- separate Magnitude, Velocity and Persistence scores;
- explainable movement-character classification;
- historical backfill + daily incremental refresh;
- public read contracts for swing history and current/latest movement profile;
- deterministic, point-in-time-safe validation.

### Out of Scope

- Trade entry/exit recommendations;
- BUY/HOLD/SELL actions;
- direct Smart Money intent inference;
- order-flow/volume-based accumulation-distribution logic;
- portfolio sizing/risk limits;
- intraday swing detection;
- automatic tuning/ML optimization of thresholds in V1;
- changing existing SmartMoneyScore scoring in the same delivery.

## Acceptance Criteria

### AC-01 — Confirmed swing observability

Given sufficient daily price history,
when a directional reversal satisfies the configured confirmation rule,
then a confirmed swing is available with ticker, direction, start/end dates, start/end prices, magnitude percent and trading-bar duration.

### AC-02 — Provisional current swing

Given the latest price has not yet produced a confirmed reversal,
when the current movement is queried,
then the active swing is marked `PROVISIONAL` and is not indistinguishable from confirmed swing history.

### AC-03 — Typical up/down profile

Given a ticker has sufficient confirmed swings,
when its movement profile is queried,
then separate up/down statistics expose at least swing count, median magnitude, P75/P90 magnitude and median/P75 duration.

### AC-04 — Velocity discrimination

Given two swings with similar percentage magnitude but materially different durations,
when velocity is calculated,
then the shorter-duration swing has a greater absolute movement velocity.

### AC-05 — Volatility-relative context

Given two tickers with the same raw percentage move but different normal volatility,
when normalized movement magnitude is evaluated,
then the result can distinguish which move is larger relative to its ticker's normal price variability while preserving the raw percentage move.

### AC-06 — Persistence discrimination

Given two paths with the same start/end return but one moves smoothly and the other oscillates materially,
when persistence is evaluated,
then the smoother path receives materially stronger persistence evidence/score.

### AC-07 — Pullback evidence

Given an upward move with a deep intermediate drawdown and another with a shallow drawdown,
when adverse excursion is measured,
then the deep-pullback move records worse persistence evidence even if final return is equal.

### AC-08 — Ticker-relative percentile

Given sufficient same-direction confirmed history,
when the current move is compared with history,
then the system exposes its magnitude/velocity percentile relative to prior same-direction swings of that ticker.

### AC-09 — No look-ahead leakage

Given a historical as-of date before a future reversal confirmation,
when the feature set is reconstructed for that date,
then future pivot confirmation and future swing endpoints do not appear in the as-of result.

### AC-10 — Explainable character label

Given valid Magnitude, Velocity and Persistence dimensions,
when a movement-character label is produced,
then the label can be traced to direction plus those component dimensions and is not based on an undocumented opaque score.

### AC-11 — Insufficient history

Given a ticker does not have the configured minimum historical sample,
when historical percentile/profile output is requested,
then the result explicitly reports insufficient history and does not silently substitute zero-percentile semantics.

### AC-12 — Historical vs incremental equivalence

Given the same configuration and source data,
when a date range is produced once by full historical calculation and once by valid incremental refresh,
then confirmed swing history and finalized daily movement outputs are equivalent for the overlapping finalized period.

### AC-13 — Reproducibility

Given a movement result,
when its provenance is inspected,
then the algorithm/config version and relevant threshold/window identity required to reproduce the result are available.

### AC-14 — Stable consumer access

Given successful calculation and validation,
when Chart/Screener/analytics consumers request movement data,
then they can use documented public read contracts without coupling to internal calculation persistence.

## Non-functional Requirements

- **Performance:** Daily incremental calculation must operate on bounded warmup/checkpoint history where algorithmically valid; full history is reserved for initload/backfill/rebuild paths.
- **Reliability:** Confirmed swing history must be deterministic and idempotent for unchanged source data + config version.
- **Security:** No new credential, external-service or privileged-write requirement is introduced by this analytical component.
- **Observability:** Refresh must expose processed ticker/date range, row/event counts, insufficient-history counts and validation outcome.
- **Compatibility:** Existing Indicator, SmartMoney, chart and R/S public contracts must remain backward compatible in V1.

## Dependencies

- Adjusted daily ticker OHLC history;
- trading calendar / ordered trading sessions;
- volatility evidence such as ATR through an approved public analytical contract or equivalent approved design;
- CherryStock DuckDB calculated-data conventions;
- daily orchestration and Data Quality conventions;
- architecture/design review by SolutionArchitect.

## Constraints

- Must comply with CherryStock database naming, transaction, public-view and validation rules.
- Must not use future information to finalize historical pivots/features before confirmation time.
- Must not treat provisional ZigZag endpoints as immutable facts.
- Must avoid a fixed market-wide percentage threshold as the sole definition of a strong move.

## Assumptions

- Adjusted EOD OHLC is appropriate for analytical price-path comparison across corporate actions.
- Daily timeframe is the first production scope.
- Sufficient ticker history exists for most actively tracked tickers, but insufficient-history handling is mandatory.

## Open Questions

No blocking business questions. Thresholds, exact scoring weights, persistence windows, physical data model and orchestration placement are Solution Architect responsibilities subject to deterministic validation and versioned configuration.

## Risks

- ZigZag confirmation naturally introduces lag; consumers may misread provisional endpoints unless status is explicit.
- Small historical swing samples can produce unstable percentiles.
- Corporate-action-adjusted historical OHLC can change after upstream restatement, requiring deterministic rebuild behavior.
- Overly aggressive composite scoring can hide useful differences between magnitude, velocity and persistence.
- A movement-character label may be over-interpreted as a trading signal if naming/documentation is not disciplined.

## Suggested Routing

- Architecture required: Yes
- Primary next owner: `SolutionArchitect.agent.md`
- Domain instructions: `.github/instructions/database.instructions.md`, `.github/instructions/indicators.instructions.md` when consuming ATR via Indicator public contracts, `.github/instructions/testing.instructions.md`
- Validation owner: `TestEngineer.agent.md`

## Handoff

```text
REQUIREMENT HANDOFF
Requirement ID: REQ-0027
Outcome: Price Movement Characterization and Swing Profile
Status: READY_FOR_DESIGN
Primary next owner: SolutionArchitect.agent.md
Material: docs/backlog/requirements/REQ-0027-price-movement-characterization.md
Open questions: None blocking; algorithm/config/data-model choices delegated to SA
Acceptance criteria count: 14
```
