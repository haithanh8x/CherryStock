# Runbook — Price Movement Character V1

## 1. Mục tiêu

Runbook này dùng để kiểm tra local implementation của `REQ-0027` theo thứ tự an toàn:

```text
Focused tests
→ schema/bootstrap
→ targeted MWG full rebuild
→ read-only contract validation
→ inspect/no-look-ahead
→ full historical initload
→ rerun/idempotency
→ incremental checkpoint
→ canonical run.py
→ metadata / audit evidence
```

Implementation state trước khi TestEngineer xác nhận độc lập:

```text
IMPLEMENTED_PENDING_VALIDATION
```

Không coi developer run thành final PASS.

---

## 2. Files chính

```text
docs/architecture/Price_Movement_Character.md
src/DuckDB/sql/price_movement_character_v1_schema.sql
src/calcEngine/priceMovementCharacter.py
src/cherrystock/domain/analytics/price_movement/
src/cherrystock/infrastructure/database/repositories/price_movement_repository.py
src/cherrystock/infrastructure/database/price_movement_validation.py
scripts/run_price_movement.py
scripts/inspect_price_movement.py
scripts/validate_price_movement_character.py
scripts/initload/init_reload_price_movement_character.py
tests/test_price_movement_character.py
tests/test_price_movement_pipeline_order.py
```

Public contracts:

```text
vw_Ticker_Movement_Swings
vw_Ticker_Movement_D
vw_Ticker_Movement_Profile
```

---

## 3. Phase 0 — Đồng bộ code và kiểm tra môi trường

Từ repository root:

```powershell
cd C:\Github\CherryStock
```

```powershell
git status
```

Nếu working tree có thay đổi local cần giữ lại, commit/stash trước khi pull.

```powershell
git pull
```

Kiểm tra Python:

```powershell
python --version
```

Expected: Python `3.13.x`.

Kiểm tra package quan trọng:

```powershell
python -c "import duckdb, pandas, numpy; print('duckdb=', duckdb.__version__, 'pandas=', pandas.__version__, 'numpy=', numpy.__version__)"
```

Nếu thiếu dependency trong virtualenv hiện tại:

```powershell
python -m pip install -e ".[dev]"
```

Không hard-code DB path. Runtime lấy `LOCAL_DB_PATH` / CherryStock settings như các pipeline khác.

---

## 4. Phase 1 — Focused unit tests trước khi ghi DuckDB

Chạy pure domain tests:

```powershell
python -m pytest tests\test_price_movement_character.py -v
```

Expected:

```text
4 passed
```

Các invariant được test:
- `PivotEndDate < ConfirmedAtDate` khi reversal được xác nhận sau pivot;
- smooth path có persistence evidence tốt hơn noisy path;
- same-direction history sinh riêng Magnitude/Velocity/Persistence scores;
- thiếu history trả `INSUFFICIENT_HISTORY`, không ép score về 0.

Chạy pipeline-order test:

```powershell
python -m pytest tests\test_price_movement_pipeline_order.py -v
```

Expected: PASS và order:

```text
Technical Indicators
→ Price Movement Character
→ SmartMoneyScore
```

Chạy regression test của canonical write service:

```powershell
python -m pytest tests\test_sync_write_pipeline_service.py -v
```

Expected: existing tests vẫn PASS. Legacy/mock caller không truyền `price_movement_repository` vẫn được giữ backward-compatible.

Có thể chạy cả ba file cùng lúc:

```powershell
python -m pytest tests\test_price_movement_character.py tests\test_price_movement_pipeline_order.py tests\test_sync_write_pipeline_service.py -v
```

Nếu test fail, dừng tại đây. Không chạy migration/initload trên DB thật cho tới khi nguyên nhân được sửa.

---

## 5. Phase 2 — Smoke test targeted trên MWG

