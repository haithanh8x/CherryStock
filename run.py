import sys
import io

from src.Ults import DuckLib
from src.Ults.Timing import timeit
from src.Ults.getData import get_last_point
from src.cherrystock.config.settings import settings
from src.cherrystock.application.services.sync_write_pipeline import SyncWritePipelineService
from src.cherrystock.application.services.movement_daily_pipeline import MovementDailyPipelineService
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
) -> dict[str, object]:
    """Run the canonical daily write pipeline in one DuckDB transaction.

    The application service owns ordering, intraday/EOD synchronization,
    stage-level data-quality validation, indicators and SmartMoney refresh.
    run.py owns only the transaction boundary and runtime dependencies.
    """
    print("[daily] ▶ Sync + Data Quality + Indicators + SmartMoney")
    summary = write_pipeline.run(
        days_diff=days_diff,
        amibroker=amibroker_adapter,
        connection=connection,
        ticker_repository=uow.tickers,
        index_repository=uow.indexes,
        trend_repository=uow.trends,
        indicator_repository=uow.indicators,
        smart_money_repository=uow.smart_money,
    )
    print("[daily] ✓ Sync + Data Quality + Indicators + SmartMoney")
    return summary


def _run_movement_steps(
    *,
    movement_pipeline: MovementDailyPipelineService,
) -> dict[str, object]:
    """Run the post-commit daily Movement pipeline.

    The core daily transaction has already committed before this function runs.
    Movement uses ticker-local transactions so one failed ticker cannot roll back
    ingestion, Indicator, or SmartMoney results.
    """
    print("[daily] ▶ Incremental ZigZag + Price Movement")
    summary = movement_pipeline.run()

    print(
        "[daily] Movement | "
        f"selected={summary['selected_ticker_count']} "
        f"zigzag={summary['zigzag_refreshed']} "
        f"price_movement={summary['price_movement_refreshed']} "
        f"failures={summary['failure_count']}"
    )

    if int(summary["failure_count"]) > 0:
        raise RuntimeError(
            "Daily Movement pipeline completed with "
            f"{summary['failure_count']} failure(s). "
            "Core daily data is already committed; run the Movement validator/runbook."
        )

    print("[daily] ✓ Incremental ZigZag + Price Movement")
    return summary


# --- HÀM MAIN ---
@timeit
def main():
    amibroker_adapter = WindowsAmiBrokerAdapter(
        database_path=settings.amibroker_database_path
    )
    write_pipeline = SyncWritePipelineService()
    connection_factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    movement_pipeline = MovementDailyPipelineService(
        connection_factory=connection_factory
    )
    days_diff = _resolve_days_diff()

    print(f"CherryStock Run All | from_last_day={days_diff}")

    # Daily Source of Truth:
    # EOD + Intraday sync -> stage Data Quality -> Index/Trend/Indicators
    # -> SmartMoneyScore -> SmartMoney Data Quality, all in one UnitOfWork.
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

    # Movement runs after the canonical daily transaction commits so it can
    # read the newly committed EOD while keeping ticker-local failure isolation.
    _run_movement_steps(movement_pipeline=movement_pipeline)

    # Chỉ export metadata sau khi core + Movement daily stages hoàn tất.
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
