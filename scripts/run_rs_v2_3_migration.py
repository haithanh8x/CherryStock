"""Execute the R/S V2.3 evaluation-governance DuckDB migration.

This is the write-capable entry point for environments where MCP is read-only.

Usage:
    python scripts/run_rs_v2_3_migration.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import (  # noqa: E402
    DuckDBConnectionFactory,
)


MIGRATION_PATH = (
    PROJECT_ROOT
    / "src"
    / "DuckDB"
    / "sql"
    / "rs_v2_3_evaluation_governance.sql"
)


def main() -> None:
    if not MIGRATION_PATH.exists():
        raise FileNotFoundError(f"Migration SQL not found: {MIGRATION_PATH}")

    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    if not sql.strip():
        raise ValueError(f"Migration SQL is empty: {MIGRATION_PATH}")

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with factory.writer() as connection:
        connection.execute("BEGIN")
        try:
            connection.execute(sql)
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise

    print(f"R/S V2.3 migration applied: {MIGRATION_PATH}")


if __name__ == "__main__":
    main()
