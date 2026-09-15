# Runbook — Price Movement Character V1

## 1. Mục tiêu

Runbook này dùng để kiểm tra local implementation của `REQ-0027` theo thứ tự an toàn và **có thể resume từ checkpoint đã PASS** thay vì bắt buộc chạy lại từ đầu.

```text
Focused tests
→ targeted MWG full rebuild
→ inspect point-in-time semantics
→ read-only contract validation
→ idempotency
→ full historical initload
→ representative ticker checks
→ ATR/source-quality checks
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

> **Runtime note:** Runbook chạy bằng Python scripts kết nối trực tiếp DuckDB qua `DuckDBConnectionFactory` / `DuckDBUnitOfWork`. Không cần bật MCP DuckDB. Nếu gặp DB lock, tắt MCP/process khác đang giữ writer connection.

---

## 2. Resume policy

### 2.1 Nguyên tắc

Không cần chạy lại các phase đã PASS nếu:

- evidence/output của phase đó còn giữ;
- code thay đổi sau checkpoint **không ảnh hưởng contract của phase đã PASS**;
- phase fail trước đó đã rollback transaction hoàn toàn;
- trước khi resume đã chạy regression tests trực tiếp liên quan tới fix mới.

Nếu một fix thay đổi segmentation/scoring/PIT semantics, phải quay lại tối thiểu Phase 1–5.

Nếu fix chỉ thay đổi source-quality guard để tránh crash do OHLC invalid, có thể resume từ Phase 6 sau khi chạy **Resume Gate R1–R3** bên dưới.

### 2.2 Checkpoint hiện tại sau lỗi Phase 6

Evidence local đã có:

```text
Phase 1 — focused tests                  PASS
Phase 2 — targeted MWG full rebuild      PASS
Phase 3 — PIT inspect                    PASS sau khi sửa false-positive diagnostic
Phase 4 — persisted contract validator   PASS
Phase 5 — MWG idempotency                PASS
Phase 6 — full historical initload       FAIL trước fix source-quality
```

Failure Phase 6 trước đó:

```text
ZeroDivisionError: float division by zero
```

UoW đã rollback nên không có partial full-universe state cần cleanup thủ công.

Sau failure này, Price Movement runtime đã có source-quality guard:

```text
High/Low/Close <= 0 hoặc non-finite
    → bar không hợp lệ cho calculation
    → drop khỏi segmentation/features
    → ticker/source được đánh dấu degraded
    → output còn lại QualityStatus = PARTIAL
    → không crash toàn universe

Open <= 0 nhưng High/Low/Close hợp lệ
    → giữ bar vì V1 không dùng Open để segmentation
    → source vẫn được đánh dấu degraded/PARTIAL
```

**Không coi `Open = 0` đơn lẻ là nguyên nhân trực tiếp của divide-by-zero.** V1 dùng High/Low/Close cho price ratios và logarithms.

### 2.3 Resume shortcut

Nếu đang resume đúng checkpoint trên, **không cần chạy lại Phase 1–5 đầy đủ**. Chạy:

```text
Resume Gate R0
→ Resume Gate R1
→ Resume Gate R2
→ Resume Gate R3
→ Phase 6
→ Phase 7 ... Phase 12
```

---

## 3. Files chính

```text
docs/architecture/Price_Movement_Character.md
src/DuckDB/sql/price_movement_character_v1_schema.sql
src/DuckDB/sql/price_movement_character_v1_profile_view.sql
src/calcEngine/priceMovementCharacter.py
src/cherrystock/domain/analytics/price_movement/engine.py
src/cherrystock/domain/analytics/price_movement/runtime.py
src/cherrystock/domain/analytics/price_movement/source_quality.py
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

## 4. Point-in-time contract

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

No-look-ahead invariant đúng:

```text
Daily row tại ngày D chỉ được dùng historical swings có ConfirmedAtDate < D.
```

Evidence persisted:

