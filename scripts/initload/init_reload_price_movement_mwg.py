from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Ults import DuckLib  # noqa: E402
from calcEngine.priceMovement import refresh_price_movement_mwg  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


SCHEMA_SQL = PROJECT_ROOT / "src" / "DuckDB" / "sql" / "price_movement_v2_schema.sql"


def main() -> int:
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)

    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None:
            raise RuntimeError("UnitOfWork did not initialize a writer connection.")

        uow.connection.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        summary = refresh_price_movement_mwg(connection=uow.connection)

        print("=== Price Movement V2 MWG initload ===")
        for key, value in summary.items():
            print(f"{key}: {value}")

    DuckLib.exportDuckDB_metadata()
    print("Price Movement V2 MWG committed; DuckDB metadata exported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
