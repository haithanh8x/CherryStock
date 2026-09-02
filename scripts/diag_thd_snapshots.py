"""One-off: THD negative-BB era vs sampled snapshot dates (read-only)."""
import duckdb

con = duckdb.connect("C:/OneDrive/Working/Datafile/CherryMon.duckdb", read_only=True)

print(con.sql("""
    WITH ranked AS (
        SELECT val."Date", val."Value", val."ConfigId", val."ComponentCode",
               ROW_NUMBER() OVER (PARTITION BY val."ConfigId", val."ComponentCode"
                                  ORDER BY val."Date" DESC) AS rn
        FROM "CherryMon"."main"."vw_Ticker_indicators" val
        INNER JOIN "CherryMon"."main"."vw_Indicator_config" cfg
            ON cfg."ConfigId" = val."ConfigId" AND cfg."ComponentCode" = val."ComponentCode"
        WHERE val."Ticker" = 'THD'
          AND val."Date" <= DATE '2026-06-24'
          AND cfg."IndicatorCode" = 'BB'
          AND cfg."ComponentCode" IN ('LOWER', 'MIDDLE', 'UPPER')
          AND val."Value" IS NOT NULL
    )
    SELECT "Date", "Value", "ConfigId", "ComponentCode"
    FROM ranked WHERE rn = 1
    ORDER BY "ConfigId", "ComponentCode"
""").df())
con.close()
