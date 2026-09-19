# ADR-014 — ZigZag Static Calibration and Promotion

- **Status:** Accepted
- **Date:** 2026-09-19
- **Requirements:** REQ-0028, REQ-0029
- **Foundation:** ADR-013 / ZigZag Swing Engine

## Context

A fixed 5% ZigZag is validated for MWG, but different tickers have materially different
volatility and noise profiles. CherryStock needs a reproducible way to recommend a static
per-ticker deviation without optimizing trading returns or changing the threshold inside a leg.

## Decision

CherryStock will add a two-stage static calibration lifecycle:

```text
V1.1 CALIBRATION
candidate grid -> TRAIN/VALIDATION selection -> TEST holdout evidence
        |
        v
ticker static recommendation
        |
        v
V1.2 PILOT
fixed 5% vs calibrated-static
        |
        v
KEEP_5_BASELINE | BASELINE_SUFFICIENT | PROMOTE_CALIBRATED
```

The default candidate grid is 2/3/4/5/6/7/8/10/12 percent.

Selection must use structural/swing-shape metrics only. Trading profit, future strategy return,
BUY/SELL success or other outcome leakage is prohibited.

The calibrated value is static for a ticker/config version. V1.1/V1.2 do not alter it per bar
or per swing.

## Persistence

Research/evaluation state is separated from production pivot persistence:

- `cal_zigzag_deviation_evaluation`
- `dim_zigzag_ticker_config`
- `cal_zigzag_pilot_evaluation`

The canonical runtime tables `cal_zigzag_pivot` and `cal_zigzag_current_leg` are not
repurposed as calibration stores.

## Promotion Policy

V1.1 recommendation alone does not authorize runtime promotion.

V1.2 compares calibrated-static against the fixed 5% baseline on identical history.
A calibrated value is promoted only when the documented material-improvement rule is met.
Otherwise 5% remains the baseline.

## Consequences

Positive:
- ticker-specific sensitivity is evidence-backed;
- 5% remains a stable benchmark;
- calibration is auditable and reproducible;
- no intraleg threshold drift.

Trade-offs:
- calibration adds batch research cost;
- some tickers may remain at 5%;
- candidate-grid choices remain versioned research assumptions.

## Rollout

No daily `run.py` integration is authorized by this ADR.