Mục tiêu: tạo schema + seed config và rebuild toàn lịch sử **chỉ MWG** trước khi chạy toàn universe.

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
```

Expected summary có dạng:

```text
status = OK
mode = full
tickers_processed = 1
tickers_rebuilt = 1
daily_rows_upserted > 0
swing_rows_upserted > 0
```

Lưu ý: command này chạy trong `DuckDBUnitOfWork`. Nếu exception xảy ra trước commit, schema/data writes trong transaction hiện tại rollback theo UoW.

---

## 6. Phase 3 — Inspect MWG và no-look-ahead

```powershell
python scripts\inspect_price_movement.py MWG --limit 10
```

Kiểm tra ba phần:

```text
latest daily movement
latest confirmed swings
movement profile
```

Dòng cuối bắt buộc:

```text
No-look-ahead diagnostic rows (must be 0): 0
```

Đối với confirmed swing, kiểm tra trực quan:

```text
PivotStartDate <= PivotEndDate <= ConfirmedAtDate
```

`PivotEndDate` là ngày cực trị; `ConfirmedAtDate` là ngày reversal khiến cực trị trở nên knowable.

Current leg phải có:

```text
SwingStatus = PROVISIONAL
```

Khi history chưa đủ 8 swing cùng hướng, đây là kết quả hợp lệ:

```text
MovementCharacter = INSUFFICIENT_HISTORY
MagnitudeScore = NULL
```

Không sửa NULL thành 0.

---

## 7. Phase 4 — Read-only persisted-contract validation

Sau smoke MWG:

```powershell
python scripts\validate_price_movement_character.py
```

Validator mở DuckDB bằng reader/read-only connection và không mutate dữ liệu.

Bắt buộc các metric lỗi bằng 0:

```text
duplicate_daily_keys = 0
duplicate_swing_keys = 0
invalid_swing_rows = 0
invalid_daily_rows = 0
same_direction_repeats = 0
historical_count_mismatch = 0
```

Ngoài ra:
- public daily row count khớp persisted enabled rows;
- public swing row count khớp persisted enabled rows;
- phải có daily rows và confirmed swing rows.

Nếu validator FAIL, dừng. Không chạy full all-ticker.

---

## 8. Phase 5 — Idempotency targeted MWG

Chạy lại full rebuild MWG:

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
```

Sau đó:

```powershell
python scripts\validate_price_movement_character.py
```

Và inspect lại:

```powershell
python scripts\inspect_price_movement.py MWG --limit 10
```

Expected:
- không duplicate key;
- swing sequence/order ổn định;
- latest date không lùi;
- cùng source + config cho kết quả logic tương đương.

Full targeted rebuild là repair path chuẩn khi source history của ticker đã bị chỉnh sửa.

---

## 9. Phase 6 — Full historical initload toàn active universe

Chỉ chạy sau khi Phase 1–5 PASS.

```powershell
python scripts\initload\init_reload_price_movement_character.py
```

Script thực hiện trong **một caller-owned UoW**:

```text
ensure schema + seed
→ full rebuild active tickers
→ historical contract validation
→ COMMIT
→ exportDuckDB_metadata()
```

Nếu calculation hoặc validation fail trước khi ra khỏi UoW:

```text
ROLLBACK
```

Sau commit thành công, script mới export DB metadata.

Expected cuối command:

```text
Price Movement Character V1 full initload committed;
historical contract validated; DB metadata exported.
```

Sau đó chạy validator độc lập lần nữa:

```powershell
python scripts\validate_price_movement_character.py
```

---

## 10. Phase 7 — Kiểm tra một số ticker đại diện

MWG:

```powershell
python scripts\inspect_price_movement.py MWG --limit 15
```

FPT:

```powershell
python scripts\inspect_price_movement.py FPT --limit 15
```

Có thể chọn thêm:
- một ticker trend mượt;
- một ticker biến động mạnh;
- một ticker có chuỗi trần/volume thấp;
- một ticker ít history.

Price Movement chỉ mô tả price path. Không diễn giải label này thành accumulation/distribution/Smart Money intent.

---

## 11. Phase 8 — Kiểm tra ATR public contract / fallback

Price Movement không đọc trực tiếp `cal_indicator_values`.

ATR được resolve qua:

```text
vw_Indicator_config
+ vw_Ticker_indicators
```

Ưu tiên `ConfigCode = ATR14_D` khi config đó tồn tại/enabled; không hard-code numeric `ConfigId`.

Nếu ATR thiếu tại một bar hợp lệ:

```text
ThresholdSource = PCT_FALLBACK
QualityStatus   = PARTIAL
ATRNormMagnitude = NULL
```

Điều này là degraded-but-explicit behavior, không phải pipeline crash.

Có thể inspect số fallback trên VS Code DuckDB extension:

```sql
SELECT
    ThresholdSource,
    QualityStatus,
    COUNT(*) AS RowCount
FROM "CherryMon"."main"."cal_price_movement_daily"
GROUP BY ThresholdSource, QualityStatus
ORDER BY ThresholdSource, QualityStatus;
```

