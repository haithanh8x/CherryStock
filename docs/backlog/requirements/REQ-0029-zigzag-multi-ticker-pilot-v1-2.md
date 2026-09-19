---
id: REQ-0029
title: ZigZag Multi-Ticker Pilot V1.2
status: IMPLEMENTED_PENDING_VALIDATION
priority: P1
owner: BusinessAnalyst
primary_next_owner: TestEngineer
related:
  prerequisite:
    - docs/backlog/requirements/REQ-0028-zigzag-deviation-calibration-v1-1.md
  architecture:
    - docs/architecture/ZigZag_Multi_Ticker_Pilot.md
  adr:
    - docs/adr/ADR-014-zigzag-static-calibration-and-promotion.md
---

# REQ-0029 — ZigZag Multi-Ticker Pilot V1.2

## Business Objective

Verify that ticker-specific calibrated static deviations materially improve swing segmentation
over a fixed 5% baseline before allowing broader production adoption.

## Scope

Manual pilot only. Default pilot universe is configurable; no hard dependency on a particular
ticker list. The workflow compares two modes on the same holdout history:

```text
BASELINE_FIXED_5
CALIBRATED_STATIC
```

## Functional Requirements

1. Read each ticker's V1.1 recommended deviation.
2. Run fixed 5% and calibrated-static ZigZag on the same evaluation window.
3. Compare structural validity, swing count, pivot density, median swing bars,
   median absolute swing %, and short-swing rate.
4. Keep 5% when the calibrated value equals 5% or improvement is not material.
5. Promotion must never depend on trading profit.
6. Persist one deterministic pilot evaluation row per ticker/version.
7. Export pilot evidence under `docs/reference/data/zigzag/pilot/`.
8. A pilot PASS must not automatically add ZigZag to `run.py`.

## Material Improvement Rule

A calibrated deviation is eligible for `PROMOTE_CALIBRATED` only when:

```text
both variants structural valid
AND calibrated short-swing rate <= baseline short-swing rate * 0.80
AND calibrated median swing bars <= baseline median swing bars * 2.0
AND calibrated swing count >= max(5, baseline swing count * 0.50)
```

Otherwise decision is `KEEP_5_BASELINE`. If the calibrated deviation itself equals 5%,
decision is `BASELINE_SUFFICIENT`.

## Acceptance Criteria

- AC-01 both variants run on identical source history.
- AC-02 all compared metrics are persisted.
- AC-03 decision is deterministic.
- AC-04 no variant with structural errors may be promoted.
- AC-05 5% remains fallback/default.
- AC-06 evidence is exported to canonical ChatGPT reference-data path.
- AC-07 pilot can be rerun for 10, 50 or arbitrary ticker lists.
- AC-08 no automatic universe-wide or daily-pipeline promotion occurs.

## BA Handoff

```text
REQUIREMENT HANDOFF
Requirement ID: REQ-0029
Outcome: fixed-5 versus calibrated-static multi-ticker pilot
Status: READY_FOR_DESIGN
Primary next owner: SolutionArchitect.agent.md
Material: docs/backlog/requirements/REQ-0029-zigzag-multi-ticker-pilot-v1-2.md
Open questions: none blocking
Acceptance criteria count: 8
```


## Current Delivery State

Implementation and runbook are present on main.

    IMPLEMENTED_PENDING_VALIDATION

Final PASS/FAIL belongs to TestEngineer after executing the version-specific runbook on local
CherryMon. No production run.py promotion is implied by this state.
