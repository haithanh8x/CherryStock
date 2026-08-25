"""Run the Technical Indicator Engine with the same checkpoint used by run.py."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from Ults.getData import get_last_point  # noqa: E402
from calcEngine.calcIndicators import refresh_technical_indicators  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


def _resolve_days_diff() -> int:
    checkpoint = get_last_point()
    if checkpoint is None:
        return 15
    if hasattr(checkpoint, "days"):
        return int(checkpoint.days)
    return int(checkpoint)


def main() -> None:
    days_diff = _resolve_days_diff()
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None or uow.indicators is None:
            raise RuntimeError("UnitOfWork did not initialize indicator dependencies.")
        summary = refresh_technical_indicators(
            from_last_day=days_diff,
            connection=uow.connection,
            repository=uow.indicators,
        )
    print(summary)


if __name__ == "__main__":
    main()
