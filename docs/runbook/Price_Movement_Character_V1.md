# Runbook — Price Movement Character V1

## 1. Mục tiêu

Runbook này dùng để kiểm tra local implementation của `REQ-0027` theo thứ tự an toàn:

```text
Focused tests
→ targeted MWG full rebuild
→ inspect point-in-time semantics
→ read-only contract validation
→ idempotency
→ full historical initload
→ representative ticker checks
→ ATR/fallback checks
→ incremental checkpoint
→ canonical run.py
→ Data Quality audit
→ public-contract checks
```

Implementation state trước khi TestEngineer xác nhận độc lập:

```text
IMPLEMENTED_PENDING_VALIDATION
```

Không coi developer/local run thành final PASS.

> **Runtime note:** Runbook này chạy bằng Python scripts kết nối trực tiếp DuckDB qua `DuckDBConnectionFactory` / `DuckDBUnitOfWork`. Không cần bật MCP DuckDB. Nên tắt MCP/process khác đang giữ writer connection nếu gặp DB lock.

---

## 2. Files chính

```text
docs/architecture/Price_Movement_Character.md
src/DuckDB/sql/price_movement_character_v1_schema.sql
src/DuckDB/sql/price_movement_character_v1_profile_view.sql
src/calcEngine/priceMovementCharacter.py
src/cherrystock/domain/analytics/price_movement/
src/cherrystock/infrastructure/database/repositories/price_movement_repository.py
src/cherrystock/infrastructure/database/price_movement_validation.py
scripts/run_price_movement.py
scripts/inspect_price_movement.py
scripts/validate_price_movement_character.py
scripts/initload/init_reload_price_movement_character.py
tests/test_price_movement_character.py
tests/test_price_movement_runtime.py
tests/test_price_movement_pipeline_order.py
tests/test_price_movement_profile_contract.py
```

Public contracts:

```text
vw_Ticker_Movement_Swings
vw_Ticker_Movement_D
vw_Ticker_Movement_Profile
```

---

## 3. Point-in-time contract cần hiểu trước khi chạy

Price Movement V1 tách hai loại fact:

```text
cal_price_movement_swing = confirmed event history
cal_price_movement_daily = as-of daily state của active leg
```

Daily state V1 chỉ có:

```text
SwingStatus = PROVISIONAL | TRANSITION
```

Không có daily row `CONFIRMED`.

Một swing có thể có:

```text
PivotEndDate = 2026-08-27
ConfirmedAtDate = 2026-09-07
```

Các daily rows từ `2026-08-27` đến trước `2026-09-07` vẫn là trạng thái `PROVISIONAL`. Sau này event được confirmed, việc query hiện tại có thể thấy event đó có `PivotEndDate <= daily.Date` nhưng `ConfirmedAtDate > daily.Date`. Đây chỉ là **geometric overlap**, không tự động có nghĩa daily calculation đã dùng future knowledge.

No-look-ahead invariant đúng là:

```text
Daily row tại ngày D chỉ được dùng historical swings có ConfirmedAtDate < D.
```

V1 lưu evidence trực tiếp bằng:

```text
HistoricalSameDirSwingCount
```

và validator đối chiếu field này với đúng tập event `ConfirmedAtDate < D`, capped bởi `ProfileMaxSwings`.

Do đó **không dùng** query kiểu sau làm no-look-ahead failure:

```text
PivotEndDate <= D AND ConfirmedAtDate > D
```

vì query đó sẽ đếm các overlap hợp lệ của active provisional leg.

---

## 4. Phase 0 — Đồng bộ code và kiểm tra môi trường

Từ repository root:

```powershell
cd C:\Github\CherryStock
git status
git pull
```

Nếu working tree có thay đổi local cần giữ lại, commit/stash trước khi pull.

Kiểm tra Python:

```powershell
python --version
```

Expected: Python `3.13.x`.

Kiểm tra dependency:

```powershell
python -c "import duckdb, pandas, numpy; print('duckdb=', duckdb.__version__, 'pandas=', pandas.__version__, 'numpy=', numpy.__version__)"
```

Nếu thiếu dependency:

```powershell
python -m pip install -e ".[dev]"
```

Không hard-code DB path. Runtime dùng CherryStock settings / `LOCAL_DB_PATH`.

---

## 5. Phase 1 — Focused tests trước khi ghi DuckDB

Chạy focused tests:

