# Runbook — ZigZag MWG MVP

## 1. Mục tiêu

Runbook này chỉ kiểm tra ZigZag Swing Engine trên ticker MWG.

Không chạy toàn universe và không tích hợp ZigZag vào run.py.

Flow:

    focused unit tests
      -> full deterministic MWG initload
      -> structural validation
      -> inspect Jul-Sep 2026 pivots/swings
      -> rerun idempotency
      -> user visual acceptance
      -> only then design multi-ticker rollout

## 2. Scope cố định

    Ticker             = MWG
    Timeframe          = D
    ConfigCode         = ZZ_D_5_MVP
    DeviationPct       = 5%
    Pivot source       = High / Low
    Confirmation       = Close
    MinimumSwingBars   = 1

ATR không được dùng trong ZigZag MVP.

## 3. Files chính

    docs/backlog/requirements/REQ-0027-price-movement-characterization.md
    docs/architecture/ZigZag_Engine.md
    docs/adr/ADR-013-zigzag-as-price-movement-segmentation-foundation.md
    src/cherrystock/domain/analytics/zigzag/engine.py
    src/cherrystock/domain/analytics/zigzag/models.py
    src/cherrystock/infrastructure/database/repositories/zigzag_repository.py
    src/calcEngine/zigzag.py
    src/DuckDB/sql/zigzag_mvp_schema.sql
    scripts/initload/init_reload_zigzag_mwg.py
    scripts/validate_zigzag_mwg.py
    tests/test_zigzag_engine.py

## 4. Public contracts

    vw_Ticker_ZigZag_Pivots
    vw_Ticker_ZigZag_Swings
    vw_Ticker_ZigZag_Current

Persistence:

    dim_zigzag_config
    cal_zigzag_pivot
    cal_zigzag_current_leg

Không có cal_zigzag_daily trong MVP.

## 5. Phase 0 — Sync

Từ repo root:

    cd C:\Github\CherryStock
    git status
    git pull

Working tree nên clean trước khi chạy mutation.

## 6. Phase 1 — Focused unit tests

    python -m pytest tests\test_zigzag_engine.py -v

Expected: tất cả PASS.

Các behavior chính:

- LOW pivot nằm tại actual trough, không nằm ở confirmation bar;
- HIGH pivot nằm tại actual peak;
- PivotDate và ConfirmedAtDate tách biệt;
- pivots alternate;
- current leg follow last confirmed pivot;
- invalid price rows được loại explicit.

Nếu fail thì dừng, không initload DB.

## 7. Phase 2 — Full MWG initload

    python scripts\initload\init_reload_zigzag_mwg.py

Expected summary có:

    status: OK
    scope: MWG_MVP_ONLY
    ticker: MWG
    config_code: ZZ_D_5_MVP
    source_rows: > 0
    usable_rows: > 0
    confirmed_pivots: > 0
    current_status: PROVISIONAL
    calculation_seconds: ...

Script dùng một DuckDBUnitOfWork:

    ensure schema/config/views
      -> load MWG OHLC
      -> O(n) ZigZag calculation
      -> replace only MWG rows for ConfigId
      -> commit
      -> export DB metadata

Failure trước commit phải rollback transaction.

## 8. Phase 3 — Structural validation + MWG review output

    python scripts\validate_zigzag_mwg.py

Expected:

    structural_errors:0
    STRUCTURAL VALIDATION: PASS

Validator kiểm tra:

- duplicate pivot keys;
- contiguous PivotSeq;
- alternating HIGH/LOW;
- PivotDate < ConfirmedAtDate;
- one confirmed pivot per trading date;
- ConfirmedAtDate không đi lùi;
- PivotPrice đúng với High/Low tại PivotDate;
- interior pivot là local extreme trên các bar strictly between hai PivotDate lân cận;
- đúng một current-leg row;
- current direction phù hợp last confirmed pivot.

Script tự in pivots và swings trong window:

    2026-07-01 -> 2026-09-30

Đây là review window bắt buộc cho case MWG đã phát hiện trước đó.

## 9. Phase 4 — Kiểm tra riêng case Jul-Sep 2026

Query pivots:

    SELECT
        PivotSeq,
        PivotType,
        PivotDate,
        PivotPrice,
        ConfirmedAtDate,
        ConfirmationPrice
    FROM "CherryMon"."main"."vw_Ticker_ZigZag_Pivots"
    WHERE Ticker = 'MWG'
      AND ConfigCode = 'ZZ_D_5_MVP'
      AND PivotDate BETWEEN DATE '2026-07-01' AND DATE '2026-09-30'
    ORDER BY PivotSeq;

