import duckdb

con = duckdb.connect("C:/OneDrive/Working/Datafile/CherryMon.duckdb", read_only=True)
print(con.sql("""
    SELECT view_name, sql FROM duckdb_views()
    WHERE view_name IN ('vw_Ticker_indicators', 'vw_Indicator_config')
""").df().to_string())
con.close()