```powershell
python -m pytest `
  tests\test_price_movement_character.py `
  tests\test_price_movement_runtime.py `
  tests\test_price_movement_pipeline_order.py `
  tests\test_price_movement_profile_contract.py `
  tests\test_sync_write_pipeline_service.py -v
```

Expected: tất cả PASS.

Các invariant chính:
- pivot confirmation/no-look-ahead semantics;
- smooth path vs noisy path persistence;
- same-direction historical scoring;
- thiếu history → `INSUFFICIENT_HISTORY`, không ép score về 0;
- runtime optimized engine giữ semantics;
- order `Indicators → Price Movement → SmartMoney`;
- bounded profile view dùng `ProfileMaxSwings`;
- canonical write service backward-compatible.

Nếu fail, dừng. Không chạy mutation trên DB thật.

---

## 6. Phase 2 — Smoke targeted MWG

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
```

Expected summary:

```text
status = OK
mode = full
tickers_processed = 1
tickers_rebuilt = 1
daily_rows_upserted > 0
swing_rows_upserted > 0
```

Runner đảm bảo:

```text
schema + seed
→ bounded profile view
→ full rebuild MWG
→ commit qua DuckDBUnitOfWork
```

Nếu exception xảy ra trước commit, UoW rollback transaction hiện tại.

---

## 7. Phase 3 — Inspect MWG + point-in-time semantics

```powershell
python scripts\inspect_price_movement.py MWG --limit 10
```

Output gồm:

```text
latest daily movement
latest confirmed swings
movement profile
Point-in-time historical-count mismatches (must be 0)
Future-confirmed swing overlaps with earlier PROVISIONAL rows (informational; may be > 0)
```

Bắt buộc:

```text
Point-in-time historical-count mismatches (must be 0): 0
```

Dòng overlap **có thể lớn hơn 0**:

```text
Future-confirmed swing overlaps with earlier PROVISIONAL rows (informational; may be > 0): N
```

`N > 0` không phải defect nếu point-in-time count mismatch vẫn bằng 0.

Đối với confirmed swing:

```text
PivotStartDate <= PivotEndDate <= ConfirmedAtDate
```

Current leg hợp lệ:

```text
SwingStatus = PROVISIONAL
```

Khi chưa đủ history:

```text
MovementCharacter = INSUFFICIENT_HISTORY
MagnitudeScore = NULL
```

Không đổi NULL thành 0.

---

## 8. Phase 4 — Read-only persisted-contract validation

```powershell
python scripts\validate_price_movement_character.py
```

Validator mở reader/read-only connection và không mutate dữ liệu.

Các metric lỗi bắt buộc bằng 0:

```text
duplicate_daily_keys = 0
duplicate_swing_keys = 0
invalid_swing_rows = 0
invalid_daily_rows = 0
same_direction_repeats = 0
historical_count_mismatch = 0
profile_bound_violations = 0
max_profile_overflow = 0
```

Ngoài ra:
- public daily row count khớp persisted enabled rows;
- public swing row count khớp persisted enabled rows;
- public profile rows tồn tại khi có confirmed swings;
- phải có daily rows và confirmed swing rows.

`historical_count_mismatch = 0` là persisted evidence chính cho point-in-time historical eligibility:

```text
ExpectedCount(D) = min(
    ProfileMaxSwings,
    count(same ticker + same config + same direction + ConfirmedAtDate < D)
)
```

Nếu validator FAIL, dừng. Không chạy full universe.

---

## 9. Phase 5 — Idempotency targeted MWG

