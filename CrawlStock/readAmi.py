import struct
import pandas as pd
import os
import win32com.client
import pythoncom
import threading
import time
import os
import pandas as pd

from Ults.Timing import timeit, toggle_print
from datetime import datetime, timedelta
from typing import Optional
from Ults.lstFiles import list_files_in_folder
from lstPara import DATAFILE_PATH, AMIBROKER_AFL_PATH, AMIBROKER_EOD_ACTIVE_PATH, AMIBROKER_EOD_COMMODITY_PATH, AMIBROKER_EOD_FOREIGN_PATH, AMIBROKER_EOD_FUTURES_PATH, AMIBROKER_EOD_INDEX_PATH, AMIBROKER_EOD_INDUSTRY_PATH, AMIBROKER_EOD_MARKET_PATH, AMIBROKER_EOD_OTHER_PATH, AMIBROKER_EOD_PROP_PATH, AMIBROKER_EOD_STOCK_PATH, AMIBROKER_EOD_SUPPLYDEMAND_PATH, AMIBROKER_EOD_WARRANT_PATH, AMIBROKER_INTRADAY_FUTURES_PATH, AMIBROKER_INTRADAY_INDEX_PATH, AMIBROKER_INTRADAY_STOCK_PATH, AMIBROKER_INTRADAY_WARRANT_PATH, AMIBROKER_LOG_PATH, DATAFILE_PATH

@toggle_print(allow_print=False)
def read_amibroker_dat(file_path, from_date=None):
    """ Reads an AmiBroker .dat file and returns a pandas DataFrame containing the stock data.
    Parameters:
        file_path (str): The path to the AmiBroker .dat file.
        from_date (str or datetime, optional): Filter data from this checkpoint date (inclusive).
                                               Accepts format 'YYYY-MM-DD' or datetime object.
    Returns:
        pd.DataFrame: A DataFrame containing the stock data.
    """

    if not os.path.exists(file_path):
        print(f"Lỗi: Không tìm thấy file tại: {file_path}")
        return None

    # Chuẩn hóa biến from_date thành số nguyên YYYYMMDD để so sánh nhanh ở tầng nhị phân
    from_date_int = None
    if from_date is not None:
        if isinstance(from_date, str):
            # Chuyển đổi '2026-06-01' -> 20260601
            cleaned_date = from_date.replace('-', '').replace('/', '')
            from_date_int = int(cleaned_date)
        elif isinstance(from_date, datetime):
            from_date_int = int(from_date.strftime('%Y%m%d'))

    # Bản cập nhật: Cấu trúc 40/48-byte chuẩn của AmiBroker
    # i: Date (4b), i: Time/Microsecs (4b), f: O (4b), f: H (4b), f: L (4b), f: C (4b), f: Vol (4b)...
    record_format = '=i i f f f f f f'  # 32-Byte Định dạng EOD chuẩn
    record_size = struct.calcsize(record_format) 
    
    data = []
    
    with open(file_path, 'rb') as f:
        f.seek(0) 
        
        while True:
            bytes_read = f.read(record_size)
            if len(bytes_read) < record_size:
                break
                
            unpacked = struct.unpack(record_format, bytes_read)
            raw_date = unpacked[0]
            
            # 1. Kiểm tra xem có phải định dạng ngày hợp lệ (Ví dụ: từ năm 1990 đến 2030)
            if 19900101 <= raw_date <= 20501231:
                
                # 2. KIỂM TRA CHECKPOINT: Nếu nhỏ hơn ngày from_date thì bỏ qua luôn (tối ưu hiệu năng)
                if from_date_int is not None and raw_date < from_date_int:
                    continue
                    
                try:
                    date_str = str(raw_date)
                    date_obj = datetime.strptime(date_str, '%Y%m%d')
                    
                    data.append({
                        'Date': date_obj,
                        'Open': round(unpacked[2], 2),
                        'High': round(unpacked[3], 2),
                        'Low': round(unpacked[4], 2),
                        'Close': round(unpacked[5], 2),
                        'Volume': int(unpacked[6]),
                        'OpenInt': round(unpacked[7], 2)
                    })
                except ValueError:
                    continue

    df = pd.DataFrame(data)
    # --- ĐOẠN ĐỔI SANG GMT+7 CHO PANDAS ---
    if not df.empty:
        # Nếu data thô từ Amibroker mặc định chưa mang múi giờ (Naive), ta coi nó là UTC 
        # rồi convert thẳng sang Asia/Ho_Chi_Minh (GMT+7)
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize('UTC').dt.tz_convert('Asia/Ho_Chi_Minh')
    return df

