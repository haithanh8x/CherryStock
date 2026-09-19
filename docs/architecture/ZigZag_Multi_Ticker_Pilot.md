# ZigZag Multi-Ticker Pilot V1.2

- **Status:** APPROVED_FOR_IMPLEMENTATION
- **Requirement:** REQ-0029
- **ADR:** ADR-014
- **Prerequisite:** V1.1 calibration results

## Purpose

Compare calibrated-static ZigZag against the fixed 5% baseline across a configurable
multi-ticker pilot.

## Flow

```text
dim_zigzag_ticker_config
          |
          v
pilot ticker list
          |
          +----------------------+
          |                      |
          v                      v
fixed 5% ZigZag          calibrated static ZigZag
          |                      |
          +----------+-----------+
                     v
                metric compare
                     |
                     v
          cal_zigzag_pilot_evaluation
                     |
                     v
KEEP_5_BASELINE / BASELINE_SUFFICIENT /
PROMOTE_CALIBRATED
```

## Comparison Contract

Both variants must use identical ticker history and metric definitions.

Promotion requires the material-improvement rules in REQ-0029. A calibrated candidate with
structural errors can never be promoted.

## Pilot Scaling

The same script supports arbitrary ticker lists. Recommended rollout:

```text
10 tickers -> 50 tickers -> active universe
```

Each expansion is a TestEngineer gate, not an automatic side effect.

## Persistence

`cal_zigzag_pilot_evaluation` stores one deterministic comparison row per
PilotVersion + Ticker.

## Evidence

```text
docs/reference/data/zigzag/pilot/
```

## SA Handoff

```text
DESIGN HANDOFF
Requirement: REQ-0029
Outcome: APPROVED_FOR_IMPLEMENTATION
Design: docs/architecture/ZigZag_Multi_Ticker_Pilot.md
ADR: ADR-014
Next owner: GeneralCoding
```
