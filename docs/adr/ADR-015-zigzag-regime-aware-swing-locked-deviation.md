# ADR-015 — ZigZag Regime-Aware Swing-Locked Deviation

- **Status:** Accepted for manual V2 evaluation
- **Date:** 2026-09-19
- **Requirement:** REQ-0030
- **Prerequisite:** ADR-014 calibrated-static baseline

## Context

A single static deviation can become too sensitive in high-volatility periods and too coarse
in low-volatility periods. Recomputing an ATR-derived threshold every bar would make the
meaning of an active ZigZag leg unstable and harder to audit.

## Decision

V2 may adapt deviation by volatility regime, but the selected deviation is **locked for the
entire active swing**.

```text
pivot confirmed
  -> calculate regime using only data known at confirmation
  -> choose multiplier
  -> clamp deviation
  -> lock for next leg
  -> next pivot confirmed
  -> repeat
```

The first bootstrap leg uses the ticker's static base deviation.

Default point-in-time regime model:

```text
TR        = max(High-Low, abs(High-prevClose), abs(Low-prevClose))
ATR20     = rolling mean(TR, 20)
ATRPct    = ATR20 / Close
Percentile= percentile rank of current ATRPct in trailing 252 known observations

LOW_VOL   < 0.30 -> 0.80 x BaseDeviation
NORMAL    0.30..0.70 -> 1.00 x BaseDeviation
HIGH_VOL  > 0.70 -> 1.30 x BaseDeviation
Clamp     0.02 .. 0.15
```

## Point-in-time rule

Regime calculation at confirmation index `i` may use rows `<= i` only.
No future ATR or future percentile data may affect the next leg.

## Compatibility

The canonical static call to `calculate_zigzag(...)` remains unchanged in behavior.
Regime mode is activated only when an explicit deviation resolver is supplied.

Each emitted pivot records the actual deviation used to confirm it.

## Scope

V2 is manual/research first and remains outside `run.py`.
Promotion to production requires separate TestEngineer evidence and a later explicit decision.
