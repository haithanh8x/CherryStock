# Runbook — ZigZag Regime-Aware V2

- **Requirement:** REQ-0030
- **Architecture:** docs/architecture/ZigZag_Regime_Aware.md
- **ADR:** ADR-015
- **Prerequisite:** V1.1 recommendation; V1.2 should be reviewed before promotion
- **Owner of final verdict:** TestEngineer

## 1. Objective

Evaluate volatility-regime-aware deviations while preserving the core invariant:

Deviation is selected only after a pivot confirmation and remains locked for the next leg.

V2 remains manual/research only.

## 2. Default regime policy

    TR         max(H-L, abs(H-prevClose), abs(L-prevClose))
    ATR20      mean(TR, 20)
    ATRPct     ATR20 / Close
    Percentile trailing 252 known observations
    LOW_VOL    <30%   -> 0.80x base
    NORMAL     30-70% -> 1.00x base
    HIGH_VOL   >70%   -> 1.30x base
    Clamp      2%..15%

Rows before sufficient percentile history default to NORMAL.

## 3. Outputs

DuckDB:

    cal_zigzag_regime_evaluation
    vw_ZigZag_Regime_Evaluation

Evidence:

    docs/reference/data/zigzag/regime/
      ZigZag_Regime_Summary_V2.0.csv
      ZigZag_Regime_Pivots_V2.0.csv

Pivot evidence contains:

    Ticker
    PivotSeq
    PivotType
    PivotDate
    PivotPrice
    ConfirmedAtDate
    ConfirmationPrice
    DeviationPctUsed
    DeviationSelectedAtDate
    RegimeUsed

## 4. Phase 0 — Preflight base deviations

    SELECT Ticker, BaseDeviationPct
    FROM "CherryMon"."main"."vw_ZigZag_Ticker_Config"
    WHERE CalibrationVersion = 'V1.1'
    ORDER BY Ticker;

Missing base deviations are a blocker.

## 5. Phase 1 — Focused tests

    python -m pytest tests\test_zigzag_engine.py tests\test_zigzag_calibration.py tests\test_zigzag_regime.py -v

Critical expectations:

- static engine remains backward compatible;
- future price changes do not alter past regime context;
- multipliers/clamps are deterministic;
- deviation resolver is invoked only after confirmed pivots.

## 6. Phase 2 — Run V2 evaluation

    python scripts\zigzag\evaluate_zigzag_regime_v2.py

Explicit:

    python scripts\zigzag\evaluate_zigzag_regime_v2.py --tickers MWG,FPT,HPG,MBB,VCB,VNM,DIG,CEO,NVL,SSI --calibration-version V1.1 --regime-version V2.0

## 7. Phase 3 — Structural summary

    SELECT
        Ticker,
        BaseDeviationPct,
        StaticSwingCount,
        RegimeSwingCount,
        StaticShortSwingRate,
        RegimeShortSwingRate,
        StaticMedianSwingBars,
        RegimeMedianSwingBars,
        StaticStructuralValid,
        RegimeStructuralValid,
        StaticScore,
        RegimeScore,
        LowVolBars,
        NormalBars,
        HighVolBars
    FROM "CherryMon"."main"."vw_ZigZag_Regime_Evaluation"
    WHERE RegimeVersion = 'V2.0'
    ORDER BY Ticker;

Expected:

    StaticStructuralValid = TRUE
    RegimeStructuralValid = TRUE

for every ticker considered promotable.

## 8. Phase 4 — Verify swing-lock evidence

Open:

    docs/reference/data/zigzag/regime/ZigZag_Regime_Pivots_V2.0.csv

For each ticker:

- first pivot has RegimeUsed = BOOTSTRAP;
- pivot N uses the deviation selected at pivot N-1 confirmation;
- DeviationSelectedAtDate must equal the previous pivot ConfirmedAtDate;
- DeviationPctUsed remains within 2%..15%;
- LOW_VOL/NORMAL/HIGH_VOL thresholds follow 0.8x/1.0x/1.3x base after clamping.

No bar-by-bar threshold drift is permitted.

## 9. Phase 5 — Point-in-time audit

The unit test protects against future leakage. For a manual sample, choose a pivot and verify
the regime was selected at its previous pivot confirmation date, not at the future pivot date.

No future ATRPct observations may enter the trailing percentile.

## 10. Phase 6 — Idempotency

    python scripts\zigzag\evaluate_zigzag_regime_v2.py
    python scripts\zigzag\evaluate_zigzag_regime_v2.py

Then:

    SELECT RegimeVersion, COUNT(*) AS Rows
    FROM "CherryMon"."main"."cal_zigzag_regime_evaluation"
    WHERE RegimeVersion = 'V2.0'
    GROUP BY RegimeVersion;

Expected: one row per requested ticker.

## 11. Phase 7 — Evidence commit

    git add docs/reference/data/zigzag/regime/
    git commit -m "test: add ZigZag V2 regime evidence"
    git push origin main

## 12. V2 gate

PASS requires:

    [ ] V1.1 static base exists
    [ ] focused tests PASS
    [ ] static backward compatibility PASS
    [ ] no future leakage
    [ ] static and regime structures valid
    [ ] per-pivot threshold evidence internally consistent
    [ ] rerun deterministic
    [ ] run.py unchanged

A V2 PASS means the research implementation is valid. It does not automatically mean
regime-aware ZigZag should replace calibrated-static production behavior.

Final verdict:

    PASS | FAIL | BLOCKED | REGRESSION
