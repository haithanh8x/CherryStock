# Runbook — ZigZag Deviation Calibration V1.1

- **Requirement:** REQ-0028
- **Architecture:** docs/architecture/ZigZag_Deviation_Calibration.md
- **ADR:** ADR-014
- **Owner of final verdict:** TestEngineer

## 1. Objective

Calibrate a static per-ticker ZigZag DeviationPct using structural swing metrics.
This runbook must not modify run.py or production pivot/current tables.

Default grid:

    2%, 3%, 4%, 5%, 6%, 7%, 8%, 10%, 12%

Default pilot tickers:

    MWG,FPT,HPG,MBB,VCB,VNM,DIG,CEO,NVL,SSI

## 2. Outputs

DuckDB:

    cal_zigzag_deviation_evaluation
    dim_zigzag_ticker_config
    vw_ZigZag_Calibration
    vw_ZigZag_Ticker_Config

ChatGPT evidence:

    docs/reference/data/zigzag/calibration/
      ZigZag_Calibration_V1.1.csv
      ZigZag_Ticker_Config_V1.1.csv

## 3. Phase 0 — Sync

    cd C:\Github\CherryStock
    git status
    git pull

Working tree should be clean before database mutation.

## 4. Phase 1 — Focused tests

    python -m pytest tests\test_zigzag_engine.py tests\test_zigzag_calibration.py -v

Expected: all tests PASS.

Stop if any existing ZigZag engine regression fails.

## 5. Phase 2 — MWG calibration sanity

Run one ticker first:

    python scripts\zigzag\calibrate_zigzag_deviation.py --tickers MWG

Expected output contains:

    MWG: deviation=...
    method=SMALLEST_ELIGIBLE | FALLBACK_SCORE
    Calibration rows: 27
    Recommendations: 1

Why 27 rows:

    9 deviations x 3 splits = 27

Inspect recommendation:

    SELECT
        CalibrationVersion,
        Ticker,
        BaseDeviationPct,
        SelectionMethod,
        TrainScore,
        ValidationScore,
        TestScore,
        Status,
        IsActive
    FROM "CherryMon"."main"."vw_ZigZag_Ticker_Config"
    WHERE CalibrationVersion = 'V1.1'
      AND Ticker = 'MWG';

## 6. Phase 3 — Inspect MWG grid

    SELECT
        SplitName,
        DeviationPct,
        SwingCount,
        PivotDensityPer100Bars,
        MedianSwingBars,
        MedianAbsSwingPct,
        ShortSwingRate,
        StructuralValid,
        IsEligible,
        CalibrationScore
    FROM "CherryMon"."main"."vw_ZigZag_Calibration"
    WHERE CalibrationVersion = 'V1.1'
      AND Ticker = 'MWG'
    ORDER BY
        CASE SplitName
            WHEN 'TRAIN' THEN 1
            WHEN 'VALIDATION' THEN 2
            ELSE 3
        END,
        DeviationPct;

Validation rules:

- selected candidate must be structurally valid on TRAIN and VALIDATION when method is SMALLEST_ELIGIBLE;
- TEST score must not participate in the selection algorithm;
- 5% must remain present in the evaluation grid;
- no trading-return metric exists in the table.

## 7. Phase 4 — 10-ticker calibration

After MWG sanity passes:

    python scripts\zigzag\calibrate_zigzag_deviation.py

Or explicit:

    python scripts\zigzag\calibrate_zigzag_deviation.py --tickers MWG,FPT,HPG,MBB,VCB,VNM,DIG,CEO,NVL,SSI --version V1.1

Check coverage:

    SELECT
        Ticker,
        BaseDeviationPct,
        SelectionMethod,
        TrainScore,
        ValidationScore,
        TestScore
    FROM "CherryMon"."main"."vw_ZigZag_Ticker_Config"
    WHERE CalibrationVersion = 'V1.1'
    ORDER BY Ticker;

Expected: one row per successfully calibrated ticker.

## 8. Phase 5 — Idempotency

Run the same command again:

    python scripts\zigzag\calibrate_zigzag_deviation.py

Then:

    SELECT
        CalibrationVersion,
        COUNT(*) AS EvaluationRows
    FROM "CherryMon"."main"."cal_zigzag_deviation_evaluation"
    WHERE CalibrationVersion = 'V1.1'
    GROUP BY CalibrationVersion;

    SELECT
        CalibrationVersion,
        COUNT(*) AS RecommendationRows
    FROM "CherryMon"."main"."dim_zigzag_ticker_config"
    WHERE CalibrationVersion = 'V1.1'
    GROUP BY CalibrationVersion;

Counts and selected deviations must remain unchanged.

## 9. Phase 6 — Evidence

Files are automatically written to:

    docs/reference/data/zigzag/calibration/

Commit only bounded reference evidence:

    git add docs/reference/data/zigzag/calibration/
    git commit -m "test: add ZigZag V1.1 calibration evidence"
    git push origin main

## 10. PASS gate

V1.1 PASS requires:

    [ ] focused tests PASS
    [ ] MWG has 27 evaluation rows
    [ ] all requested tickers have deterministic recommendations or explicit SKIP reason
    [ ] selected deviations unchanged on rerun
    [ ] no structural invalid candidate is selected as SMALLEST_ELIGIBLE
    [ ] evidence CSV generated
    [ ] run.py unchanged

Only after PASS proceed to V1.2.

Final verdict:

    PASS | FAIL | BLOCKED | REGRESSION
