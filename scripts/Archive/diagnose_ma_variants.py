"""Compare stored MA values vs user's expected reference values for MWG."""
import duckdb

DB_PATH = r"c:\onedrive\working\datafile\cherrymon.duckdb"

with duckdb.connect(DB_PATH, read_only=True) as con:
    # MA50 daily: 50 phiên gần nhất tính TOI ĐÚNG ngày 2026-08-24 (đã xác nhận = 74.7006)
    # User nói "thực tế" là 73.91. Thử các biến thể:
    print("=== Variant A: last 50 sessions INCLUDING 2026-08-24 (current impl) ===")
    print(con.execute(
        """
        SELECT AVG(Close) AS ma50
        FROM (
            SELECT Close FROM "CherryMon"."main"."raw_stock_eod"
            WHERE Ticker='MWG' AND Date <= DATE '2026-08-24'
            ORDER BY Date DESC LIMIT 50
        )
        """
    ).df())

    print("=== Variant B: last 50 sessions EXCLUDING 2026-08-24 (shifted 1 day) ===")
    print(con.execute(
        """
        SELECT AVG(Close) AS ma50
        FROM (
            SELECT Close FROM "CherryMon"."main"."raw_stock_eod"
            WHERE Ticker='MWG' AND Date < DATE '2026-08-24'
            ORDER BY Date DESC LIMIT 50
        )
        """
    ).df())

    print("=== Variant C: last 49 sessions including today (n-1 window?) ===")
    print(con.execute(
        """
        SELECT AVG(Close) AS ma50
        FROM (
            SELECT Close FROM "CherryMon"."main"."raw_stock_eod"
            WHERE Ticker='MWG' AND Date <= DATE '2026-08-24'
            ORDER BY Date DESC LIMIT 49
        )
        """
    ).df())

    # Weekly: close cuối tuần (W-FRI). Tuần chứa 2026-08-24 là thứ Hai,
    # nên kỳ tuần cuối cùng ĐÃ KẾT THÚC là Friday 2026-08-21.
    print("=== Weekly closes (W-FRI), last 6 ===")
    print(con.execute(
        """
        WITH weekly AS (
            SELECT date_trunc('week', Date + INTERVAL 4 DAY)::DATE AS week_end_fri,
                   arg_max(Close, Date) AS week_close,
                   MAX(Date) AS max_date_in_week
            FROM "CherryMon"."main"."raw_stock_eod"
            WHERE Ticker='MWG' AND Date < DATE '2026-08-24'
            GROUP BY week_end_fri
            ORDER BY week_end_fri DESC LIMIT 60
        )
        SELECT * FROM weekly LIMIT 6
        """
    ).df())

    print("=== MA50_W variant: mean of last 50 completed weeks (before current week) ===")
    print(con.execute(
        """
        WITH weekly AS (
            SELECT date_trunc('week', Date + INTERVAL 4 DAY)::DATE AS week_end,
                   arg_max(Close, Date) AS week_close
            FROM "CherryMon"."main"."raw_stock_eod"
            WHERE Ticker='MWG' AND Date < DATE '2026-08-24'
            GROUP BY week_end
        ),
        ranked AS (
            SELECT week_close FROM weekly ORDER BY week_end DESC LIMIT 50
        )
        SELECT COUNT(*) AS n, AVG(week_close) AS ma50_w
        FROM ranked
        """
    ).df())
