# Runbook — Price Movement V2 Post-Golive Reconciliation

## 1. Purpose

Provide a standard local export and ChatGPT verification procedure after Price Movement V2 is
initialized or later rebuilt for a ticker.

This runbook is safe to repeat. It does not mutate Price Movement data; it only reads public
contracts and writes bounded CSV evidence under docs/reference/data/**.

## 2. Preconditions

Required:

- Price Movement schema exists;
- target ticker has confirmed Price Movement swings;
- target ticker has one movement profile;
- upstream ZigZag public swings exist for the Price Movement config's ZigZagConfigCode.

For MWG:

    python scripts\validate_price_movement_mwg.py

should already return:

    STRUCTURAL VALIDATION: PASS

## 3. Default export — no manual date selection

For MWG:

    python scripts\export_price_movement_reconciliation.py --ticker MWG

The exporter automatically:

1. reads PM_ZZ_D_V2;
2. reads ProfileLookbackSwings;
3. selects the recent swing set used by the profile;
4. determines the required movement date window;
5. adds ATR warmup OHLC history;
6. exports upstream ZigZag and downstream Price Movement facts;
7. recomputes core reconciliation checks;
8. exits non-zero when reconciliation fails.

This avoids manual TradingView-style export work.

## 4. Optional bounded date override

Only use this when investigating a known historical window.

Single-line command:

    python scripts\export_price_movement_reconciliation.py --ticker MWG --start-date 2026-07-01 --end-date 2026-09-30

## 5. Output location

Canonical path:

    docs/reference/data/price_movement/<ticker-lower>/

For MWG:

    docs/reference/data/price_movement/mwg/

Expected files:

    MWG_Price_Movement_Config.csv
    MWG_OHLC_<range>_with_warmup.csv
    MWG_ZigZag_Pivots_<range>.csv
    MWG_ZigZag_Swings_<range>.csv
    MWG_Price_Movement_Swings_<range>.csv
    MWG_Movement_Profile.csv
    MWG_Price_Movement_Reconciliation_Summary.csv

## 6. Summary PASS contract

Open:

    docs/reference/data/price_movement/mwg/
    MWG_Price_Movement_Reconciliation_Summary.csv

Required:

    MissingMovementSwingCount = 0
    ExtraMovementSwingCount = 0
    IdentityMismatchCount = 0
    NumericMismatchCount = 0
    SwingPctFormulaMismatchCount = 0
    TradingBarsMismatchCount = 0
    VelocityMismatchCount = 0
    PathEfficiencyBoundsViolationCount = 0
    PersistenceBoundsViolationCount = 0
    PointInTimeViolationCount = 0
    ProfileLastSwingMismatchCount = 0
    ProfileAsOfMismatchCount = 0
    TotalCoreErrors = 0
    ReconciliationStatus = PASS

If any count is non-zero, do not mark reconciliation PASS.

## 7. Commit evidence for ChatGPT

After exporter PASS:

    git status
    git add docs/reference/data/price_movement/mwg/
    git commit -m "test: add MWG Price Movement reconciliation evidence"
    git push origin main

For another ticker replace the final path with its lowercase ticker folder.

## 8. Ask ChatGPT to verify

Recommended request:

    Read docs/reference/data/price_movement/mwg/ from CherryStock main.
    Verify REQ-0031 Price Movement V2 against the reconciliation runbook.
    Cross-check ZigZag swing identity, formulas, TradingBars, path metric bounds,
    point-in-time semantics and current movement profile. Report PASS/FAIL with
    exact SwingSeq evidence for any mismatch.

ChatGPT can then read the committed CSV package directly from GitHub.

## 9. What ChatGPT should verify independently

### 9.1 Segmentation lineage

Price Movement must not invent new swing boundaries.

For each exported SwingSeq compare:

    ZigZag StartPivotSeq == Price Movement StartPivotSeq
    ZigZag EndPivotSeq == Price Movement EndPivotSeq
    ZigZag StartDate == Price Movement StartDate
    ZigZag EndDate == Price Movement EndDate
    ZigZag StartPrice == Price Movement StartPrice
    ZigZag EndPrice == Price Movement EndPrice
    ZigZag ConfirmedAtDate == Price Movement ConfirmedAtDate

### 9.2 Magnitude

    expected = EndPrice / StartPrice - 1

Compare to SwingPct.

### 9.3 Trading duration

Using exported OHLC:

    expected TradingBars =
        count(Date between StartDate and EndDate inclusive) - 1

### 9.4 Velocity

    expected VelocityPctPerBar =
        SwingPct / TradingBars

### 9.5 Descriptive-only volatility

ATR/ATRNormalizedMove may change descriptive metrics but must not change:

    StartPivotSeq
    EndPivotSeq
    StartDate
    EndDate
    Direction

### 9.6 Point-in-time

Required:

    EndDate < ConfirmedAtDate

Path features use OHLC only through EndDate.

### 9.7 Bounds

Required:

    0 <= PathEfficiency <= 1
    0 <= DirectionalPersistenceRate <= 1

### 9.8 Profile

Profile should use the latest configured ProfileLookbackSwings only.

DirectionalBias:

    sum(SwingPct) / sum(abs(SwingPct))

MovementCharacter must match the config thresholds.

## 10. Failure routing

Identity/date/price mismatch:

    likely upstream/downstream lineage defect
    -> SolutionArchitect if contract ambiguity
    -> GeneralCoding if implementation defect

Formula/TradingBars/metric mismatch:

    -> GeneralCoding

Duplicate/missing persistence rows or rerun issue:

    -> GeneralCoding + database migration procedure

Only classification semantics disputed while calculations are correct:

    -> BusinessAnalyst / SolutionArchitect

## 11. Evidence retention

CSV files here are reproducible reference evidence, not runtime Source of Truth.

Runtime truth remains:

    vw_Ticker_ZigZag_Swings
    vw_Ticker_Price_Movement_Swings
    vw_Ticker_Movement_Profile

Regenerate evidence after a relevant ZigZag or Price Movement config/code change.