Chạy lại:

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
python scripts\validate_price_movement_character.py
python scripts\inspect_price_movement.py MWG --limit 10
```

Expected:
- không duplicate key;
- swing sequence/order ổn định;
- latest date không lùi;
- same source + same config → logic tương đương;
- point-in-time mismatch vẫn 0;
- profile không vượt `ProfileMaxSwings`.

Full targeted rebuild là repair path chuẩn khi source history của ticker bị correction.

---

## 10. Phase 6 — Full historical initload active universe

Chỉ chạy sau Phase 1–5 PASS:

```powershell
python scripts\initload\init_reload_price_movement_character.py
```

Flow trong một caller-owned UoW:

```text
ensure schema + seed
→ ensure bounded profile view
→ full rebuild active tickers
→ historical contract validation
→ COMMIT
→ exportDuckDB_metadata()
```

Nếu calculation/validation fail trước khi ra khỏi UoW:

```text
ROLLBACK
```

Expected cuối command:

```text
Price Movement Character V1 full initload committed;
historical contract validated; DB metadata exported.
```

Sau đó chạy lại validator độc lập:

```powershell
python scripts\validate_price_movement_character.py
```

---

## 11. Phase 7 — Inspect ticker đại diện

```powershell
python scripts\inspect_price_movement.py MWG --limit 15
python scripts\inspect_price_movement.py FPT --limit 15
```

Nên kiểm tra thêm:
- ticker trend mượt;
- ticker biến động mạnh;
- ticker có chuỗi trần/volume thấp;
- ticker ít history.

Price Movement chỉ mô tả price path. Không suy diễn label thành accumulation/distribution/Smart Money intent.

---

## 12. Phase 8 — ATR public contract / fallback

Price Movement không đọc trực tiếp `cal_indicator_values`.

ATR resolve qua:

```text
vw_Indicator_config
+ vw_Ticker_indicators
```

Ưu tiên `ConfigCode = ATR14_D` khi config đó tồn tại/enabled; không hard-code numeric `ConfigId`.

Nếu ATR thiếu:

```text
ThresholdSource = PCT_FALLBACK
QualityStatus   = PARTIAL
ATRNormMagnitude = NULL
```

Đây là degraded-but-explicit behavior.

Inspect fallback:

```sql
SELECT
    ThresholdSource,
    QualityStatus,
    COUNT(*) AS RowCount
FROM "CherryMon"."main"."cal_price_movement_daily"
GROUP BY ThresholdSource, QualityStatus
ORDER BY ThresholdSource, QualityStatus;
```

Nếu fallback bất thường cao, kiểm tra ATR metadata/data trước khi đổi threshold.

---

## 13. Phase 9 — Incremental checkpoint

Sau full initload:

```powershell
python scripts\run_price_movement.py --mode incremental --ticker MWG
python scripts\validate_price_movement_character.py
python scripts\inspect_price_movement.py MWG --limit 10
```

Nếu không có source date mới, rerun phải an toàn và không tạo duplicate.

Incremental semantics:
- resume từ latest persisted `PROVISIONAL` checkpoint;
- giữ prior confirmed swing history;
- chỉ event có `ConfirmedAtDate < current Date` được dùng làm historical knowledge;
- ticker thiếu usable checkpoint → full rebuild thay vì đoán mid-swing state.

Nếu historical OHLC/Indicator data trước checkpoint bị correction:

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
```

---

## 14. Phase 10 — Canonical daily pipeline

```powershell
python run.py
```

Expected order:

```text
AmiBroker/Yahoo/FA/Ticker sync
→ Data Quality
→ Composite Index
→ Trend / Moving Average
→ Technical Indicators
→ Price Movement Character
→ SmartMoneyScore
→ COMMIT
→ export DB metadata
```

Console header:

```text
Sync + DQ + Indicators + Price Movement + SmartMoney
```

Price Movement DQ:

```text
cal_price_movement_daily
key = ConfigId + Ticker + Date
```

Nếu Price Movement DQ FAIL, exception phải propagate và UoW rollback write set.

Sau `run.py`:

```powershell
python scripts\validate_price_movement_character.py
```

---

## 15. Phase 11 — Data Quality audit evidence

```sql
SELECT
    validation_id,
    pipeline,
    table_name,
    status,
    created_at
FROM "CherryMon"."main"."sys_data_quality_audit"
WHERE pipeline = 'Price Movement Character'
ORDER BY created_at DESC
LIMIT 20;
```

Expected latest daily pipeline audit là `PASS` hoặc status phù hợp DataValidation contract hiện hành.

Nếu FAIL, đọc failure detail trước khi rerun unchanged command.

---

## 16. Phase 12 — Public-contract checks

### 12.1 Latest checkpoint

```sql
SELECT
    MAX(Date) AS MovementMaxDate,
    COUNT(DISTINCT Ticker) AS Tickers
FROM "CherryMon"."main"."vw_Ticker_Movement_D";
```

```sql
SELECT MAX(Date) AS OHLCMaxDate
FROM "CherryMon"."main"."vw_Ticker_OHLC_D";
```

Sau successful daily run, latest dates nên cùng trading checkpoint cho active universe hợp lệ.

### 12.2 Profile sample

