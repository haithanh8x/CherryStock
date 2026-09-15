from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.price_movement_validation import (  # noqa: E402
    validate_price_movement_historical_contract,
)


def main() -> int:
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with factory.reader() as connection:
        validation = validate_price_movement_historical_contract(connection)
    print("Price Movement Character validation PASS:", validation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
