# ZigZag Regime-Aware V2

- **Status:** APPROVED_FOR_IMPLEMENTATION
- **Requirement:** REQ-0030
- **ADR:** ADR-015
- **Prerequisite:** calibrated-static ticker base deviation

## Purpose

Evaluate a point-in-time volatility-regime policy that changes deviation only between
confirmed swings.

## Flow

```text
vw_Ticker_OHLC_D
      |
      +--> regime feature series
      |      TR -> ATR20 -> ATRPct -> trailing percentile
      |
      +--> base deviation from dim_zigzag_ticker_config
      |
      v
calculate_zigzag(deviation_resolver=...)
      |
      v
bootstrap uses base deviation
      |
pivot confirmed
      |
regime at confirmation index
      |
LOW / NORMAL / HIGH
      |
0.8x / 1.0x / 1.3x
      |
clamp 2%..15%
      |
LOCK for next leg
```

## Invariants

- static ZigZag behavior is unchanged when no resolver is supplied;
- regime resolver uses data through the confirmation index only;
- deviation is constant throughout an active leg;
- emitted pivots retain the actual deviation used for confirmation;
- one-pivot-per-trading-date and all ADR-013 semantics remain mandatory.

## Evaluation Persistence

`cal_zigzag_regime_evaluation` stores static-vs-regime summary metrics and regime counts.
Pivot-level evidence is exported to CSV rather than written into production pivot tables.

## Evidence

```text
docs/reference/data/zigzag/regime/
```

## SA Handoff

```text
DESIGN HANDOFF
Requirement: REQ-0030
Outcome: APPROVED_FOR_IMPLEMENTATION
Design: docs/architecture/ZigZag_Regime_Aware.md
ADR: ADR-015
Next owner: GeneralCoding
```