```text
HistoricalSameDirSwingCount(D)
=
min(
    ProfileMaxSwings,
    count(same ConfigId + Ticker + Direction + ConfirmedAtDate < D)
)
```

Query kiểu:

```text
PivotEndDate <= D AND ConfirmedAtDate > D
```

chỉ thể hiện future-confirmed swing overlap với provisional history và **không tự động là knowledge leak**.

---

# RESUME GATES

## R0 — Đồng bộ Git trước khi resume

```powershell
cd C:\Github\CherryStock
git status
git pull
```

Nếu có rebase đang dở:

```powershell
git status
```

Nếu Git báo:

```text
all conflicts fixed: run "git rebase --continue"
```

thì hoàn tất:

```powershell
git -c core.editor=true rebase --continue
```

Không chạy nested rebase / `git_auto_sync.ps1` khi rebase hiện tại chưa kết thúc.

Expected trước khi test:

```text
working tree không có unresolved conflict
không có rebase/merge/cherry-pick đang in progress
```

---

## R1 — Regression test cho source-quality fix

Bắt buộc chạy sau fix zero/non-positive price:

```powershell
python -m pytest tests\test_price_movement_runtime.py -v
```

Test phải cover ít nhất:

```text
valid runtime == reference semantics
Low/High/Close <= 0 → invalid calculation bar được drop, không crash
Open = 0 only → bar vẫn được giữ, source đánh dấu PARTIAL
```

Expected: tất cả test trong file PASS.

Nếu FAIL: dừng, không rerun Phase 6.

---

## R2 — Recheck MWG contract sau code change

Không cần full Phase 1–5, nhưng chạy lightweight regression:

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
python scripts\inspect_price_movement.py MWG --limit 10
python scripts\validate_price_movement_character.py
```

Bắt buộc:

```text
Point-in-time historical-count mismatches (must be 0): 0
historical_count_mismatch = 0
profile_bound_violations = 0
max_profile_overflow = 0
```

`Future-confirmed swing overlaps ...` có thể > 0 và chỉ là informational.

---

## R3 — Kiểm tra ticker/source xấu trước full initload

Nếu đã biết ticker có historical bad OHLC, chạy targeted smoke trên 1–3 ticker đại diện, ví dụ:

```powershell
python scripts\run_price_movement.py --mode full --ticker VNX
python scripts\run_price_movement.py --mode full --ticker PTG
```

Expected:

```text
status = OK
không ZeroDivisionError
source_quality_status có thể = PARTIAL
invalid_ohlc_rows có thể > 0
invalid_calculation_rows_dropped có thể > 0
open_only_invalid_rows_retained có thể > 0
```

Các counter source-quality trong refresh summary:

```text
source_quality_status
source_rows
invalid_ohlc_rows
invalid_calculation_rows_dropped
open_only_invalid_rows_retained
degraded_tickers
tickers_without_usable_price_rows
```

Ý nghĩa:

```text
invalid_ohlc_rows
    = bất kỳ Open/High/Low/Close invalid/non-positive

invalid_calculation_rows_dropped
    = High/Low/Close invalid nên không thể tham gia calculation

open_only_invalid_rows_retained
    = chỉ Open invalid nhưng High/Low/Close dùng được; bar được giữ

degraded_tickers
    = số ticker có source-quality degradation

tickers_without_usable_price_rows
    = ticker không còn bất kỳ High/Low/Close bar hợp lệ nào
```

`degraded_tickers > 0` không tự động FAIL.

`tickers_without_usable_price_rows > 0` cần lưu evidence và TestEngineer review; không được silently coi đó là ticker có calculation đầy đủ.

Sau targeted bad-source smoke:

```powershell
python scripts\validate_price_movement_character.py
```

Nếu PASS, chuyển sang Phase 6.

---

# FULL RUNBOOK

## Phase 0 — Environment

Nếu chạy từ đầu:

```powershell
cd C:\Github\CherryStock
git status
git pull
python --version
python -c "import duckdb, pandas, numpy; print('duckdb=', duckdb.__version__, 'pandas=', pandas.__version__, 'numpy=', numpy.__version__)"
```

Expected Python `3.13.x`.

Không hard-code DB path. Runtime dùng CherryStock settings / `LOCAL_DB_PATH`.

---

## Phase 1 — Focused tests

```powershell
python -m pytest `
  tests\test_price_movement_character.py `
  tests\test_price_movement_runtime.py `
  tests\test_price_movement_pipeline_order.py `
  tests\test_price_movement_profile_contract.py `
  tests\test_sync_write_pipeline_service.py -v
```

