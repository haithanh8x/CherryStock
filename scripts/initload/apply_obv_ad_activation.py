"""Apply PHASE 1 indicator_obv_ad_activate.sql through the project write path."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.Ults.DuckLib import DuckDBManager, executeDuckSQL  # noqa: E402

SQL_PATH = PROJECT_ROOT / "src" / "DuckDB" / "sql" / "indicator_obv_ad_activate.sql"


def main() -> int:
    manager = DuckDBManager(read_only=False)
    con = manager.get_connection(read_only=False)
    try:
        executeDuckSQL(con, str(SQL_PATH), "OBV + AD activation (PHASE 1)")
        rows = con.execute(
            """
            SELECT IndicatorCode, IsActive FROM "CherryMon"."main"."dim_indicator"
            WHERE IndicatorCode IN ('OBV', 'AD') ORDER BY IndicatorCode
            """
        ).fetchall()
        print("dim_indicator after activation:", rows)
        configs = con.execute(
            """
            SELECT ConfigCode, ConfigId, IsEnabled
            FROM "CherryMon"."main"."dim_indicator_config"
            WHERE ConfigCode IN ('OBV_D','OBV_W','OBV_M','AD_D','AD_W','AD_M')
            ORDER BY ConfigCode
            """
        ).fetchall()
        print("dim_indicator_config after activation:", configs)
    except Exception:
        raise
    finally:
        manager.close_connection(con)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
