import sys
import io

from Ults.Timing import timeit
from CrawlStock.readAmi import syncAmibroker_EOD, syncAmibroker_Intraday, upsert_lstTicker, upsert_stock_fa
from Ults.DuckLib import executeDuckSQL, getCherryMon_local, getCherryMon_motherDuck
from lstPara import DUCKDB_SQL_PATH

# --- HÀM MAIN ---
@timeit
def main():
        # Kết nối đến cơ sở dữ liệu DuckDB hay MotherDuckDB
        conn = getCherryMon_local()
                
        syncAmibroker_EOD(conn, from_last_day=1)
        #syncAmibroker_Intraday(conn, from_last_day=0)
        upsert_stock_fa(con=conn)
        upsert_lstTicker(con=conn)

        executeDuckSQL(con=conn, sql_file_path=str(DUCKDB_SQL_PATH / "updateHoliday.sql"))

        conn.close()

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
    main() # thực thi hàm main() để chạy toàn bộ quy trình đồng bộ dữ liệu từ Amibroker vào DuckDB/MotherDuckDB
