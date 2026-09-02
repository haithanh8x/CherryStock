# CR_RS_V2_4_BB_Negative_Lower_Handling

## 1. Change Summary

- **Change ID:** CR-RS-V2.4-BB-NEGATIVE-20260902
- **Release / Change:** BB Negative LOWER Handling
- **Date:** 2026-09-02
- **Type:** Calculation Engine / Bug Fix
- **Status:** IN PROGRESS
- **Parent release:** R/S Ladder V2.4
- **Affected provider:** Bollinger Bands LEVEL provider
- **Production file:** `src/calcEngine/levelLadder.py`
- **Validation runbook:** `tests/test_R_S_V2_4_BB_Negative_Lower.md`
- **Bug branch:** `fix/rs-v2-4-bb-negative-lower`
- **Pull Request:** PR #13 (stacked on warm-up fix branch until validation completes)

## 2. Problem

Historical monthly evaluation progressed past the Volume Profile warm-up defect and exposed an independent BB provider failure:

```text
ValueError: Invalid BB value for ConfigId=2: -0.41172686931244584
```

Observed affected tickers include:

```text
CTP
GEE
L40
THD
VIC
VIW
VVS
```

The negative value occurs in Bollinger Band LOWER components on W/M timeframes during extreme price acceleration.

Mathematically:

```text
LOWER = MIDDLE - K * STD
```

A negative LOWER value can therefore be a valid arithmetic output even though it is not a valid tradable PRICE_LEVEL.

## 3. Domain Decision

For an R/S LEVEL provider:

```text
PRICE_LEVEL <= 0
    = invalid level candidate
    = SKIP candidate
    != fatal pipeline error
```

This applies to finite BB price-level outputs.

The provider must continue to fail on genuinely malformed values such as:

```text
NaN
Infinity
invalid ValueSemantic
invalid configuration metadata
```

## 4. Scope

Allowed production change:

```text
src/calcEngine/levelLadder.py::load_bb_level_candidates()
```

Allowed automated tests:

```text
tests/test_rs_ladder.py
```

The fix MUST NOT change:

```text
BB indicator calculation formula
Indicator Engine persistence
MA provider behavior
R/S Strength formula
clustering thresholds
Source Effectiveness formulas
Promotion Gate thresholds
runtime source weights
provider registration
```

## 5. Expected Behavior

Input rows:

```text
BB20_2_W:LOWER  = -4.86
BB20_2_W:MIDDLE = 120.00
BB20_2_W:UPPER  = 244.86
```

Expected provider output:

```text
LOWER  -> skipped
MIDDLE -> candidate
UPPER  -> candidate
```

The provider should log a diagnostic warning/debug message containing ticker/config/component/value.

## 6. Acceptance Criteria

1. finite BB value > 0 remains a LEVEL candidate;
2. finite BB value <= 0 is skipped;
3. NaN/Infinity still raises;
4. invalid ValueSemantic still raises;
5. existing BB positive-value tests remain PASS;
6. R/S golden regression remains PASS;
7. previously failing H5 baseline no longer stops at negative BB LOWER;
8. no unrelated production-code changes.

## 7. Release Governance

Bug code must live on a dedicated fix branch.

Runbook and this Change Request live on `main`.

Bug PR must not be merged until local agent reports:

```text
## Final Verdict: PASS
Action: KEEP
```

## 8. Rollback

If regression is detected:

```text
revert BB provider candidate-skip commit
```

No database migration is required.
