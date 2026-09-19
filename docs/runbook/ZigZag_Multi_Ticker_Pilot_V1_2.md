# Runbook — ZigZag Multi-Ticker Pilot V1.2

- **Requirement:** REQ-0029
- **Architecture:** docs/architecture/ZigZag_Multi_Ticker_Pilot.md
- **ADR:** ADR-014
- **Prerequisite:** V1.1 PASS
- **Owner of final verdict:** TestEngineer

## 1. Objective

Compare fixed 5% against V1.1 calibrated-static deviation on the same chronological TEST
holdout for each pilot ticker.

No production promotion or run.py integration occurs in this runbook.

## 2. Outputs

DuckDB:

    cal_zigzag_pilot_evaluation
    vw_ZigZag_Pilot

Evidence:

    docs/reference/data/zigzag/pilot/
      ZigZag_MultiTicker_Pilot_V1.2.csv

## 3. Phase 0 — Preflight V1.1

    SELECT
        Ticker,
        BaseDeviationPct,
        SelectionMethod
    FROM "CherryMon"."main"."vw_ZigZag_Ticker_Config"
    WHERE CalibrationVersion = 'V1.1'
    ORDER BY Ticker;

All pilot tickers must have a V1.1 recommendation.

If missing, stop and rerun V1.1. Do not silently fall back.

## 4. Phase 1 — Focused tests

    python -m pytest tests\test_zigzag_engine.py tests\test_zigzag_calibration.py -v

Expected: PASS.

## 5. Phase 2 — Run pilot

    python scripts\zigzag\run_zigzag_multi_ticker_pilot.py

Explicit variant:

    python scripts\zigzag\run_zigzag_multi_ticker_pilot.py --tickers MWG,FPT,HPG,MBB,VCB,VNM,DIG,CEO,NVL,SSI --calibration-version V1.1 --pilot-version V1.2

The script uses only the TEST slice from the same chronological 60/20/20 split used by V1.1.

## 6. Phase 3 — Review decisions

    SELECT
        Ticker,
        BaselineDeviationPct,
        CalibratedDeviationPct,
        BaselineSwingCount,
        CalibratedSwingCount,
        BaselineShortSwingRate,
        CalibratedShortSwingRate,
        BaselineMedianSwingBars,
        CalibratedMedianSwingBars,
        BaselineScore,
        CalibratedScore,
        Decision
    FROM "CherryMon"."main"."vw_ZigZag_Pilot"
    WHERE PilotVersion = 'V1.2'
    ORDER BY Ticker;

Allowed decisions:

    BASELINE_SUFFICIENT
    KEEP_5_BASELINE
    PROMOTE_CALIBRATED

Promotion rule:

    both structural valid
    AND calibrated ShortSwingRate <= baseline * 0.80
    AND calibrated MedianSwingBars <= baseline * 2.0
    AND calibrated SwingCount >= max(5, baseline SwingCount * 0.50)

If calibrated deviation equals 5%, decision must be BASELINE_SUFFICIENT.

## 7. Phase 4 — Structural protection

    SELECT
        Ticker,
        BaselineStructuralValid,
        CalibratedStructuralValid,
        Decision
    FROM "CherryMon"."main"."cal_zigzag_pilot_evaluation"
    WHERE PilotVersion = 'V1.2'
      AND (
          BaselineStructuralValid = FALSE
          OR CalibratedStructuralValid = FALSE
      );

Expected:

- no structurally invalid calibrated variant may have PROMOTE_CALIBRATED.

## 8. Phase 5 — Idempotency

Run the pilot twice with unchanged V1.1 recommendations:

    python scripts\zigzag\run_zigzag_multi_ticker_pilot.py
    python scripts\zigzag\run_zigzag_multi_ticker_pilot.py

Then:

    SELECT PilotVersion, COUNT(*) AS Rows
    FROM "CherryMon"."main"."cal_zigzag_pilot_evaluation"
    WHERE PilotVersion = 'V1.2'
    GROUP BY PilotVersion;

Expected: one row per pilot ticker, no duplicates.

## 9. Phase 6 — Evidence

    git add docs/reference/data/zigzag/pilot/
    git commit -m "test: add ZigZag V1.2 pilot evidence"
    git push origin main

## 10. Expansion gate

V1.2 PASS requires:

    [ ] V1.1 PASS
    [ ] focused tests PASS
    [ ] identical TEST window per baseline/calibrated pair
    [ ] all pilot decisions deterministic
    [ ] no invalid variant promoted
    [ ] evidence exported and reviewed
    [ ] run.py unchanged

Do not activate calibrated configs universe-wide from this runbook.

Final verdict:

    PASS | FAIL | BLOCKED | REGRESSION
