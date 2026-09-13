# Yahoo Finance EOD Diagnostic Runbook

- **Status:** ACTIVE
- **Objective:** xác định hữu hạn nguyên nhân khi CherryStock không thấy Yahoo Finance EOD trong `raw_other_eod`.
- **Diagnostic script:** `scripts/check_yahoo_eod.py`
- **Production source adapter:** `src/CrawlStock/readYahooFinance.py`
- **Daily orchestrator:** `src/cherrystock/application/services/sync_write_pipeline.py`
- **Target:** `"CherryMon"."main"."raw_other_eod"`

## 1. Scope

Yahoo EOD hiện đồng bộ các ticker:

```text
DX-Y.NYB
BTC-USD
VND=X
GC=F
```

Logical key:

```text
Ticker + Date
```

Script chẩn đoán tách lỗi thành ba boundary:

```text
Yahoo source
    ↓
production normalize
    ↓
DuckDB raw_other_eod
```

Mặc định script **read-only với DuckDB**. Chỉ khi truyền `--sync DAYS` script mới gọi production `syncYahooFinance_EOD()` để ghi dữ liệu.

Không dùng runbook này để thay đổi architecture, ticker scope hoặc Data Quality rule.

---

## 2. Preconditions

Chạy từ repository root:

```powershell
git pull
python --version
python -c "import yfinance, duckdb; print('dependencies OK')"
```

Không thiết lập `PYTHONPATH` thủ công. Script tự bootstrap repository path theo Python execution convention của CherryStock.

---

## 3. Fast diagnostic — chạy đầu tiên

```powershell
python scripts\check_yahoo_eod.py
```

Command này thực hiện:

1. kiểm tra `raw_other_eod` có tồn tại;
2. thống kê Yahoo rows theo ticker;
3. kiểm tra ticker thiếu;
4. kiểm tra duplicate `Ticker + Date`;
5. probe Yahoo trực tiếp bằng `yfinance` trong 10 ngày gần nhất;
6. chạy production normalizer `_normalize_yf_eod()` trên response;
7. trả terminal verdict `PASS` hoặc `FAIL`.

### PASS

Ví dụ:

```text
PASS DX-Y.NYB: rows=... range=... .. ...
PASS BTC-USD: rows=... range=... .. ...
PASS VND=X: rows=... range=... .. ...
PASS GC=F: rows=... range=... .. ...

=== Verdict ===
PASS
Action: STOP
```

Kết luận: Yahoo source, production normalization và current DuckDB target đều có dữ liệu. Nếu UI/view khác vẫn không thấy data, issue nằm ngoài Yahoo ingestion boundary. **STOP** và tạo task mới cho downstream consumer/view.

### FAIL

Đi đúng một branch bên dưới theo evidence. Không tự mở thêm hypothesis ngoài branch hiện tại.

---

## 4. Branch A — DuckDB không có Yahoo rows nhưng source probe PASS

Dấu hiệu:

```text
FAIL: raw_other_eod contains no rows for configured Yahoo tickers.
...
PASS DX-Y.NYB ...
PASS BTC-USD ...
```

hoặc một số configured ticker bị thiếu trong DuckDB nhưng source probe ticker đó PASS.

### Action

Chạy production sync riêng Yahoo với window nhỏ:

```powershell
python scripts\check_yahoo_eod.py --sync 10
```

Script gọi đúng production function:

```text
syncYahooFinance_EOD(from_last_day=10)
```

sau đó đọc lại DuckDB.

### PASS criteria

```text
Production Yahoo sync completed
DuckDB có rows cho toàn bộ configured ticker
Duplicate Ticker+Date groups: 0
Verdict: PASS
```

Action: **KEEP + STOP**.

### FAIL criteria

- production sync raise exception;
- sync hoàn tất nhưng vẫn không có rows;
- target table missing;
- duplicate logical key xuất hiện.

Action: capture exact exception/output và **STOP**. Không rerun unchanged command.

---

## 5. Branch B — Yahoo source probe FAIL

Chạy source-only để cô lập network/API/parser khỏi DuckDB:

```powershell
python scripts\check_yahoo_eod.py --source-only --period 10d
```

### Nếu tất cả ticker FAIL

Khả năng thuộc source/environment boundary, ví dụ:

- network/proxy/DNS;
- Yahoo/yfinance response failure;
- yfinance dependency/runtime incompatibility.

Kiểm tra đúng một lần:

```powershell
python -c "import yfinance as yf; print(yf.__version__)"
```

Sau đó lưu exact error từ script và **STOP**. Không sửa DuckDB khi source chưa trả dữ liệu usable.

### Nếu chỉ một ticker FAIL

Mixed-calendar Yahoo source không đảm bảo mọi ticker có cùng ngày giao dịch, nhưng `10d` bình thường phải đủ để thấy usable history cho configured symbols.

Nếu một ticker vẫn trả empty/error trong source-only probe, classify source/ticker-specific failure và **STOP** với ticker + exact message.

Không xóa ticker khỏi `YAHOO_OTHER_TICKERS` chỉ để làm test pass.

---

## 6. Branch C — DuckDB rows tồn tại nhưng dữ liệu cũ

Chạy:

```powershell
python scripts\check_yahoo_eod.py --db-only
```

Đọc cột `max_date` từng ticker.

Sau đó chạy source-only:

