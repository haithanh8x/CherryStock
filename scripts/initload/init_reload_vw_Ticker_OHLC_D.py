from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Ults.DuckLib import executeDuckSQL  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402

VIEW_SQL = PROJECT_ROOT / "src" / "DuckDB" / "sql" / "vw_Ticker_OHLC_D.sql"


def main() -> None:
    """Create or replace main.vw_Ticker_OHLC_D."""
    factory = DuckDBConnectionFactory()
    with factory.writer() as connection:
        executeDuckSQL(
            con=connection,
            sql_file_path=str(VIEW_SQL),
            sql_description="Rebuild vw_Ticker_OHLC_D",
        )


if __name__ == "__main__":
    main()
