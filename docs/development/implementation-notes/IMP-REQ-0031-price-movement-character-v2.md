# IMP-REQ-0031 — Price Movement Character V2

## Requirement / design

    docs/backlog/requirements/REQ-0031-zigzag-price-movement-character-v2.md
    docs/architecture/Price_Movement_Character_V2.md
    docs/adr/ADR-016-zigzag-price-movement-characterization-v2.md

## Delivery state

    IMPLEMENTED_PENDING_VALIDATION

Implementation is present on main. Final TestEngineer PASS is not claimed.

## Changed modules

Domain:

    src/cherrystock/domain/analytics/price_movement/__init__.py
    src/cherrystock/domain/analytics/price_movement/models.py
    src/cherrystock/domain/analytics/price_movement/classifier.py
    src/cherrystock/domain/analytics/price_movement/engine.py

Persistence / orchestration:

    src/DuckDB/sql/price_movement_v2_schema.sql
    src/cherrystock/infrastructure/database/repositories/price_movement_repository.py
    src/calcEngine/priceMovement.py

Operations / verification:

    scripts/initload/init_reload_price_movement_mwg.py
    scripts/validate_price_movement_mwg.py
    scripts/export_price_movement_reconciliation.py
    tests/test_price_movement_zigzag.py

Runbooks:

    docs/runbook/ZigZag_Price_Movement_Character_V2.md
    docs/runbook/ZigZag_Price_Movement_Reconciliation.md

## Key implementation decisions

1. Active ZigZag public swings are the segmentation Source of Truth.
2. V1.1 BaseDeviationPct recommendations are not used unless separately promoted upstream.
3. Price Movement recomputes SwingPct for reconciliation but preserves all ZigZag identities.
4. ATR20Pct is descriptive only and cannot change swing boundaries.
5. Path features use OHLC only through EndDate.
6. Profile classification uses versioned config thresholds.
7. Repository methods never commit; caller-owned UnitOfWork owns transaction boundaries.
8. Full target-ticker rebuild is deterministic delete/replace within the Price Movement scope.
9. run.py is intentionally unchanged.

## DuckDB forward migration

Additive objects:

    dim_price_movement_config
    cal_price_movement_swing
    cal_price_movement_profile
    vw_Ticker_Price_Movement_Swings
    vw_Ticker_Movement_Profile

Seed config:

    PM_ZZ_D_V2
    ZigZagConfigCode = ZZ_D_5_MVP

No ZigZag or SmartMoney object is altered.

## Execution

Architecture artifact gate:

    .\scripts\render_archify_analytics.ps1 -NoOpen

Focused tests:

    python -m pytest tests\test_zigzag_engine.py tests\test_price_movement_zigzag.py -v
    python -m pytest tests\test_sync_write_pipeline_service.py -v

MWG initload / validation:

    python scripts\initload\init_reload_price_movement_mwg.py
    python scripts\validate_price_movement_mwg.py

Reconciliation export:

    python scripts\export_price_movement_reconciliation.py --ticker MWG

## ChatGPT evidence contract

The exporter writes:

    docs/reference/data/price_movement/mwg/

After local PASS, commit the bounded evidence package to main so ChatGPT can independently
verify formulas, ZigZag lineage, profile semantics and point-in-time constraints.

## Known gates

- Archify generated HTML still requires local render/validation.
- GitHub connector cannot execute local CherryMon pytest/initload.
- No multi-ticker scheduling is authorized before MWG TestEngineer PASS.
- No run.py integration is authorized by REQ-0031.

## Test Engineer handoff

    Objective: REQ-0031 MWG technical validation
    Runbook: docs/runbook/ZigZag_Price_Movement_Character_V2.md
    Reconciliation: docs/runbook/ZigZag_Price_Movement_Reconciliation.md
    Expected outcome: PASS | FAIL | BLOCKED | REGRESSION
