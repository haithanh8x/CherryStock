# DuckDB local → Cloudflare R2 (cherrystock)

Module sync độc lập, đồng thời được `run.py` gọi sau khi Ingest và Aggregate hoàn tất. Đồng bộ lần đầu: `"CherryMon"."main"."vw_Ticker_Active"` thành object **`s3://cherrystock/vw_Ticker_Active.parquet`**. Giữ nguyên tên view và tên cột, không rename. Parquet/ZSTD phù hợp để tải dữ liệu cho frontend qua một lớp public access hoặc Worker riêng (R2 bucket mặc định không public).

## Cấu hình local

Cài dependency: `pip install boto3` (DuckDB và python-dotenv có trong project).

Thêm vào `.env` local (không commit credentials):

```dotenv
LOCAL_DB_PATH=C:/Datafile/CherryMon.duckdb
CLOUDFLARE_ACCOUNT_ID=<your-account-id>
R2_ACCESS_KEY_ID=<r2-access-key>
R2_SECRET_ACCESS_KEY=<r2-secret-key>
# Tùy chọn: tắt bước upload tự động trong run.py
# CHERRYSTOCK_R2_SYNC_ENABLED=false
```

Tạo R2 API token có quyền Object Read/Write cho bucket `cherrystock`. Không sử dụng Cloudflare Global API key.

Chạy tại thư mục gốc repo:

```powershell
python -m scripts.cloudflare_sync.sync_view --dry-run
python -m scripts.cloudflare_sync.sync_view
```

Chạy toàn bộ pipeline hàng ngày (tự động upload R2 sau khi các bước trước thành công):

```powershell
python run.py
```

Bước upload được bật mặc định. Đặt `CHERRYSTOCK_R2_SYNC_ENABLED=false` trong `.env` để bỏ qua. Nếu upload lỗi, `run.py` báo lỗi (Ingest/Aggregate đã commit, không rollback); có thể chạy lại `python -m scripts.cloudflare_sync.sync_view` riêng.

Quy trình: đọc DuckDB ở chế độ read-only → xuất Parquet snapshot → từ chối view rỗng → upload vào `_staging/` → kiểm tra size và SHA256 metadata → copy sang key cố định → kiểm tra object đích → xóa staging. Rerun an toàn ở mức snapshot replacement; không hỗ trợ incremental theo hàng trong phiên bản đầu.

**Lưu ý:** `vw_Ticker_Active` có thể chứa thông tin hiện tại, không phải lịch sử point-in-time. Nếu xuất cho GitHub Pages, cần cấu hình public access/Worker và CORS riêng; không nhúng R2 secret vào React. Kiểm tra dữ liệu và schema trước khi cho phép public.
