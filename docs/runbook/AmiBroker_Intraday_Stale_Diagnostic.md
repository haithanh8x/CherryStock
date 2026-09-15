# AmiBroker Intraday Stale Diagnostic Runbook

- **Status:** ACTIVE
- **Objective:** xác định hữu hạn nguyên nhân khi daily pipeline FAIL vì một bảng AmiBroker Intraday có `max_date < expected_date`.
- **Primary owner:** Test Engineer
- **Skill:** `.github/skills/data-quality-validation/SKILL.md`
- **Daily orchestrator:** `src/cherrystock/application/services/sync_write_pipeline.py`
- **Production loader:** `src/CrawlStock/readAmi.py`
- **Trading calendar:** `"CherryMon"."main"."dimCalendar"`

## 1. Trigger

Dùng runbook này khi `python run.py` dừng với lỗi dạng:

```text
[DataValidation][AUDIT] ... | pipeline=AmiBroker Intraday Futures | ... | status=FAIL
RuntimeError: Data quality validation failed for '"CherryMon"."main"."raw_futures_intraday"':
Data is stale: max_date=YYYY-MM-DD, expected_date=YYYY-MM-DD.
```

Runbook áp dụng tương tự cho:

```text
raw_futures_intraday
raw_index_intraday
raw_stock_intraday
raw_warrant_intraday
```

Không dùng runbook này để nới lỏng Data Quality, đổi trading calendar hoặc bỏ `raise_on_fail=True`.

---

## 2. Quality contract

AmiBroker Intraday hiện có bốn source/target:

| Source folder | DuckDB target |
|---|---|
| `Intraday/futures` | `raw_futures_intraday` |
| `Intraday/index` | `raw_index_intraday` |
| `Intraday/stock` | `raw_stock_intraday` |
| `Intraday/warrant` | `raw_warrant_intraday` |

Logical key:

```text
Ticker + Date + RawTime + TickSeq
```

Required fields của daily DQ:

```text
Ticker
Date
DateTime
RawTime
TickSeq
Close
Volume
```

Freshness contract:

```text
max(Date) của target == latest trading date từ dimCalendar
```

Nếu `max(Date) < expected trading date`, validation phải FAIL.

---

## 3. Scope

### In scope

- xác định `expected_date` từ `dimCalendar`;
- so sánh max date của cả bốn intraday tables;
- kiểm tra source folder của domain bị stale;
- kiểm tra `LastWriteTime` của `.dat`;
- đọc trực tiếp `.dat` bằng production parser để xác định source max date;
- phân loại lỗi thành source stale, ingestion stale hoặc calendar/scheduling issue;
- xác nhận lại sau khi source đã được refresh.

### Out of scope

- sửa parser;
- đổi schema;
- đổi Data Quality thresholds;
- tự sửa `dimCalendar`;
- disable validation;
- xóa dữ liệu để ép reload;
- điều tra domain khác sau khi current hypothesis đã có verdict.

---

## 4. Preconditions

Chạy từ repository root:

```powershell
cd C:\Github\CherryStock
git status --short
python --version
```

Xác nhận production settings đọc được:

```powershell
python -c "from cherrystock.config.settings import settings; print('DB=', settings.local_db_path); print('Intraday=', settings.amibroker_intraday_path)"
```

Nếu import/config FAIL: verdict `BLOCKED`, lưu exact error và **STOP**.

---

## 5. Step 1 — xác định expected trading date và trạng thái bốn target

Chạy trong DuckDB Extension:

```sql
WITH expected AS (
    SELECT MAX(CAST(FullDate AS DATE)) AS expected_date
    FROM "CherryMon"."main"."dimCalendar"
    WHERE IsHoliday = 'N'
      AND CAST(FullDate AS DATE) <= CURRENT_DATE
), intraday AS (
    SELECT 'futures' AS source, MAX(Date) AS max_date, COUNT(*) AS total_rows
    FROM "CherryMon"."main"."raw_futures_intraday"

    UNION ALL

    SELECT 'index', MAX(Date), COUNT(*)
    FROM "CherryMon"."main"."raw_index_intraday"

    UNION ALL

    SELECT 'stock', MAX(Date), COUNT(*)
    FROM "CherryMon"."main"."raw_stock_intraday"

    UNION ALL

    SELECT 'warrant', MAX(Date), COUNT(*)
    FROM "CherryMon"."main"."raw_warrant_intraday"
)
SELECT
    i.source,
    e.expected_date,
    i.max_date,
    date_diff('day', i.max_date, e.expected_date) AS lag_days,
    i.total_rows
FROM intraday i
CROSS JOIN expected e
ORDER BY i.source;
```

### PASS branch

Nếu tất cả:

