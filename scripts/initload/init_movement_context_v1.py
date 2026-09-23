from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Ults import DuckLib  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


SCHEMA_SQL = PROJECT_ROOT / "src" / "DuckDB" / "sql" / "movement_context_v1_schema.sql"


def main() -> int:
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)

    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None:
            raise RuntimeError("UnitOfWork did not initialize a writer connection.")

        uow.connection.execute(SCHEMA_SQL.read_text(encoding="utf-8"))

        rows = uow.connection.execute(
            """
            SELECT
                MovementContextConfigCode,
                Ticker,
                ContextAsOfDate,
                ContextStatus,
                MovementAgeTradingDays,
                MovementFreshnessStatus,
                TrendRegime,
                TrendQuality,
                LastSwingState,
                CurrentLegDirection,
                CurrentMoveSpeedState
            FROM "CherryMon"."main"."vw_Ticker_Movement_Context"
            WHERE Ticker = 'MWG'
            ORDER BY MovementContextConfigId
            """
        ).fetchall()

        print("=== MovementContext V1 migration ===")
        print("schema: applied")
        print(f"mwg_context_rows: {len(rows)}")
        for row in rows:
            print(row)

    DuckLib.exportDuckDB_metadata()
    print("MovementContext V1 committed; DuckDB metadata exported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
