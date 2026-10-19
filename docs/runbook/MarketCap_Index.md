# MarketCap Group Index — Local Agent Execution Runbook

- **Trạng thái:** IMPLEMENTED_PENDING_LOCAL_EXECUTION
- **Repo / nhánh:** `haithanh8x/CherryStock` / `main`
- **Phạm vi:** Khởi tạo lịch sử 4 nhóm Market Cap, kích hoạt incremental qua `run.py`
- **Yêu cầu của người dùng:** **KHÔNG chạy pytest, unit test, integration test, benchmark, tạo test case hoặc visual test.** Chỉ thực thi job và báo kết quả vận hành.
- **Engine:** `src/calcEngine/marketCapIndex.py`
- **Schema:** `src/DuckDB/sql/marketcap_index_schema.sql`
- **Standalone CLI:** `scripts/run_marketcap_index.py`
- **Daily orchestration:** `run.py`
- **Dữ liệu nguồn:** `CherryMon.main.vw_Ticker_Active`, `CherryMon.main.vw_Ticker_OHLC_D`
- **Dữ liệu đích:** `CherryMon.main.cal_MarketCap_Index_D`; read view `CherryMon.main.vw_MarketCap_Index_D`

## 1. Nhiệm vụ giao local agent

Agent làm việc trên máy Windows chứa DuckDB CherryStock. Kéo phiên bản mới nhất của `main`, chạy **full initload một lần**, sau đó sử dụng `run.py` để incremental trong các phiên tiếp theo. Ghi lại các dòng log và summary, không sửa dữ liệu nguồn thủ công, không chạy test. Nếu có lỗi, dừng đúng bước bị lỗi, báo traceback và nguyên nhân; không tự bỏ qua lỗi hoặc làm sai khác nhóm MarketCap.

Nhóm lấy từ cột **`MarketCap_Group` đã có** trong `vw_Ticker_Active`, **không tính lại ngưỡng vốn hóa** trong engine:

| MarketCap_Group | Chỉ số |
|---|---|
| `Large Cap` | Large Cap Index |
| `Mid Cap` | Mid Cap Index |
| `Small Cap` | Small Cap Index |
| `Micro Cap` | Micro Cap Index |

Mỗi nhóm có hai chuỗi `Index_Method`: `EW` (equal-weight) và `FFMC` (free-float-market-cap weight). Kỳ vọng **tối đa 8 chuỗi theo ngày**, không mặc định mọi nhóm đều có dữ liệu FFMC mỗi phiên. Điểm cơ sở cho từng chuỗi là **1000**.

**Lưu ý diễn giải lịch sử:** engine dùng nhóm `MarketCap_Group` và `FreeFloat` **mới nhất** áp ngược lên dữ liệu OHLC lịch sử. Đây là proxy (`HISTORICAL_PROXY_LATEST_MARKETCAP_GROUP`), **không phải point-in-time**, không dùng để kết luận về backtest không thiên lệch sống sót.

## 2. Chuẩn bị và lấy bản mới nhất

Mở PowerShell trong `C:\Github\CherryStock`:

```powershell
cd C:\Github\CherryStock
git status --short
git branch --show-current
git pull --ff-only origin main
```

- Chỉ tiếp tục khi đang ở nhánh `main` và pull thành công.
- Nếu workspace có thay đổi chưa commit, **không reset/clean/overwrite**; báo chủ sở hữu hoặc xử lý theo quy định repo trước khi pull.
- Sử dụng Python environment, dependencies và đường dẫn DB đã được cấu hình cho CherryStock. Nếu môi trường chưa cấu hình, tham chiếu `docs/development/Python_Execution_Conventions.md`.
- Bảo đảm `vw_Ticker_Active` đã được cập nhật và có `MarketCap_Group`; `vw_Ticker_OHLC_D` có lịch sử giá đóng cửa dương.
- Không chạy đồng thời với tiến trình khác có quyền ghi vào cùng file DuckDB.

## 3. Full initload (thực hiện một lần)

Chạy tại repo root:

```powershell
python scripts\run_marketcap_index.py
```

Script tự chạy DDL từ `marketcap_index_schema.sql`, tạo bảng và view đích nếu chưa có, rồi nạp lịch sử theo 4 nhóm và hai phương pháp EW/FFMC. Không cần chạy tay SQL migration. Mặc định **không truyền `--days` = full history**.

Log thành công có dạng:

```text
[MarketCapIndex] {'mode': 'full', 'days': None, 'from_date': '...', 'rows': ..., 'members': ...}
```

Ghi lại `mode`, `from_date`, `rows`, `members`, thời gian bắt đầu/kết thúc và traceback nếu gặp lỗi. `rows` là số dòng index (mỗi ngày × nhóm × method có dữ liệu), không phải số ticker.

**Đặc điểm giao dịch:** DDL, xóa/thay các dòng đích và insert chạy trong `DuckDBUnitOfWork`. Khi thất bại, không coi initload thành công; sửa lỗi nguồn/cấu hình rồi rerun. **Không được xóa các bảng nguồn hoặc các `cal_Industry_Index_*`.**

## 4. Incremental riêng lẻ (khi cần rerun/backfill cửa sổ)

```powershell
python scripts\run_marketcap_index.py --days 10
```

`--days 10` = **10 phiên giao dịch mới nhất có dữ liệu nguồn**, không phải 10 ngày lịch. Engine tính lại các dòng index từ ngày cutoff, lấy previous close trước cửa sổ, nối với điểm index đã lưu trước cutoff và thay thế các dòng trong cửa sổ. Có thể rerun cùng tham số khi cần xử lý lại dữ liệu mới nhất.

