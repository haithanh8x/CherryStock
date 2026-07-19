

Python  
content \= """\# Cấu trúc thư mục và Kiến trúc Dự án CherryStock

Tài liệu này mô tả chi tiết cấu trúc thư mục, các phân hệ chức năng, tham số cấu hình, và tài liệu kỹ thuật của các hàm (API Reference) trong hệ thống pipeline xử lý dữ liệu chứng khoán \*\*CherryStock\*\*.

\---

\#\# I. Tổng quan Kiến trúc và Cấu trúc Thư mục

Kết quả chạy mã

File generated successfully.

\`\`\`text  
CherryStock/  
├── .kiro/  
│   └── specs/  
│       ├── CherryMon Arch.drawio      \# Sơ đồ kiến trúc toàn bộ hệ thống CherryMon  
│       └── project\_structured.md      \# Tài liệu mô tả cấu trúc dự án (File này)  
├── CrawlStock/                        \# Phân hệ Ingest (Thu thập & Nạp dữ liệu)  
│   ├── readAmi.py                     \# Bộ giải mã nhị phân AmiBroker (.dat) & Đồng bộ dữ liệu EOD/Intraday  
│   └── lstDuckDB.py                   \# Thư viện quản trị an toàn SQL & Upsert an toàn vào DuckDB  
├── Amibroker/                         \# Phân hệ lưu trữ các Script/Formula và Batch thực thi của AmiBroker  
│   ├── Batch/                         \# Các file kịch bản điều phối AmiBroker (.abb, .bat, .vbs, .apx)  
│   └── Formulas/                      \# Bộ mã nguồn AFL để quét kỹ thuật, tính toán chỉ báo, trích xuất dữ liệu  
├── DuckDB/                            \# Hệ lưu trữ cơ sở dữ liệu phân tích dạng nhúng (Local / MotherDuck)  
│   └── sql/transforms/                \# Các file SQL biến đổi dữ liệu (BCTC, VietStock,...)  
├── Orchestrator/                      \# Các kịch bản tự động hóa và điều phối lịch trình chạy (Rundeck, Batch)  
├── Telegram/                          \# Module Bot nhắn tin, gửi thông báo tín hiệu và cảnh báo giao dịch  
├── lstPara.py                         \# Khai báo biến môi trường, danh mục đường dẫn hệ thống AmiBroker  
└── run.py                             \# Điểm khởi chạy (Main Entry Point) thực thi đồng bộ hóa toàn luồng dữ liệu

## **II. Chi tiết Phân hệ chức năng**

### **1\. Phân hệ CrawlStock (Data Ingestion Pipeline)**

* **readAmi.py**: Đóng vai trò giải mã các tệp tin cấu hình nhị phân .dat từ thư mục cài đặt gốc của phần mềm AmiBroker, bóc tách cấu trúc byte thành dữ liệu dạng mảng cấu trúc để đưa vào pandas.DataFrame. Hỗ trợ cơ chế lọc thời gian tăng trưởng (incremental) trực tiếp khi đọc nhị phân.  
* **lstDuckDB.py**: Cung cấp các wrapper/procedure thực hiện đưa dữ liệu từ tầng ứng dụng (DataFrame) vào DuckDB an toàn. Xử lý chuẩn hóa kiểu dữ liệu thông qua cơ chế so khớp schema tự động và ép kiểu chống lỗi chuỗi bẩn bằng TRY\_CAST.

### **2\. Phân hệ Amibroker (Analysis Scripts & Automation)**

* **Batch**:  
  * ALL\_Shares.abb / ALL\_Shares.bat / ALL\_Shares.vbs: Bộ ba điều phối giúp kích hoạt chế độ chạy ngầm tự động (Batch Mode) của AmiBroker nhằm quét và kết xuất dữ liệu tự động mà không cần mở giao diện GUI.  
  * ALL\_Shares.apx: Dự án phân tích chỉ báo kỹ thuật, tự động tính toán: RSI, TSI, ATR %, các đường MA (MA5, MA20), tín hiệu MACD, góc dốc xu hướng (Slope), lọc thanh khoản (Volume \> 5000 trong 5 phiên liên tiếp), và xuất ra file trung gian All\_Shares.csv.  
  * ALL\_Shares\_TimeSeries.apx: Dự án xuất chuỗi thời gian lịch sử giá cổ phiếu (ALL\_Shares\_TimeSeries.csv).  
  * ThongKe.apx & Ticker\_Attr.apx: Xuất bảng tóm tắt thống kê và thuộc tính của các mã cổ phiếu.  
* **Formulas**: Lưu trữ toàn bộ các file code chiến lược và chỉ báo kỹ thuật bằng ngôn ngữ AFL (AmiBroker Formula Language) như Ichimoku, Bollinger Bands, Volume Price Analysis (VPA), Mua bán chủ động, Nước ngoài & Tự doanh.

### **3\. Phân hệ Telegram & Orchestrator**

* **KieuNuDaiGia\_Funds.py**: Kịch bản quét điều kiện tín hiệu giao dịch thuật toán từ DuckDB và thực hiện đẩy thông báo tự động (Alert Notification) vào kênh Telegram *Manhattan Channel*.  
* **Orchestrator**: Tích hợp các file kịch bản khởi chạy (.bat, .vbs) điều phối cùng Rundeck phục vụ lập lịch chạy tự động định kỳ cho luồng Intraday và EOD.

## **III. Tài liệu kỹ thuật các hàm lõi (API Reference)**

### **1\. Module: CrawlStock/readAmi.py**

#### **Hàm read\_amibroker\_dat**

* **Mô tả**: Đọc trực tiếp cấu trúc nhị phân (32-byte/40-byte) của tệp tin AmiBroker .dat thô. Tự động chuyển đổi định dạng ngày sang số nguyên để kiểm tra checkpoint tại tầng nhị phân nhằm tối ưu hiệu năng đọc. Định dạng nến trả về tự động được cấu hình múi giờ Việt Nam (Asia/Ho\_Chi\_Minh).  
* **Tham số**:  
  * file\_path (*str*): Đường dẫn vật lý tới tệp .dat cần đọc.  
  * from\_date (*str / datetime, Optional*): Điểm checkpoint thời gian (Ví dụ: '2026-06-01'). Các bản ghi trước ngày này sẽ bị bỏ qua lập tức để tăng tốc độ.  
* **Kết quả trả về**: pandas.DataFrame chứa các trường: Date (mang tz GMT+7), Open, High, Low, Close, Volume, OpenInt. Trả về None nếu tệp tin không tồn tại.

#### **Hàm upsert\_stock\_eod**

* **Mô tả**: Liệt kê các tệp .dat trong thư mục chỉ định, trích xuất mã chứng khoán (Ticker) dựa theo tên tệp tin, bóc tách nhị phân, gộp thành khối DataFrame duy nhất, sau đó tiến hành tạo cấu trúc bảng đích với khóa chính kết hợp PRIMARY KEY (Ticker, Date) và thực thi câu lệnh nạp cập nhật **Upsert 1:1** (INSERT INTO ... ON CONFLICT DO UPDATE).  
* **Tham số**:  
  * con (*duckdb.DuckDBPyConnection*): Kết nối đang hoạt động tới DuckDB.  
  * folder\_path (*str*): Đường dẫn thư mục chứa các file nhị phân đầu vào.  
  * table\_name (*str*): Tên bảng đích nhận dữ liệu trong cơ sở dữ liệu.  
  * from\_date (*Optional*): Ngày checkpoint truyền xuống tầng giải mã nhị phân.  
* **Kết quả trả về**: Không có (None).

#### **Hàm syncAmibroker\_EOD**

* **Mô tả**: Hàm điều phối cấp cao phục vụ quét và đồng bộ dữ liệu cuối ngày (End Of Day). Tự động cố định mốc thời gian checkpoint tăng trưởng là **3 ngày trước** (now \- 3 days). Duyệt tuần tự qua 12 danh mục dữ liệu của AmiBroker và nạp vào các bảng lưu trữ thô raw\_\*\_eod. Tự động giải phóng kết nối database ở cuối tiến trình.  
* **Tham số**: con (*duckdb.DuckDBPyConnection*).  
* **Kết quả trả về**: Không có (None).

#### **Hàm syncAmibroker\_Intraday**

* **Mô tả**: Hàm điều phối phục vụ quét dữ liệu đồ thị nến thời gian ngắn trong ngày (Intraday). Nhằm tối ưu hóa tốc độ nhảy số real-time, hàm cố định mốc quét tăng trưởng siêu ngắn từ **1 ngày trước** (now \- 1 day). Tiến hành ánh xạ dữ liệu nhị phân từ 4 phân hệ Intraday thô (Futures, Index, Stock, Warrant) vào các bảng lưu trữ raw\_\*\_intraday và đóng kết nối.  
* **Tham số**: con (*duckdb.DuckDBPyConnection*).  
* **Kết quả trả về**: Không có (None).

### **2\. Module: CrawlStock/lstDuckDB.py**

#### **Hàm prc\_upsert\_by\_ticker**

* **Mô tả**: Thực hiện thủ tục nạp dữ liệu an toàn dựa trên cơ chế xóa dữ liệu cũ của mã chứng khoán đó rồi nạp lại (Delete-then-Insert) được đóng gói chặt chẽ trong khối Transaction quản lý lỗi (BEGIN TRANSACTION / COMMIT / ROLLBACK). Hàm tự động so khớp cấu trúc cột giữa DataFrame tạm thời (View) và bảng đích thực tế, đồng thời áp dụng toán tử TRY\_CAST ép kiểu an toàn cho các trường Số, Boolean, Ngày giờ để triệt tiêu các lỗi tràn bộ nhớ hoặc lỗi định dạng do chuỗi ký tự bẩn gây ra.  
* **Tham số**:  
  * con (*duckdb.DuckDBPyConnection*): Kết nối DuckDB.  
  * table (*str*): Tên bảng cơ sở dữ liệu đích.  
  * df (*pd.DataFrame*): Khối dữ liệu mới của mã cần nạp.  
  * ticker (*str*): Mã chứng khoán định danh định vị dòng xóa.  
  * ticker\_col (*str, Default: 'Ticker'*): Tên cột định danh mã chứng khoán.  
* **Kết quả trả về**: Không có (None). Tự động thực thi an toàn dữ liệu hoặc sinh ngoại lệ lỗi nếu có sự cố.

## **IV. Bảng tổng hợp cấu hình ánh xạ luồng dữ liệu (Pipeline Data Mapping)**

Dưới đây là bảng cấu hình ánh xạ chi tiết của toàn luồng xử lý từ các thư mục của AmiBroker vào hệ phân tích cơ sở dữ liệu DuckDB:

| Chức năng điều phối | Phân hệ dữ liệu nguồn | Mốc thời gian Incremental | Bảng dữ liệu đích trong DuckDB | Cơ chế ràng buộc dữ liệu |
| :---- | :---- | :---- | :---- | :---- |
| syncAmibroker\_EOD | AMIBROKER\_EOD\_ACTIVE\_PATH | now \- 3 days | raw\_active\_eod | Primary Key (Ticker, Date) |
| syncAmibroker\_EOD | AMIBROKER\_EOD\_COMMODITY\_PATH | now \- 3 days | raw\_commodity\_eod | Primary Key (Ticker, Date) |
| syncAmibroker\_EOD | AMIBROKER\_EOD\_FOREIGN\_PATH | now \- 3 days | raw\_foreign\_eod | Primary Key (Ticker, Date) |
| syncAmibroker\_EOD | AMIBROKER\_EOD\_FUTURES\_PATH | now \- 3 days | raw\_futures\_eod | Primary Key (Ticker, Date) |
| syncAmibroker\_EOD | AMIBROKER\_EOD\_INDEX\_PATH | now \- 3 days | raw\_index\_eod | Primary Key (Ticker, Date) |
| syncAmibroker\_EOD | AMIBROKER\_EOD\_INDUSTRY\_PATH | now \- 3 days | raw\_industry\_eod | Primary Key (Ticker, Date) |
| syncAmibroker\_EOD | AMIBROKER\_EOD\_MARKET\_PATH | now \- 3 days | raw\_market\_eod | Primary Key (Ticker, Date) |
| syncAmibroker\_EOD | AMIBROKER\_EOD\_OTHER\_PATH | now \- 3 days | raw\_other\_eod | Primary Key (Ticker, Date) |
| syncAmibroker\_EOD | AMIBROKER\_EOD\_PROP\_PATH | now \- 3 days | raw\_prop\_eod | Primary Key (Ticker, Date) |
| syncAmibroker\_EOD | AMIBROKER\_EOD\_STOCK\_PATH | now \- 3 days | raw\_stock\_eod | Primary Key (Ticker, Date) |
| syncAmibroker\_EOD | AMIBROKER\_EOD\_SUPPLYDEMAND\_PATH | now \- 3 days | raw\_supplydemand\_eod | Primary Key (Ticker, Date) |
| syncAmibroker\_EOD | AMIBROKER\_EOD\_WARRANT\_PATH | now \- 3 days | raw\_warrant\_eod | Primary Key (Ticker, Date) |
| syncAmibroker\_Intraday | AMIBROKER\_INTRADAY\_FUTURES\_PATH | now \- 1 day | raw\_futures\_intraday | Primary Key (Ticker, Date) |
| syncAmibroker\_Intraday | AMIBROKER\_INTRADAY\_INDEX\_PATH | now \- 1 day | raw\_index\_intraday | Primary Key (Ticker, Date) |
| syncAmibroker\_Intraday | AMIBROKER\_INTRADAY\_STOCK\_PATH | now \- 1 day | raw\_stock\_intraday | Primary Key (Ticker, Date) |
| syncAmibroker\_Intraday | AMIBROKER\_INTRADAY\_WARRANT\_PATH | now \- 1 day | raw\_warrant\_intraday | Primary Key (Ticker, Date) |
| """ |  |  |  |  |

with open("project\_structured.md", "w", encoding="utf-8") as f:  
f.write(content.strip())  
print("File generated successfully.")

Your Markdown file is ready  
\[file-tag: code-generated-file-0-1782032472688868214\]

Tệp tin tài liệu cấu trúc hệ thống và đặc tả kỹ thuật chi tiết (\`project\_structured.md\`) đã được cập nhật toàn diện và lưu thành công. Bạn có thể lưu trực tiếp tệp này vào thư mục \`.kiro/specs/\` của dự án để làm tài liệu chuẩn (Documentation) lâu dài cho hệ thống \*\*CherryStock\*\*\!  
