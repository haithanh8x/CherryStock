# Runbook — Price Movement Character V1 — Validation After PIT Fix

## 1. Mục tiêu

Runbook này là **runbook mới, độc lập** dùng để tiếp tục validation sau khi đã phát hiện false-positive trong no-look-ahead diagnostic cũ.

Không sửa hoặc thay thế runbook đang chạy:

```text
docs/runbook/Price_Movement_Character_V1.md
```

Runbook này giả định trạng thái hiện tại:

```text
Phase 1 focused tests: PASS
Phase 2 targeted MWG full rebuild: PASS
Legacy Phase 3 diagnostic: false-positive do future-confirmed overlap trên PROVISIONAL rows
Engine defect: NOT CONFIRMED
Persisted PIT validator: PASS
```

Mục tiêu tiếp theo:

```text
Pull PIT/profile fixes
→ rerun focused regression
→ inspect MWG bằng diagnostic mới
→ validate persisted PIT contract
→ targeted idempotency
→ full historical initload
→ full-universe validation
→ incremental validation
→ canonical run.py
→ DQ/public contract evidence
→ handoff TestEngineer
```

> Runtime dùng Python scripts kết nối trực tiếp DuckDB qua `DuckDBConnectionFactory` / `DuckDBUnitOfWork`. **Không cần bật MCP DuckDB**.

---

## 2. Contract PIT cần dùng

Price Movement V1 có hai loại fact khác nhau:

```text
cal_price_movement_swing = confirmed swing event history
cal_price_movement_daily = as-of state của active leg theo từng ngày
```

Daily state V1 chỉ có:

```text
PROVISIONAL
TRANSITION
```

Không có daily row `CONFIRMED`.

Một swing có thể có:

```text
PivotEndDate < ConfirmedAtDate
```

Ví dụ:

```text
PivotEndDate      = 2026-08-27
ConfirmedAtDate  = 2026-09-07
```

Daily rows từ pivot đến trước confirmation vẫn hợp lệ là `PROVISIONAL`.

Do đó query:

```text
PivotEndDate <= D
AND ConfirmedAtDate > D
```

**không được dùng làm proof của future knowledge leak**.

Invariant point-in-time đúng là:

```text
HistoricalSameDirSwingCount(D)
=
min(
    ProfileMaxSwings,
    count(
        same ConfigId
        + same Ticker
        + same Direction
        + ConfirmedAtDate < D
    )
)
```

Bất kỳ mismatch nào ở invariant này mới là blocking defect.

---

## 3. Phase A — Đồng bộ fix mới

Từ repository root:

```powershell
cd C:\Github\CherryStock
```

Kiểm tra local changes trước:

```powershell
git status
```

Nếu có file điều tra local như:

```text
scripts\diag_price_movement_no_lookahead.py
```

thì giữ lại nếu cần evidence, nhưng không để nó ảnh hưởng tracked source ngoài ý muốn.

Pull code mới:

```powershell
git pull
```

Kiểm tra HEAD:

```powershell
git log -1 --oneline
```

HEAD phải chứa hoặc mới hơn commit PIT/runbook fixes hiện hành.

---

## 4. Phase B — Focused regression sau fix

Chạy toàn bộ Price Movement focused suite:

```powershell
python -m pytest `
  tests\test_price_movement_character.py `
  tests\test_price_movement_runtime.py `
  tests\test_price_movement_pipeline_order.py `
  tests\test_price_movement_profile_contract.py `
  tests\test_sync_write_pipeline_service.py -v
