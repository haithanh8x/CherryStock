"""One-off: THD price vs BB W bands around negative LOWER era (read-only)."""
import duckdb

con = duckdb.connect("C:/OneDrive/Working/Datafile/CherryMon.duckdb", read_only=True)
print(con.sql("""
    SELECT e."Date", e."Close",
           bb."Value" AS BB_W_LOWER
    FROM "CherryMon"."main"."raw_stock_eod" e
    LEFT JOIN "CherryMon"."main"."vw_Ticker_indicators" bb
        ON bb."Ticker" = e."Ticker" AND bb."ConfigId" = 2
       AND bb."ComponentCode" = 'LOWER' AND bb."Date" = e."Date"
    WHERE e."Ticker" = 'THD'
      AND e."Date" BETWEEN DATE '2026-05-20' AND DATE '2026-07-03'
    ORDER BY e."Date"
""").df())
con.close()