Query derived swings:

    SELECT
        SwingSeq,
        Direction,
        StartDate,
        StartPrice,
        EndDate,
        EndPrice,
        ConfirmedAtDate,
        SwingPct
    FROM "CherryMon"."main"."vw_Ticker_ZigZag_Swings"
    WHERE Ticker = 'MWG'
      AND ConfigCode = 'ZZ_D_5_MVP'
      AND EndDate >= DATE '2026-07-01'
      AND StartDate <= DATE '2026-09-30'
    ORDER BY SwingSeq;

Review rule:

- UP swing phải bắt đầu từ LOW pivot thực tế;
- DOWN swing phải bắt đầu từ HIGH pivot thực tế;
- không chấp nhận start point nằm giữa một leg đang giảm/tăng;
- ConfirmedAtDate có thể muộn hơn PivotDate và đó là behavior đúng.

Case cũ MWG 2026-07-23 / 66 không được coi là đúng chỉ vì thuật toán đổi state tại đó.
Start của UP swing phải phản ánh actual trough theo ZigZag 5% rule.

## 10. Phase 5 — Idempotency

Chạy lại cùng command:

    python scripts\initload\init_reload_zigzag_mwg.py
    python scripts\validate_zigzag_mwg.py

Expected:

- pivot count không đổi;
- PivotSeq/PivotType/PivotDate/PivotPrice/ConfirmedAtDate không đổi;
- không duplicate;
- current leg vẫn chỉ một row.

Có thể lấy snapshot trước/sau:

    SELECT
        COUNT(*) AS PivotRows,
        MIN(PivotDate) AS MinPivotDate,
        MAX(PivotDate) AS MaxPivotDate,
        MAX(PivotSeq) AS MaxPivotSeq
    FROM "CherryMon"."main"."cal_zigzag_pivot"
    WHERE Ticker = 'MWG'
      AND ConfigId = 1;

## 11. Phase 6 — Current provisional leg

    SELECT *
    FROM "CherryMon"."main"."vw_Ticker_ZigZag_Current"
    WHERE Ticker = 'MWG'
      AND ConfigCode = 'ZZ_D_5_MVP';

Expected:

    Status = PROVISIONAL

Direction:

- last pivot LOW -> current Direction UP;
- last pivot HIGH -> current Direction DOWN.

Candidate endpoint có thể thay đổi ở lần chạy sau. Không coi candidate là confirmed pivot.

## 12. Phase 7 — Performance sanity

MVP engine không có expanding path calculation.

Quan sát field:

    calculation_seconds

Mục đích Phase 1 là xác nhận algorithm có complexity gần O(n) cho riêng MWG, không phải
benchmark toàn universe.

Nếu một MWG history vài nghìn bars mất nhiều giây bất thường, dừng mở rộng ticker và profile
engine trước.

## 13. Phase 8 — Daily pipeline regression

ZigZag MVP không được gọi từ run.py.

Kiểm tra focused pipeline tests hiện có nếu muốn xác nhận regression:

    python -m pytest tests\test_sync_write_pipeline_service.py -v

Không cần chạy toàn daily pipeline chỉ để validate ZigZag.

## 14. Expansion gate

Không tạo all-ticker initload trước khi đủ toàn bộ:

    [ ] unit tests PASS
    [ ] structural validator PASS
    [ ] initload rerun idempotent
    [ ] Jul-Sep 2026 pivot list đã review
    [ ] UP/DOWN legs nhìn đúng với MWG chart
    [ ] user chấp nhận ZZ_D_5_MVP hoặc yêu cầu config khác

Sau khi user approve mới chuyển requirement sang:

    MULTI_TICKER_PILOT

Khi đó mới thiết kế:

- list ticker pilot;
- 3% / 5% / 8% configs nếu cần;
- incremental checkpoint;
- scale/performance benchmark;
- future Movement Character features.

## 15. Không làm trong MVP

Không:

- enable trong run.py;
- chạy 1,600+ ticker;
- dùng ATR cho pivot;
- tạo daily historical ZigZag state table;
- tính Magnitude/Velocity/Persistence score;
- thay SmartMoneyScore;
- tự động gọi output là BUY/SELL.

## 16. Evidence gửi TestEngineer

    python -m pytest tests\test_zigzag_engine.py -v
    python scripts\initload\init_reload_zigzag_mwg.py
    python scripts\validate_zigzag_mwg.py
    python scripts\initload\init_reload_zigzag_mwg.py
    python scripts\validate_zigzag_mwg.py

Final technical verdict:

    PASS | FAIL | BLOCKED | REGRESSION

User visual acceptance của MWG là gate riêng trước khi mở rộng scope.