@timeit
@toggle_print(allow_print=False)
def upsert_stock_eod(con, folder_path: str, table_name: str, from_last_day: Optional[int] = None):
    """
    1. Liệt kê các file .dat trong thư mục.
    2. Tính toán checkpoint dựa trên số ngày gần nhất (from_last_day).
    3. Đọc dữ liệu chứng khoán của từng file nhị phân.
    4. Chỉ thực hiện DROP TABLE khi đọc toàn bộ (from_last_day = None).
    5. Thực hiện Upsert 1:1 vào DuckDB.
    """
    # Bước 1: Liệt kê các file .dat trong folder
    pd1 = list_files_in_folder(folder_path, file_extension=".dat")
    
    if pd1.empty:
        print("Không tìm thấy file .dat nào trong thư mục được chỉ định.")
        return

    # Bước 2: Tính toán ngày checkpoint (from_date) từ tham số from_last_day
    from_date = None
    if from_last_day is not None:
        from_date = datetime.now() - timedelta(days=from_last_day)

    all_stock_data = []

    # Bước 3: Duyệt qua từng file, đọc dữ liệu thô và ghép mã Ticker
    for _, row in pd1.iterrows():
        file_name = row['file_name']
        file_path = row['file_path']
        
        # Lấy Ticker bằng cách bỏ phần mở rộng .dat (Ví dụ: 'AAA.dat' -> 'AAA')
        ticker = os.path.splitext(file_name)[0]
        
        # Đọc dữ liệu file .dat kèm checkpoint ngày
        pd2 = read_amibroker_dat(file_path, from_date=from_date) 
        
        if pd2 is not None and not pd2.empty:
            pd2.insert(0, 'Ticker', ticker)
            all_stock_data.append(pd2)
            
    if not all_stock_data:
        print(f"Không trích xuất được dữ liệu mới/hợp lệ từ thư mục: {folder_path}")
        return

    # Gộp tất cả các dữ liệu đơn lẻ thành một DataFrame tổng
    df_combined = pd.concat(all_stock_data, ignore_index=True)
    if not df_combined.empty:
        # Ép kiểu dữ liệu Date về dạng chuỗi chỉ có Ngày (YYYY-MM-DD) hoặc chuẩn datetime.date
        df_combined['Date'] = pd.to_datetime(df_combined['Date']).dt.date
        # SỬA LỖI DUPLICATE KEY TRÊN DATAFRAME, Sắp xếp theo thứ tự ngày tăng dần và chỉ giữ lại bản ghi cuối cùng nếu trùng (Ticker, Date)
        df_combined.drop_duplicates(subset=['Ticker', 'Date'], keep='last', inplace=True)

    # Chỉ DROP TABLE khi nạp lại toàn bộ (from_last_day = None)
    if from_last_day is None:
        print(f"-> Phát hiện cấu hình quét ALL. Thực hiện DROP TABLE: {table_name}")
        con.execute(f"DROP TABLE IF EXISTS {table_name};")
        
    # Tạo bảng đích nếu chưa tồn tại với Khóa chính kết hợp
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            Ticker VARCHAR,
            Date DATE,
            Open DOUBLE,
            High DOUBLE,
            Low DOUBLE,
            Close DOUBLE,
            Volume BIGINT,
            OpenInt DOUBLE,
            PRIMARY KEY (Ticker, Date)
        );
    """)

    # Tự động tạo mệnh đề UPDATE cho cấu trúc Upsert
    exclude_cols = ['Ticker', 'Date']
    update_cols = [col for col in df_combined.columns if col not in exclude_cols]
    update_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_cols])

    # Thực hiện lệnh INSERT ON CONFLICT (Upsert) 1:1 bảo vệ dữ liệu cũ
    upsert_query = f"""
        INSERT INTO {table_name} SELECT * FROM df_combined
        ON CONFLICT(Ticker, Date) DO UPDATE SET {update_clause};
    """
    
    con.execute(upsert_query)
    
@timeit
@toggle_print(allow_print=False)
def syncAmibroker_EOD(con, from_last_day: Optional[int] = None):
    three_days_ago = datetime.now() - timedelta(days=3)    
    # Khai báo mảng chứa cặp cấu hình (folder_path, table_name) tương ứng 1:1
    sync_configs = [
        (AMIBROKER_EOD_ACTIVE_PATH, "raw_active_eod"),
        (AMIBROKER_EOD_COMMODITY_PATH, "raw_commodity_eod"),
        (AMIBROKER_EOD_FOREIGN_PATH, "raw_foreign_eod"),
        (AMIBROKER_EOD_FUTURES_PATH, "raw_futures_eod"),
        (AMIBROKER_EOD_INDEX_PATH, "raw_index_eod"),
        (AMIBROKER_EOD_INDUSTRY_PATH, "raw_industry_eod"),
        (AMIBROKER_EOD_MARKET_PATH, "raw_market_eod"),
        (AMIBROKER_EOD_OTHER_PATH, "raw_other_eod"),
        (AMIBROKER_EOD_PROP_PATH, "raw_prop_eod"),
        (AMIBROKER_EOD_STOCK_PATH, "raw_stock_eod"),
        (AMIBROKER_EOD_SUPPLYDEMAND_PATH, "raw_supplydemand_eod"),
        (AMIBROKER_EOD_WARRANT_PATH, "raw_warrant_eod"),
    ]
    
    total_categories = len(sync_configs)

    # Sử dụng vòng lặp for và tận dụng kĩ thuật unpack tuple trực tiếp
    for index, (folder_path, table_name) in enumerate(sync_configs, start=1):
        print(f"[{index}/{total_categories}] Tiến hành xử lý dữ liệu cho bảng: {table_name}")

        upsert_stock_eod(
            con=con,
            folder_path=str(folder_path),
            table_name=table_name,
            from_last_day=from_last_day
        )
        print("-" * 50)  # Đường gạch phân cách cho log dễ nhìn trực quan

@timeit
@toggle_print(allow_print=False)
def syncAmibroker_Intraday(con, from_last_day: Optional[int] = None):
    
    one_days_ago = datetime.now() - timedelta(days=1)
    # Khai báo mảng chứa cặp cấu hình (folder_path, table_name) tương ứng 1:1
    sync_configs = [
        (AMIBROKER_INTRADAY_FUTURES_PATH, "raw_futures_intraday"),
        (AMIBROKER_INTRADAY_INDEX_PATH, "raw_index_intraday"),
        (AMIBROKER_INTRADAY_STOCK_PATH, "raw_stock_intraday"),
        (AMIBROKER_INTRADAY_WARRANT_PATH, "raw_warrant_intraday"),
    ]

    total_categories = len(sync_configs)

    # Sử dụng vòng lặp for và tận dụng kĩ thuật unpack tuple trực tiếp
    for index, (folder_path, table_name) in enumerate(sync_configs, start=1):
        print(f"[{index}/{total_categories}] Tiến hành xử lý dữ liệu cho bảng: {table_name}")

        upsert_stock_eod(
            con=con,
            folder_path=str(folder_path),
            table_name=table_name,
            from_last_day=from_last_day
        )
        print("-" * 50)  # Đường gạch phân cách cho log dễ nhìn trực quan

@timeit
@toggle_print(allow_print=False)
def upsert_stock_fa(con):
    """
    1. Chạy ngầm file Export Shares.afl qua AmiBroker COM (Python 32-bit).
    2. Spool file broker.log để bắt output từ lệnh _TRACE() trong AFL.
    3. Đọc kết quả từ CSV và Upsert động (Dynamic Schema) vào bảng raw_stock_fa trên DuckDB.
    """
    # CHÚ Ý: Đảm bảo biến DATAFILE_PATH và AMIBROKER_AFL_PATH đã được khai báo hoặc import
    EXPORTED_CSV_PATH = DATAFILE_PATH / "tmp_Export_Shares.csv" 
    AMIBROKER_AFL_SHARES = AMIBROKER_AFL_PATH / "Export Shares.afl"
    
    print(f"[*] Bắt đầu tiến trình cập nhật Fundamental Analysis (FA)...")

    # 1. Reset file log trước khi chạy để đảm bảo chỉ đọc log mới nhất
    if os.path.exists(AMIBROKER_LOG_PATH):
        open(AMIBROKER_LOG_PATH, 'w', encoding='utf-8').close()

    # Hàm để chạy AmiBroker ở luồng (thread) riêng
    def run_amibroker_explore():
        # KHỞI TẠO COM CHO LUỒNG PHỤ (BẮT BUỘC)
        pythoncom.CoInitialize() 
        try:
            # Di chuyển việc Dispatch COM vào bên trong Thread
            ab_thread = win32com.client.Dispatch("Broker.Application")
            aa_thread = ab_thread.Analysis
            aa_thread.LoadFormula(AMIBROKER_AFL_SHARES.as_posix())
            
            # Cấu hình phạm vi quét
            aa_thread.ApplyTo = 0       # 0 = All symbols (Quét toàn bộ thị trường)
            aa_thread.RangeMode = 2     # 2 = 1 last quote (Chỉ lấy ngày gần nhất)
            aa_thread.RangeN = 1
            
            # Chạy lệnh (Đồng bộ)
            aa_thread.Explore()
            
            # Lưu file CSV
            aa_thread.Export(EXPORTED_CSV_PATH.as_posix())
            
        except Exception as e:
            print(f"❌ LỖI trong luồng AmiBroker COM: {e}")
        finally:
            # GIẢI PHÓNG COM KHI THREAD KẾT THÚC
            pythoncom.CoUninitialize()

    # Khởi động luồng chạy AmiBroker
    explore_thread = threading.Thread(target=run_amibroker_explore)
    explore_thread.start()

    # 2. Spool (Tailing) file broker.log do _TRACE() sinh ra trong lúc AmiBroker đang tính toán
    last_pos = 0
    while explore_thread.is_alive():
        if os.path.exists(AMIBROKER_LOG_PATH):
            with open(AMIBROKER_LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_pos)
                new_lines = f.readlines()
                last_pos = f.tell()
                
                for line in new_lines:
                    print(f"[AmiBroker _TRACE]: {line.strip()}")
        
        # Nghỉ 0.5s trước khi quét log tiếp
        time.sleep(0.5)

    # Đọc nốt những dòng log cuối cùng sau khi thread vừa kết thúc
    if os.path.exists(AMIBROKER_LOG_PATH):
        with open(AMIBROKER_LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(last_pos)
            for line in f.readlines():
                print(f"[AmiBroker _TRACE]: {line.strip()}")

    # Đảm bảo luồng chạy đã kết thúc hoàn toàn
    explore_thread.join()
    print("[*] AmiBroker Script Execution Hoàn tất!")

    # 3. Nạp dữ liệu vào DuckDB
    # Chuyển đổi Path object thành chuỗi (string) để os.path.exists nhận diện đúng
    if not os.path.exists(EXPORTED_CSV_PATH.as_posix()):
        print(f"❌ Không tìm thấy file dữ liệu tại {EXPORTED_CSV_PATH.as_posix()}")
        return

    # Đọc CSV (sử dụng as_posix() để tương thích tốt trên Windows)
    df = pd.read_csv(EXPORTED_CSV_PATH.as_posix())

    if df.empty:
        print("❌ Dữ liệu FA trống.")
        return

    # Chuẩn hóa tên cột khóa chính
    if 'Ticker' not in df.columns:
        df.rename(columns={df.columns[0]: 'Ticker'}, inplace=True)
    
    # Ép kiểu dữ liệu an toàn cho Khóa Chính
    df['Ticker'] = df['Ticker'].astype(str)

    # Đăng ký View ảo trên DuckDB
    con.register("df_fa_tmp", df)
    table_name = "raw_stock_fa"

    # Xây dựng câu lệnh CREATE TABLE Động và Gán PRIMARY KEY
    con.execute("CREATE TEMPORARY TABLE _tmp_schema AS SELECT * FROM df_fa_tmp LIMIT 0;")
    schema_info = con.execute("DESCRIBE _tmp_schema;").fetchall()
    
    cols_def = []
    update_cols = []
    
    for row in schema_info:
        col_name, col_type = row[0], row[1]
        if col_name == 'Ticker':
            cols_def.append(f'"{col_name}" {col_type} PRIMARY KEY')
        else:
            cols_def.append(f'"{col_name}" {col_type}')
            update_cols.append(col_name)

    # 4. Thực thi tạo bảng (nếu chưa có)
    create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(cols_def)});"
    con.execute(create_sql)

    # 5. Tạo mệnh đề Upsert (DO UPDATE SET...)
    update_clause = ", ".join([f'"{c}" = EXCLUDED."{c}"' for c in update_cols])

    # Thực hiện lệnh Upsert
    print(f"[*] Đang ghi đè (Upsert) {len(df)} bản ghi FA vào bảng '{table_name}'...")
    con.execute(f"""
        INSERT INTO {table_name}
        SELECT * FROM df_fa_tmp
        ON CONFLICT (Ticker) DO UPDATE SET {update_clause};
    """)
    
    # Dọn dẹp View ảo
    con.execute("DROP TABLE _tmp_schema;")
    con.unregister("df_fa_tmp")
    
    print("[✔] Quá trình Upsert Stock FA hoàn tất thành công!")

@timeit
@toggle_print(allow_print=False)
def upsert_lstTicker(con):
    """
    1. Đọc file Excel lstTicker.xlsx tại sheet có tên 'Ticker'.
    2. Chuẩn hóa dữ liệu văn bản và ép kiểu dữ liệu an toàn cho Khóa chính Ticker.
    3. Tự động phát hiện cấu trúc cột động (Dynamic Schema Setup).
    4. Thực hiện Upsert (INSERT ON CONFLICT) vào bảng 'raw_lstTicker' trong DuckDB.
    """
    # Nếu không truyền đường dẫn cụ thể, tự động lấy file từ thư mục cấu hình mặc định
    SRC_FILE_PATH = DATAFILE_PATH / "lstTicker.xlsx"
    file_path = SRC_FILE_PATH
        
    print(f"[*] Bắt đầu đọc file danh sách mã: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ LỖI: Không tìm thấy file Excel tại đường dẫn: {file_path}")
        return

    try:
        # Đọc dữ liệu trực tiếp từ sheet 'Ticker'
        df = pd.read_excel(file_path, sheet_name="Ticker")
    except Exception as e:
        print(f"❌ LỖI: Không thể đọc sheet 'Ticker' từ file Excel. Chi tiết: {e}")
        # Phương án dự phòng: Nếu lỗi tên sheet, thử đọc sheet đầu tiên
        try:
            print("[!] Thử đọc sheet đầu tiên của file Excel làm dự phòng...")
            df = pd.read_excel(file_path, sheet_name=0)
        except Exception as e_inner:
            print(f"❌ LỖI nghiêm trọng: Thất bại khi đọc file Excel. {e_inner}")
            return

    if df.empty:
        print("❌ CẢNH BÁO: File dữ liệu Excel trống hoặc không có bản ghi nào.")
        return

    # Chuẩn hóa tên cột: Xóa khoảng trắng thừa ở đầu/cuối tên cột
    df.columns = [str(col).strip() for col in df.columns]

    # Kiểm tra cột khóa chính 'Ticker' bắt buộc phải tồn tại
    if 'Ticker' not in df.columns:
        # Nếu không thấy chữ 'Ticker' chính xác, thử tìm cột đầu tiên làm Ticker
        print(f"[!] Không tìm thấy cột tên 'Ticker'. Tự động chọn cột đầu tiên '{df.columns[0]}' làm Ticker.")
        df.rename(columns={df.columns[0]: 'Ticker'}, inplace=True)

    # 🌟 LÀM SẠCH DỮ LIỆU SƠ BỘ:
    # Loại bỏ các hàng có mã Ticker bị trống (NaN)
    df.dropna(subset=['Ticker'], inplace=True)
    
    # Ép kiểu Ticker về String, viết hoa toàn bộ và xóa khoảng trắng (ví dụ: " ssi " -> "SSI")
    df['Ticker'] = df['Ticker'].astype(str).str.strip().str.upper()

    # Loại bỏ hoàn toàn các ký tự xuống dòng hoặc tab trong toàn bộ DataFrame để tránh lỗi SQL bẩn
    df = df.replace(to_replace=[r'\\r', r'\\n', r'\\t'], value=' ', regex=True)

    table_name = "raw_lstTicker"

    # Đăng ký temporary view ảo để DuckDB ánh xạ trực tiếp sang Pandas DataFrame
    con.register("df_ticker_tmp", df)

    # Sử dụng kỹ thuật tạo bảng tạm giới hạn 0 dòng để trích xuất cấu trúc kiểu dữ liệu của các cột
    con.execute("CREATE TEMPORARY TABLE _tmp_ticker_schema AS SELECT * FROM df_ticker_tmp LIMIT 0;")
    schema_info = con.execute("DESCRIBE _tmp_ticker_schema;").fetchall()
    
    cols_def = []
    update_cols = []
    
    # Vòng lặp duyệt qua Schema để sinh câu lệnh SQL động
    for row in schema_info:
        col_name, col_type = row[0], row[1]
        # Bao bọc tên cột bằng dấu nháy kép "" để chống lỗi các tên cột có dấu cách hoặc ký tự đặc biệt
        if col_name == 'Ticker':
            cols_def.append(f'"{col_name}" {col_type} PRIMARY KEY')
        else:
            cols_def.append(f'"{col_name}" {col_type}')
            update_cols.append(col_name)

    # 1. Tạo bảng thực tế nếu chưa tồn tại kèm định nghĩa khóa chính PRIMARY KEY (Ticker)
    create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(cols_def)});"
    con.execute(create_sql)

    # 2. Xây dựng mệnh đề UPDATE cho cấu trúc DO UPDATE SET khi có xung đột khóa chính
    # Sinh chuỗi dạng: "Company Name" = EXCLUDED."Company Name", "Industry" = EXCLUDED."Industry"
    update_clause = ", ".join([f'"{c}" = EXCLUDED."{c}"' for c in update_cols])

    # 3. Thực thi lệnh INSERT hỏa tốc kết hợp cấu trúc xử lý ON CONFLICT của DuckDB
    print(f"[*] Đang tiến hành ghi đè (Upsert) {len(df)} mã chứng khoán vào bảng '{table_name}'...")
    
    upsert_query = f"""
        INSERT INTO {table_name}
        SELECT * FROM df_ticker_tmp
        ON CONFLICT (Ticker) DO UPDATE SET {update_clause};
    """
    con.execute(upsert_query)
    
    # Dọn dẹp tài nguyên và giải phóng view tạm
    con.execute("DROP TABLE _tmp_ticker_schema;")
    con.unregister("df_ticker_tmp")
    
    print(f"[✔] Quá trình cập nhật danh mục bảng '{table_name}' hoàn tất thành công!")