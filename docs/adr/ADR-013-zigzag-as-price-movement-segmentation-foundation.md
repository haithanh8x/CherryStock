# ADR-013 — ZigZag as the Price Movement Segmentation Foundation

- **Status:** Accepted for MWG MVP implementation
- **Date:** 2026-09-19
- **Requirement:** REQ-0027
- **Supersedes for segmentation:** ATR-adaptive reversal choice previously described in Price Movement V1
- **Keeps:** ADR-012 domain-boundary decision

## Context

The first Price Movement implementation used an ATR-adaptive reversal threshold and mixed
segmentation with expensive per-bar path analytics. MWG validation exposed a correctness
problem: an UP leg could start from a point inside an existing decline rather than from the
actual trough. Full-universe profiling also showed that per-bar feature recomputation was too
expensive for the daily pipeline.

The system therefore needs a simpler and more inspectable foundation whose only responsibility
is to identify confirmed price pivots and the active provisional leg.

## Decision

CherryStock will use a **percentage-reversal ZigZag state machine** as the segmentation
foundation for REQ-0027.

For the first MVP:

- source = adjusted daily OHLC from vw_Ticker_OHLC_D;
- candidate peak = daily High;
- candidate trough = daily Low;
- reversal confirmation = daily Close;
- DeviationPct = 5%;
- MinimumSwingBars = 1;
- scope = MWG only;
- execution = manual initload/validation only;
- no ATR dependency;
- no integration into run.py;
- no SmartMoney dependency;
- no movement-score calculation.

The configured 5% value is an evaluation parameter, not a permanent universal threshold.

## Pivot Semantics

A pivot has two dates:

    PivotDate
    ConfirmedAtDate

PivotDate is the date on which the actual High/Low extreme occurred.

ConfirmedAtDate is the later date on which the Close has reversed by at least DeviationPct
from that candidate extreme.

This distinction is mandatory for point-in-time safety. For the daily MVP, every confirmed
pivot must satisfy:

    PivotDate < ConfirmedAtDate

## State Machine

### Bootstrap

Before the first pivot is confirmed, the engine tracks:

- the lowest Low and the best High reached after that low;
- the highest High and the best Low reached after that high.

It tests both possible first reversal directions.

If both directions satisfy the deviation on the same daily bar, the engine resolves the
ambiguity deterministically:

1. choose the side with the larger excursion beyond DeviationPct;
2. if tied, choose the earlier candidate pivot date;
3. if still tied, choose LOW.

This rule handles bootstrap ambiguity without inventing intraday information.

### Daily-bar whipsaw policy

Daily OHLC does not reveal whether High occurred before Low on the same trading day.
Therefore the MVP adopts **one confirmed pivot per trading date**.

Consequences:

- consecutive PivotDates must be strictly increasing;
- a next-leg candidate must come from a bar strictly after the previous PivotDate;
- a candidate updated on the current bar cannot be confirmed on that same bar;
- post-hoc deduplication of emitted pivots is prohibited because it can break alternation
  and local-extreme semantics;
- the local-extreme validator excludes the two neighboring pivot bars and evaluates the
  current interior pivot only on bars strictly between adjacent PivotDates.

This is a daily-resolution policy, not an assertion about the true intraday order.

### UP state

After a confirmed LOW:

- track the highest High as candidate HIGH;
- when Close falls at least DeviationPct from that candidate HIGH, confirm the HIGH pivot;
- transition to DOWN;
- carry forward the lowest Low observed since the candidate HIGH as the next provisional
  candidate LOW.

### DOWN state

After a confirmed HIGH:

- track the lowest Low as candidate LOW;
- when Close rises at least DeviationPct from that candidate LOW, confirm the LOW pivot;
- transition to UP;
- carry forward the highest High observed since the candidate LOW as the next provisional
  candidate HIGH.

## Persistence Decision

The MVP is **event-first**.

Persist:

1. dim_zigzag_config
2. cal_zigzag_pivot
3. cal_zigzag_current_leg

Expose:

1. vw_Ticker_ZigZag_Pivots
2. vw_Ticker_ZigZag_Swings
3. vw_Ticker_ZigZag_Current

Do not persist one historical current-state row per trading day.

The derived swing contract is built from adjacent confirmed pivots:

    LOW  → HIGH = UP
    HIGH → LOW  = DOWN

## Performance Decision

The state machine must be O(n) over ordered bars.

The inner loop must not:

- slice/copy an expanding DataFrame;
- refit a regression per bar;
- rebuild historical percentile arrays per bar;
- rescan the full active leg.

Higher-level movement features are deferred until pivot correctness is accepted.

## Rollout Decision

Only MWG is enabled in the first initload.

Expansion is blocked until:

- structural pivot validation has zero errors;
- repeated initload is idempotent;
- MWG Jul–Sep 2026 pivots are visually reviewed;
- the user explicitly accepts the 5% behavior or selects a revised config.

Only then may the design move to a multi-ticker pilot.

## Consequences

### Positive

- pivot location is based on actual tracked extremes;
- confirmation lag is explicit;
- no ATR/Indicator dependency for segmentation;
- event storage is much smaller than daily historical movement state;
- algorithm complexity is linear;
- ZigZag pivots become reusable by chart/pattern/future movement analytics.

### Negative / Trade-offs

- fixed-percentage deviation may behave differently across volatility regimes;
- provisional endpoint repainting remains inherent to ZigZag;
- daily bars cannot establish intraday ordering when both extremes occur in one bar;
- a separate validation/calibration step is required before universe-wide rollout.

## Relationship to ADR-012

ADR-012 remains valid for the broader conclusion that movement/swing analytics are a separate
stateful analytical domain rather than ordinary long-format indicator values.

ADR-013 replaces only the earlier ATR-adaptive segmentation choice and introduces ZigZag as
the foundational component.

## Validation

Required evidence:

- tests/test_zigzag_engine.py;
- scripts/initload/init_reload_zigzag_mwg.py;
- scripts/validate_zigzag_mwg.py;
- manual visual review of MWG Jul–Sep 2026.
