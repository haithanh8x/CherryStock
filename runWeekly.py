import io
import sys

from src.Ults import DuckLib
from src.Ults.Timing import timeit
from src.cherrystock.application.services.movement_weekly_pipeline import (
    MovementWeeklyPipelineService,
)
from src.cherrystock.config.settings import settings
from src.cherrystock.infrastructure.database.connection import DuckDBConnectionFactory


def _progress(stage: str, index: int, total: int, ticker: str, status: str) -> None:
    print(f"[weekly][{stage} {index}/{total}] {ticker}: {status}")


def _run_movement_weekly(
    *,
    movement_pipeline: MovementWeeklyPipelineService,
) -> dict[str, object]:
    print("[weekly] ▶ Full-universe ZigZag + Price Movement")
    summary = movement_pipeline.run(progress_callback=_progress)

    print(
        "[weekly] Movement | "
        f"active={summary['active_ticker_count']} "
        f"zigzag_ok={summary['zigzag_ok']} "
        f"price_movement_ok={summary['price_movement_ok']} "
        f"failures={summary['failure_count']} "
        f"elapsed_seconds={summary['elapsed_seconds']}"
    )

    if int(summary["failure_count"]) > 0:
        raise RuntimeError(
            "Weekly Movement pipeline completed with "
            f"{summary['failure_count']} failure(s). "
            "Use the weekly Movement runbook/validator before retrying."
        )

    print("[weekly] ✓ Full-universe ZigZag + Price Movement")
    return summary


@timeit
def main() -> None:
    """CherryStock weekly runner.

    Run manually/scheduled once per week:
        python runWeekly.py
    """

    print("CherryStock Weekly Run All")

    connection_factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    movement_pipeline = MovementWeeklyPipelineService(
        connection_factory=connection_factory
    )

    _run_movement_weekly(movement_pipeline=movement_pipeline)

    DuckLib.exportDuckDB_metadata()
    print("✓ Weekly Run All hoàn tất. DuckDB metadata đã được export.")


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
