# Runbook — ZigZag Deviation Roadmap V1.1 → V1.2 → V2

## Purpose

This is the parent execution runbook for the ZigZag deviation roadmap.

The stages are intentionally gated:

    MWG ZigZag foundation
      -> V1.1 calibration
      -> TestEngineer PASS
      -> V1.2 multi-ticker pilot
      -> TestEngineer PASS / pilot decision
      -> V2 regime-aware evaluation
      -> TestEngineer PASS / research decision

Do not skip a gate.

## Stage 0 — Foundation preflight

Required prior state:

    REQ-0027 MWG ZigZag technical validation PASS
    canonical engine structural errors = 0
    run.py does not invoke ZigZag

Focused regression:

    python -m pytest tests\test_zigzag_engine.py -v

## Stage 1 — V1.1

Run:

    docs/runbook/ZigZag_Deviation_Calibration_V1_1.md

Minimum commands:

    python -m pytest tests\test_zigzag_engine.py tests\test_zigzag_calibration.py -v
    python scripts\zigzag\calibrate_zigzag_deviation.py --tickers MWG
    python scripts\zigzag\calibrate_zigzag_deviation.py

Stop condition:

    TestEngineer verdict != PASS

Only a PASS opens V1.2.

## Stage 2 — V1.2

Run:

    docs/runbook/ZigZag_Multi_Ticker_Pilot_V1_2.md

Minimum commands:

    python -m pytest tests\test_zigzag_engine.py tests\test_zigzag_calibration.py -v
    python scripts\zigzag\run_zigzag_multi_ticker_pilot.py

Review all decisions:

    BASELINE_SUFFICIENT
    KEEP_5_BASELINE
    PROMOTE_CALIBRATED

Stop condition:

    TestEngineer verdict != PASS

Only a reviewed PASS opens V2 evaluation.

## Stage 3 — V2

Run:

    docs/runbook/ZigZag_Regime_Aware_V2.md

Minimum commands:

    python -m pytest tests\test_zigzag_engine.py tests\test_zigzag_calibration.py tests\test_zigzag_regime.py -v
    python scripts\zigzag\evaluate_zigzag_regime_v2.py

Review:

- no future leakage;
- static backward compatibility;
- structural validity;
- pivot-level DeviationPctUsed;
- RegimeUsed and DeviationSelectedAtDate;
- deterministic rerun.

## Evidence locations

    docs/reference/data/zigzag/calibration/
    docs/reference/data/zigzag/pilot/
    docs/reference/data/zigzag/regime/

All ChatGPT-readable evidence must remain under docs/reference/data/**.

## Production boundary

None of V1.1, V1.2 or V2 is automatically part of run.py.

A separate approved production-promotion decision is required after TestEngineer evidence.
