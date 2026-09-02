"""Read-only diagnostic for RS Ladder V1 public contract (tests/test_R_S.md sections 3-6)."""
import json
import sys

import duckdb

DB = "C:/OneDrive/Working/Datafile/CherryMon.duckdb"

con = duckdb.connect(DB, read_only=True)

print("== 3.1 objects ==")
print(con.sql("""
    SELECT table_schema, table_name, table_type
    FROM information_schema.tables
    WHERE (table_name LIKE 'vw_%' OR table_name = 'raw_stock_eod')
    ORDER BY table_name
""").df().to_string())

for view in ("raw_stock_eod", "vw_Indicator_config", "vw_Ticker_indicators"):
    print(f"\n== 3.2 describe {view} ==")
    try:
        cols = con.sql(f"""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = '{view}' ORDER BY ordinal_position
        """).df()["column_name"].tolist()
        print(cols)
    except Exception as exc:
        print("ERROR:", exc)

print("\n== 4. MWG snapshot ==")
snap = con.sql("""
    SELECT "Ticker", "Date", "Close"
    FROM "CherryMon"."main"."raw_stock_eod"
    WHERE "Ticker" = 'MWG' AND "Close" IS NOT NULL
    ORDER BY "Date" DESC LIMIT 1
""").df()
print(snap.to_string())
as_of = snap["Date"].iloc[0] if len(snap) else None
print("AS_OF_DATE:", as_of)

print("\n== 5. V1 MA config family ==")
cfg = con.sql("""
    SELECT "ConfigId", "ConfigCode", "IndicatorCode", "Timeframe", "Parameters",
           "ComponentCode", "ConfigIsEnabled", "IndicatorIsActive", "ComponentIsActive"
    FROM "CherryMon"."main"."vw_Indicator_config"
    WHERE "IndicatorCode" = 'MA'
      AND "Timeframe" IN ('D', 'W', 'M')
      AND "ComponentCode" = 'VALUE'
      AND "ConfigIsEnabled" = TRUE
      AND "IndicatorIsActive" = TRUE
      AND COALESCE("ComponentIsActive", TRUE) = TRUE
    ORDER BY "Timeframe", "ConfigId"
""").df()
print(cfg.to_string())
lengths = {}
for _, row in cfg.iterrows():
    try:
        p = json.loads(row["Parameters"]) if isinstance(row["Parameters"], str) else row["Parameters"]
        lengths.setdefault(row["Timeframe"], set()).add(p.get("length"))
    except Exception as exc:
        print("PARAM PARSE FAIL:", row["ConfigCode"], exc)
print("lengths by timeframe:", {k: sorted(v) for k, v in lengths.items()})
print("target count (12):", len(cfg))

print("\n== 6. latest MA values for MWG ==")
if as_of is not None:
    latest = con.sql(f"""
        WITH ranked AS (
            SELECT val."Ticker", val."Date", val."ConfigId", val."ComponentCode", val."Value",
                   cfg."ConfigCode", cfg."Timeframe", cfg."Parameters",
                   ROW_NUMBER() OVER (PARTITION BY val."ConfigId", val."ComponentCode"
                                      ORDER BY val."Date" DESC) AS rn
            FROM "CherryMon"."main"."vw_Ticker_indicators" val
            INNER JOIN "CherryMon"."main"."vw_Indicator_config" cfg
                ON cfg."ConfigId" = val."ConfigId" AND cfg."ComponentCode" = val."ComponentCode"
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
        SELECT "Ticker", "Date", "ConfigId", "ComponentCode", "Value",
               "ConfigCode", "Timeframe", "Parameters"
        FROM ranked WHERE rn = 1
        ORDER BY "Timeframe", "ConfigId"
    """).df()
    print(latest.to_string())
    print("rows:", len(latest), "| all >0:", bool((latest["Value"] > 0).all()) if len(latest) else "n/a")

con.close()
