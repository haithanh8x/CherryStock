---
id: REQ-0028
title: ZigZag Deviation Calibration V1.1
status: READY_FOR_DESIGN
priority: P1
owner: BusinessAnalyst
primary_next_owner: SolutionArchitect
related:
  prerequisite:
    - docs/backlog/requirements/REQ-0027-price-movement-characterization.md
  architecture:
    - docs/architecture/ZigZag_Deviation_Calibration.md
  adr:
    - docs/adr/ADR-014-zigzag-static-calibration-and-promotion.md
---

# REQ-0028 — ZigZag Deviation Calibration V1.1

## Business Objective

Determine a reproducible ticker-specific static `DeviationPct` for ZigZag without optimizing
for trading profit. The selected value must describe price-swing structure with less noise while
preserving meaningful swings and point-in-time correctness.

## Scope

V1.1 is a manual research/calibration workflow. It does not change `run.py`, does not replace
`ZZ_D_5_MVP`, and does not enable universe-wide ZigZag persistence.

Candidate grid:

```text
2%, 3%, 4%, 5%, 6%, 7%, 8%, 10%, 12%
```

Historical evaluation uses chronological TRAIN / VALIDATION / TEST splits with default
60% / 20% / 20%.

## Functional Requirements

1. Load adjusted daily OHLC from `vw_Ticker_OHLC_D`.
2. Evaluate every configured candidate deviation with the canonical ZigZag engine.
3. Measure structural validity, swing count, pivot density, median swing bars, median absolute
   swing %, and short-swing rate.
4. Selection uses TRAIN + VALIDATION only. TEST is holdout evidence and must not change the
   chosen deviation.
5. Prefer the smallest eligible deviation to avoid oversmoothing.
6. If no candidate satisfies eligibility, select the highest deterministic calibration score and
   mark the recommendation `FALLBACK_SCORE`.
7. Persist evaluation results and ticker recommendation separately from runtime pivots.
8. Export ChatGPT-readable evidence under `docs/reference/data/zigzag/calibration/`.
9. Rerun with unchanged data/config must be deterministic.
10. No profit, BUY/SELL return or future-price objective may be used in calibration.

## Eligibility Rules

Default candidate eligibility on TRAIN and VALIDATION:

```text
StructuralValid      = TRUE
SwingCount           >= 5
MedianSwingBars      >= 5
ShortSwingRate(<3)   <= 10%
MedianAbsSwingPct    >= 1.5 * DeviationPct
```

If multiple candidates are eligible, choose the smallest deviation whose VALIDATION metrics
also satisfy the rules.

## Acceptance Criteria

- AC-01 all grid deviations are evaluated for each requested ticker.
- AC-02 all structural errors are zero for an eligible candidate.
- AC-03 selection is based only on TRAIN + VALIDATION.
- AC-04 TEST metrics are produced separately after selection.
- AC-05 selected deviation is deterministic for unchanged source/config.
- AC-06 5% remains available as baseline even when not selected.
- AC-07 no trading-return metric participates in selection.
- AC-08 recommendation and evaluation rows are idempotently replaceable.
- AC-09 ChatGPT evidence is exported to the canonical reference-data path.
- AC-10 V1.1 does not mutate canonical daily ZigZag runtime integration.

## Non-functional Requirements

- Calculation must be bounded by ticker x candidate-grid x chronological splits.
- No query-per-bar database access.
- All calculations must be point-in-time safe.
- Research persistence must be separate from `cal_zigzag_pivot`.

## BA Handoff

```text
REQUIREMENT HANDOFF
Requirement ID: REQ-0028
Outcome: ticker-specific static ZigZag deviation calibration
Status: READY_FOR_DESIGN
Primary next owner: SolutionArchitect.agent.md
Material: docs/backlog/requirements/REQ-0028-zigzag-deviation-calibration-v1-1.md
Open questions: none blocking
Acceptance criteria count: 10
```
