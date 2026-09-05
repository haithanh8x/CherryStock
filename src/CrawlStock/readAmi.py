import struct
import pandas as pd
import numpy as np
import os
import re
import threading
import time

from Ults.DuckLib import DuckDBManager
from Ults.Timing import timeit, toggle_print
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Sequence
from Ults.lstFiles import list_files_in_folder
from Ults.lstPara import DATAFILE_PATH, AMIBROKER_AFL_PATH, AMIBROKER_LOG_PATH

from cherrystock.application.ports.amibroker import AmiBrokerPort
from cherrystock.application.ports.market_data_sync import MarketDataSyncPort
from cherrystock.application.services.sync_amibroker_fa import SyncAmiBrokerFAService
from cherrystock.application.services.sync_amibroker_market_data import SyncAmiBrokerMarketDataService
from cherrystock.config.settings import settings


def _build_default_amibroker_adapter() -> "AmiBrokerPort":
    """Create the default Windows adapter only when AmiBroker sync is requested."""
    if os.name != "nt":
        raise RuntimeError("AmiBroker integration is available only on Windows.")

    from cherrystock.infrastructure.amibroker.windows_adapter import WindowsAmiBrokerAdapter

    return WindowsAmiBrokerAdapter(database_path=settings.amibroker_database_path)


class DuckDBMarketDataSyncAdapter:
    """Adapter that satisfies the market-data sync port using local upsert routine."""

    def __init__(self, connection=None) -> None:
        self._connection = connection

    def upsert_stock_eod(
        self,
        folder_path,
        table_name: str,
        from_last_day: int | None = None,
    ) -> None:
        upsert_stock_eod(
            folder_path=str(folder_path),
            table_name=table_name,
            from_last_day=from_last_day,
            connection=self._connection,
        )

    def reset_intraday_targets(self, table_names: Sequence[str]) -> None:
        reset_amibroker_intraday_tables(
            table_names=table_names,
            connection=self._connection,
        )

    def upsert_intraday(
        self,
        folder_path,
        table_name: str,
        from_last_day: int | None = None,
    ) -> None:
        upsert_amibroker_intraday(
            folder_path=str(folder_path),
            table_name=table_name,
            from_last_day=from_last_day,
            connection=self._connection,
        )

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
def upsert_stock_eod(
    folder_path: str,
    table_name: str,
    from_last_day: Optional[int] = None,
    connection=None,
):
    con = connection or DuckDBManager.get_connection()
    owns_connection = connection is None
    """
    1. Liệt kê các file .dat trong thư mục.
    2. Tính toán checkpoint dựa trên số ngày gần nhất (from_last_day).
    3. Đọc dữ liệu chứng khoán của từng file nhị phân.
    4. Chỉ thực hiện DROP TABLE khi đọc toàn bộ (from_last_day = None).
    5. Thực hiện Upsert 1:1 vào DuckDB.
    """
    try:
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
    finally:
        if owns_connection:
            DuckDBManager.close_connection(con)
    

_AMIBROKER_INTRADAY_DTYPE = np.dtype(
    [
        ("Date", "<i4"),
        ("RawTime", "<i4"),
        ("Open", "<f4"),
        ("High", "<f4"),
        ("Low", "<f4"),
        ("Close", "<f4"),
        ("Volume", "<f4"),
        ("OpenInt", "<f4"),
    ]
)


def _quote_table_identifier(table_name: str) -> str:
    """Quote a trusted simple DuckDB table identifier."""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name) is None:
        raise ValueError(f"Invalid table name: {table_name!r}")
    return f'"{table_name}"'


def _normalize_from_date_int(from_date=None) -> int | None:
    if from_date is None:
        return None
    if isinstance(from_date, str):
        return int(from_date.replace("-", "").replace("/", ""))
    if isinstance(from_date, datetime):
        return int(from_date.strftime("%Y%m%d"))
    raise TypeError("from_date must be None, str, or datetime")


