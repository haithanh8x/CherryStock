"""One-off diagnostic: BB negative values for ConfigId=2 (read-only)."""
import duckdb

con = duckdb.connect("C:/OneDrive/Working/Datafile/CherryMon.duckdb", read_only=True)
print(con.sql("""
    SELECT v."Ticker", v."Date", v."ComponentCode", v."Value", cfg."ConfigCode"
    FROM "CherryMon"."main"."vw_Ticker_indicators" v
    INNER JOIN "CherryMon"."main"."vw_Indicator_config" cfg
        ON cfg."ConfigId" = v."ConfigId" AND cfg."ComponentCode" = v."ComponentCode"
    WHERE v."ConfigId" = 2 AND v."Value" <= 0
    ORDER BY v."Date" DESC
    LIMIT 8
""").df())
print(con.sql("""
    SELECT "ConfigId", "ConfigCode", "IndicatorCode", "Timeframe", "ComponentCode",
           "ValueSemantic", "Unit"
    FROM "CherryMon"."main"."vw_Indicator_config"
    WHERE "ConfigId" = 2
""").df())
con.close()
