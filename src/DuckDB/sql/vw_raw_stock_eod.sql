-- Public enriched stock EOD view with derived reference/limit prices and limit streaks.
-- Grain: one row per Ticker + Date.
--
-- Price units follow raw_stock_eod: thousand VND/share.
--
-- Standard-session rules (VNX rules effective 2026):
--   HOSE  : reference = nearest previous closing price, normal band +/-7%.
--   HNX   : reference = nearest previous closing price, normal band +/-10%.
--   UPCOM : reference = weighted-average price of nearest previous eligible
--           regular-lot continuous-matching session, normal band +/-15%.
--
-- Quote units:
--   HOSE stock: <10,000 VND = 10 VND; 10,000-49,950 = 50 VND; >=50,000 = 100 VND.
--   HNX stock : 100 VND.
--   UPCOM     : 100 VND.
--
-- Ceiling is rounded DOWN and Floor is rounded UP to the applicable quote unit.
--
-- IMPORTANT QUALITY BOUNDARY
-- --------------------------
-- raw_stock_fa.Market is a current snapshot, not a point-in-time exchange history.
-- raw_stock_eod can be corporate-action adjusted historically.
-- raw_stock_intraday does not carry an explicit regular-lot/negotiated-trade flag.
-- Therefore this view is a standard-rule DERIVED contract, not an exchange-published
-- authoritative daily price-limit feed. Special-session rules (first trading day,
-- trading resumption after long suspension, ex-right/corporate actions, exchange
-- migration history) are not silently guessed.
--
-- UPCOM best-effort eligible-session proxy:
--   * OpenInt IN (1,2,3) => FireAnt matched-trade classification is present.
--   * Volume >= 100 and Volume divisible by 100 => regular-lot-compatible tick.
-- The resulting VWAP is marked proxy because the source does not explicitly prove
-- that negotiated/odd-lot records are fully excluded.
--
-- LimitUp / LimitDown mean DAILY CLOSE at the derived ceiling/floor.
-- Streaks count consecutive available EOD rows with the same TRUE state.

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_raw_stock_eod" AS
WITH market_ranked AS (
    SELECT
        fa."Ticker",
        fa."Market",
        fa."Date",
        ROW_NUMBER() OVER (
            PARTITION BY fa."Ticker"
            ORDER BY fa."Date" DESC NULLS LAST
        ) AS rn
    FROM "CherryMon"."main"."raw_stock_fa" AS fa
),
market_map AS (
    SELECT
        "Ticker",
        CASE
            WHEN upper(trim(CAST("Market" AS VARCHAR))) IN ('HOSE', 'HSX') THEN 'HOSE'
            WHEN upper(trim(CAST("Market" AS VARCHAR))) = 'HNX' THEN 'HNX'
            WHEN upper(trim(CAST("Market" AS VARCHAR))) IN ('UPCOM', 'UPCOM ') THEN 'UPCOM'
            ELSE upper(trim(CAST("Market" AS VARCHAR)))
        END AS "Market"
    FROM market_ranked
    WHERE rn = 1
),
upcom_session_vwap AS (
    SELECT
        i."Ticker",
        i."Date",
        ROUND(
            (
                SUM(CAST(i."Close" AS DOUBLE) * CAST(i."Volume" AS DOUBLE))
                / NULLIF(SUM(CAST(i."Volume" AS DOUBLE)), 0.0)
            ) / 0.1
        ) * 0.1 AS session_reference_price
    FROM "CherryMon"."main"."raw_stock_intraday" AS i
    WHERE i."Close" IS NOT NULL
      AND i."Close" > 0
      AND i."Volume" IS NOT NULL
      AND i."Volume" >= 100
      AND MOD(i."Volume", 100) = 0
      AND i."OpenInt" IN (1, 2, 3)
    GROUP BY i."Ticker", i."Date"
),
history_inputs AS (
    SELECT
        e."Ticker",
        e."Date",
        e."Open",
        e."High",
        e."Low",
        e."Close",
        e."Volume",
        e."OpenInt",
        m."Market",
        LAST_VALUE(e."Close" IGNORE NULLS) OVER (
            PARTITION BY e."Ticker"
            ORDER BY e."Date"
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS previous_close_raw,
        LAST_VALUE(u.session_reference_price IGNORE NULLS) OVER (
            PARTITION BY e."Ticker"
            ORDER BY e."Date"
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS previous_upcom_vwap_raw
    FROM "CherryMon"."main"."raw_stock_eod" AS e
    LEFT JOIN market_map AS m
        ON m."Ticker" = e."Ticker"
    LEFT JOIN upcom_session_vwap AS u
        ON u."Ticker" = e."Ticker"
       AND u."Date" = e."Date"
),
reference_raw AS (
    SELECT
        h.*,
        CASE
            WHEN h."Market" IN ('HOSE', 'HNX') THEN h.previous_close_raw
            WHEN h."Market" = 'UPCOM' THEN h.previous_upcom_vwap_raw
            ELSE NULL
        END AS reference_price_raw,
        CASE
            WHEN h."Market" IN ('HOSE', 'HNX') AND h.previous_close_raw IS NOT NULL
                THEN 'PREVIOUS_CLOSE_STANDARD_RULE'
            WHEN h."Market" = 'UPCOM' AND h.previous_upcom_vwap_raw IS NOT NULL
                THEN 'UPCOM_INTRADAY_LOT100_VWAP_PROXY'
            WHEN h."Market" IS NULL OR h."Market" = ''
                THEN 'MISSING_MARKET'
            ELSE 'MISSING_PREVIOUS_REFERENCE'
        END AS reference_price_source,
        CASE
            WHEN h."Market" IN ('HOSE', 'HNX') AND h.previous_close_raw IS NOT NULL THEN FALSE
            WHEN h."Market" = 'UPCOM' AND h.previous_upcom_vwap_raw IS NOT NULL THEN TRUE
            ELSE NULL
        END AS reference_price_is_proxy
    FROM history_inputs AS h
),
reference_quote AS (
    SELECT
        r.*,
        CASE
            WHEN r.reference_price_raw IS NULL THEN NULL
            WHEN r."Market" = 'HOSE' AND r.reference_price_raw < 10.0 THEN 0.01
            WHEN r."Market" = 'HOSE' AND r.reference_price_raw < 50.0 THEN 0.05
            WHEN r."Market" = 'HOSE' THEN 0.10
            WHEN r."Market" IN ('HNX', 'UPCOM') THEN 0.10
            ELSE NULL
        END AS reference_quote_unit
    FROM reference_raw AS r
),
reference_normalized AS (
    SELECT
        q.*,
        CASE
            WHEN q.reference_price_raw IS NULL OR q.reference_quote_unit IS NULL THEN NULL
            ELSE
                ROUND(q.reference_price_raw / q.reference_quote_unit)
                * q.reference_quote_unit
        END AS reference_price
    FROM reference_quote AS q
),
band_input AS (
    SELECT
        n.*,
        CASE
            WHEN n."Market" = 'HOSE' THEN 0.07
            WHEN n."Market" = 'HNX' THEN 0.10
            WHEN n."Market" = 'UPCOM' THEN 0.15
            ELSE NULL
        END AS price_band_rate,
        CASE
            WHEN n.reference_price IS NULL THEN NULL
            ELSE CAST(ROUND(n.reference_price * 1000.0) AS BIGINT)
        END AS reference_vnd
    FROM reference_normalized AS n
),
band_targets AS (
    SELECT
        b.*,
        CAST(b.reference_vnd AS DOUBLE) * (1.0 + b.price_band_rate) AS ceiling_target_vnd,
        CAST(b.reference_vnd AS DOUBLE) * (1.0 - b.price_band_rate) AS floor_target_vnd,
        CASE
            WHEN b."Market" = 'HOSE' AND b.reference_vnd < 10000 THEN 10
            WHEN b."Market" = 'HOSE' AND b.reference_vnd < 50000 THEN 50
            WHEN b."Market" = 'HOSE' THEN 100
            WHEN b."Market" IN ('HNX', 'UPCOM') THEN 100
            ELSE NULL
        END AS reference_quote_unit_vnd
    FROM band_input AS b
),
band_quote_units AS (
    SELECT
        t.*,
        CASE
            WHEN t."Market" = 'HOSE' AND t.ceiling_target_vnd < 10000.0 THEN 10
            WHEN t."Market" = 'HOSE' AND t.ceiling_target_vnd < 50000.0 THEN 50
            WHEN t."Market" = 'HOSE' THEN 100
            WHEN t."Market" IN ('HNX', 'UPCOM') THEN 100
            ELSE NULL
        END AS ceiling_quote_unit_vnd,
        CASE
            WHEN t."Market" = 'HOSE' AND t.floor_target_vnd < 10000.0 THEN 10
            WHEN t."Market" = 'HOSE' AND t.floor_target_vnd < 50000.0 THEN 50
            WHEN t."Market" = 'HOSE' THEN 100
            WHEN t."Market" IN ('HNX', 'UPCOM') THEN 100
            ELSE NULL
        END AS floor_quote_unit_vnd
    FROM band_targets AS t
),
rounded_band AS (
    SELECT
        q.*,
        CASE
            WHEN q.ceiling_target_vnd IS NULL OR q.ceiling_quote_unit_vnd IS NULL THEN NULL
            ELSE CAST(
                FLOOR(q.ceiling_target_vnd / q.ceiling_quote_unit_vnd)
                * q.ceiling_quote_unit_vnd
                AS BIGINT
            )
        END AS ceiling_rounded_vnd,
        CASE
            WHEN q.floor_target_vnd IS NULL OR q.floor_quote_unit_vnd IS NULL THEN NULL
            ELSE CAST(
                CEIL(q.floor_target_vnd / q.floor_quote_unit_vnd)
                * q.floor_quote_unit_vnd
                AS BIGINT
            )
        END AS floor_rounded_vnd
    FROM band_quote_units AS q
),
price_limits_vnd AS (
    SELECT
        r.*,
        CASE
            WHEN r.reference_vnd IS NULL THEN NULL
            WHEN r.reference_vnd = r.reference_quote_unit_vnd
                THEN r.reference_vnd + r.reference_quote_unit_vnd
            WHEN r.ceiling_rounded_vnd = r.reference_vnd
                THEN r.reference_vnd + r.reference_quote_unit_vnd
            ELSE r.ceiling_rounded_vnd
        END AS ceiling_price_vnd,
        CASE
            WHEN r.reference_vnd IS NULL THEN NULL
            WHEN r.reference_vnd = r.reference_quote_unit_vnd
                THEN r.reference_vnd
            WHEN r.floor_rounded_vnd = r.reference_vnd
                THEN CASE
                    WHEN r.reference_vnd - r.reference_quote_unit_vnd <= 0
                        THEN r.reference_vnd
                    ELSE r.reference_vnd - r.reference_quote_unit_vnd
                END
            ELSE r.floor_rounded_vnd
        END AS floor_price_vnd
    FROM rounded_band AS r
),
flagged AS (
    SELECT
        p.*,
        CASE
            WHEN p."Market" IS NULL OR p.reference_price IS NULL THEN 'MISSING_INPUT'
            ELSE 'STANDARD_RULE_DERIVED'
        END AS price_band_rule_quality,
        CASE
            WHEN p.ceiling_price_vnd IS NULL OR p."Close" IS NULL THEN NULL
            ELSE ABS(CAST(p."Close" AS DOUBLE) * 1000.0 - p.ceiling_price_vnd) <= 0.5
        END AS limit_up,
        CASE
            WHEN p.floor_price_vnd IS NULL OR p."Close" IS NULL THEN NULL
            ELSE ABS(CAST(p."Close" AS DOUBLE) * 1000.0 - p.floor_price_vnd) <= 0.5
        END AS limit_down
    FROM price_limits_vnd AS p
),
streak_groups AS (
    SELECT
        f.*,
        SUM(CASE WHEN f.limit_up IS DISTINCT FROM TRUE THEN 1 ELSE 0 END) OVER (
            PARTITION BY f."Ticker"
            ORDER BY f."Date"
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS up_group,
        SUM(CASE WHEN f.limit_down IS DISTINCT FROM TRUE THEN 1 ELSE 0 END) OVER (
            PARTITION BY f."Ticker"
            ORDER BY f."Date"
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS down_group
    FROM flagged AS f
),
streaked AS (
    SELECT
        g.*,
        CASE
            WHEN g.limit_up IS NULL THEN NULL
            WHEN g.limit_up = FALSE THEN CAST(0 AS BIGINT)
            ELSE CAST(
                SUM(CASE WHEN g.limit_up = TRUE THEN 1 ELSE 0 END) OVER (
                    PARTITION BY g."Ticker", g.up_group
                    ORDER BY g."Date"
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                )
                AS BIGINT
            )
        END AS limit_up_streak,
        CASE
            WHEN g.limit_down IS NULL THEN NULL
            WHEN g.limit_down = FALSE THEN CAST(0 AS BIGINT)
            ELSE CAST(
                SUM(CASE WHEN g.limit_down = TRUE THEN 1 ELSE 0 END) OVER (
                    PARTITION BY g."Ticker", g.down_group
                    ORDER BY g."Date"
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                )
                AS BIGINT
            )
        END AS limit_down_streak
    FROM streak_groups AS g
)
SELECT
    s."Ticker",
    s."Date",
    s."Open",
    s."High",
    s."Low",
    s."Close",
    s."Volume",
    s."OpenInt",
    s."Market",
    CASE
        WHEN s."Market" IS NULL OR s."Market" = '' THEN 'MISSING'
        ELSE 'RAW_STOCK_FA_CURRENT_SNAPSHOT'
    END AS "Market_Source",
    CASE
        WHEN s."Market" IS NULL OR s."Market" = '' THEN NULL
        ELSE FALSE
    END AS "Market_IsPointInTime",
    CAST(s.reference_price AS DOUBLE) AS "ReferencePrice",
    s.reference_price_source AS "ReferencePrice_Source",
    s.reference_price_is_proxy AS "ReferencePrice_IsProxy",
    CAST(s.price_band_rate AS DOUBLE) AS "PriceBandRate",
    s.price_band_rule_quality AS "PriceBandRuleQuality",
    CAST(s.ceiling_price_vnd AS DOUBLE) / 1000.0 AS "CeilingPrice",
    CAST(s.floor_price_vnd AS DOUBLE) / 1000.0 AS "FloorPrice",
    s.limit_up AS "LimitUp",
    s.limit_up_streak AS "LimitUpStreak",
    s.limit_down AS "LimitDown",
    s.limit_down_streak AS "LimitDownStreak"
FROM streaked AS s;
