---
id: REQ-0030
title: ZigZag Regime-Aware Swing-Locked Deviation V2
status: IMPLEMENTED_PENDING_VALIDATION
priority: P1
owner: BusinessAnalyst
primary_next_owner: TestEngineer
related:
  prerequisite:
    - docs/backlog/requirements/REQ-0029-zigzag-multi-ticker-pilot-v1-2.md
  architecture:
    - docs/architecture/ZigZag_Regime_Aware.md
  adr:
    - docs/adr/ADR-015-zigzag-regime-aware-swing-locked-deviation.md
---

# REQ-0030 — ZigZag Regime-Aware Swing-Locked Deviation V2

## Business Objective

Allow ZigZag sensitivity to adapt to a ticker's volatility regime without changing the
threshold inside an active swing and without introducing look-ahead behavior.

## Scope

V2 is a manual evaluation workflow first. It uses each ticker's V1.1/V1.2 static base
deviation and adjusts it only when a confirmed pivot establishes the start of the next leg.

Default regime signal:

```text
TrueRange
ATR20 = rolling mean(TrueRange, 20)
ATRPct = ATR20 / Close
ATRPct percentile over trailing 252 observations
```

Default regime mapping:

```text
LOW_VOL    percentile < 30%   multiplier 0.80
NORMAL     30%..70%           multiplier 1.00
HIGH_VOL   > 70%              multiplier 1.30
```

Final deviation is clamped to 2%..15%.

## Functional Requirements

1. Regime statistics use only observations available at the pivot confirmation date.
2. The first bootstrap pivot uses the base deviation.
3. After a pivot is confirmed, determine the next leg's regime and lock its deviation.
4. Locked deviation may not change until the next pivot confirmation.
5. Every confirmed pivot must retain the actual deviation used to confirm it.
6. Compare regime-locked output with the ticker's calibrated-static baseline.
7. Export pivot-level and summary evidence under `docs/reference/data/zigzag/regime/`.
8. V2 remains outside `run.py` until independently validated.

## Acceptance Criteria

- AC-01 no future ATR/percentile observations participate in a regime decision.
- AC-02 deviation does not change inside a leg.
- AC-03 LOW/NORMAL/HIGH mapping is deterministic.
- AC-04 every pivot records the threshold used.
- AC-05 static mode remains behaviorally backward compatible.
- AC-06 regime workflow is deterministic/idempotent for unchanged input.
- AC-07 evidence includes regime counts and pivot-level thresholds.
- AC-08 no automatic production promotion occurs.

## BA Handoff

```text
REQUIREMENT HANDOFF
Requirement ID: REQ-0030
Outcome: point-in-time regime-aware swing-locked ZigZag deviation
Status: READY_FOR_DESIGN
Primary next owner: SolutionArchitect.agent.md
Material: docs/backlog/requirements/REQ-0030-zigzag-regime-aware-v2.md
Open questions: none blocking
Acceptance criteria count: 8
```


## Current Delivery State

Implementation and runbook are present on main.

    IMPLEMENTED_PENDING_VALIDATION

Final PASS/FAIL belongs to TestEngineer after executing the version-specific runbook on local
CherryMon. No production run.py promotion is implied by this state.
