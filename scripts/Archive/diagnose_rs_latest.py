"""Informational cross-check (join via ConfigCode since vw_Ticker_indicators lacks ConfigId)."""
import json

import duckdb

con = duckdb.connect("C:/OneDrive/Working/Datafile/CherryMon.duckdb", read_only=True)
as_of = "2026-08-28"

latest = con.sql(f"""
    WITH ranked AS (
        SELECT val."Ticker", val."Date", val."ComponentCode", val."Value",
               cfg."ConfigId", cfg."ConfigCode", cfg."Timeframe", cfg."Parameters",
               ROW_NUMBER() OVER (PARTITION BY cfg."ConfigCode", val."ComponentCode"
                                  ORDER BY val."Date" DESC) AS rn
        FROM "CherryMon"."main"."vw_Ticker_indicators" val
        INNER JOIN "CherryMon"."main"."vw_Indicator_config" cfg
            ON cfg."IndicatorCode" = val."IndicatorCode"
           AND cfg."Timeframe" = val."Timeframe"
        WHERE val."Ticker" = 'MWG'
          AND val."Date" <= DATE '{as_of}'
          AND cfg."IndicatorCode" = 'MA'
          AND cfg."Timeframe" IN ('D', 'W', 'M')
          AND cfg."ConfigIsEnabled" = TRUE
          AND cfg."IndicatorIsActive" = TRUE
          AND COALESCE(cfg."ComponentIsActive", TRUE) = TRUE
          AND val."ComponentCode" = 'VALUE'
          AND val."Value" IS NOT NULL
    )
    SELECT "Ticker", "Date", "ConfigId", "ConfigCode", "Timeframe", "Value", "Parameters"
    FROM ranked WHERE rn = 1
    ORDER BY "Timeframe", "ConfigCode"
""").df()
print(latest.to_string())
print("rows:", len(latest))
if len(latest):
    print("all >0:", bool((latest["Value"] > 0).all()))
    lens = sorted({json.loads(p)["length"] for p in latest["Parameters"]})
    print("lengths:", lens)
con.close()
