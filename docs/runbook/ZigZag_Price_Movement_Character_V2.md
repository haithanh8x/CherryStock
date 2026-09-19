# Runbook — REQ-0031 ZigZag Price Movement Character V2

- Requirement: REQ-0031
- Architecture: docs/architecture/Price_Movement_Character_V2.md
- ADR: ADR-016
- Initial scope: MWG only
- Final validation owner: TestEngineer

## 1. Objective

Deploy and independently validate the MWG-first Price Movement V2 implementation.

Price Movement must consume confirmed ZigZag public swings and must not detect pivots,
change deviation, modify run.py or alter SmartMoney.

## 2. Main artifacts

    docs/backlog/requirements/REQ-0031-zigzag-price-movement-character-v2.md
    docs/architecture/Price_Movement_Character_V2.md
    docs/adr/ADR-016-zigzag-price-movement-characterization-v2.md
    src/DuckDB/sql/price_movement_v2_schema.sql
    src/cherrystock/domain/analytics/price_movement/models.py
    src/cherrystock/domain/analytics/price_movement/classifier.py
    src/cherrystock/domain/analytics/price_movement/engine.py
    src/cherrystock/infrastructure/database/repositories/price_movement_repository.py
    src/calcEngine/priceMovement.py
    scripts/initload/init_reload_price_movement_mwg.py
    scripts/validate_price_movement_mwg.py
    scripts/export_price_movement_reconciliation.py
    tests/test_price_movement_zigzag.py

## 3. Phase 0 — Sync

    cd C:\Github\CherryStock
    git status
    git pull origin main

### Archify deferral

Archify render/showcase validation is intentionally **not a REQ-0031 deployment or PASS gate**.

Current known issue: the Price Movement V2 connections/labels can cross existing nodes and
cause showcase layout validation to fail. This is a visualization/layout concern only and does
not block Price Movement calculation, persistence, reconciliation, or TestEngineer validation.

For REQ-0031:

    SKIP .\scripts\render_archify_analytics.ps1 -NoOpen

Do not hand-edit generated Archify HTML. Architecture visualization cleanup may be handled later
as separate documentation/layout maintenance.

## 4. Phase 1 — Focused unit/regression tests

Run:

    python -m pytest tests\test_zigzag_engine.py tests\test_price_movement_zigzag.py -v

Then daily pipeline regression:

    python -m pytest tests\test_sync_write_pipeline_service.py -v

Expected:

- existing ZigZag tests remain PASS;
- all Price Movement formula/classifier/point-in-time tests PASS;
- daily pipeline service regression PASS.

Stop if an existing ZigZag or daily pipeline test regresses.

## 5. Phase 2 — MWG initload

Prerequisite:

MWG ZigZag must already exist and validate for the configured upstream ZigZagConfigCode.

Run:

    python scripts\initload\init_reload_price_movement_mwg.py

Expected summary includes:

    status: OK
    ticker: MWG
    price_movement_config_code: PM_ZZ_D_V2
    zigzag_config_code: ZZ_D_5_MVP
    source_zigzag_swings: <N>
    confirmed_movement_swings: <same N>
    profile_character: <supported label>
    swing_rows_inserted: <same N>
    profile_rows_inserted: 1

The initload executes the additive schema inside the same caller-owned DuckDB UnitOfWork.

## 6. Phase 3 — Structural validation

Run:

    python scripts\validate_price_movement_mwg.py

PASS requires:

    zigzag_swings == movement_swings
    profile_rows == 1
    structural_errors == 0
    STRUCTURAL VALIDATION: PASS

The validator independently checks:

- 1:1 upstream ZigZag swing identity;
- Start/End pivot/date/price consistency;
- ConfirmedAtDate consistency;
- SwingPct formula;
- UP/DOWN sign;
- TradingBars from OHLC dates;
- Velocity formula;
- PathEfficiency in [0,1];
- DirectionalPersistenceRate in [0,1];
- profile last swing/as-of consistency;
- supported MovementCharacter;
- run.py contains no Price Movement integration.

## 7. Phase 4 — Direct SQL review

### 7.1 Config

    SELECT *
    FROM "CherryMon"."main"."dim_price_movement_config"
    WHERE ConfigCode = 'PM_ZZ_D_V2';

Expected upstream:

    ZigZagConfigCode = ZZ_D_5_MVP