```text
max_date = expected_date
```

thì current stale condition không còn tồn tại.

Action: `PASS / STOP`.

### FAIL branch

Nếu một hoặc nhiều table có:

```text
max_date < expected_date
```

chỉ tiếp tục với **domain đầu tiên đang stale**. Không mở nhiều hypothesis song song.

Ví dụ:

```text
futures  expected=2026-09-15  max=2026-09-14
```

→ tiếp tục Step 2 với `futures`.

---

## 6. Step 2 — kiểm tra source folder thực tế

Ví dụ domain `futures`.

Lấy path từ production settings, không hard-code path riêng:

```powershell
$root = python -c "from cherrystock.config.settings import settings; print(settings.amibroker_intraday_path / 'futures')"
$root
```

Kiểm tra file `.dat` mới nhất:

```powershell
Get-ChildItem $root -Recurse -Filter *.dat |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 20 FullName, Length, LastWriteTime
```

### Evidence interpretation

Nếu tất cả file gần nhất vẫn có `LastWriteTime` trước expected trading date, đây là bằng chứng source có khả năng chưa refresh.

`LastWriteTime` chỉ là tín hiệu filesystem, chưa phải kết luận cuối. Tiếp tục Step 3 để đọc ngày thực tế bên trong `.dat`.

Nếu folder không tồn tại hoặc không có `.dat`: verdict `BLOCKED`, ghi path và **STOP**.

---

## 7. Step 3 — đọc trực tiếp `.dat` bằng production parser

Không viết parser chẩn đoán riêng. Dùng đúng `read_amibroker_intraday_dat()` của production.

Cho `futures`:

```powershell
@'
from cherrystock.config.settings import settings
from CrawlStock.readAmi import _list_intraday_dat_files, read_amibroker_intraday_dat

folder = settings.amibroker_intraday_path / "futures"
files = _list_intraday_dat_files(folder)

print(f"folder={folder}")
print(f"files={len(files)}")

rows = []
for path in files:
    df = read_amibroker_intraday_dat(path)
    if df is None or df.empty:
        continue
    rows.append((path.stem, df["Date"].max(), len(df), path.stat().st_mtime))

rows.sort(key=lambda x: (x[1], x[0]), reverse=True)

for row in rows[:20]:
    print(row)

source_max_date = max((row[1] for row in rows), default=None)
print(f"SOURCE_MAX_DATE={source_max_date}")
'@ | python -
```

Đổi `"futures"` thành `"index"`, `"stock"` hoặc `"warrant"` chỉ khi domain stale tương ứng là target của current diagnostic.

---

## 8. Verdict branches

### Branch A — source `.dat` cũng stale

Evidence:

```text
expected_date   = 2026-09-15
DB max_date     = 2026-09-14
SOURCE_MAX_DATE = 2026-09-14
```

Kết luận:

```text
AmiBroker/FireAnt source has not produced/refreshed the expected trading date.
```

Verdict: `FAIL` nếu source lẽ ra phải có data tại thời điểm chạy; hoặc `BLOCKED` nếu đang nằm trước source publication/refresh window.

Action:

1. refresh/download Intraday data trong FireAnt/AmiBroker theo operational procedure của source;
2. không sửa validator;
3. sau khi source đã có expected date, chạy Step 10;
4. **STOP** current diagnostic.

Không đổi `expected_date` thành `MAX(Date)` của source chỉ để pass.

---

### Branch B — source current nhưng DuckDB stale

Evidence:

```text
expected_date   = 2026-09-15
DB max_date     = 2026-09-14
SOURCE_MAX_DATE = 2026-09-15
```

Kết luận: source đã có data mới nhưng ingestion/upsert không đưa data vào target.

Verdict: `FAIL`.

Action: handoff sang General Coding với evidence:

```text
Domain:
Expected date:
Source max date:
DB max date:
Source folder:
Production parser result:
Original run.py exception:
```

**STOP**. Không tự thay parser hoặc transaction trong runbook này.

---

### Branch C — DB current nhưng `run.py` vẫn báo stale

Evidence sau khi lỗi được report:

```text
DB max_date = expected_date
```

nhưng captured exception trước đó nói DB stale.

Kiểm tra xem một run khác đã cập nhật DB sau thời điểm exception hay không. So sánh log timestamp và current DB state.

Nếu current state đã đạt expected date: classify original event là historical/transient state và chạy Step 10 một lần.

Nếu lỗi tái hiện với current DB vẫn current: `FAIL / STOP` và handoff General Coding; không mở hypothesis mới trong cùng runbook.

---

### Branch D — expected trading date có dấu hiệu sai

Nếu `dimCalendar` trả một ngày mà source/market không được kỳ vọng có dữ liệu, không sửa `dimCalendar` trong runbook này.

