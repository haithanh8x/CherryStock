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
-- Missing-data contract:
--   EOD Volume=0 with no Intraday row => true zero flow/value.
--   EOD Volume>0 with no Intraday row => NULL (Intraday coverage missing).
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
    CASE
        WHEN d."Ticker" IS NOT NULL THEN d."TradingValue"
        WHEN COALESCE(e."Volume", 0) = 0 THEN 0.0
        ELSE NULL
    END AS "TradingValue",
    CASE
        WHEN d."Ticker" IS NOT NULL THEN d."BuyUp_Val"
        WHEN COALESCE(e."Volume", 0) = 0 THEN 0.0
        ELSE NULL
    END AS "BuyUp_Val",
    CASE
        WHEN d."Ticker" IS NOT NULL THEN d."BuyUp_Vol"
        WHEN COALESCE(e."Volume", 0) = 0 THEN 0
        ELSE NULL
    END AS "BuyUp_Vol",
    CASE
        WHEN d."Ticker" IS NOT NULL THEN d."SellDown_Val"
        WHEN COALESCE(e."Volume", 0) = 0 THEN 0.0
        ELSE NULL
    END AS "SellDown_Val",
    CASE
        WHEN d."Ticker" IS NOT NULL THEN d."SellDown_Vol"
        WHEN COALESCE(e."Volume", 0) = 0 THEN 0
        ELSE NULL
    END AS "SellDown_Vol",
    CASE
        WHEN d."Ticker" IS NOT NULL THEN d."ATO_Val"
        WHEN COALESCE(e."Volume", 0) = 0 THEN 0.0
        ELSE NULL
    END AS "ATO_Val",
    CASE
        WHEN d."Ticker" IS NOT NULL THEN d."ATO_Vol"
        WHEN COALESCE(e."Volume", 0) = 0 THEN 0
        ELSE NULL
    END AS "ATO_Vol",
    CASE
        WHEN d."Ticker" IS NOT NULL THEN d."ATC_Val"
        WHEN COALESCE(e."Volume", 0) = 0 THEN 0.0
        ELSE NULL
    END AS "ATC_Val",
    CASE
        WHEN d."Ticker" IS NOT NULL THEN d."ATC_Vol"
        WHEN COALESCE(e."Volume", 0) = 0 THEN 0
        ELSE NULL
    END AS "ATC_Vol"
FROM "CherryMon"."main"."raw_stock_eod" AS e
LEFT JOIN intraday_daily AS d
    ON d."Ticker" = e."Ticker"
   AND d."Date" = e."Date";
