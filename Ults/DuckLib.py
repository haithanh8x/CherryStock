import os
import duckdb

from Ults.Timing import timeit, toggle_print
from lstPara import DB_MOTHERDUCK_PATH, DB_MOTHERDUCK_TOKEN, DB_PATH_CHERRYMON, LOCAL_DB_PATH


class DuckDBManager:
    """Manage a shared DuckDB connection for the whole workflow."""

    _instance: duckdb.DuckDBPyConnection | None = None

    @classmethod
    def _create_connection(cls, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        """Create a fresh DuckDB connection using the configured environment."""
        db_env = (os.getenv("DUCKDB_ENV", "local") or "local").strip().lower()

        if db_env == "cloud":
            token = os.getenv("MOTHERDUCK_TOKEN", DB_MOTHERDUCK_TOKEN)
            return duckdb.connect(f"md:?token={token}")

        local_path = os.getenv("LOCAL_DB_PATH", LOCAL_DB_PATH)
        return duckdb.connect(local_path, read_only=read_only)

    @classmethod
    def get_connection(cls, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        """Return the shared connection, creating it if needed."""
        if cls._instance is None or getattr(cls._instance, "closed", False):
            cls._instance = cls._create_connection(read_only)
        return cls._instance

    @classmethod
    def close_connection(cls) -> None:
        """Close the shared connection and clear the singleton reference."""
        if cls._instance is not None and not getattr(cls._instance, "closed", True):
            try:
                cls._instance.close()
            except Exception:
                pass
        cls._instance = None

    def __enter__(self):
        return self.get_connection()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Keep the shared connection alive so later steps can reuse it.
        return False

@timeit
@toggle_print(allow_print=False)
def executeDuckSQL(con: duckdb.DuckDBPyConnection, sql_file_path: str) -> None:
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

def returnSQL(con: duckdb.DuckDBPyConnection, sqlString: str):
    """
    Thực thi câu lệnh SELECT trên kết nối DuckDB và trả về kết quả dưới dạng Pandas DataFrame.
    
    :param con: Đối tượng kết nối DuckDB (duckdb.DuckDBPyConnection)
    :param sqlString: Chuỗi câu lệnh SQL SELECT cần truy vấn (str)
    :return: Pandas DataFrame chứa kết quả truy vấn, hoặc None nếu xảy ra lỗi.
    """
    # Loại bỏ khoảng trắng thừa để kiểm tra tính hợp lệ của câu lệnh
    clean_sql = sqlString.strip().lower()
    
    # Rào trước nếu câu lệnh truyền vào không phải là SELECT hoặc WITH
    if not (clean_sql.startswith("select") or clean_sql.startswith("with")):
        print("⚠️ [Cảnh báo]: Hàm này chỉ hỗ trợ các câu lệnh truy vấn dữ liệu (SELECT / WITH).")
        return None

    try:
        # Chuyển thẳng kết quả từ vùng nhớ của DuckDB sang Pandas DataFrame
        # Cách này đem lại tốc độ xử lý và đọc ghi tối ưu cực hạn trên RAM
        df_result = con.execute(sqlString).df()
        return df_result
            
    except Exception as e:
        print(f"[Lỗi thực thi SQL trong returnSQL]: {e}")
        return None