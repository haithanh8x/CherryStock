-- Public daily ticker OHLC + intraday transaction-flow contract.
-- Grain: one row per Ticker + Date.
--
-- OHLCV remains owned by raw_stock_eod.
-- TradingValue / BuyUp / SellDown / ATO / ATC are derived from raw_stock_intraday
-- tick records. FireAnt documents intraday OpenInt as:
--   1 = active sell
--   2 = active buy
--   3 = active buy and sell simultaneously
--
-- ATO/ATC require BOTH OpenInt=3 and an auction-session timestamp.
-- OpenInt=3 outside those windows remains included in TradingValue but is not
-- force-classified as ATO or ATC.
--
-- Value-unit contract:
--   *_Val = SUM(tick Close * tick Volume)
-- The result is in source-price-unit * source-volume-unit. No silent price-scale
-- multiplier is applied here.

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Ticker_OHLC_D" AS
WITH intraday_daily AS (
    SELECT
        i."Ticker",
        i."Date",

        SUM(
            CAST(i."Close" AS DOUBLE) * CAST(i."Volume" AS DOUBLE)
        ) AS "TradingValue",

        SUM(
            CASE
                WHEN i."OpenInt" = 2
                THEN CAST(i."Close" AS DOUBLE) * CAST(i."Volume" AS DOUBLE)
                ELSE 0.0
            END
        ) AS "BuyUp_Val",
        SUM(
            CASE
                WHEN i."OpenInt" = 2 THEN i."Volume"
                ELSE 0
            END
        ) AS "BuyUp_Vol",

        SUM(
            CASE
                WHEN i."OpenInt" = 1
                THEN CAST(i."Close" AS DOUBLE) * CAST(i."Volume" AS DOUBLE)
                ELSE 0.0
            END
        ) AS "SellDown_Val",
        SUM(
            CASE
                WHEN i."OpenInt" = 1 THEN i."Volume"
                ELSE 0
            END
        ) AS "SellDown_Vol",

        SUM(
            CASE
                WHEN i."OpenInt" = 3
                 AND CAST(i."DateTime" AS TIME) >= TIME '09:00:00'
                 AND CAST(i."DateTime" AS TIME) <= TIME '09:15:00'
                THEN CAST(i."Close" AS DOUBLE) * CAST(i."Volume" AS DOUBLE)
                ELSE 0.0
            END
        ) AS "ATO_Val",
        SUM(
            CASE
                WHEN i."OpenInt" = 3
                 AND CAST(i."DateTime" AS TIME) >= TIME '09:00:00'
                 AND CAST(i."DateTime" AS TIME) <= TIME '09:15:00'
                THEN i."Volume"
                ELSE 0
            END
        ) AS "ATO_Vol",

        SUM(
            CASE
                WHEN i."OpenInt" = 3
                 AND CAST(i."DateTime" AS TIME) >= TIME '14:30:00'
                 AND CAST(i."DateTime" AS TIME) <= TIME '14:45:00'
                THEN CAST(i."Close" AS DOUBLE) * CAST(i."Volume" AS DOUBLE)
                ELSE 0.0
            END
        ) AS "ATC_Val",
        SUM(
            CASE
                WHEN i."OpenInt" = 3
                 AND CAST(i."DateTime" AS TIME) >= TIME '14:30:00'
                 AND CAST(i."DateTime" AS TIME) <= TIME '14:45:00'
                THEN i."Volume"
                ELSE 0
            END
        ) AS "ATC_Vol"
    FROM "CherryMon"."main"."raw_stock_intraday" AS i
    GROUP BY
        i."Ticker",
        i."Date"
)
SELECT
    e."Ticker",
    e."Date",
    e."Open",
    e."High",
    e."Low",
    e."Close",
    e."Volume",
    d."TradingValue",
    d."BuyUp_Val",
    d."BuyUp_Vol",
    d."SellDown_Val",
    d."SellDown_Vol",
    d."ATO_Val",
    d."ATO_Vol",
    d."ATC_Val",
    d."ATC_Vol"
FROM "CherryMon"."main"."raw_stock_eod" AS e
LEFT JOIN intraday_daily AS d
    ON d."Ticker" = e."Ticker"
   AND d."Date" = e."Date";
