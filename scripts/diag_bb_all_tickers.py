"""One-off: probe all 340 tickers for BB negative/latest-row issues in eval window.

The H5 crash happened mid-loop (ticker after MWG, alphabetical). Find every
ticker whose latest-at-or-before snapshot BB level rows contain a non-positive
value. Read-only.
"""
from datetime import date

import duckdb

con = duckdb.connect("C:/OneDrive/Working/Datafile/CherryMon.duckdb", read_only=True)

# Find tickers where the latest BB LOWER/MIDDLE/UPPER row (per config/component)
# has a non-positive value at some evaluation snapshot date in the range.
bad = con.sql("""
    WITH candidates AS (
        SELECT
            val."Ticker", val."Date", val."ConfigId", val."ComponentCode", val."Value",
            cfg."ConfigCode"
        FROM "CherryMon"."main"."vw_Ticker_indicators" val
        INNER JOIN "CherryMon"."main"."vw_Indicator_config" cfg
            ON cfg."ConfigId" = val."ConfigId"
           AND cfg."ComponentCode" = val."ComponentCode"
        WHERE cfg."IndicatorCode" = 'BB'
          AND cfg."ComponentCode" IN ('LOWER', 'MIDDLE', 'UPPER')
          AND cfg."ConfigIsEnabled" = TRUE
          AND cfg."IndicatorIsActive" = TRUE
          AND val."Value" IS NOT NULL
          AND val."Date" BETWEEN DATE '2023-07-04' AND DATE '2026-07-03'
    ),
    latest AS (
        SELECT *, ROW_NUMBER() OVER (
            PARTITION BY "Ticker", "ConfigId", "ComponentCode"
            ORDER BY "Date" DESC
        ) AS rn
        FROM candidates
    )
    SELECT "Ticker", "Date", "ConfigId", "ComponentCode", "Value", "ConfigCode"
    FROM latest
    WHERE rn = 1 AND "Value" <= 0
    ORDER BY "Ticker", "ConfigId", "ComponentCode"
""").df()
print("bad latest rows:", len(bad))
print(bad.head(30))
if len(bad):
    print("tickers affected:", sorted(bad["Ticker"].unique()))
con.close()
