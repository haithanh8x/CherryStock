<<<<<<< HEAD
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
=======
"""One-off: execute R/S V2.3 evaluation governance migration against CherryMon.

Runs the exact SQL file with no edits (per tests/test_R_S_V2_3.md Seq 2).
Idempotent: CREATE TABLE IF NOT EXISTS + conditional INSERT.
"""
from pathlib import Path

import duckdb

sys_path_root = Path(__file__).resolve().parents[1]

SQL_FILE = sys_path_root / "src" / "DuckDB" / "sql" / "rs_v2_3_evaluation_governance.sql"
DB = "C:/OneDrive/Working/Datafile/CherryMon.duckdb"

sql_text = SQL_FILE.read_text(encoding="utf-8")
con = duckdb.connect(DB)
try:
    con.execute("BEGIN TRANSACTION")
    con.execute(sql_text)
    con.execute("COMMIT")
    print("MIGRATION EXECUTED OK")

    print("\n== validation: baseline model version ==")
    print(con.sql("""
        SELECT "ModelVersion", "ParentVersion", "Status", "Signature", "CreatedAt"
        FROM "CherryMon"."main"."dim_rs_model_version"
        WHERE "ModelVersion" = 'RS_V2_3_BASELINE'
    """).df().to_string())

    print("\n== validation: five objects ==")
    print(con.sql("""
        SELECT table_name
        FROM information_schema.tables
        WHERE lower(table_catalog) = 'cherrymon'
          AND table_schema = 'main'
          AND table_name IN (
              'dim_rs_model_version',
              'cal_rs_evaluation_run',
              'cal_rs_evaluation_event',
              'cal_rs_evaluation_metric',
              'sys_rs_model_promotion_audit'
          )
        ORDER BY table_name
    """).df().to_string())
finally:
    con.close()
>>>>>>> 1b4c3ad (auto-sync: 2026-09-02 13:31:44)