def _decode_intraday_time(raw_time: pd.Series) -> pd.DataFrame:
    """
    Decode the second 32-bit field used by FireAnt/AmiBroker intraday records.

    Supported numeric forms:
    - HHMM
    - HHMMSS
    - HHMMSSmmm

    RawTime is persisted unchanged even after decoding so the source value remains
    auditable. Duplicate timestamps are handled separately by TickSeq.
    """
    values = raw_time.astype("int64").to_numpy()
    if np.any(values < 0):
        bad = values[values < 0][:5].tolist()
        raise ValueError(f"Negative AmiBroker intraday RawTime values: {bad}")

    hours = np.zeros(len(values), dtype=np.int64)
    minutes = np.zeros(len(values), dtype=np.int64)
    seconds = np.zeros(len(values), dtype=np.int64)
    millis = np.zeros(len(values), dtype=np.int64)

    mask_hhmm = values <= 2359
    mask_hhmmss = (values > 2359) & (values <= 235959)
    mask_hhmmssmmm = (values > 235959) & (values <= 235959999)
    mask_unknown = ~(mask_hhmm | mask_hhmmss | mask_hhmmssmmm)

    # HHMM
    hours[mask_hhmm] = values[mask_hhmm] // 100
    minutes[mask_hhmm] = values[mask_hhmm] % 100

    # HHMMSS
    hours[mask_hhmmss] = values[mask_hhmmss] // 10000
    minutes[mask_hhmmss] = (values[mask_hhmmss] // 100) % 100
    seconds[mask_hhmmss] = values[mask_hhmmss] % 100

    # HHMMSSmmm
    hours[mask_hhmmssmmm] = values[mask_hhmmssmmm] // 10000000
    minutes[mask_hhmmssmmm] = (values[mask_hhmmssmmm] // 100000) % 100
    seconds[mask_hhmmssmmm] = (values[mask_hhmmssmmm] // 1000) % 100
    millis[mask_hhmmssmmm] = values[mask_hhmmssmmm] % 1000

    invalid = (
        mask_unknown
        | (hours > 23)
        | (minutes > 59)
        | (seconds > 59)
        | (millis > 999)
    )
    if np.any(invalid):
        bad = values[invalid][:10].tolist()
        raise ValueError(
            "Unsupported AmiBroker intraday RawTime encoding. "
            f"Examples: {bad}. Expected HHMM, HHMMSS, or HHMMSSmmm."
        )

    return pd.DataFrame(
        {
            "Hour": hours,
            "Minute": minutes,
            "Second": seconds,
            "Millisecond": millis,
        }
    )


@toggle_print(allow_print=False)
def read_amibroker_intraday_dat(file_path, from_date=None):
    """
    Read one FireAnt/AmiBroker 32-byte intraday .dat file at tick grain.

    Binary layout verified against the current FireAnt data files:
        int32 Date (YYYYMMDD)
        int32 RawTime
        float Open
        float High
        float Low
        float Close
        float Volume
        float OpenInt

    FireAnt intraday is tick-level. OpenInt is preserved exactly as source data;
    for Vietnamese stocks/futures FireAnt documents values 1/2/3 as active
    sell/buy/both transaction classifications.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file Intraday: {file_path}")

    file_size = file_path.stat().st_size
    record_size = _AMIBROKER_INTRADAY_DTYPE.itemsize
    if file_size % record_size != 0:
        raise ValueError(
            f"File {file_path} có size {file_size} không chia hết cho "
            f"record size {record_size}."
        )

    records = np.fromfile(file_path, dtype=_AMIBROKER_INTRADAY_DTYPE)
    if records.size == 0:
        return pd.DataFrame(
            columns=[
                "Date",
                "DateTime",
                "RawTime",
                "TickSeq",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "OpenInt",
            ]
        )

    valid_date = (records["Date"] >= 19900101) & (records["Date"] <= 20501231)
    records = records[valid_date]

    from_date_int = _normalize_from_date_int(from_date)
    if from_date_int is not None:
        records = records[records["Date"] >= from_date_int]

    if records.size == 0:
        return pd.DataFrame()

    df = pd.DataFrame.from_records(records)
    time_parts = _decode_intraday_time(df["RawTime"])

    base_date = pd.to_datetime(df["Date"].astype(str), format="%Y%m%d", errors="raise")
    df["DateTime"] = (
        base_date
        + pd.to_timedelta(time_parts["Hour"], unit="h")
        + pd.to_timedelta(time_parts["Minute"], unit="m")
        + pd.to_timedelta(time_parts["Second"], unit="s")
        + pd.to_timedelta(time_parts["Millisecond"], unit="ms")
    )

    # Preserve same-timestamp ticks deterministically in original file order.
    df["TickSeq"] = (
        df.groupby(["Date", "RawTime"], sort=False, dropna=False)
        .cumcount()
        .astype("int64")
    )

    prices = ["Open", "High", "Low", "Close", "OpenInt"]
    for column in prices:
        df[column] = pd.to_numeric(df[column], errors="raise").astype("float64")

    volume = pd.to_numeric(df["Volume"], errors="raise")
    if (~np.isfinite(volume.to_numpy())).any() or (volume < 0).any():
        raise ValueError(f"Invalid Volume values detected in {file_path}")
    if not np.allclose(volume.to_numpy(), np.rint(volume.to_numpy()), atol=1e-6):
        raise ValueError(f"Non-integer tick Volume values detected in {file_path}")
    df["Volume"] = np.rint(volume.to_numpy()).astype("int64")

    df["Date"] = base_date.dt.date

    return df[
        [
            "Date",
            "DateTime",
            "RawTime",
            "TickSeq",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "OpenInt",
        ]
    ]


def _list_intraday_dat_files(folder_path: str | Path) -> list[Path]:
    """
    Discover .dat files recursively.

    Recursive discovery also supports FireAnt/MetaKit installations that group
    intraday symbols into alphabetic subdirectories.
    """
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Không tìm thấy thư mục Intraday: {folder}")
    return sorted(path for path in folder.rglob("*.dat") if path.is_file())


def _create_intraday_table(con, table_name: str) -> None:
    table = _quote_table_identifier(table_name)
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            Ticker VARCHAR NOT NULL,
            Date DATE NOT NULL,
            DateTime TIMESTAMP NOT NULL,
            RawTime INTEGER NOT NULL,
            TickSeq BIGINT NOT NULL,
            Open DOUBLE,
            High DOUBLE,
            Low DOUBLE,
            Close DOUBLE,
            Volume BIGINT,
            OpenInt DOUBLE,
            PRIMARY KEY (Ticker, Date, RawTime, TickSeq)
        );
        """
    )


def reset_amibroker_intraday_tables(
    table_names: Sequence[str],
    connection=None,
) -> None:
    """Drop all configured intraday targets before a full/init reload."""
    con = connection or DuckDBManager.get_connection()
    owns_connection = connection is None
    try:
        for table_name in table_names:
            table = _quote_table_identifier(table_name)
            print(f"-> Init Intraday: DROP TABLE IF EXISTS {table_name}")
            con.execute(f"DROP TABLE IF EXISTS {table};")
    finally:
        if owns_connection:
            DuckDBManager.close_connection(con)


@timeit
@toggle_print(allow_print=False)
def upsert_amibroker_intraday(
    folder_path: str,
    table_name: str,
    from_last_day: Optional[int] = None,
    connection=None,
):
    """
    Load one FireAnt/AmiBroker intraday source folder into one tick-level table.

    Unlike EOD, intraday keeps every tick. It never collapses data to (Ticker, Date).
    """
    con = connection or DuckDBManager.get_connection()
    owns_connection = connection is None
    table = _quote_table_identifier(table_name)

    try:
        files = _list_intraday_dat_files(folder_path)
        if not files:
            raise RuntimeError(f"Không tìm thấy file .dat trong: {folder_path}")

        from_date = None
        if from_last_day is not None:
            from_date = datetime.now() - timedelta(days=from_last_day)

        _create_intraday_table(con, table_name)

        total_rows = 0
        loaded_files = 0

        for file_path in files:
            ticker = file_path.stem
            df_intraday_tmp = read_amibroker_intraday_dat(
                file_path,
                from_date=from_date,
            )
            if df_intraday_tmp is None or df_intraday_tmp.empty:
                continue

            df_intraday_tmp.insert(0, "Ticker", ticker)

            con.register("df_intraday_tmp", df_intraday_tmp)
            try:
                con.execute(
                    f"""
                    INSERT INTO {table} (
                        Ticker,
                        Date,
                        DateTime,
                        RawTime,
                        TickSeq,
                        Open,
                        High,
                        Low,
                        Close,
                        Volume,
                        OpenInt
                    )
                    SELECT
                        Ticker,
                        Date,
                        DateTime,
                        RawTime,
                        TickSeq,
                        Open,
                        High,
                        Low,
                        Close,
                        Volume,
                        OpenInt
                    FROM df_intraday_tmp
                    ON CONFLICT (Ticker, Date, RawTime, TickSeq)
                    DO UPDATE SET
                        DateTime = EXCLUDED.DateTime,
                        Open = EXCLUDED.Open,
                        High = EXCLUDED.High,
                        Low = EXCLUDED.Low,
                        Close = EXCLUDED.Close,
                        Volume = EXCLUDED.Volume,
                        OpenInt = EXCLUDED.OpenInt;
                    """
                )
            finally:
                con.unregister("df_intraday_tmp")

            total_rows += len(df_intraday_tmp)
            loaded_files += 1

        print(
            f"[✔] {table_name}: loaded/upserted {total_rows:,} ticks "
            f"from {loaded_files:,}/{len(files):,} files."
        )
    finally:
        if owns_connection:
            DuckDBManager.close_connection(con)


@timeit
@toggle_print(allow_print=False)
def syncAmibroker_EOD(from_last_day: Optional[int] = None, connection=None): 
    sync_port: MarketDataSyncPort = DuckDBMarketDataSyncAdapter(connection=connection)
    service = SyncAmiBrokerMarketDataService(sync_port=sync_port)
    service.sync_eod(
        eod_targets=settings.amibroker_eod_targets,
        from_last_day=from_last_day,
    )

@timeit
@toggle_print(allow_print=False)
def syncAmibroker_Intraday(
    from_last_day: Optional[int] = None,
    connection=None,
    reset: Optional[bool] = None,
):
    """
    Sync all four FireAnt/AmiBroker Intraday sources:
    futures, index, stock and warrant.

    Default behavior:
    - from_last_day=None -> init/full reload and reset all four target tables first.
    - from_last_day=N    -> incremental upsert for the most recent N calendar days.

    Pass reset explicitly only when an operator needs to override that default.
    """
    should_reset = (from_last_day is None) if reset is None else reset

    sync_port: MarketDataSyncPort = DuckDBMarketDataSyncAdapter(connection=connection)
    service = SyncAmiBrokerMarketDataService(sync_port=sync_port)
    service.sync_intraday(
        intraday_targets=settings.amibroker_intraday_targets,
        from_last_day=from_last_day,
        reset=should_reset,
    )

@timeit
@toggle_print(allow_print=False)
def upsert_stock_fa(amibroker: "AmiBrokerPort | None" = None, connection=None):
    """
    1. Chạy ngầm file Export Shares.afl qua AmiBroker COM (Python 32-bit).
    2. Spool file broker.log để bắt output từ lệnh _TRACE() trong AFL.
    3. Đọc kết quả từ CSV và Upsert động (Dynamic Schema) vào bảng raw_stock_fa trên DuckDB.
    """
    # CHÚ Ý: Đảm bảo biến DATAFILE_PATH và AMIBROKER_AFL_PATH đã được khai báo hoặc import
    EXPORTED_CSV_PATH = DATAFILE_PATH / "tmp_Export_Shares.csv" 
    AMIBROKER_AFL_SHARES = AMIBROKER_AFL_PATH / "Export Shares.afl"
    con = connection or DuckDBManager.get_connection()
    owns_connection = connection is None

    try:
        if amibroker is None:
            amibroker = _build_default_amibroker_adapter()

        service = SyncAmiBrokerFAService(amibroker)

        print(f"[*] Bắt đầu tiến trình cập nhật Fundamental Analysis (FA)...")

    # 1. Reset file log trước khi chạy để đảm bảo chỉ đọc log mới nhất
        if os.path.exists(AMIBROKER_LOG_PATH):
            open(AMIBROKER_LOG_PATH, 'w', encoding='utf-8').close()

    # Hàm để chạy AmiBroker ở luồng (thread) riêng
        def run_amibroker_explore():
            try:
                service.run_latest_export(
                    formula_path=AMIBROKER_AFL_SHARES,
                    export_path=EXPORTED_CSV_PATH,
                    apply_to=0,
                    range_mode=2,
                    range_n=1,
                )
            except Exception as e:
                print(f"❌ LỖI trong luồng AmiBroker COM: {e}")

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
    finally:
        if owns_connection:
            DuckDBManager.close_connection(con)

@timeit
@toggle_print(allow_print=False)
def upsert_lstTicker(connection=None, repository=None):
    """
    1. Đọc file Excel lstTicker.xlsx tại sheet có tên 'Ticker'.
    2. Chuẩn hóa dữ liệu văn bản và ép kiểu dữ liệu an toàn cho Khóa chính Ticker.
    3. Tự động phát hiện cấu trúc cột động (Dynamic Schema Setup).
    4. Thực hiện Upsert (INSERT ON CONFLICT) vào bảng 'raw_lstTicker' trong DuckDB.
    """
    # Nếu không truyền đường dẫn cụ thể, tự động lấy file từ thư mục cấu hình mặc định
    SRC_FILE_PATH = DATAFILE_PATH / "lstTicker.xlsx"
    file_path = SRC_FILE_PATH
    con = connection or DuckDBManager.get_connection()
    owns_connection = connection is None
    try:
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

        if repository is not None:
            repository.replace_from_dataframe(dataframe=df, table_name=table_name)
            print(f"[✔] Quá trình cập nhật danh mục bảng '{table_name}' hoàn tất thành công!")
            return

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

    # 1. Xóa bảng cũ (nếu có) rồi tạo bảng thực tế kèm định nghĩa khóa chính PRIMARY KEY (Ticker)
    #    Theo yêu cầu: thêm DROP TABLE phía trước khi CREATE
        create_sql = f"DROP TABLE IF EXISTS {table_name}; CREATE TABLE {table_name} ({', '.join(cols_def)});"
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
    finally:
        if owns_connection:
            DuckDBManager.close_connection(con)