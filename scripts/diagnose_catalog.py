import duckdb

con = duckdb.connect("C:/OneDrive/Working/Datafile/CherryMon.duckdb", read_only=True)
rows = con.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_catalog = 'CherryMon'
      AND table_schema = 'main'
      AND table_name = 'vw_Ticker_indicators'
    ORDER BY ordinal_position
""").fetchall()
print("with catalog filter:", rows)

rows2 = con.execute("""
    SELECT DISTINCT table_catalog FROM information_schema.columns
    WHERE table_name = 'vw_Ticker_indicators'
""").fetchall()
print("catalogs:", rows2)
con.close()
