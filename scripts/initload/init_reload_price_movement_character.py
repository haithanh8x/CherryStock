from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Ults import DuckLib  # noqa: E402
from Ults.DuckLib import executeDuckSQL  # noqa: E402
from calcEngine.priceMovementCharacter import refresh_price_movement_character  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.price_movement_validation import (  # noqa: E402
    validate_price_movement_historical_contract,
)
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


SCHEMA_SQL = PROJECT_ROOT / "src" / "DuckDB" / "sql" / "price_movement_character_v1_schema.sql"


def main() -> int:
    """Create/seed V1 objects, rebuild full history, validate, then commit atomically."""
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)

    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None or uow.price_movement is None:
            raise RuntimeError("UnitOfWork did not initialize Price Movement dependencies.")

        executeDuckSQL(
            con=uow.connection,
            sql_file_path=str(SCHEMA_SQL),
            sql_description="Price Movement Character V1 schema + metadata seed",
        )
        summary = refresh_price_movement_character(
            from_last_day=None,
            tickers=None,
            mode="full",
            connection=uow.connection,
            repository=uow.price_movement,
        )
        if int(summary.get("daily_rows_upserted", 0)) <= 0:
            raise RuntimeError(
                "Price Movement full initload produced no daily rows: "
                f"{summary}"
            )
        if int(summary.get("swing_rows_upserted", 0)) <= 0:
            raise RuntimeError(
                "Price Movement full initload produced no confirmed swings: "
                f"{summary}"
            )

        validation = validate_price_movement_historical_contract(uow.connection)
        print("Price Movement full historical summary:", summary)
        print("Price Movement historical contract validation:", validation)

    DuckLib.exportDuckDB_metadata()
    print(
        "Price Movement Character V1 full initload committed; "
        "historical contract validated; DB metadata exported."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
