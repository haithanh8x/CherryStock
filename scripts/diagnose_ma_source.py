"""Check whether user's reference values match a different data source (e.g. adjusted close)."""
import duckdb

DB_PATH = r"c:\onedrive\working\datafile\cherrymon.duckdb"

with duckdb.connect(DB_PATH, read_only=True) as con:
    print("=== raw_stock_eod schema ===")
    print(con.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name='raw_stock_eod' ORDER BY ordinal_position"
    ).df())

    # Có thể nguồn "thực tế" của user dùng giá điều chỉnh (adjusted) khác với Close thô.
    # So sánh MA50 nếu dùng các cột khác (nếu có).
    cols = [r[0] for r in con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name='raw_stock_eod'"
    ).fetchall()]
    print("columns:", cols)

    # Kiểm tra xem có sự kiện cổ tức/phát hành gần đây làm lệch không:
    # so sánh Close ngày 2026-08-24 và 2026-08-21
    print(con.execute(
        """
        SELECT Date, Open, High, Low, Close
        FROM "CherryMon"."main"."raw_stock_eod"
        WHERE Ticker='MWG' AND Date >= DATE '2026-08-18'
        ORDER BY Date
        """
    ).df())
