"""One-off: inspect the actual runtime query for a BB negative-value ticker.

Reproduce _load_latest_indicator_rows for ticker=NBB, BB, all timeframes,
components LOWER/MIDDLE/UPPER, as-of 2023-07-04..2026-07-03 sampling range.
Read-only.
"""
import duckdb

con = duckdb.connect("C:/OneDrive/Working/Datafile/CherryMon.duckdb", read_only=True)
df = con.sql("""
    WITH ranked AS (
        SELECT
            val."Ticker", val."Date", val."ConfigId", val."ComponentCode", val."Value",
            cfg."ConfigCode", cfg."IndicatorCode", cfg."Timeframe",
            ROW_NUMBER() OVER (
                PARTITION BY val."ConfigId", val."ComponentCode"
                ORDER BY val."Date" DESC
            ) AS rn
        FROM "CherryMon"."main"."vw_Ticker_indicators" val
        INNER JOIN "CherryMon"."main"."vw_Indicator_config" cfg
            ON cfg."ConfigId" = val."ConfigId"
           AND cfg."ComponentCode" = val."ComponentCode"
        WHERE val."Ticker" = 'NBB'
          AND val."Date" <= DATE '2026-07-03'
          AND cfg."IndicatorCode" = 'BB'
          AND cfg."ConfigIsEnabled" = TRUE
          AND cfg."IndicatorIsActive" = TRUE
          AND val."ComponentCode" IN ('LOWER', 'MIDDLE', 'UPPER')
          AND val."Value" IS NOT NULL
    )
    SELECT "Ticker", "Date", "ConfigId", "ComponentCode", "Value", "ConfigCode", "Timeframe"
    FROM ranked WHERE rn = 1
    ORDER BY "Timeframe", "ConfigId", "ComponentCode"
""").df()
print(df)
print("negative rows:", len(df[df["Value"] <= 0]))
con.close()
