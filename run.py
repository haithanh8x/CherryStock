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


def _resolve_days_diff(default_days: int = 15) -> int:
    """Resolve số ngày cần cập nhật từ checkpoint hiện tại."""
    days_diff_raw = get_last_point()
    if days_diff_raw is None:
        return default_days
    if hasattr(days_diff_raw, "days"):
        return int(days_diff_raw.days)
    return int(days_diff_raw)


def _run_all_steps(
    *,
    write_pipeline: SyncWritePipelineService,
    amibroker_adapter: WindowsAmiBrokerAdapter,
    connection,
    days_diff: int,
    uow: DuckDBUnitOfWork,
) -> None:
    """
    Chạy toàn bộ write pipeline theo đúng thứ tự Run All trong NiceGUI_chart.py.

    Tất cả step dùng chung một writer connection/UoW để đảm bảo cùng transaction.
    Nếu một step lỗi, context manager của DuckDBUnitOfWork sẽ rollback toàn bộ.
    """
    steps = (
        (
            "Đồng bộ AmiBroker EOD",
            lambda: write_pipeline._sync_amibroker_eod(
                from_last_day=days_diff,
                connection=connection,
            ),
        ),
        (
            "Đồng bộ Yahoo Finance EOD",
            lambda: write_pipeline._sync_yahoo_eod(
                from_last_day=days_diff,
                connection=connection,
            ),
        ),
        (
            "Cập nhật Fundamental Analysis",
            lambda: write_pipeline._upsert_fa(
                amibroker=amibroker_adapter,
                connection=connection,
            ),
        ),
        (
            "Cập nhật danh sách Ticker",
            lambda: write_pipeline._upsert_tickers(
                connection=connection,
                repository=uow.tickers,
            ),
        ),
        (
            "Cập nhật ngày nghỉ",
            lambda: write_pipeline._execute_sql(
                con=connection,
                sql_file_path=str(write_pipeline._sql_dir / "updateHoliday.sql"),
                sql_description="Update Holiday Table",
            ),
        ),
        (
            "Tính VNINDEX_NOT_VIN",
            lambda: write_pipeline._calc_index(
                connection=connection,
                repository=uow.indexes,
            ),
        ),
        (
            "Tính Moving Average / Trend",
            lambda: write_pipeline._calc_trend(
                from_last_day=days_diff,
                connection=connection,
                repository=uow.trends,
            ),
        ),
    )

    for index, (title, step) in enumerate(steps, start=1):
        print(f"[{index}/{len(steps)}] ▶ {title}")
        step()
        print(f"[{index}/{len(steps)}] ✓ {title}")


# --- HÀM MAIN ---
@timeit
def main():
    amibroker_adapter = WindowsAmiBrokerAdapter(
        database_path=settings.amibroker_database_path
    )
    write_pipeline = SyncWritePipelineService()
    connection_factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    days_diff = _resolve_days_diff()

    print(f"CherryStock Run All | from_last_day={days_diff}")

    # Tương đương nút Run All trong NiceGUI_chart.py:
    # 7 step tuần tự, dùng chung một DuckDB UnitOfWork/transaction.
    with DuckDBUnitOfWork(connection_factory) as uow:
        connection = uow.connection
        if connection is None:
            raise RuntimeError("UnitOfWork did not initialize a writer connection.")

        _run_all_steps(
            write_pipeline=write_pipeline,
            amibroker_adapter=amibroker_adapter,
            connection=connection,
            days_diff=days_diff,
            uow=uow,
        )

    # Chỉ export metadata sau khi toàn bộ transaction đã commit thành công.
    DuckLib.exportDuckDB_metadata()
    print("✓ Run All hoàn tất. DuckDB metadata đã được export.")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding="utf-8",
        line_buffering=True,
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer,
        encoding="utf-8",
        line_buffering=True,
    )
    main()
