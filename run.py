import sys
import io
from time import perf_counter

from src.Ults import DuckLib
from src.Ults.Timing import timeit
from src.Ults.getData import get_last_point
from src.cherrystock.config.settings import settings
from src.cherrystock.application.services.sync_write_pipeline import SyncWritePipelineService
from src.cherrystock.application.services.movement_daily_pipeline import MovementDailyPipelineService
from src.cherrystock.infrastructure.amibroker.windows_adapter import WindowsAmiBrokerAdapter
from src.cherrystock.infrastructure.database.connection import DuckDBConnectionFactory
from src.cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork
from src.calcEngine.industryIndex import refresh_industry_index

# Tạm thời bỏ daily ZigZag + Price Movement; đổi thành True để chạy lại.
ENABLE_MOVEMENT_PIPELINE = False

# Full-history AmiBroker AFL indicator refresh runs after the core EOD sync commits.
ENABLE_AFL_INDICATOR_FULL_REFRESH = False

# FFMC/EW industry indices run independently after the core data sync commits.
ENABLE_INDUSTRY_INDEX_REFRESH = True


def _resolve_days_diff(default_days: int = 15) -> int:
    """Resolve số ngày cần cập nhật từ checkpoint hiện tại."""
    days_diff_raw = get_last_point()
    if days_diff_raw is None:
        return default_days
    if hasattr(days_diff_raw, "days"):
        return int(days_diff_raw.days)
    return int(days_diff_raw)


def _run_ingest_steps(
    *,
    write_pipeline: SyncWritePipelineService,
    amibroker_adapter: WindowsAmiBrokerAdapter,
    connection,
    days_diff: int,
    uow: DuckDBUnitOfWork,
) -> dict[str, object]:
    """Run the canonical daily write pipeline in one DuckDB transaction.

    The application service owns ordering, intraday/EOD synchronization,
    stage-level data-quality validation.
    run.py owns only the transaction boundary and runtime dependencies.
    """
    print("[INGEST] START | Source sync + Data Quality")
    started = perf_counter()
    summary = write_pipeline.run(
        days_diff=days_diff,
        amibroker=amibroker_adapter,
        connection=connection,
        ticker_repository=uow.tickers,
        index_repository=uow.indexes,
        trend_repository=None, # uow.trends
        indicator_repository=uow.indicators,
        smart_money_repository=None, # uow.smart_money
    )
    elapsed = perf_counter() - started
    print("[INGEST] DONE | Source sync + Data Quality")
    print(
        "⏱️   [Duration] 'sync_data_quality' "
        f"total time: {elapsed:.1f} seconds"
    )
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
    started = perf_counter()
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

    elapsed = perf_counter() - started
    print("[daily] ✓ Incremental ZigZag + Price Movement")
    print(
        "⏱️   [Duration] 'incremental_zigzag_price_movement' "
        f"total time: {elapsed:.1f} seconds"
    )
    return summary


def _run_ingest_data(
    *,
    connection_factory: DuckDBConnectionFactory,
    amibroker_adapter: WindowsAmiBrokerAdapter,
    days_diff: int,
) -> None:
    """PHẦN 1 — INGEST DATA: đồng bộ nguồn và kiểm tra Data Quality.

    EOD, Intraday, Yahoo, FA và Ticker Master chạy trong một UnitOfWork.
    Không đưa các phép tổng hợp hậu xử lý vào transaction này.
    """
    print("\n========== [1/2] INGEST DATA ==========")
    started = perf_counter()
    with DuckDBUnitOfWork(connection_factory) as uow:
        if uow.connection is None:
            raise RuntimeError("UnitOfWork did not initialize a writer connection.")
        _run_ingest_steps(
            write_pipeline=SyncWritePipelineService(),
            amibroker_adapter=amibroker_adapter,
            connection=uow.connection,
            days_diff=days_diff,
            uow=uow,
        )
    print(f"[INGEST] COMMITTED | duration={perf_counter() - started:.1f}s")


def _run_aggregate_data(
    *,
    connection_factory: DuckDBConnectionFactory,
    days_diff: int,
) -> None:
    """PHẦN 2 — AGGREGATE DATA: tổng hợp sau khi ingest đã commit.

    Mỗi engine có transaction riêng; lỗi tổng hợp không rollback ingest.
    """
    print("\n========== [2/2] AGGREGATE DATA ==========")
    started = perf_counter()

    # 2.1 Industry Index — FFMC / Equal Weight
    if ENABLE_INDUSTRY_INDEX_REFRESH:
        print("[AGGREGATE] START | Industry Index FFMC + EW")
        step_started = perf_counter()
        with DuckDBUnitOfWork(connection_factory) as uow:
            if uow.connection is None:
                raise RuntimeError("UnitOfWork did not initialize an industry-index connection.")
            summary = refresh_industry_index(
                days=max(1, days_diff), connection=uow.connection
            )
        print(f"[AGGREGATE] COMMITTED | Industry Index | {summary}")
        print(f"⏱️   [Duration] 'industry_index_refresh' total time: {perf_counter() - step_started:.1f} seconds")
    else:
        print("[AGGREGATE] SKIP | Industry Index")

    # 2.2 AFL Indicators — disabled until incremental export is verified
    if ENABLE_AFL_INDICATOR_FULL_REFRESH:
        from scripts.sync_amibroker_indicator_full import main as run_afl_indicator_refresh

        print(f"[AGGREGATE] START | AFL Indicators incremental (days={max(1, days_diff)})")
        step_started = perf_counter()
        result = run_afl_indicator_refresh(["--mode", "incremental", "--days", str(max(1, days_diff))])
        if result not in (None, 0):
            raise RuntimeError(f"AFL indicator refresh failed with exit code {result}")
        print(f"⏱️   [Duration] 'afl_indicator_incremental_refresh' total time: {perf_counter() - step_started:.1f} seconds")
    else:
        print("[AGGREGATE] SKIP | AFL Indicators (temporarily disabled)")

    # 2.3 ZigZag + Price Movement
    if ENABLE_MOVEMENT_PIPELINE:
        _run_movement_steps(
            movement_pipeline=MovementDailyPipelineService(
                connection_factory=connection_factory
            )
        )
    else:
        print("[AGGREGATE] SKIP | ZigZag + Price Movement")

    # 2.4 Metadata export — after all enabled calculations
    step_started = perf_counter()
    print("[AGGREGATE] START | DuckDB Metadata")
    DuckLib.exportDuckDB_metadata()
    print(f"⏱️   [Duration] 'exportDuckDB_metadata' total time: {perf_counter() - step_started:.1f} seconds")
    print(f"[AGGREGATE] DONE | duration={perf_counter() - started:.1f}s")


@timeit
def main() -> None:
    """CherryStock daily orchestration: INGEST DATA → AGGREGATE DATA."""
    days_diff = _resolve_days_diff()
    connection_factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    amibroker_adapter = WindowsAmiBrokerAdapter(
        database_path=settings.amibroker_database_path
    )

    print(f"CherryStock Run All | from_last_day={days_diff}")
    _run_ingest_data(
        connection_factory=connection_factory,
        amibroker_adapter=amibroker_adapter,
        days_diff=days_diff,
    )
    _run_aggregate_data(
        connection_factory=connection_factory,
        days_diff=days_diff,
    )
    print("\n✓ CherryStock Run All completed: Ingest + Aggregate.")


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
