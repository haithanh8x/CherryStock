"""Verify MA20_W/MA50_W/MA20_M/MA50_M columns in cal_Trends."""
import duckdb

DB_PATH = r"c:\onedrive\working\datafile\cherrymon.duckdb"
TABLE = '"CherryMon"."main"."cal_Trends"'

with duckdb.connect(DB_PATH, read_only=True) as con:
    summary = con.execute(
        f"""
        SELECT COUNT(*) AS total_rows,
               COUNT(MA20) AS has_ma20,
               COUNT(MA20_W) AS has_ma20_w,
               COUNT(MA50_W) AS has_ma50_w,
               COUNT(MA20_M) AS has_ma20_m,
               COUNT(MA50_M) AS has_ma50_m
        FROM {TABLE}
        """
    ).df()
    print(summary)

    latest = con.execute(
        f"""
        SELECT Ticker, Date, Close, MA20, MA20_W, MA50_W, MA20_M, MA50_M
        FROM {TABLE}
        WHERE Ticker = 'MWG'
        ORDER BY Date DESC
        LIMIT 5
        """
    ).df()
    print(latest)
