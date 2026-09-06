from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Ults.DuckLib import executeDuckSQL  # noqa: E402
from calcEngine.smartMoneyScore import refresh_smart_money_score  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


SCHEMA_SQL = PROJECT_ROOT / "src" / "DuckDB" / "sql" / "smart_money_v1_schema.sql"


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh SmartMoneyScore checkpoint.")
    parser.add_argument(
        "--days",
        type=int,
        default=15,
        help="Replace this many recent calendar days after full-history deterministic calculation.",
    )
    parser.add_argument(
        "--tickers",
        nargs="*",
        default=None,
        help="Optional ticker persistence subset. Normalization still uses the full active universe.",
    )
    args = parser.parse_args()

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None or uow.smart_money is None:
            raise RuntimeError("UnitOfWork did not initialize SmartMoney dependencies.")
        executeDuckSQL(
            con=uow.connection,
            sql_file_path=str(SCHEMA_SQL),
            sql_description="Ensure SmartMoney V1 schema",
        )
        summary = refresh_smart_money_score(
            from_last_day=args.days,
            tickers=args.tickers,
            connection=uow.connection,
            repository=uow.smart_money,
        )
        print("SmartMoney incremental summary:", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
