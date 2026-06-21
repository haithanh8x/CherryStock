import struct
import pandas as pd
import os

from datetime import datetime, timedelta
from Ults.Timing import timeit
from Ults.lstFiles import list_files_in_folder
from lstPara import AMIBROKER_EOD_ACTIVE_PATH, AMIBROKER_EOD_COMMODITY_PATH, AMIBROKER_EOD_FOREIGN_PATH, AMIBROKER_EOD_FUTURES_PATH, AMIBROKER_EOD_INDEX_PATH, AMIBROKER_EOD_INDUSTRY_PATH, AMIBROKER_EOD_MARKET_PATH, AMIBROKER_EOD_OTHER_PATH, AMIBROKER_EOD_PROP_PATH, AMIBROKER_EOD_STOCK_PATH, AMIBROKER_EOD_SUPPLYDEMAND_PATH, AMIBROKER_EOD_WARRANT_PATH, AMIBROKER_INTRADAY_FUTURES_PATH, AMIBROKER_INTRADAY_INDEX_PATH, AMIBROKER_INTRADAY_STOCK_PATH, AMIBROKER_INTRADAY_WARRANT_PATH

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
def upsert_stock_eod(con, folder_path: str, table_name: str, from_date=None):
    """
    1. Liệt kê các file .dat trong thư mục.
    2. Đọc dữ liệu chứng khoán của từng file.
    3. Gộp dữ liệu kèm cột Ticker tương ứng với file_name.
    4. Thực hiện Upsert 1:1 vào DuckDB.
    """
    # Bước 1: Liệt kê các file .dat trong folder
    # print(f"-> Đang quét thư mục: {folder_path}")
    pd1 = list_files_in_folder(folder_path, file_extension=".dat")

    
    if pd1.empty:
        print("Không tìm thấy file .dat nào trong thư mục được chỉ định.")
        return

    all_stock_data = []

    # Bước 2 & 3: Duyệt qua từng file, đọc dữ liệu và ghép tên file (Ticker)
    #print(f"-> Phát hiện {len(pd1)} file. Đang đọc dữ liệu AmiBroker...")
    for _, row in pd1.iterrows():
        file_name = row['file_name']
        file_path = row['file_path']
        
        # Lấy Ticker bằng cách bỏ phần mở rộng .dat (Ví dụ: 'AAA.dat' -> 'AAA')
        ticker = os.path.splitext(file_name)[0]
        
        # Đọc dữ liệu file .dat
        pd2 = read_amibroker_dat(file_path, from_date=from_date) 
        
        # Kiểm tra nếu file có dữ liệu hợp lệ
        if pd2 is not None and not pd2.empty:
            # Chèn thêm cột Ticker vào đầu hoặc cuối dataframe
            pd2.insert(0, 'Ticker', ticker)
            all_stock_data.append(pd2)
            
    if not all_stock_data:
        print("Không trích xuất được dữ liệu hợp lệ từ bất kỳ file nào.")
        return

    # Gộp tất cả các DataFrames lẻ thành một DataFrame tổng duy nhất
    df_combined = pd.concat(all_stock_data, ignore_index=True)
    
    con.execute(f"DROP TABLE IF EXISTS {table_name};")
    # Tạo bảng đích với Khóa chính kết hợp (Ticker, Date) nếu chưa tồn tại
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

    # Tự động tạo mệnh đề UPDATE cho tất cả các cột trừ khóa chính (Ticker, Date)
    exclude_cols = ['Ticker', 'Date']
    update_cols = [col for col in df_combined.columns if col not in exclude_cols]
    update_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_cols])

    # Thực hiện lệnh INSERT ON CONFLICT (Upsert) 1:1
    # print(f"-> Đang thực hiện Upsert {len(df_combined)} bản ghi vào bảng '{table_name}' trong DuckDB...")
    
    upsert_query = f"""
        INSERT INTO {table_name} SELECT * FROM df_combined
        ON CONFLICT(Ticker, Date) DO UPDATE SET {update_clause};
    """
    
    con.execute(upsert_query)
    #print("Quá trình Upsert hoàn tất thành công!")
    
@timeit
def syncAmibroker_EOD(con):
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
            from_date=three_days_ago
        )
        print("-" * 50)  # Đường gạch phân cách cho log dễ nhìn trực quan
    
    con.close()

@timeit
def syncAmibroker_Intraday(con):
    
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
            con,
            folder_path=str(folder_path),
            table_name=table_name,
            from_date=one_days_ago
        )
        print("-" * 50)  # Đường gạch phân cách cho log dễ nhìn trực quan
    
    con.close()