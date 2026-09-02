-- R/S V2.1 DuckDB preflight validation.
-- Read-only. No DDL/DML. Run manually before production smoke/deployment.

-- 1. ATR14_D configuration and semantic contract.
SELECT
    cfg."ConfigId",
    cfg."ConfigCode",
    cfg."IndicatorCode",
    cfg."Timeframe",
    cfg."ComponentCode",
    cfg."ValueSemantic",
    cfg."Unit",
    cfg."ConfigIsEnabled",
    cfg."IndicatorIsActive",
    cfg."ComponentIsActive"
FROM "CherryMon"."main"."vw_Indicator_config" cfg
WHERE cfg."ConfigCode" = 'ATR14_D';

-- Expected:
-- IndicatorCode=ATR, Timeframe=D, ComponentCode=VALUE,
-- ValueSemantic=VOLATILITY_DISTANCE, Unit=PRICE,
-- all active/enabled flags TRUE.

-- 2. ATR14_D calculated-value coverage.
SELECT
    v."ConfigId",
    COUNT(*) AS Records,
    COUNT(DISTINCT v."Ticker") AS Tickers,
    MIN(v."Date") AS MinDate,
    MAX(v."Date") AS MaxDate,
    SUM(CASE WHEN v."Value" IS NULL THEN 1 ELSE 0 END) AS NullValues,
    MIN(v."Value") AS MinATR,
    MAX(v."Value") AS MaxATR
FROM "CherryMon"."main"."vw_Ticker_indicators" v
INNER JOIN "CherryMon"."main"."vw_Indicator_config" cfg
    ON cfg."ConfigId" = v."ConfigId"
   AND cfg."ComponentCode" = v."ComponentCode"
WHERE cfg."ConfigCode" = 'ATR14_D'
GROUP BY v."ConfigId";

-- 3. MWG point-in-time ATR smoke for the V2.1 benchmark date.
SELECT
    v."Ticker",
    v."Date",
    cfg."ConfigCode",
    v."Value" AS ATR14_D
FROM "CherryMon"."main"."vw_Ticker_indicators" v
INNER JOIN "CherryMon"."main"."vw_Indicator_config" cfg
    ON cfg."ConfigId" = v."ConfigId"
   AND cfg."ComponentCode" = v."ComponentCode"
WHERE v."Ticker" = 'MWG'
  AND v."Date" <= DATE '2026-08-28'
  AND cfg."ConfigCode" = 'ATR14_D'
ORDER BY v."Date" DESC
LIMIT 1;

-- 4. Structural OHLCV source coverage for MWG.
SELECT
    "Ticker",
    COUNT(*) AS Records,
    MIN("Date") AS MinDate,
    MAX("Date") AS MaxDate,
    SUM(CASE WHEN "High" IS NULL THEN 1 ELSE 0 END) AS NullHigh,
    SUM(CASE WHEN "Low" IS NULL THEN 1 ELSE 0 END) AS NullLow,
    SUM(CASE WHEN "Close" IS NULL THEN 1 ELSE 0 END) AS NullClose
FROM "CherryMon"."main"."raw_stock_eod"
WHERE "Ticker" = 'MWG'
  AND "Date" BETWEEN DATE '2025-08-20' AND DATE '2026-08-28'
GROUP BY "Ticker";

-- 5. Confirm no future raw bar is needed for the benchmark as_of_date.
SELECT
    MAX("Date") AS LatestEligibleDate
FROM "CherryMon"."main"."raw_stock_eod"
WHERE "Ticker" = 'MWG'
  AND "Date" <= DATE '2026-08-28';

-- PASS criteria:
-- - ATR14_D config exists and is fully active.
-- - ATR14_D has non-null positive values and reaches the benchmark date or latest
--   eligible prior trading date.
-- - raw_stock_eod has enough history for 52W / Swing and no material High/Low gaps.
