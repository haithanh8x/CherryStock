-- R/S V2.3 read-only preflight.
-- Run AFTER rs_v2_3_evaluation_governance.sql.
-- No DDL/DML in this file.

-- 1. Required evaluation/governance objects.
SELECT
    table_name
FROM information_schema.tables
WHERE table_catalog = 'CherryMon'
  AND table_schema = 'main'
  AND table_name IN (
      'dim_rs_model_version',
      'cal_rs_evaluation_run',
      'cal_rs_evaluation_event',
      'cal_rs_evaluation_metric',
      'sys_rs_model_promotion_audit'
  )
ORDER BY table_name;

-- Expected: 5 rows.

-- 2. Baseline model registration.
SELECT
    "ModelVersion",
    "ParentVersion",
    "Status",
    "Signature",
    "CreatedAt"
FROM "CherryMon"."main"."dim_rs_model_version"
WHERE "ModelVersion" = 'RS_V2_3_BASELINE';

-- Expected: one row, Status=BASELINE.

-- 3. Historical raw OHLCV coverage available for multi-ticker evaluation.
SELECT
    COUNT(DISTINCT "Ticker") AS Tickers,
    COUNT(*) AS Records,
    MIN("Date") AS MinDate,
    MAX("Date") AS MaxDate,
    SUM(CASE WHEN "High" IS NULL OR "Low" IS NULL OR "Close" IS NULL THEN 1 ELSE 0 END) AS NullOHLC,
    SUM(CASE WHEN "Volume" IS NULL THEN 1 ELSE 0 END) AS NullVolume
FROM "CherryMon"."main"."raw_stock_eod"
WHERE "Date" >= DATE '2025-01-01'
  AND "Date" <= DATE '2026-08-28';

-- 4. Indicator PIT history used by current R/S providers.
SELECT
    cfg."IndicatorCode",
    MIN(val."Date") AS MinDate,
    MAX(val."Date") AS MaxDate,
    COUNT(*) AS Records,
    COUNT(DISTINCT val."Ticker") AS Tickers
FROM "CherryMon"."main"."vw_Ticker_indicators" val
INNER JOIN "CherryMon"."main"."vw_Indicator_config" cfg
    ON cfg."ConfigId" = val."ConfigId"
   AND cfg."ComponentCode" = val."ComponentCode"
WHERE cfg."IndicatorCode" IN ('MA', 'BB', 'RSI', 'ATR')
  AND cfg."ConfigIsEnabled" = TRUE
  AND cfg."IndicatorIsActive" = TRUE
GROUP BY cfg."IndicatorCode"
ORDER BY cfg."IndicatorCode";

-- Expected: MA/BB/RSI/ATR all present with historical coverage.

-- 5. Benchmark cross-ticker raw coverage.
SELECT
    "Ticker",
    COUNT(*) AS Records,
    MIN("Date") AS MinDate,
    MAX("Date") AS MaxDate,
    SUM(CASE WHEN "High" IS NULL OR "Low" IS NULL OR "Close" IS NULL THEN 1 ELSE 0 END) AS NullOHLC,
    SUM(CASE WHEN "Volume" IS NULL OR "Volume" <= 0 THEN 1 ELSE 0 END) AS InvalidVolume
FROM "CherryMon"."main"."raw_stock_eod"
WHERE "Ticker" IN ('MWG', 'FPT', 'HPG')
  AND "Date" BETWEEN DATE '2025-01-01' AND DATE '2026-08-28'
GROUP BY "Ticker"
ORDER BY "Ticker";

-- 6. Forward outcome coverage for a safe evaluation endpoint.
-- Evaluation end=2026-07-31 should have >=20 later bars by 2026-08-28.
SELECT
    "Ticker",
    COUNT(*) AS ForwardBars,
    MIN("Date") AS FirstForwardDate,
    MAX("Date") AS LastForwardDate
FROM "CherryMon"."main"."raw_stock_eod"
WHERE "Ticker" IN ('MWG', 'FPT', 'HPG')
  AND "Date" > DATE '2026-07-31'
  AND "Date" <= DATE '2026-08-28'
GROUP BY "Ticker"
ORDER BY "Ticker";

-- PASS criteria:
-- - all 5 V2.3 objects exist;
-- - RS_V2_3_BASELINE exists with Status=BASELINE;
-- - raw_stock_eod has broad historical coverage;
-- - MA/BB/RSI/ATR historical PIT values exist;
-- - MWG/FPT/HPG have usable history;
-- - each benchmark ticker has at least 20 forward bars after 2026-07-31.
