from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Ults import DuckLib  # noqa: E402
from Ults.DuckLib import executeDuckSQL  # noqa: E402
from calcEngine.smartMoneyScore import refresh_smart_money_score  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


SCHEMA_SQL = PROJECT_ROOT / "src" / "DuckDB" / "sql" / "smart_money_v1_schema.sql"


def main() -> int:
    """Bootstrap SmartMoney V1 metadata/storage and perform full historical backfill."""
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)

    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None or uow.smart_money is None:
            raise RuntimeError("UnitOfWork did not initialize SmartMoney dependencies.")

        executeDuckSQL(
            con=uow.connection,
            sql_file_path=str(SCHEMA_SQL),
            sql_description="SmartMoney V1 schema + metadata seed",
        )
        summary = refresh_smart_money_score(
            from_last_day=None,
            tickers=None,
            model_ids=None,
            connection=uow.connection,
            repository=uow.smart_money,
        )
        if int(summary.get("score_rows_upserted", 0)) <= 0:
            raise RuntimeError(f"SmartMoney full historical initload produced no score rows: {summary}")
        print("SmartMoney full historical summary:", summary)

    DuckLib.exportDuckDB_metadata()
    print("SmartMoney V1 full historical initload committed; DB metadata exported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