Expected: tất cả PASS.

Nếu fail, dừng trước khi mutate DB thật.

---

## Phase 2 — Smoke targeted MWG

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
```

Expected:

```text
status = OK
mode = full
tickers_processed = 1
tickers_rebuilt = 1
daily_rows_upserted > 0
swing_rows_upserted > 0
```

Runner:

```text
schema + seed
→ bounded profile view
→ full rebuild MWG
→ commit qua DuckDBUnitOfWork
```

---

## Phase 3 — Inspect MWG + PIT semantics

```powershell
python scripts\inspect_price_movement.py MWG --limit 10
```

Bắt buộc:

```text
Point-in-time historical-count mismatches (must be 0): 0
```

Informational, có thể > 0:

```text
Future-confirmed swing overlaps with earlier PROVISIONAL rows: N
```

Confirmed event:

```text
PivotStartDate <= PivotEndDate <= ConfirmedAtDate
```

Current leg:

```text
SwingStatus = PROVISIONAL
```

Thiếu history hợp lệ:

```text
MovementCharacter = INSUFFICIENT_HISTORY
MagnitudeScore = NULL
```

---

## Phase 4 — Persisted-contract validator

```powershell
python scripts\validate_price_movement_character.py
```

Bắt buộc bằng 0:

```text
duplicate_daily_keys
 duplicate_swing_keys
invalid_swing_rows
invalid_daily_rows
same_direction_repeats
historical_count_mismatch
profile_bound_violations
max_profile_overflow
```

Validator là read-only.

---

## Phase 5 — Idempotency targeted MWG

```powershell
python scripts\run_price_movement.py --mode full --ticker MWG
python scripts\validate_price_movement_character.py
python scripts\inspect_price_movement.py MWG --limit 10
```

Expected:

- không duplicate;
- swing order ổn định;
- latest date không lùi;
- PIT mismatch = 0;
- profile không vượt `ProfileMaxSwings`.

---

## Phase 6 — Full historical initload active universe

### 6.1 Khi chạy từ đầu

Chỉ chạy sau Phase 1–5 PASS.

### 6.2 Khi resume sau zero-price failure

Nếu Phase 1–5 đã PASS trước đó và Phase 6 fail do `ZeroDivisionError`, không cần rerun toàn Phase 1–5; phải PASS **R0–R3** rồi chạy tiếp tại đây.

### 6.3 Command

```powershell
python scripts\initload\init_reload_price_movement_character.py
```

Flow:

```text
ensure schema + seed
→ ensure bounded profile view
→ full rebuild active tickers
→ source-quality degradation handled explicitly
→ historical contract validation
→ COMMIT
→ exportDuckDB_metadata()
```

Nếu calculation hoặc validation fail trước khi UoW đóng:

```text
ROLLBACK
```

Do đó sau failed attempt **không DELETE thủ công Price Movement tables** trước khi rerun.

### 6.4 Expected success

```text
Price Movement Character V1 full initload committed;
historical contract validated; DB metadata exported.
```

Refresh summary có thể cho thấy:

```text
source_quality_status = PARTIAL
invalid_ohlc_rows > 0
invalid_calculation_rows_dropped > 0
open_only_invalid_rows_retained > 0
degraded_tickers > 0
```

Các giá trị > 0 này phản ánh historical source degradation, không phải automatic pipeline failure.

Tuy nhiên:

```text
tickers_without_usable_price_rows > 0
```

phải được ghi lại làm evidence và review riêng.

Sau initload:

```powershell
python scripts\validate_price_movement_character.py
```

Nếu validator FAIL: dừng tại Phase 6.

---

## Phase 7 — Inspect representative tickers

```powershell
python scripts\inspect_price_movement.py MWG --limit 15
python scripts\inspect_price_movement.py FPT --limit 15
python scripts\inspect_price_movement.py VNX --limit 15
python scripts\inspect_price_movement.py PTG --limit 15
```

Mục tiêu:

- MWG/FPT: normal source cases;
- VNX/PTG: known degraded historical-source examples;
- xác nhận bad source không làm pipeline crash;
- degraded output được explicit bằng `QualityStatus = PARTIAL` khi applicable.

Price Movement chỉ mô tả price path; không suy diễn thành Smart Money intent.

---

## Phase 8 — ATR + source-quality contract

ATR resolve qua:

```text
vw_Indicator_config
+ vw_Ticker_indicators
```

Không đọc trực tiếp `cal_indicator_values`.

ATR missing/invalid:

```text
ThresholdSource = PCT_FALLBACK
QualityStatus = PARTIAL
ATRNormMagnitude = NULL
```

Price invalid contract:

```text
High/Low/Close invalid hoặc <= 0
→ drop calculation bar
→ PARTIAL source quality

