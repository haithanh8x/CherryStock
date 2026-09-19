from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Ults import DuckLib  # noqa: E402
from Ults.DuckLib import executeDuckSQL  # noqa: E402
from calcEngine.zigzag import refresh_zigzag_mwg  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


SCHEMA_SQL = PROJECT_ROOT / "src" / "DuckDB" / "sql" / "zigzag_mvp_schema.sql"


def main() -> int:
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)

    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None:
            raise RuntimeError("UnitOfWork did not initialize a writer connection.")

        executeDuckSQL(
            con=uow.connection,
            sql_file_path=str(SCHEMA_SQL),
            sql_description="Ensure ZigZag MWG MVP schema",
        )
        summary = refresh_zigzag_mwg(connection=uow.connection)

        print("=== ZigZag MWG MVP initload ===")
        for key, value in summary.items():
            print(f"{key}: {value}")

    DuckLib.exportDuckDB_metadata()
    print("ZigZag MWG MVP committed; DuckDB metadata exported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
