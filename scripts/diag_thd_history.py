"""One-off: THD BB20_2_W LOWER history in eval window (read-only)."""
import duckdb

con = duckdb.connect("C:/OneDrive/Working/Datafile/CherryMon.duckdb", read_only=True)
print(con.sql("""
    SELECT "Date", "Value"
    FROM "CherryMon"."main"."vw_Ticker_indicators"
    WHERE "Ticker" = 'THD' AND "ConfigId" = 2 AND "ComponentCode" = 'LOWER'
      AND "Date" BETWEEN DATE '2023-07-04' AND DATE '2026-07-03'
    ORDER BY "Date" DESC
    LIMIT 15
""").df())
con.close()