Open invalid hoặc <= 0 only
→ retain bar
→ PARTIAL source quality
```

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

Optional inspect bad raw OHLC:

```sql
SELECT
    Ticker,
    COUNT(*) AS BadCalculationRows
FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
WHERE High IS NULL OR Low IS NULL OR Close IS NULL
   OR High <= 0 OR Low <= 0 OR Close <= 0
GROUP BY Ticker
ORDER BY BadCalculationRows DESC, Ticker;
```

---

## Phase 9 — Incremental checkpoint

Sau full initload PASS:

```powershell
python scripts\run_price_movement.py --mode incremental --ticker MWG
python scripts\validate_price_movement_character.py
python scripts\inspect_price_movement.py MWG --limit 10
```

Incremental semantics:

- resume latest persisted `PROVISIONAL` checkpoint;
- giữ prior confirmed history;
- chỉ `ConfirmedAtDate < current Date` được dùng làm historical knowledge;
- thiếu usable checkpoint → targeted full rebuild;
- historical source correction trước checkpoint → targeted full rebuild.

---

## Phase 10 — Canonical daily pipeline

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

Sau run:

```powershell
python scripts\validate_price_movement_character.py
```

Nếu Price Movement DQ/calculation fail, exception phải propagate và UoW rollback write set.

---

## Phase 11 — Data Quality audit

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

Expected latest audit là `PASS` hoặc status phù hợp DataValidation contract hiện hành.

---

## Phase 12 — Public-contract checks

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

### 12.2 Profile bound

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

### 12.3 PIT historical eligibility

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

---

## 13. Repair / rollback

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

---

## 14. Evidence gửi TestEngineer

### Khi chạy từ đầu

Lưu output Phase 1–12.

### Khi resume sau Phase 6 zero-price failure

Tối thiểu lưu:

```powershell
# Resume regression
python -m pytest tests\test_price_movement_runtime.py -v

# Lightweight contract recheck
python scripts\run_price_movement.py --mode full --ticker MWG
python scripts\inspect_price_movement.py MWG --limit 10
python scripts\validate_price_movement_character.py

# Known degraded-source smoke
python scripts\run_price_movement.py --mode full --ticker VNX
python scripts\run_price_movement.py --mode full --ticker PTG
python scripts\validate_price_movement_character.py

# Resume Phase 6
python scripts\initload\init_reload_price_movement_character.py
python scripts\validate_price_movement_character.py

# Continue
python scripts\run_price_movement.py --mode incremental --ticker MWG
python run.py
python scripts\validate_price_movement_character.py
```

Final independent verdict thuộc `TestEngineer.agent.md`:

```text
PASS | FAIL | BLOCKED | REGRESSION
```
