"""Diagnose MA mismatch for MWG between raw_stock_eod and cal_Trends."""
import duckdb

DB_PATH = r"c:\onedrive\working\datafile\cherrymon.duckdb"

with duckdb.connect(DB_PATH, read_only=True) as con:
    # 1. raw_lstTicker có bị trùng Ticker không? (join có thể nhân bản dòng)
    print("=== raw_lstTicker rows for MWG ===")
    print(con.execute(
        """
        SELECT Ticker, COUNT(*) AS n
        FROM "CherryMon"."main"."raw_lstTicker"
        WHERE Ticker = 'MWG'
        GROUP BY Ticker
        """
    ).df())

    # 2. Join giống cal_Moving_Average -> đếm số dòng eod sau join
    print("=== joined row count vs raw eod row count (MWG) ===")
    print(con.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM "CherryMon"."main"."raw_stock_eod" WHERE Ticker='MWG') AS raw_rows,
          (SELECT COUNT(*)
           FROM "CherryMon"."main"."raw_lstTicker" lt
           JOIN "CherryMon"."main"."raw_stock_eod" eod ON lt.Ticker = eod.Ticker
           WHERE lt.Ticker = 'MWG' AND lt.status = 'Y') AS joined_rows
        """
    ).df())

    # 3. Tính MA50 trực tiếp từ raw_stock_eod tại 2026-08-24
    print("=== direct MA from raw_stock_eod (last 50 sessions to 2026-08-24) ===")
    print(con.execute(
        """
        WITH last50 AS (
            SELECT Close
            FROM "CherryMon"."main"."raw_stock_eod"
            WHERE Ticker = 'MWG' AND Date <= DATE '2026-08-24'
            ORDER BY Date DESC
            LIMIT 50
        )
        SELECT COUNT(*) AS n, AVG(Close) AS ma50_direct, MIN(Close) AS min_close, MAX(Close) AS max_close
        FROM last50
        """
    ).df())

    # 4. Giá trị đang lưu trong cal_Trends
    print("=== cal_Trends stored values (MWG @ 2026-08-24) ===")
    print(con.execute(
        """
        SELECT Ticker, Date, Close, MA20, MA50, MA20_W, MA50_W, MA20_M, MA50_M
        FROM "CherryMon"."main"."cal_Trends"
        WHERE Ticker = 'MWG' AND Date = DATE '2026-08-24'
        """
    ).df())

    # 5. Kiểm tra duplicate (Ticker, Date) trong raw_stock_eod cho MWG
    print("=== duplicate (Ticker,Date) in raw_stock_eod for MWG ===")
    print(con.execute(
        """
        SELECT Date, COUNT(*) AS n
        FROM "CherryMon"."main"."raw_stock_eod"
        WHERE Ticker = 'MWG'
        GROUP BY Date
        HAVING COUNT(*) > 1
        ORDER BY Date DESC
        LIMIT 10
        """
    ).df())