```

Expected:

```text
PASS
```

Blocking nếu:
- runtime/domain test fail;
- pipeline order sai;
- profile contract fail;
- existing sync service regression.

Không tiếp tục mutation DB nếu Phase B FAIL.

---

## 5. Phase C — Re-apply targeted MWG với bounded profile view

Chạy full targeted rebuild MWG:

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

Runner hiện phải thực hiện:

```text
ensure schema + metadata seed
→ ensure bounded vw_Ticker_Movement_Profile
→ rebuild MWG
→ COMMIT through DuckDBUnitOfWork
```

---

## 6. Phase D — Inspect MWG bằng diagnostic PIT mới

Chạy:

```powershell
python scripts\inspect_price_movement.py MWG --limit 10
```

Expected output có cả hai diagnostic:

```text
Point-in-time historical-count mismatches (must be 0): 0
Future-confirmed swing overlaps with earlier PROVISIONAL rows (informational; may be > 0): N
```

Điều kiện PASS:

```text
Point-in-time historical-count mismatches = 0
```

Dòng overlap có thể:

```text
N > 0
```

và vẫn PASS.

Ngoài ra kiểm tra:

```text
PivotStartDate <= PivotEndDate <= ConfirmedAtDate
```

Daily active leg hợp lệ:

```text
SwingStatus = PROVISIONAL
```

Nếu chưa đủ same-direction history:

```text
MovementCharacter = INSUFFICIENT_HISTORY
MagnitudeScore = NULL
```

Không đổi `NULL` thành `0`.

---

## 7. Phase E — Read-only persisted contract validation

Chạy:

```powershell
python scripts\validate_price_movement_character.py
```

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

Các evidence khác:

```text
public_daily_rows > 0
public_swing_rows > 0
public_profile_rows > 0
```

Điều kiện PIT blocking quan trọng nhất:

```text
historical_count_mismatch = 0
```

Điều kiện profile blocking:

```text
profile_bound_violations = 0
max_profile_overflow = 0
```

Nếu Phase E FAIL, dừng và không chạy full universe.

---

## 8. Phase F — Targeted idempotency MWG

Chạy lần 2:

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
```

Sau đó:

```powershell
python scripts\validate_price_movement_character.py
python scripts\inspect_price_movement.py MWG --limit 10
```

Expected:
- không duplicate;
- swing order/sequence ổn định;
- latest date không lùi;
- PIT mismatch vẫn 0;
- profile vẫn bounded;
- same input/config cho logically equivalent result.

Nếu cần quantitative compare trước/sau, snapshot row count và latest state trước lần rebuild thứ hai.

---

## 9. Phase G — Full historical initload toàn active universe

Chỉ chạy nếu Phase B–F PASS:

```powershell
python scripts\initload\init_reload_price_movement_character.py
```

Expected flow:

```text
schema + seed
→ bounded profile view
→ full rebuild all active tickers
→ historical validation
→ COMMIT
→ exportDuckDB_metadata()
```

Expected cuối command:

```text
Price Movement Character V1 full initload committed;
historical contract validated; DB metadata exported.
```

Nếu validation fail trong UoW:

```text
ROLLBACK
```

Không chạy lại unchanged command nếu cùng lỗi lặp lại.

---

## 10. Phase H — Full-universe validator

Ngay sau full initload:

```powershell
python scripts\validate_price_movement_character.py
```

Bắt buộc vẫn:

```text
historical_count_mismatch = 0
profile_bound_violations = 0
max_profile_overflow = 0
```

Và tất cả duplicate/invalid/repeat metric bằng 0.

---

## 11. Phase I — Inspect ticker đại diện

Chạy ít nhất:

```powershell
python scripts\inspect_price_movement.py MWG --limit 15
python scripts\inspect_price_movement.py FPT --limit 15
```

Nên bổ sung:
- ticker trend mượt;
- ticker biến động lớn;
- ticker chuỗi trần/volume thấp;
- ticker ít history.

Với mỗi ticker, check:

```text
PIT mismatch = 0
profile SwingCount <= ProfileMaxSwings
confirmed swing date ordering hợp lệ
current leg PROVISIONAL nếu đang active
```

Không diễn giải Price Movement label thành Smart Money intent.

---

## 12. Phase J — ATR/fallback evidence

Query:

```sql
SELECT
    ThresholdSource,
    QualityStatus,
    COUNT(*) AS RowCount
FROM "CherryMon"."main"."cal_price_movement_daily"
GROUP BY ThresholdSource, QualityStatus
ORDER BY ThresholdSource, QualityStatus;
```

Expected valid sources:

```text
ATR_PLUS_FLOOR
PCT_FALLBACK
```

Nếu fallback:

```text
ThresholdSource = PCT_FALLBACK
QualityStatus = PARTIAL
ATRNormMagnitude = NULL
```

đây là degraded-but-explicit behavior.

