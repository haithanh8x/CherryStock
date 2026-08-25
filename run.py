import sys
import io

from src.Ults import DuckLib
from src.Ults.Timing import timeit
from src.Ults.getData import get_last_point
from src.cherrystock.config.settings import settings
from src.cherrystock.application.services.sync_write_pipeline import SyncWritePipelineService
from src.cherrystock.infrastructure.amibroker.windows_adapter import WindowsAmiBrokerAdapter
from src.cherrystock.infrastructure.database.connection import DuckDBConnectionFactory
from src.cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork

# --- HÀM MAIN ---
@timeit
def main():
        amibroker_adapter = WindowsAmiBrokerAdapter(database_path=settings.amibroker_database_path)
        write_pipeline = SyncWritePipelineService()
        connection_factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
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
        with DuckDBUnitOfWork(connection_factory) as uow:
                connection = uow.connection
                if connection is None:
                        raise RuntimeError("UnitOfWork did not initialize a writer connection.")

                write_pipeline.run(
                        days_diff=days_diff,
                        amibroker=amibroker_adapter,
                        connection=connection,
                        ticker_repository=uow.tickers,
                        index_repository=uow.indexes,
                        trend_repository=uow.trends,
                        indicator_repository=uow.indicators,
                )

        # sync DuckDB metadata
        DuckLib.exportDuckDB_metadata()
        # --------------------------------------------------------------------------------- 

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
    main() # thực thi hàm main() để chạy toàn bộ quy trình đồng bộ dữ liệu từ Amibroker vào DuckDB/MotherDuckDB