Chạy read-only cross-check:

```sql
SELECT
    FullDate,
    IsHoliday
FROM "CherryMon"."main"."dimCalendar"
WHERE CAST(FullDate AS DATE) BETWEEN CURRENT_DATE - INTERVAL 7 DAY AND CURRENT_DATE
ORDER BY FullDate DESC;
```

Verdict: `BLOCKED` nếu expected-date contract cần domain/architecture decision.

Handoff sang owner của trading-calendar/data contract và **STOP**.

---

## 9. Optional audit cross-check

Nếu log có `validation_id`, có thể tìm audit row:

```sql
SELECT
    validation_id,
    checked_at,
    pipeline_name,
    table_name,
    expected_date,
    max_date,
    status,
    errors,
    warnings
FROM "CherryMon"."main"."sys_data_quality_audit"
WHERE validation_id = '<validation_id>';
```

Lưu ý: daily pipeline chạy trong shared DuckDB transaction. Nếu blocking DQ raise và UnitOfWork rollback, audit row vừa ghi trong transaction có thể không còn sau rollback. Trong trường hợp đó, stdout/stderr chứa `validation_id`, `status` và exact error vẫn là execution evidence của failed run.

Không kết luận rằng validation không chạy chỉ vì audit row không tồn tại sau rollback.

---

## 10. Final verification — chỉ chạy sau khi source đã được refresh hoặc blocker đã được xử lý

### 10.1 Xác nhận source trước

Chạy lại Step 3.

PASS condition:

```text
SOURCE_MAX_DATE = expected_date
```

### 10.2 Chạy canonical daily pipeline đúng một lần

```powershell
python run.py
```

Không rerun unchanged command nếu nó FAIL lại cùng một lỗi.

### 10.3 Xác nhận target

Chạy lại Step 1.

PASS condition cho affected domain:

```text
max_date = expected_date
lag_days = 0
```

và `run.py` không còn dừng tại stale gate đó.

---

## 11. PASS / FAIL / BLOCKED criteria

### PASS

Tất cả điều kiện sau đúng:

```text
source .dat max date = expected trading date
DuckDB target max date = expected trading date
lag_days = 0
run.py không còn FAIL tại stale gate của affected domain
```

Action: `KEEP / STOP`.

### FAIL

Một trong các điều kiện sau đúng:

- source current nhưng DB stale;
- production parser đọc được expected date nhưng ingestion không persist/upsert được;
- rerun sau focused repair vẫn FAIL cùng boundary;
- duplicate/semantic lỗi khác xuất hiện trong cùng affected domain sau freshness được khôi phục.

Action: capture exact evidence, handoff đúng owner, `STOP`.

### BLOCKED

- source folder unavailable;
- dependency/import/config unavailable;
- source chưa tới publication/refresh window;
- expected trading date contract cần quyết định ngoài diagnostic scope.

Action: ghi blocker và `STOP`.

---

## 12. Required output format

```text
TEST VERDICT
Objective: Diagnose AmiBroker Intraday stale failure
Affected domain: futures | index | stock | warrant
Expected trading date:
DuckDB max date:
Source max date:
Source folder:
Validation ID:
Verdict: PASS | FAIL | BLOCKED
Evidence:
- ...
Action: KEEP | FIX_ONCE | STOP
Next owner:
```

---

## 13. Anti-patterns

Không thực hiện các cách sau để làm pipeline pass giả:

```python
raise_on_fail=False
```

```text
expected_date = MAX(Date) của bảng đang stale
```

```text
DELETE/DROP target rồi hy vọng reload tự sửa
```

```text
disable freshness check riêng futures/index/stock/warrant mà không có contract mới
```

```text
rerun python run.py nhiều lần mà source chưa thay đổi
```

Freshness failure phải được xử lý tại source/ingestion/calendar boundary tương ứng, không che bằng validation override.

---

## 14. Current production references

- `.github/copilot-instructions.md`
- `.github/agents/TestEngineer.agent.md`
- `.github/instructions/testing.instructions.md`
- `.github/instructions/database.instructions.md`
- `.github/instructions/crawler.instructions.md`
- `.github/skills/data-quality-validation/SKILL.md`
- `docs/runbook/Daily_Data_Pipeline.md`
- `src/CrawlStock/readAmi.py`
- `src/Ults/DataValidation.py`
- `src/Ults/DataQualityOrchestration.py`
- `src/cherrystock/application/services/sync_amibroker_market_data.py`
- `src/cherrystock/application/services/sync_write_pipeline.py`
- `src/cherrystock/config/settings.py`
- `src/cherrystock/infrastructure/database/unit_of_work.py`