```sql
SELECT
    Ticker,
    Direction,
    SwingCount,
    MagnitudeMedian,
    MagnitudeP75,
    MagnitudeP90,
    DurationBarsMedian,
    VelocityMedian,
    PersistenceMedian
FROM "CherryMon"."main"."vw_Ticker_Movement_Profile"
WHERE Ticker IN ('MWG', 'FPT')
ORDER BY Ticker, Direction;
```

Profile invariant:

```sql
SELECT COUNT(*) AS ProfileBoundViolations
FROM "CherryMon"."main"."vw_Ticker_Movement_Profile" AS p
INNER JOIN "CherryMon"."main"."dim_price_movement_config" AS c
    ON c.ConfigId = p.ConfigId
WHERE p.SwingCount > c.ProfileMaxSwings;
```

Expected:

```text
ProfileBoundViolations = 0
```

### 12.3 No-look-ahead / point-in-time historical eligibility

Đây là invariant đúng. Không dùng geometric overlap query `PivotEndDate <= D AND ConfirmedAtDate > D` làm failure.

```sql
SELECT COUNT(*) AS InvalidKnowledgeRows
FROM (
    SELECT
        d.ConfigId,
        d.Ticker,
        d.Date,
        d.Direction,
        d.HistoricalSameDirSwingCount AS StoredCount,
        LEAST(c.ProfileMaxSwings, COUNT(s.PivotStartDate)) AS ExpectedCount
    FROM "CherryMon"."main"."cal_price_movement_daily" AS d
    INNER JOIN "CherryMon"."main"."dim_price_movement_config" AS c
        ON c.ConfigId = d.ConfigId
    LEFT JOIN "CherryMon"."main"."cal_price_movement_swing" AS s
        ON s.ConfigId = d.ConfigId
       AND s.Ticker = d.Ticker
       AND s.Direction = d.Direction
       AND s.ConfirmedAtDate < d.Date
    WHERE d.Direction IN ('UP', 'DOWN')
    GROUP BY
        d.ConfigId,
        d.Ticker,
        d.Date,
        d.Direction,
        d.HistoricalSameDirSwingCount,
        c.ProfileMaxSwings
) AS point_in_time
WHERE StoredCount <> ExpectedCount;
```

Expected:

```text
InvalidKnowledgeRows = 0
```

Optional informational query — **không phải failure condition**:

```sql
SELECT COUNT(*) AS FutureConfirmedOverlapRows
FROM "CherryMon"."main"."cal_price_movement_daily" AS d
INNER JOIN "CherryMon"."main"."cal_price_movement_swing" AS s
    ON s.ConfigId = d.ConfigId
   AND s.Ticker = d.Ticker
   AND s.Direction = d.Direction
   AND s.ConfirmedAtDate > d.Date
   AND s.PivotEndDate <= d.Date;
```

`FutureConfirmedOverlapRows > 0` là bình thường khi một provisional leg về sau được xác nhận thành confirmed swing. Nó không chứng minh future event đã được dùng để chấm daily row tại thời điểm D.

---

## 17. Repair / rollback

Một ticker:

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
```

Một nhóm:

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG --ticker FPT
```

Toàn V1:

```powershell
python scripts\initload\init_reload_price_movement_character.py
```

Không DELETE thủ công production tables nếu targeted/full runner có thể repair idempotently.

Schema migration additive. Nếu DDL/seed lỗi, sửa forward migration/script; không hand-edit generated `DB_Metadata.md` để giả physical state.

---

## 18. Evidence gửi TestEngineer

Tối thiểu lưu output:

```powershell
python -m pytest `
  tests\test_price_movement_character.py `
  tests\test_price_movement_runtime.py `
  tests\test_price_movement_pipeline_order.py `
  tests\test_price_movement_profile_contract.py `
  tests\test_sync_write_pipeline_service.py -v
```

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
python scripts\inspect_price_movement.py MWG --limit 10
python scripts\validate_price_movement_character.py
python scripts\initload\init_reload_price_movement_character.py
python scripts\validate_price_movement_character.py
python scripts\run_price_movement.py --mode incremental --ticker MWG
python scripts\inspect_price_movement.py MWG --limit 10
python run.py
python scripts\validate_price_movement_character.py
```

Final independent verdict thuộc `TestEngineer.agent.md`:

```text
PASS | FAIL | BLOCKED | REGRESSION
```
