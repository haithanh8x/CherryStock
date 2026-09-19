# REQ-0028 / REQ-0029 / REQ-0030 — ZigZag Deviation Roadmap Implementation

## Outcome

    IMPLEMENTED_PENDING_VALIDATION

## Delivered

V1.1:
- static ticker-specific deviation calibration;
- 2/3/4/5/6/7/8/10/12% default grid;
- chronological TRAIN/VALIDATION/TEST;
- structural/swing metrics;
- deterministic recommendation persistence;
- calibration evidence export.

V1.2:
- configurable multi-ticker pilot;
- fixed 5% versus calibrated-static on TEST holdout;
- material-improvement promotion rule;
- pilot persistence and evidence export.

V2:
- optional swing-locked deviation resolver in the canonical engine;
- ATR20/Close trailing-percentile volatility regimes;
- 0.8x / 1.0x / 1.3x multipliers;
- 2%..15% clamp;
- pivot-level actual DeviationPctUsed evidence;
- static behavior remains default when resolver is absent.

## Runtime boundary

No change was made to the daily run.py orchestration. The new scripts are manual research
workflows under scripts/zigzag/.

## Main implementation files

    src/cherrystock/domain/analytics/zigzag/research.py
    src/cherrystock/domain/analytics/zigzag/regime.py
    src/cherrystock/domain/analytics/zigzag/engine.py
    src/cherrystock/infrastructure/database/repositories/zigzag_research_repository.py
    src/DuckDB/sql/zigzag_research_schema.sql
    scripts/zigzag/calibrate_zigzag_deviation.py
    scripts/zigzag/run_zigzag_multi_ticker_pilot.py
    scripts/zigzag/evaluate_zigzag_regime_v2.py
    tests/test_zigzag_calibration.py
    tests/test_zigzag_regime.py

## Runbooks

    docs/runbook/ZigZag_Deviation_Calibration_V1_1.md
    docs/runbook/ZigZag_Multi_Ticker_Pilot_V1_2.md
    docs/runbook/ZigZag_Regime_Aware_V2.md

## Validation order

    V1.1 runbook
      -> PASS
      -> V1.2 runbook
      -> PASS / pilot decisions
      -> V2 runbook
      -> PASS / research decision

Implementation owner does not self-certify PASS.

## Architecture artifact

The Archify typed source was updated:

    docs/architecture/diagrams/cherrystock-analytics-calculation-engines.architecture.json

Generated HTML still requires local render:

    .\scripts\render_archify_analytics.ps1 -NoOpen
