-- vw_Ticker_OHLC_D read-only preflight.
-- Run after src/DuckDB/sql/vw_Ticker_OHLC_D.sql.
-- No DDL/DML.

-- 1) View exists.
SELECT table_name
FROM information_schema.views
WHERE lower(table_catalog) = 'cherrymon'
  AND lower(table_schema) = 'main'
  AND lower(table_name) = 'vw_ticker_ohlc_d';

-- PASS: 1 row.

-- 2) Public column contract.
SELECT ordinal_position, column_name, data_type
FROM information_schema.columns
WHERE lower(table_catalog) = 'cherrymon'
  AND lower(table_schema) = 'main'
  AND lower(table_name) = 'vw_ticker_ohlc_d'
ORDER BY ordinal_position;

-- Expected 18 columns:
-- Ticker, Date, Open, High, Low, Close, Volume,
-- TradingValue, TradingValue_Source, TradingValue_IsProxy,
-- BuyUp_Val, BuyUp_Vol, SellDown_Val, SellDown_Vol,
-- ATO_Val, ATO_Vol, ATC_Val, ATC_Vol.

-- 3) One row per Ticker + Date.
SELECT COUNT(*) AS duplicate_groups
FROM (
    SELECT "Ticker", "Date", COUNT(*) AS rows_per_key
    FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
    GROUP BY "Ticker", "Date"
    HAVING COUNT(*) > 1
) AS d;

-- PASS: 0.

-- 4) Value/provenance distribution.
SELECT
    "TradingValue_Source",
    "TradingValue_IsProxy",
    COUNT(*) AS rows,
    MIN("Date") AS min_date,
    MAX("Date") AS max_date
FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
GROUP BY "TradingValue_Source", "TradingValue_IsProxy"
ORDER BY "TradingValue_Source";

-- Expected combinations:
-- INTRADAY_TICK            / FALSE
-- EOD_TYPICAL_PRICE_PROXY  / TRUE
-- NO_TRADE                 / FALSE
-- MISSING_INPUT            / NULL (only when H/L/C are incomplete)

-- 5) Verify proxy formula exactly for positive-volume dates without Intraday.
WITH intraday_keys AS (
    SELECT DISTINCT "Ticker", "Date"
    FROM "CherryMon"."main"."raw_stock_intraday"
), expected AS (
    SELECT
        e."Ticker",
        e."Date",
        CAST(ROUND(((e."High" + e."Low" + e."Close") / 3.0)
            * CAST(e."Volume" AS DOUBLE) * 1000.0) AS BIGINT) AS expected_value
    FROM "CherryMon"."main"."raw_stock_eod" AS e
    LEFT JOIN intraday_keys AS i
        ON i."Ticker" = e."Ticker" AND i."Date" = e."Date"
    WHERE i."Ticker" IS NULL
      AND e."Volume" > 0
      AND e."High" IS NOT NULL
      AND e."Low" IS NOT NULL
      AND e."Close" IS NOT NULL
)
SELECT COUNT(*) AS invalid_proxy_rows
FROM expected AS x
INNER JOIN "CherryMon"."main"."vw_Ticker_OHLC_D" AS v
    ON v."Ticker" = x."Ticker" AND v."Date" = x."Date"
WHERE v."TradingValue" <> x.expected_value
   OR v."TradingValue_Source" <> 'EOD_TYPICAL_PRICE_PROXY'
   OR v."TradingValue_IsProxy" IS DISTINCT FROM TRUE;

-- PASS: 0.

-- 6) Verify Intraday dates use tick value, not EOD proxy.
WITH expected AS (
    SELECT
        "Ticker",
        "Date",
        CAST(ROUND(SUM(CAST("Close" AS DOUBLE) * CAST("Volume" AS DOUBLE) * 1000.0)) AS BIGINT) AS expected_value
    FROM "CherryMon"."main"."raw_stock_intraday"
    GROUP BY "Ticker", "Date"
)
SELECT COUNT(*) AS invalid_intraday_trading_value_rows
FROM expected AS x
INNER JOIN "CherryMon"."main"."vw_Ticker_OHLC_D" AS v
    ON v."Ticker" = x."Ticker" AND v."Date" = x."Date"
WHERE v."TradingValue" <> x.expected_value
   OR v."TradingValue_Source" <> 'INTRADAY_TICK'
   OR v."TradingValue_IsProxy" IS DISTINCT FROM FALSE;

-- PASS: 0.

-- 7) Zero-volume EOD-only days must be true zero, not proxy.
WITH intraday_keys AS (
    SELECT DISTINCT "Ticker", "Date"
    FROM "CherryMon"."main"."raw_stock_intraday"
)
SELECT COUNT(*) AS invalid_no_trade_rows
FROM "CherryMon"."main"."raw_stock_eod" AS e
LEFT JOIN intraday_keys AS i
    ON i."Ticker" = e."Ticker" AND i."Date" = e."Date"
INNER JOIN "CherryMon"."main"."vw_Ticker_OHLC_D" AS v
    ON v."Ticker" = e."Ticker" AND v."Date" = e."Date"
WHERE i."Ticker" IS NULL
  AND COALESCE(e."Volume", 0) = 0
  AND (
       v."TradingValue" <> 0
       OR v."TradingValue_Source" <> 'NO_TRADE'
       OR v."TradingValue_IsProxy" IS DISTINCT FROM FALSE
  );

-- PASS: 0.

-- 8) Flow fields must stay NULL when positive-volume EOD uses proxy.
SELECT COUNT(*) AS proxy_rows_with_fake_flow
FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
WHERE "TradingValue_Source" = 'EOD_TYPICAL_PRICE_PROXY'
  AND (
       "BuyUp_Val" IS NOT NULL OR "BuyUp_Vol" IS NOT NULL
       OR "SellDown_Val" IS NOT NULL OR "SellDown_Vol" IS NOT NULL
       OR "ATO_Val" IS NOT NULL OR "ATO_Vol" IS NOT NULL
       OR "ATC_Val" IS NOT NULL OR "ATC_Vol" IS NOT NULL
  );

-- PASS: 0.

-- 9) TradingValue must cover classified flow buckets on Intraday dates.
SELECT COUNT(*) AS invalid_value_decomposition_rows
FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
WHERE "TradingValue_Source" = 'INTRADAY_TICK'
  AND "TradingValue" + 2.5 <
      COALESCE("BuyUp_Val", 0)
    + COALESCE("SellDown_Val", 0)
    + COALESCE("ATO_Val", 0)
    + COALESCE("ATC_Val", 0);

-- PASS: 0.

-- 10) OI=3 timestamp distribution remains informational.
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
