-- R/S V2.2 Volume Profile preflight.
-- READ ONLY. No DDL/DML. Run manually against CherryMon before production smoke.

-- 1. Global raw_stock_eod Volume coverage.
SELECT
    COUNT(*) AS Records,
    COUNT(DISTINCT "Ticker") AS Tickers,
    MIN("Date") AS MinDate,
    MAX("Date") AS MaxDate,
    SUM(CASE WHEN "Volume" IS NULL THEN 1 ELSE 0 END) AS NullVolume,
    SUM(CASE WHEN "Volume" <= 0 THEN 1 ELSE 0 END) AS NonPositiveVolume,
    SUM(CASE WHEN "High" IS NULL OR "Low" IS NULL THEN 1 ELSE 0 END) AS NullHighLow
FROM "CherryMon"."main"."raw_stock_eod";

-- 2. MWG Volume Profile benchmark window.
SELECT
    "Ticker",
    COUNT(*) AS Records,
    MIN("Date") AS MinDate,
    MAX("Date") AS MaxDate,
    SUM(CASE WHEN "Volume" IS NULL THEN 1 ELSE 0 END) AS NullVolume,
    SUM(CASE WHEN "Volume" <= 0 THEN 1 ELSE 0 END) AS NonPositiveVolume,
    MIN("Low") AS MinLow,
    MAX("High") AS MaxHigh,
    SUM("Volume") AS TotalVolume
FROM "CherryMon"."main"."raw_stock_eod"
WHERE "Ticker" = 'MWG'
  AND "Date" <= DATE '2026-08-28'
  AND "Date" >= DATE '2026-01-01'
GROUP BY "Ticker";

-- 3. Latest 120 eligible MWG trading bars, matching default VolumeProfileConfig.
WITH latest_120 AS (
    SELECT "Date", "High", "Low", "Close", "Volume"
    FROM "CherryMon"."main"."raw_stock_eod"
    WHERE "Ticker" = 'MWG'
      AND "Date" <= DATE '2026-08-28'
      AND "High" IS NOT NULL
      AND "Low" IS NOT NULL
      AND "Volume" IS NOT NULL
      AND "Volume" > 0
    ORDER BY "Date" DESC
    LIMIT 120
)
SELECT
    COUNT(*) AS EligibleBars,
    MIN("Date") AS WindowStart,
    MAX("Date") AS WindowEnd,
    MIN("Low") AS PriceLow,
    MAX("High") AS PriceHigh,
    SUM("Volume") AS TotalVolume
FROM latest_120;

-- 4. Data sanity: High must be >= Low on benchmark window.
SELECT COUNT(*) AS InvalidHighLow
FROM "CherryMon"."main"."raw_stock_eod"
WHERE "Ticker" = 'MWG'
  AND "Date" <= DATE '2026-08-28'
  AND "Date" >= DATE '2026-01-01'
  AND (
      "High" IS NULL
      OR "Low" IS NULL
      OR "High" < "Low"
      OR "Low" <= 0
  );

-- PASS criteria:
-- - MWG has at least 30 eligible positive-volume bars; target default uses latest 120.
-- - latest 120 window ends at latest eligible date <= 2026-08-28.
-- - no invalid High/Low rows in the benchmark window.
-- - TotalVolume > 0 and PriceHigh > PriceLow.
