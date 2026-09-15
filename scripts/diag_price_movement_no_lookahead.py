"""Diag: inspect no-look-ahead violation rows for Price Movement (MWG)."""
import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from cherrystock.config.settings import settings  # noqa: E402

db_path = settings.local_db_path
print("DB path:", db_path)

con = duckdb.connect(db_path, read_only=True)
rows = con.execute(
    """
    SELECT d.Date, d.Direction, d.SwingStatus, d.CurrentSwingPct,
           s.SwingSeq, s.PivotStartDate, s.PivotEndDate, s.ConfirmedAtDate,
           s.SwingPct
    FROM "CherryMon"."main"."cal_price_movement_daily" AS d
    INNER JOIN "CherryMon"."main"."cal_price_movement_swing" AS s
        ON s.ConfigId = d.ConfigId
       AND s.Ticker = d.Ticker
       AND s.Direction = d.Direction
       AND s.ConfirmedAtDate > d.Date
       AND s.PivotEndDate <= d.Date
    WHERE d.Ticker = 'MWG'
    ORDER BY d.Date DESC, s.SwingSeq DESC
    LIMIT 15
    """
).df()
print(rows.to_string(index=False))

# Focus: does the leak only affect PROVISIONAL daily rows (current leg)?
cnt = con.execute(
    """
    SELECT d.SwingStatus, COUNT(*) AS n
    FROM "CherryMon"."main"."cal_price_movement_daily" AS d
    INNER JOIN "CherryMon"."main"."cal_price_movement_swing" AS s
        ON s.ConfigId = d.ConfigId
       AND s.Ticker = d.Ticker
       AND s.Direction = d.Direction
       AND s.ConfirmedAtDate > d.Date
       AND s.PivotEndDate <= d.Date
    WHERE d.Ticker = 'MWG'
    GROUP BY d.SwingStatus
    """
).df()
print("\nLeak rows by SwingStatus:")
print(cnt.to_string(index=False))
con.close()

# Second connection: cross-check whether leak only touches PROVISIONAL daily rows
con = duckdb.connect(db_path, read_only=True)
r1 = con.execute(
    """
    SELECT COUNT(*)
    FROM "CherryMon"."main"."cal_price_movement_daily" AS d
    INNER JOIN "CherryMon"."main"."cal_price_movement_swing" AS s
        ON s.ConfigId = d.ConfigId AND s.Ticker = d.Ticker AND s.Direction = d.Direction
       AND s.ConfirmedAtDate > d.Date AND s.PivotEndDate <= d.Date
    WHERE d.SwingStatus = 'CONFIRMED'
    """
).fetchone()[0]
print("Leak on CONFIRMED daily rows:", r1)
r2 = con.execute(
    """
    SELECT COUNT(*)
    FROM "CherryMon"."main"."cal_price_movement_daily" AS d
    INNER JOIN "CherryMon"."main"."cal_price_movement_swing" AS s
        ON s.ConfigId = d.ConfigId AND s.Ticker = d.Ticker AND s.Direction = d.Direction
       AND s.ConfirmedAtDate <= d.Date AND s.PivotEndDate > d.Date
    """
).fetchone()[0]
print("Swing confirmed but pivot-end after daily date:", r2)
con.close()
