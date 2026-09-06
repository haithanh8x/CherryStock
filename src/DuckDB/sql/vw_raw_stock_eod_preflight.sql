-- vw_raw_stock_eod read-only preflight.
-- Run after src/DuckDB/sql/vw_raw_stock_eod.sql.
-- No DDL/DML.

-- 1) View exists.
SELECT table_name
FROM information_schema.views
WHERE lower(table_catalog) = 'cherrymon'
  AND lower(table_schema) = 'main'
  AND lower(table_name) = 'vw_raw_stock_eod';

-- PASS: 1 row.

-- 2) Public column contract.
SELECT ordinal_position, column_name, data_type
FROM information_schema.columns
WHERE lower(table_catalog) = 'cherrymon'
  AND lower(table_schema) = 'main'
  AND lower(table_name) = 'vw_raw_stock_eod'
ORDER BY ordinal_position;

-- Expected 22 columns:
-- Ticker, Date, Open, High, Low, Close, Volume, OpenInt,
-- Market, Market_Source, Market_IsPointInTime,
-- ReferencePrice, ReferencePrice_Source, ReferencePrice_IsProxy,
-- PriceBandRate, PriceBandRuleQuality,
-- CeilingPrice, FloorPrice,
-- LimitUp, LimitUpStreak, LimitDown, LimitDownStreak.

-- 3) Row preservation: view must preserve raw_stock_eod grain.
SELECT
    (SELECT COUNT(*) FROM "CherryMon"."main"."raw_stock_eod") AS raw_rows,
    (SELECT COUNT(*) FROM "CherryMon"."main"."vw_raw_stock_eod") AS view_rows;

-- PASS: raw_rows = view_rows.

-- 4) One row per Ticker + Date.
SELECT COUNT(*) AS duplicate_groups
FROM (
    SELECT "Ticker", "Date", COUNT(*) AS rows_per_key
    FROM "CherryMon"."main"."vw_raw_stock_eod"
    GROUP BY "Ticker", "Date"
    HAVING COUNT(*) > 1
) AS d;

-- PASS: 0.

-- 5) Market mapping / quality distribution.
SELECT
    "Market",
    "Market_Source",
    "Market_IsPointInTime",
    COUNT(*) AS rows,
    MIN("Date") AS min_date,
    MAX("Date") AS max_date
FROM "CherryMon"."main"."vw_raw_stock_eod"
GROUP BY "Market", "Market_Source", "Market_IsPointInTime"
ORDER BY rows DESC;

-- Review: HOSE/HNX/UPCOM should dominate. Missing/other values require investigation.

-- 6) Standard band rates by market.
SELECT
    "Market",
    "PriceBandRate",
    COUNT(*) AS rows
FROM "CherryMon"."main"."vw_raw_stock_eod"
WHERE "Market" IN ('HOSE', 'HNX', 'UPCOM')
GROUP BY "Market", "PriceBandRate"
ORDER BY "Market", "PriceBandRate";

-- PASS ordinary rule:
-- HOSE  = 0.07
-- HNX   = 0.10
-- UPCOM = 0.15

-- 7) Ceiling/Floor ordering.
SELECT COUNT(*) AS invalid_price_band_order
FROM "CherryMon"."main"."vw_raw_stock_eod"
WHERE "ReferencePrice" IS NOT NULL
  AND (
       "CeilingPrice" IS NULL
       OR "FloorPrice" IS NULL
       OR "CeilingPrice" < "ReferencePrice"
       OR "FloorPrice" > "ReferencePrice"
  );

-- PASS: 0 for supported standard-rule rows.

-- 8) HNX/UPCOM prices must align to 100 VND = 0.1 thousand VND.
SELECT COUNT(*) AS invalid_hnx_upcom_quote_units
FROM "CherryMon"."main"."vw_raw_stock_eod"
WHERE "Market" IN ('HNX', 'UPCOM')
  AND "ReferencePrice" IS NOT NULL
  AND (
       ABS("ReferencePrice" * 10.0 - ROUND("ReferencePrice" * 10.0)) > 1e-8
       OR ABS("CeilingPrice" * 10.0 - ROUND("CeilingPrice" * 10.0)) > 1e-8
       OR ABS("FloorPrice" * 10.0 - ROUND("FloorPrice" * 10.0)) > 1e-8
  );

-- PASS: 0.

-- 9) LimitUp/LimitDown must agree with daily Close and derived prices.
SELECT COUNT(*) AS invalid_limit_flags
FROM "CherryMon"."main"."vw_raw_stock_eod"
WHERE
    ("LimitUp" = TRUE AND ABS("Close" * 1000.0 - "CeilingPrice" * 1000.0) > 0.5)
 OR ("LimitDown" = TRUE AND ABS("Close" * 1000.0 - "FloorPrice" * 1000.0) > 0.5)
 OR ("LimitUp" = TRUE AND "LimitDown" = TRUE);

-- PASS: 0.

-- 10) Streak semantic consistency.
SELECT COUNT(*) AS invalid_streak_rows
FROM "CherryMon"."main"."vw_raw_stock_eod"
WHERE
    ("LimitUp" = TRUE AND COALESCE("LimitUpStreak", 0) < 1)
 OR ("LimitUp" = FALSE AND COALESCE("LimitUpStreak", -1) <> 0)
 OR ("LimitUp" IS NULL AND "LimitUpStreak" IS NOT NULL)
 OR ("LimitDown" = TRUE AND COALESCE("LimitDownStreak", 0) < 1)
 OR ("LimitDown" = FALSE AND COALESCE("LimitDownStreak", -1) <> 0)
 OR ("LimitDown" IS NULL AND "LimitDownStreak" IS NOT NULL);

-- PASS: 0.

-- 11) UPCOM reference lineage coverage.
SELECT
    "ReferencePrice_Source",
    "ReferencePrice_IsProxy",
    COUNT(*) AS rows,
    MIN("Date") AS min_date,
    MAX("Date") AS max_date
FROM "CherryMon"."main"."vw_raw_stock_eod"
WHERE "Market" = 'UPCOM'
GROUP BY "ReferencePrice_Source", "ReferencePrice_IsProxy"
ORDER BY rows DESC;

-- Expected recent Intraday-covered rows:
-- UPCOM_INTRADAY_LOT100_VWAP_PROXY / TRUE
-- Historical rows without a previous eligible Intraday VWAP remain missing rather
-- than fabricating an official UPCOM reference from Close or Typical Price.

-- 12) Latest derived limit events for manual spot-check.
SELECT
    "Ticker",
    "Date",
    "Market",
    "Close",
    "ReferencePrice",
    "CeilingPrice",
    "FloorPrice",
    "LimitUp",
    "LimitUpStreak",
    "LimitDown",
    "LimitDownStreak",
    "ReferencePrice_Source",
    "PriceBandRuleQuality"
FROM "CherryMon"."main"."vw_raw_stock_eod"
WHERE "LimitUp" = TRUE OR "LimitDown" = TRUE
ORDER BY "Date" DESC, "Ticker"
LIMIT 100;