### 7.2 Enriched swings

    SELECT
        Ticker,
        SwingSeq,
        Direction,
        StartDate,
        StartPrice,
        EndDate,
        EndPrice,
        ConfirmedAtDate,
        SwingPct,
        TradingBars,
        VelocityPctPerBar,
        AvgATRPct,
        ATRNormalizedMove,
        PathEfficiency,
        DirectionalPersistenceRate
    FROM "CherryMon"."main"."vw_Ticker_Price_Movement_Swings"
    WHERE Ticker = 'MWG'
      AND PriceMovementConfigCode = 'PM_ZZ_D_V2'
    ORDER BY SwingSeq;

### 7.3 Profile

    SELECT *
    FROM "CherryMon"."main"."vw_Ticker_Movement_Profile"
    WHERE Ticker = 'MWG'
      AND PriceMovementConfigCode = 'PM_ZZ_D_V2';

Expected exactly one row.

## 8. Phase 5 — Idempotency

Capture business row counts:

    SELECT COUNT(*)
    FROM "CherryMon"."main"."cal_price_movement_swing"
    WHERE Ticker = 'MWG';

    SELECT COUNT(*)
    FROM "CherryMon"."main"."cal_price_movement_profile"
    WHERE Ticker = 'MWG';

Run initload again:

    python scripts\initload\init_reload_price_movement_mwg.py

Rerun validator:

    python scripts\validate_price_movement_mwg.py

Expected:

- same swing count;
- one profile row;
- no duplicates;
- same business values;
- structural_errors = 0.

CalculatedAt may change and is not a business-value idempotency failure.

## 9. Phase 6 — Post-golive reconciliation export

Run:

    python scripts\export_price_movement_reconciliation.py --ticker MWG

Default behavior:

- reads profile lookback;
- exports the most recent profile swing set;
- automatically adds ATR warmup OHLC;
- requires reconciliation status PASS.

Expected console:

    reconciliation_status: PASS
    total_core_errors: 0

Output:

    docs/reference/data/price_movement/mwg/

Package includes:

    MWG_Price_Movement_Config.csv
    MWG_OHLC_<range>_with_warmup.csv
    MWG_ZigZag_Pivots_<range>.csv
    MWG_ZigZag_Swings_<range>.csv
    MWG_Price_Movement_Swings_<range>.csv
    MWG_Movement_Profile.csv
    MWG_Price_Movement_Reconciliation_Summary.csv

Detailed reconciliation procedure:

    docs/runbook/ZigZag_Price_Movement_Reconciliation.md

## 10. Phase 7 — Commit validation evidence

Only after local validator + exporter PASS:

    git add docs/reference/data/price_movement/mwg/
    git commit -m "test: add MWG Price Movement V2 validation evidence"
    git push origin main

Do not commit secrets or unrelated local data.

## 11. Phase 8 — ChatGPT verification

After push, ask ChatGPT to read:

    docs/reference/data/price_movement/mwg/

ChatGPT should cross-check:

1. Price Movement rows map 1:1 to ZigZag swings.
2. endpoint dates/prices/pivot ids match;
3. SwingPct and velocity recompute exactly;
4. TradingBars reconcile to OHLC;
5. PathEfficiency and persistence remain bounded;
6. no path feature uses OHLC after EndDate;
7. profile uses the configured recent lookback;
8. MovementCharacter follows config thresholds;
9. reconciliation summary reports TotalCoreErrors = 0.

## 12. MWG gate

REQ-0031 MWG technical PASS requires:

    [ ] focused unit tests PASS
    [ ] existing ZigZag regression PASS
    [ ] daily pipeline regression PASS
    [ ] MWG initload PASS
    [ ] structural_errors = 0
    [ ] ZigZag swing count == Price Movement swing count
    [ ] idempotent rerun
    [ ] reconciliation_status = PASS
    [ ] total_core_errors = 0
    [ ] evidence committed under docs/reference/data/price_movement/mwg/
    [ ] run.py unchanged

Archify status is explicitly excluded from this technical PASS decision.

Final verdict belongs to TestEngineer:

    PASS | FAIL | BLOCKED | REGRESSION

## 13. Expansion gate

Do not move to multi-ticker scheduling until MWG PASS.

A later expansion may use the reusable refresh_price_movement_ticker function, but requires a
separate approved rollout/promotion decision. REQ-0031 does not authorize daily run.py
integration.
