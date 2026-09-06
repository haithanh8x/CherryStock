-- vw_Ticker_OHLC_D read-only preflight.
-- Run after src/DuckDB/sql/vw_Ticker_OHLC_D.sql.
-- No DDL/DML.

-- 1) View exists.
SELECT
    table_name
FROM information_schema.views
WHERE lower(table_catalog) = 'cherrymon'
  AND lower(table_schema) = 'main'
  AND lower(table_name) = 'vw_ticker_ohlc_d';

-- PASS: 1 row.


-- 2) Public column contract.
SELECT
    ordinal_position,
    column_name,
    data_type
FROM information_schema.columns
WHERE lower(table_catalog) = 'cherrymon'
  AND lower(table_schema) = 'main'
  AND lower(table_name) = 'vw_ticker_ohlc_d'
ORDER BY ordinal_position;

-- Expected columns:
-- Ticker, Date, Open, High, Low, Close, Volume,
-- TradingValue,
-- BuyUp_Val, BuyUp_Vol,
-- SellDown_Val, SellDown_Vol,
-- ATO_Val, ATO_Vol,
-- ATC_Val, ATC_Vol.


-- 3) One row per Ticker + Date.
SELECT
    COUNT(*) AS duplicate_groups
FROM (
    SELECT
        "Ticker",
        "Date",
        COUNT(*) AS rows_per_key
    FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
    GROUP BY "Ticker", "Date"
    HAVING COUNT(*) > 1
) AS d;

-- PASS: duplicate_groups = 0.


-- 4) Recent non-negative flow/value checks.
WITH recent AS (
    SELECT
        "Ticker",
        "Date",
        "TradingValue",
        "BuyUp_Val",
        "BuyUp_Vol",
        "SellDown_Val",
        "SellDown_Vol",
        "ATO_Val",
        "ATO_Vol",
        "ATC_Val",
        "ATC_Vol"
    FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_stock_intraday"
    )
)
SELECT
    COUNT(*) AS rows_checked,
    SUM(CASE WHEN "TradingValue" < 0 THEN 1 ELSE 0 END) AS negative_trading_value,
    SUM(CASE WHEN "BuyUp_Val" < 0 OR "BuyUp_Vol" < 0 THEN 1 ELSE 0 END) AS negative_buyup,
    SUM(CASE WHEN "SellDown_Val" < 0 OR "SellDown_Vol" < 0 THEN 1 ELSE 0 END) AS negative_selldown,
    SUM(CASE WHEN "ATO_Val" < 0 OR "ATO_Vol" < 0 THEN 1 ELSE 0 END) AS negative_ato,
    SUM(CASE WHEN "ATC_Val" < 0 OR "ATC_Vol" < 0 THEN 1 ELSE 0 END) AS negative_atc
FROM recent;

-- PASS: all negative_* counts = 0.


-- 5) TradingValue must be >= explicitly classified value buckets.
-- A positive remainder is valid because OpenInt=3 outside ATO/ATC or other
-- source classifications are intentionally not force-assigned.
-- Tolerance: 4 buckets are rounded independently (each +/- 0.5), so the sum
-- can legitimately exceed TradingValue by up to 2 units.
SELECT
    COUNT(*) AS invalid_value_decomposition_rows
FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
WHERE "TradingValue" IS NOT NULL
  AND "TradingValue" + 2.5 <
      COALESCE("BuyUp_Val", 0)
    + COALESCE("SellDown_Val", 0)
    + COALESCE("ATO_Val", 0)
    + COALESCE("ATC_Val", 0);

-- PASS: 0.


-- 6) OI=3 timestamp distribution to validate auction classification assumptions.
-- Informational: review top timestamps; expected ATO/ATC clusters should be visible.
SELECT
    CAST("DateTime" AS TIME) AS trade_time,
    COUNT(*) AS ticks,
    SUM("Volume") AS volume
