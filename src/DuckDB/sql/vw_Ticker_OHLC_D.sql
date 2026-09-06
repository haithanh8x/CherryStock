-- Public daily ticker OHLC + intraday transaction-flow contract.
-- Grain: one row per Ticker + Date.
--
-- OHLCV remains owned by raw_stock_eod.
-- TradingValue / BuyUp / SellDown / ATO / ATC are derived from raw_stock_intraday.
--
-- Missing-data contract:
--   EOD Volume=0 with no Intraday row => true zero flow/value.
--   EOD Volume>0 with no Intraday row => NULL (Intraday coverage missing).
--
-- Value-unit contract:
--   AmiBroker stock price is stored in thousand VND/share.
--   *_Val = ROUND(SUM(tick Close * tick Volume * 1000))::BIGINT
--   All *_Val and *_Vol outputs are integer values with no decimal points.
--
-- Auction windows (verified against raw_stock_intraday OpenInt=3 tick times):
--   ATO: 09:00:00 - 09:20:00 (matching results publish after 09:15 close)
--   ATC: 14:30:00 - 14:50:00 (matching results publish after 14:45 close)

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Ticker_OHLC_D" AS
WITH intraday_daily AS (
    SELECT
        i."Ticker",
        i."Date",
        CAST(ROUND(SUM(CAST(i."Close" AS DOUBLE) * CAST(i."Volume" AS DOUBLE) * 1000.0)) AS BIGINT) AS "TradingValue",
        CAST(ROUND(SUM(CASE WHEN i."OpenInt" = 2 THEN CAST(i."Close" AS DOUBLE) * CAST(i."Volume" AS DOUBLE) * 1000.0 ELSE 0.0 END)) AS BIGINT) AS "BuyUp_Val",
        CAST(SUM(CASE WHEN i."OpenInt" = 2 THEN i."Volume" ELSE 0 END) AS BIGINT) AS "BuyUp_Vol",
        CAST(ROUND(SUM(CASE WHEN i."OpenInt" = 1 THEN CAST(i."Close" AS DOUBLE) * CAST(i."Volume" AS DOUBLE) * 1000.0 ELSE 0.0 END)) AS BIGINT) AS "SellDown_Val",
        CAST(SUM(CASE WHEN i."OpenInt" = 1 THEN i."Volume" ELSE 0 END) AS BIGINT) AS "SellDown_Vol",
        CAST(ROUND(SUM(CASE
            WHEN i."OpenInt" = 3
             AND CAST(i."DateTime" AS TIME) >= TIME '09:00:00'
             AND CAST(i."DateTime" AS TIME) <= TIME '09:20:00'
            THEN CAST(i."Close" AS DOUBLE) * CAST(i."Volume" AS DOUBLE) * 1000.0
            ELSE 0.0 END)) AS BIGINT) AS "ATO_Val",
        CAST(SUM(CASE
            WHEN i."OpenInt" = 3
             AND CAST(i."DateTime" AS TIME) >= TIME '09:00:00'
             AND CAST(i."DateTime" AS TIME) <= TIME '09:20:00'
            THEN i."Volume" ELSE 0 END) AS BIGINT) AS "ATO_Vol",
        CAST(ROUND(SUM(CASE
            WHEN i."OpenInt" = 3
             AND CAST(i."DateTime" AS TIME) >= TIME '14:30:00'
             AND CAST(i."DateTime" AS TIME) <= TIME '14:50:00'
            THEN CAST(i."Close" AS DOUBLE) * CAST(i."Volume" AS DOUBLE) * 1000.0
            ELSE 0.0 END)) AS BIGINT) AS "ATC_Val",
        CAST(SUM(CASE
            WHEN i."OpenInt" = 3
             AND CAST(i."DateTime" AS TIME) >= TIME '14:30:00'
             AND CAST(i."DateTime" AS TIME) <= TIME '14:50:00'
            THEN i."Volume" ELSE 0 END) AS BIGINT) AS "ATC_Vol"
    FROM "CherryMon"."main"."raw_stock_intraday" AS i
    GROUP BY i."Ticker", i."Date"
)
SELECT
    e."Ticker",
    e."Date",
    e."Open",
    e."High",
    e."Low",
    e."Close",
    e."Volume",
    CASE WHEN d."Ticker" IS NOT NULL THEN d."TradingValue" WHEN COALESCE(e."Volume", 0) = 0 THEN CAST(0 AS BIGINT) ELSE NULL END AS "TradingValue",
    CASE WHEN d."Ticker" IS NOT NULL THEN d."BuyUp_Val" WHEN COALESCE(e."Volume", 0) = 0 THEN CAST(0 AS BIGINT) ELSE NULL END AS "BuyUp_Val",
    CASE WHEN d."Ticker" IS NOT NULL THEN d."BuyUp_Vol" WHEN COALESCE(e."Volume", 0) = 0 THEN CAST(0 AS BIGINT) ELSE NULL END AS "BuyUp_Vol",
    CASE WHEN d."Ticker" IS NOT NULL THEN d."SellDown_Val" WHEN COALESCE(e."Volume", 0) = 0 THEN CAST(0 AS BIGINT) ELSE NULL END AS "SellDown_Val",
    CASE WHEN d."Ticker" IS NOT NULL THEN d."SellDown_Vol" WHEN COALESCE(e."Volume", 0) = 0 THEN CAST(0 AS BIGINT) ELSE NULL END AS "SellDown_Vol",
    CASE WHEN d."Ticker" IS NOT NULL THEN d."ATO_Val" WHEN COALESCE(e."Volume", 0) = 0 THEN CAST(0 AS BIGINT) ELSE NULL END AS "ATO_Val",
    CASE WHEN d."Ticker" IS NOT NULL THEN d."ATO_Vol" WHEN COALESCE(e."Volume", 0) = 0 THEN CAST(0 AS BIGINT) ELSE NULL END AS "ATO_Vol",
    CASE WHEN d."Ticker" IS NOT NULL THEN d."ATC_Val" WHEN COALESCE(e."Volume", 0) = 0 THEN CAST(0 AS BIGINT) ELSE NULL END AS "ATC_Val",
    CASE WHEN d."Ticker" IS NOT NULL THEN d."ATC_Vol" WHEN COALESCE(e."Volume", 0) = 0 THEN CAST(0 AS BIGINT) ELSE NULL END AS "ATC_Vol"
FROM "CherryMon"."main"."raw_stock_eod" AS e
LEFT JOIN intraday_daily AS d
    ON d."Ticker" = e."Ticker"
   AND d."Date" = e."Date";