Nếu fallback bất thường cao, kiểm tra ATR metadata/data trước khi thay đổi Price Movement threshold.

---

## 12. Phase 9 — Incremental checkpoint test

Sau full initload, chạy incremental cho MWG:

```powershell
python scripts\run_price_movement.py --mode incremental --ticker MWG
```

Nếu không có source date mới, command phải rerun an toàn và không tạo duplicate.

Sau đó:

```powershell
python scripts\validate_price_movement_character.py
```

Incremental semantics:
- resume từ latest persisted `PROVISIONAL` checkpoint;
- giữ prior confirmed swing history để chấm percentile;
- chỉ event có `ConfirmedAtDate < current Date` được dùng làm historical knowledge;
- nếu ticker không có usable checkpoint, ticker đó full rebuild thay vì đoán state giữa swing.

Nếu historical OHLC hoặc Indicator data cũ bị correction trước checkpoint, dùng targeted full rebuild:

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
```

---

## 13. Phase 10 — Canonical daily pipeline `run.py`

Khi initload + validator đã PASS, chạy canonical daily:

```powershell
python run.py
```

Expected order trong write transaction:

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

Console header phải có:

```text
Sync + DQ + Indicators + Price Movement + SmartMoney
```

Price Movement DQ chạy trên:

```text
cal_price_movement_daily
key = ConfigId + Ticker + Date
```

Nếu Price Movement DQ FAIL, exception phải propagate lên `run.py`; UoW rollback write set thay vì commit partial daily state.

Sau `run.py`:

```powershell
python scripts\validate_price_movement_character.py
```

---

## 14. Phase 11 — Data Quality audit evidence

Trên VS Code DuckDB extension:

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

Expected daily pipeline audit gần nhất là `PASS` hoặc status phù hợp contract DataValidation hiện hành.

Nếu audit FAIL, đọc chi tiết failure trước khi rerun unchanged command.

---

## 15. Phase 12 — Public-contract checks

Daily latest dates:

```sql
SELECT
    MAX(Date) AS MovementMaxDate,
    COUNT(DISTINCT Ticker) AS Tickers
FROM "CherryMon"."main"."vw_Ticker_Movement_D";
```

OHLC latest date:

```sql
SELECT MAX(Date) AS OHLCMaxDate
FROM "CherryMon"."main"."vw_Ticker_OHLC_D";
```

Sau successful daily run, hai latest dates nên cùng trading checkpoint cho active universe hợp lệ.

Profile sample:

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

No-look-ahead invariant:

```sql
SELECT COUNT(*) AS InvalidKnowledgeRows
FROM "CherryMon"."main"."cal_price_movement_daily" AS d
INNER JOIN "CherryMon"."main"."cal_price_movement_swing" AS s
    ON s.ConfigId = d.ConfigId
   AND s.Ticker = d.Ticker
   AND s.Direction = d.Direction
   AND s.ConfirmedAtDate > d.Date
   AND s.PivotEndDate <= d.Date;
```

Expected:

```text
InvalidKnowledgeRows = 0
```

---

## 16. Repair / rollback procedure

### Một ticker sai hoặc source được correction

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
```

### Một nhóm ticker

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG --ticker FPT
```

### Toàn bộ Price Movement V1 cần rebuild

```powershell
python scripts\initload\init_reload_price_movement_character.py
```

Không DELETE thủ công production tables để “reset” nếu targeted/full runner có thể repair idempotently.

Schema migration là additive. Nếu DDL/seed có lỗi, sửa forward migration/script; không hand-edit generated `DB_Metadata.md` để giả lập physical state.

---

## 17. Evidence cần gửi lại cho TestEngineer

Tối thiểu lưu output của:

```powershell
python -m pytest tests\test_price_movement_character.py tests\test_price_movement_pipeline_order.py tests\test_sync_write_pipeline_service.py -v
```

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
```

```powershell
python scripts\inspect_price_movement.py MWG --limit 10
```

```powershell
python scripts\initload\init_reload_price_movement_character.py
```

```powershell
python scripts\validate_price_movement_character.py
```

```powershell
python scripts\run_price_movement.py --mode incremental --ticker MWG
```

```powershell
python run.py
```

Final independent verdict thuộc `TestEngineer.agent.md`:

```text
PASS | FAIL | BLOCKED | REGRESSION
```
