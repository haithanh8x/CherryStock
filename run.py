import sys
import io

from CrawlStock.readYahooFinance import syncYahooFinance_EOD
from Ults import DuckLib
from Ults.Timing import timeit
from CrawlStock.readAmi import syncAmibroker_EOD, syncAmibroker_Intraday, upsert_lstTicker, upsert_stock_fa
from Ults.DuckLib import DuckDBManager, executeDuckSQL
from Ults.getData import get_last_point
from lstPara import DUCKDB_SQL_PATH, START_DATE
from calcEngine.calcIndexes import calculate_VNINDEX_NOT_VIN
from CrawlStock.readYahooFinance import syncYahooFinance_EOD
from calcEngine import calc_fv_Trend

# --- HÀM MAIN ---
@timeit
def main():
        conn = DuckDBManager.get_connection()
        days_diff_raw = get_last_point()   # Cộng thêm 1 ngày để đồng bộ từ ngày tiếp theo sau lần cập nhật cuối cùng
        days_diff = 15
        if days_diff_raw is not None:
        # Nếu kết quả là đối tượng Timedelta của Pandas, dùng thuộc tính .days để lấy số ngày
                if hasattr(days_diff_raw, 'days'):
                        days_diff = int(days_diff_raw.days)
                else:
                        # Nếu đã là dạng số hoặc chuỗi số, ép trực tiếp về int
                        days_diff = int(days_diff_raw)


        # ---------------------------------------------------------------------------------
        # syncAmibroker_Intraday(conn, from_last_day=0)

        syncAmibroker_EOD(from_last_day=days_diff)
        syncYahooFinance_EOD(from_last_day=days_diff)
        upsert_stock_fa()
        upsert_lstTicker()
        executeDuckSQL(con=conn, sql_file_path=str(DUCKDB_SQL_PATH / "updateHoliday.sql"))

        # cal indexes
        calculate_VNINDEX_NOT_VIN()
        calc_fv_Trend.cal_Moving_Average(from_last_day=days_diff)

        # sync DuckDB metadata
        DuckLib.exportDuckDB_metadata()
        # --------------------------------------------------------------------------------- 
        DuckDBManager.close_connection()

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
    main() # thực thi hàm main() để chạy toàn bộ quy trình đồng bộ dữ liệu từ Amibroker vào DuckDB/MotherDuckDB
