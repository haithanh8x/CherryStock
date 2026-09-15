from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Ults.DuckLib import executeDuckSQL  # noqa: E402
from calcEngine.priceMovementCharacter import refresh_price_movement_character  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


SCHEMA_SQL = PROJECT_ROOT / "src" / "DuckDB" / "sql" / "price_movement_character_v1_schema.sql"


def _parse_date(raw: str | None) -> date | None:
    return date.fromisoformat(raw) if raw else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh Price Movement Character for all or selected active tickers."
    )
    parser.add_argument(
        "--mode",
        choices=("incremental", "full"),
        default="incremental",
        help="incremental resumes from the latest point-in-time checkpoint; full rebuilds requested tickers",
    )
    parser.add_argument(
        "--ticker",
        action="append",
        dest="tickers",
        help="repeatable ticker filter, e.g. --ticker MWG --ticker FPT",
    )
    parser.add_argument(
        "--end-date",
        help="optional inclusive YYYY-MM-DD source cutoff for reproducible local testing",
    )
    args = parser.parse_args()

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None or uow.price_movement is None:
            raise RuntimeError("UnitOfWork did not initialize Price Movement dependencies.")

        executeDuckSQL(
            con=uow.connection,
            sql_file_path=str(SCHEMA_SQL),
            sql_description="Ensure Price Movement Character V1 schema",
        )
        summary = refresh_price_movement_character(
            from_last_day=None if args.mode == "full" else 1,
            tickers=args.tickers,
            end_date=_parse_date(args.end_date),
            mode=args.mode,
            connection=uow.connection,
            repository=uow.price_movement,
        )
        print("Price Movement refresh summary:", summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