FROM "CherryMon"."main"."raw_stock_intraday"
WHERE "OpenInt" = 3
  AND "Date" >= (
      SELECT MAX("Date") - INTERVAL 30 DAY
      FROM "CherryMon"."main"."raw_stock_intraday"
  )
GROUP BY CAST("DateTime" AS TIME)
ORDER BY ticks DESC
LIMIT 50;


-- 7) Quantify OI=3 records intentionally left unclassified.
WITH oi3 AS (
    SELECT
        "Ticker",
        "Date",
        "DateTime",
        "Close",
        "Volume"
    FROM "CherryMon"."main"."raw_stock_intraday"
    WHERE "OpenInt" = 3
      AND "Date" >= (
          SELECT MAX("Date") - INTERVAL 30 DAY
          FROM "CherryMon"."main"."raw_stock_intraday"
      )
),
classified AS (
    SELECT
        *,
        CASE
            WHEN CAST("DateTime" AS TIME) >= TIME '09:00:00'
             AND CAST("DateTime" AS TIME) <= TIME '09:20:00'
            THEN 'ATO'
            WHEN CAST("DateTime" AS TIME) >= TIME '14:30:00'
             AND CAST("DateTime" AS TIME) <= TIME '14:50:00'
            THEN 'ATC'
            ELSE 'UNCLASSIFIED_OI3'
        END AS bucket
    FROM oi3
)
SELECT
    bucket,
    COUNT(*) AS ticks,
    SUM("Volume") AS volume,
    SUM(CAST("Close" AS DOUBLE) * CAST("Volume" AS DOUBLE)) AS value
FROM classified
GROUP BY bucket
ORDER BY bucket;

-- Review only. UNCLASSIFIED_OI3 is not automatically a failure.


-- 8) Zero-trade days versus missing-Intraday days.
WITH recent_eod AS (
    SELECT
        e."Ticker",
        e."Date",
        e."Volume",
        CASE WHEN i."Ticker" IS NULL THEN FALSE ELSE TRUE END AS has_intraday
    FROM "CherryMon"."main"."raw_stock_eod" AS e
    LEFT JOIN (
        SELECT DISTINCT "Ticker", "Date"
        FROM "CherryMon"."main"."raw_stock_intraday"
    ) AS i
        ON i."Ticker" = e."Ticker"
       AND i."Date" = e."Date"
    WHERE e."Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_stock_eod"
    )
)
SELECT
    SUM(
        CASE
            WHEN r."Volume" = 0
             AND r.has_intraday = FALSE
             AND (
                    v."TradingValue" <> 0
                 OR v."BuyUp_Val" <> 0 OR v."BuyUp_Vol" <> 0
                 OR v."SellDown_Val" <> 0 OR v."SellDown_Vol" <> 0
                 OR v."ATO_Val" <> 0 OR v."ATO_Vol" <> 0
                 OR v."ATC_Val" <> 0 OR v."ATC_Vol" <> 0
             )
            THEN 1 ELSE 0
        END
    ) AS invalid_zero_trade_rows,
    SUM(
        CASE
            WHEN r."Volume" > 0
             AND r.has_intraday = FALSE
             AND (
                    v."TradingValue" IS NOT NULL
                 OR v."BuyUp_Val" IS NOT NULL OR v."BuyUp_Vol" IS NOT NULL
                 OR v."SellDown_Val" IS NOT NULL OR v."SellDown_Vol" IS NOT NULL
                 OR v."ATO_Val" IS NOT NULL OR v."ATO_Vol" IS NOT NULL
                 OR v."ATC_Val" IS NOT NULL OR v."ATC_Vol" IS NOT NULL
             )
            THEN 1 ELSE 0
        END
    ) AS invalid_missing_coverage_rows
FROM recent_eod AS r
INNER JOIN "CherryMon"."main"."vw_Ticker_OHLC_D" AS v
    ON v."Ticker" = r."Ticker"
   AND v."Date" = r."Date";

-- PASS: both counts = 0.