```powershell
python scripts\check_yahoo_eod.py --source-only --period 10d
```

### Source mới hơn DB

Nếu Yahoo probe có `max_date` mới hơn DuckDB, chạy một production sync:

```powershell
python scripts\check_yahoo_eod.py --sync 10
```

Nếu DB cập nhật: **PASS / KEEP / STOP**.

Nếu DB không cập nhật: **FAIL / STOP** và giữ exact output.

### Source và DB cùng ngày

Không phải missing Yahoo ingestion. Có thể consumer đang kỳ vọng calendar khác. **STOP** và kiểm tra downstream task riêng.

---

## 7. Branch D — daily `run.py` không thấy dữ liệu sau khi Yahoo standalone sync PASS

Daily pipeline dùng shared DuckDB transaction:

```text
BEGIN
  ...
  Yahoo EOD sync
  Yahoo DQ
  ...
  later stages
COMMIT
```

Nếu một blocking stage phía sau Yahoo raise trước COMMIT, toàn bộ daily write set bị rollback. Vì vậy log có thể cho thấy Yahoo sync chạy nhưng dữ liệu mới không còn sau khi `run.py` kết thúc lỗi.

### Check

1. Chạy standalone Yahoo diagnostic/sync và xác nhận PASS.
2. Chạy normal daily pipeline:

```powershell
python run.py
```

3. Nếu `run.py` FAIL sau Yahoo stage, ghi lại **first blocking exception**.
4. Chạy lại read-only:

```powershell
python scripts\check_yahoo_eod.py --db-only
```

Nếu standalone sync PASS nhưng daily run rollback do stage khác, issue không nằm ở Yahoo adapter. **STOP** và xử lý blocking daily-pipeline failure theo stage owner.

Không thay đổi transaction boundary để che lỗi.

---

## 8. Direct DuckDB SQL cross-check

Khi cần nhìn raw data trực tiếp trong DuckDB extension:

```sql
SELECT
    Ticker,
    MIN(Date) AS MinDate,
    MAX(Date) AS MaxDate,
    COUNT(*) AS Rows
FROM "CherryMon"."main"."raw_other_eod"
WHERE Ticker IN ('DX-Y.NYB', 'BTC-USD', 'VND=X', 'GC=F')
GROUP BY Ticker
ORDER BY Ticker;
```

Latest rows:

```sql
WITH ranked AS (
    SELECT
        Ticker,
        Date,
        Open,
        High,
        Low,
        Close,
        Volume,
        ROW_NUMBER() OVER (PARTITION BY Ticker ORDER BY Date DESC) AS rn
    FROM "CherryMon"."main"."raw_other_eod"
    WHERE Ticker IN ('DX-Y.NYB', 'BTC-USD', 'VND=X', 'GC=F')
)
SELECT Ticker, Date, Open, High, Low, Close, Volume
FROM ranked
WHERE rn <= 5
ORDER BY Ticker, Date DESC;
```

Duplicate check:

```sql
SELECT Ticker, Date, COUNT(*) AS Rows
FROM "CherryMon"."main"."raw_other_eod"
WHERE Ticker IN ('DX-Y.NYB', 'BTC-USD', 'VND=X', 'GC=F')
GROUP BY Ticker, Date
HAVING COUNT(*) > 1
ORDER BY Ticker, Date;
```

---

## 9. Diagnostic interpretation matrix

| DuckDB | Yahoo probe | Meaning | Action |
|---|---|---|---|
| PASS | PASS | ingestion boundary healthy | STOP; inspect downstream only if needed |
| FAIL/empty | PASS | persistence/sync path issue | run `--sync 10` once |
| PASS/stale | PASS/newer | sync checkpoint/execution issue | run `--sync 10` once |
| any | FAIL | source/network/yfinance/ticker issue | capture exact source error and STOP |
| standalone PASS | daily rollback | later daily blocking stage | fix that stage, not Yahoo adapter |

---

## 10. Finite test contract

### Target

Determine whether missing Yahoo EOD is caused by source retrieval, production normalization, DuckDB persistence, or daily transaction rollback.

### In scope

- configured Yahoo ticker availability;
- production normalization;
- `raw_other_eod` presence/current rows;
- duplicate logical keys;
- explicit standalone production sync;
- daily rollback interpretation.

### Out of scope

- adding/removing Yahoo tickers;
- changing Yahoo provider;
- schema redesign;
- changing daily transaction architecture;
- downstream chart/UI/view defects.

### Retry budget

- one initial diagnostic;
- one focused `--sync 10` repair execution when source PASS and DB FAIL/stale;
- no unchanged retry.

### Terminal verdict

```text
PASS
FAIL
BLOCKED
```

Then exactly one action:

```text
KEEP
FIX ONCE
STOP
```

---

## 11. Expected operator evidence

Khi báo issue, paste nguyên output của một trong các command sau:

```powershell
python scripts\check_yahoo_eod.py
python scripts\check_yahoo_eod.py --db-only
python scripts\check_yahoo_eod.py --source-only --period 10d
python scripts\check_yahoo_eod.py --sync 10
```

Tối thiểu evidence phải có:

```text
configured tickers
DuckDB summary
Yahoo source result per ticker
exact exception nếu có
final verdict
```

Không kết luận "Yahoo không có data" chỉ từ downstream view/UI khi chưa kiểm tra `raw_other_eod` và source probe.
