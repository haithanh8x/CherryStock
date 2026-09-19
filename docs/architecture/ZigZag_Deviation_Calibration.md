# ZigZag Deviation Calibration V1.1

- **Status:** APPROVED_FOR_IMPLEMENTATION
- **Requirement:** REQ-0028
- **ADR:** ADR-014
- **Foundation:** docs/architecture/ZigZag_Engine.md

## Purpose

Calibrate a static per-ticker ZigZag deviation using structural swing quality rather than
trading profit.

## Flow

```text
vw_Ticker_OHLC_D
      |
      v
chronological split
TRAIN 60 / VALIDATION 20 / TEST 20
      |
      v
candidate grid
2 3 4 5 6 7 8 10 12 %
      |
      v
canonical calculate_zigzag()
      |
      v
SwingMetrics
      |
      +--> cal_zigzag_deviation_evaluation
      |
      v
TRAIN + VALIDATION selector
      |
      v
dim_zigzag_ticker_config
      |
      v
TEST holdout evidence
```

## Metrics

For each ticker / split / deviation:

- source bars;
- confirmed pivots;
- swing count;
- pivot density per 100 bars;
- median swing bars;
- median absolute swing percentage;
- short swing rate for swings shorter than 3 bars;
- structural-valid flag;
- deterministic calibration score;
- eligibility flag.

## Selection

Eligibility is defined by REQ-0028. Among candidates eligible in both TRAIN and VALIDATION,
choose the smallest deviation. If none is eligible, choose the highest deterministic average
TRAIN+VALIDATION score and mark `FALLBACK_SCORE`.

TEST never participates in selection.

## Data Model

### cal_zigzag_deviation_evaluation

Grain:

```text
CalibrationVersion + Ticker + SplitName + DeviationPct
```

### dim_zigzag_ticker_config

Grain:

```text
CalibrationVersion + Ticker + Timeframe
```

Stores selected static `BaseDeviationPct`, method and status.

## Operational Boundary

Manual script only. No writes to canonical pivot/current tables and no `run.py` integration.

## Evidence

Exports go to:

```text
docs/reference/data/zigzag/calibration/
```

## SA Handoff

```text
DESIGN HANDOFF
Requirement: REQ-0028
Outcome: APPROVED_FOR_IMPLEMENTATION
Design: docs/architecture/ZigZag_Deviation_Calibration.md
ADR: ADR-014
Next owner: GeneralCoding
```