Nếu fallback rate bất thường cao, kiểm tra ATR public contract trước:

```text
vw_Indicator_config
vw_Ticker_indicators
```

Price Movement không được bypass public indicator contract để đọc trực tiếp `cal_indicator_values`.

---

## 13. Phase K — Incremental checkpoint validation

Chạy:

```powershell
python scripts\run_price_movement.py --mode incremental --ticker MWG
```

Sau đó:

```powershell
python scripts\validate_price_movement_character.py
python scripts\inspect_price_movement.py MWG --limit 10
```

Expected nếu không có source date mới:
- rerun safe;
- no duplicate;
- PIT mismatch = 0;
- profile bound = 0 violations.

Incremental contract:

```text
resume latest persisted PROVISIONAL state
+ prior confirmed history
+ historical eligibility uses ConfirmedAtDate < D
```

Nếu source historical data trước checkpoint bị correction, repair bằng:

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
```

---

## 14. Phase L — Canonical daily pipeline

Chạy:

```powershell
python run.py
```

Expected order:

```text
AmiBroker/Yahoo/FA/Ticker
→ DQ
→ Composite Index
→ Trend
→ Technical Indicators
→ Price Movement Character
→ SmartMoneyScore
→ COMMIT
→ export DB metadata
```

Sau `run.py`:

```powershell
python scripts\validate_price_movement_character.py
```

Nếu Price Movement DQ FAIL, transaction phải rollback thay vì commit partial state.

---

## 15. Phase M — Data Quality audit

Query:

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

Expected latest entry tương ứng canonical daily run là `PASS` hoặc status hợp lệ theo DataValidation contract hiện hành.

---

## 16. Phase N — Public profile contract

Kiểm tra bound:

```sql
SELECT
    p.ConfigId,
    p.Ticker,
    p.Direction,
    p.SwingCount,
    c.ProfileMaxSwings
FROM "CherryMon"."main"."vw_Ticker_Movement_Profile" AS p
INNER JOIN "CherryMon"."main"."dim_price_movement_config" AS c
    ON c.ConfigId = p.ConfigId
WHERE p.SwingCount > c.ProfileMaxSwings;
```

Expected:

```text
0 rows
```

Sample:

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
    PersistenceMedian,
    LatestConfirmedAtDate
FROM "CherryMon"."main"."vw_Ticker_Movement_Profile"
WHERE Ticker IN ('MWG', 'FPT')
ORDER BY Ticker, Direction;
```

---

## 17. Phase O — Canonical PIT SQL check

Dùng query này, không dùng geometric overlap query cũ:

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
) AS pit
WHERE StoredCount <> ExpectedCount;
```

Expected:

```text
InvalidKnowledgeRows = 0
```

Đây là canonical persisted proof cho historical eligibility V1.

---

## 18. Repair paths

Một ticker:

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
```

Một nhóm:

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG --ticker FPT
```

Toàn universe:

```powershell
python scripts\initload\init_reload_price_movement_character.py
```

Không DELETE thủ công nếu runner có thể repair idempotently.

---

## 19. Evidence package cho TestEngineer

Lưu output của tối thiểu:

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
```

```powershell
python scripts\initload\init_reload_price_movement_character.py
python scripts\validate_price_movement_character.py
```

```powershell
python scripts\run_price_movement.py --mode incremental --ticker MWG
python run.py
python scripts\validate_price_movement_character.py
```

Evidence bắt buộc phải cho thấy:

```text
historical_count_mismatch = 0
profile_bound_violations = 0
max_profile_overflow = 0
```

Final verdict thuộc TestEngineer:

```text
PASS | FAIL | BLOCKED | REGRESSION
```

---

## 20. Stop conditions

Dừng ngay nếu một trong các điều kiện sau xuất hiện:

```text
focused tests FAIL
historical_count_mismatch > 0
profile_bound_violations > 0
max_profile_overflow > 0
duplicate key > 0
invalid persisted rows > 0
same_direction_repeats > 0
canonical daily UoW commits partial state after blocking failure
```

Không dừng chỉ vì:

```text
Future-confirmed swing overlaps with earlier PROVISIONAL rows > 0
```

nếu canonical PIT mismatch vẫn bằng 0.
