import os
import duckdb

from Ults.Timing import timeit, toggle_print
from lstPara import DB_MOTHERDUCK_PATH, DB_MOTHERDUCK_TOKEN, DB_PATH_CHERRYMON

# DuckDB connection functions
def getCherryMon_motherDuck() -> duckdb.DuckDBPyConnection:
    """ Khởi tạo và trả về kết nối tới MotherDuck """
    return duckdb.connect(
        database=DB_MOTHERDUCK_PATH, 
        config={"motherduck_token": DB_MOTHERDUCK_TOKEN}
    )

def getCherryMon_local() -> duckdb.DuckDBPyConnection:
    """ Khởi tạo và trả về kết nối tới cơ sở dữ liệu cục bộ """
    return duckdb.connect(
        database=DB_PATH_CHERRYMON
    )

@timeit
@toggle_print(allow_print=False)
def executeDuckSQL(con, sql_file_path: str) -> None:
    """
    Thực thi file script SQL để cập nhật trạng thái Holiday trong DuckDB.
    
    Parameters:
    - con: Đối tượng kết nối DuckDB (DuckDB Connection)
    - sql_file_path: Đường dẫn đến file chứa script SQL (updateHoliday.sql)
    """
    # 1. Kiểm tra xem file SQL có tồn tại hay không để tránh lỗi hệ thống
    if not os.path.exists(sql_file_path):
        raise FileNotFoundError(f"Không tìm thấy file SQL tại đường dẫn: {sql_file_path}")
    
    try:
        # 2. Đọc nội dung file SQL bằng UTF-8 để tránh lỗi font tiếng Việt (nếu có comment)
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_script = file.read()
        
        # 3. Thực thi đoạn script SQL trên kết nối hiện tại
        print(f"Đang thực thi script từ file: {sql_file_path}...")
        con.execute(sql_script)
        print("Cập nhật dữ liệu thành công!")
        
    except Exception as e:
        print(f"Có lỗi xảy ra trong quá trình thực thi: {e}")
        raise e