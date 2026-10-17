"""Run the standalone CherryStock industry-index calculation from repo root.

Examples:
  python scripts/run_industry_index.py --days 10
  python scripts/run_industry_index.py
  python scripts/run_industry_index.py --days null
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.calcEngine.industryIndex import refresh_industry_index  # noqa: E402
from src.cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from src.cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


def _days(value: str) -> int | None:
    if value.strip().lower() in {"null", "none", "all"}:
        return None
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--days must be positive or null") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("--days must be positive or null")
    return number


def main(argv: list[str] | None = None) -> dict[str, object]:
    parser = argparse.ArgumentParser(description="Refresh CherryStock industry index")
    parser.add_argument(
        "--days", type=_days, default=None,
        help="N most recent trading sessions; null/omitted means full history",
    )
    args = parser.parse_args(argv)
    with DuckDBUnitOfWork(DuckDBConnectionFactory()) as uow:
        summary = refresh_industry_index(days=args.days, connection=uow.connection)
    print("[IndustryIndex] COMMITTED", summary)
    return summary


if __name__ == "__main__":
    main()