Dòng log mong đợi:

```text
[MarketCapIndex] {'mode': 'incremental', 'days': 10, 'from_date': '...', 'rows': ..., 'members': ...}
```

Nếu bảng đích còn rỗng, gọi `--days 10` sẽ **tự bootstrap toàn bộ lịch sử** với `mode='full'`. Không nhất thiết phải chạy riêng incremental ngay sau initload nếu không có dữ liệu mới: mục đích của bước này là lệnh vận hành/rerun.

Khi `MarketCap_Group`, universe thành phần hoặc `FreeFloat` hiện tại thay đổi và muốn **tái dựng nhất quán toàn bộ lịch sử proxy**, chạy lại full initload (không truyền `--days`). Nếu chỉ cần cập nhật dữ liệu phiên gần đây, dùng incremental.

## 5. Daily incremental qua run.py

Sau initload, lịch chạy hằng ngày của CherryStock vẫn là:

```powershell
python run.py
```

Luồng thực tế:

1. `INGEST DATA`: đồng bộ nguồn và commit.
2. `AGGREGATE DATA`: tính Industry Index (nếu enabled).
3. **MarketCap Group Index**: engine `refresh_marketcap_index(days=max(1, days_diff), connection=uow.connection)` trong **transaction riêng**.
4. Tiếp tục các bước aggregate đang bật, DuckDB metadata export và R2 sync hiện có.

Log cần xuất hiện:

```text
[AGGREGATE] START | MarketCap Group Index EW + FFMC
[AGGREGATE] COMMITTED | MarketCap Group Index | {...}
[Duration] 'marketcap_index_refresh' total time: ... seconds
```

`days_diff` do `run.py` tính từ checkpoint; **không cố định 10 phiên**. Lần chạy đầu nếu target chưa có dữ liệu vẫn tự full-bootstrap. MarketCap Index hiện được gọi trực tiếp trong `run.py`, không có flag enable/disable riêng.

**R2:** Daily R2 sync hiện chỉ publish `vw_Ticker_Active` sang `cherrystock/vw_Ticker_Active.parquet`. Runbook này **không tự publish** `vw_MarketCap_Index_D` lên R2; muốn sử dụng trên GitHub Pages cần thêm một tác vụ sync/export riêng.

## 6. Kiểm tra trạng thái vận hành (không phải test suite)

Sau khi job kết thúc, chỉ cần xác nhận bằng **log COMMITTED** và có dữ liệu đã lưu. Nếu agent có sẵn kết nối read-only DuckDB, có thể ghi nhận nhanh:

```sql
SELECT "MarketCap_Group", "Index_Method",
       MIN("Date") AS first_date, MAX("Date") AS latest_date,
       COUNT(*) AS row_count
FROM "CherryMon"."main"."vw_MarketCap_Index_D"
GROUP BY 1, 2
ORDER BY 1, 2;
```

Đây là quan sát dữ liệu đã được ghi, **không phải chạy test**. Không yêu cầu đối soát benchmark, pytest hay tạo báo cáo test. Không sửa metadata bằng tay: nếu `python run.py` chạy đầy đủ, bước metadata export đã nằm trong pipeline.

## 7. Xử lý sự cố và báo cáo hoàn thành

- **`missing/invalid MarketCap_Group`**: engine không tự tạo nhóm; xác minh luồng cập nhật `vw_Ticker_Active`. Các giá trị được nhận là `Large Cap`, `Mid Cap`, `Small Cap`, `Micro Cap` (case-insensitive; dấu `_` được đổi sang dấu cách). Sau khi nguồn chính xác, rerun.
- **`Duplicate active tickers` / `Duplicate OHLC ticker/date`**: dừng, gửi log và báo nhóm dữ liệu nguồn có trùng lặp; không sửa tay/khử trùng lặp một cách tùy tiện.
- **`No eligible daily OHLC` / `No MarketCap index rows`**: dừng và kiểm tra dữ liệu nguồn, không tạo dòng giả.
- **File DuckDB đang bị writer khác khóa**: đóng writer gây xung đột, sau đó rerun.
- **Thất bại sau khi INGEST đã commit**: MarketCap transaction có thể rollback riêng; sửa nguyên nhân và chạy `python scripts\run_marketcap_index.py --days 10` để phục hồi, không cần chạy lại toàn bộ AmiBroker ingest nếu dữ liệu nguồn đã commit.
- **Thay đổi nhãn nhóm, phương pháp tính hoặc backfill toàn lịch sử**: chạy lại full initload. Không drop bảng để thử lại.

### Mẫu báo cáo local agent

```text
CherryStock MarketCap Index rollout
Branch / HEAD: main / <commit>
Local DB: <đường dẫn đang cấu hình, không đính kèm credentials>
Initload: SUCCESS | FAILED
  mode=<...> from_date=<...> rows=<...> members=<...>
Daily incremental: NOT RUN (chờ phiên giao dịch) | SUCCESS | FAILED
  days=<...> from_date=<...> rows=<...>
Output: cal_MarketCap_Index_D + vw_MarketCap_Index_D
Errors: <none / traceback tóm tắt>
Tests: NOT RUN (theo yêu cầu)
Source data manually modified: NO
```

Chỉ báo **SUCCESS** khi job thực sự chạy xong trên máy local; việc code đã merge lên GitHub chưa chứng minh initload thành công.
