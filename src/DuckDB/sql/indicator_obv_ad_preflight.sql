-- OBV + AD Line read-only validation after activation and targeted initload.
-- No DDL/DML.

-- 1) Master definitions must be active with exact runtime inputs.
SELECT
    IndicatorCode,
    FunctionName,
    RequiredInputs,
    IsActive
FROM "CherryMon"."main"."dim_indicator"
WHERE IndicatorCode IN ('OBV', 'AD')
ORDER BY IndicatorCode;

-- Expected:
-- AD  | ad  | ["High","Low","Close","Volume"] | true
-- OBV | obv | ["Close","Volume"]              | true

-- 2) Single VALUE component contract.
SELECT
    IndicatorCode,
    ComponentCode,
    ValueSemantic,
    Unit,
    IsPrimary,
    IsActive
FROM "CherryMon"."main"."dim_indicator_component"
WHERE IndicatorCode IN ('OBV', 'AD')
ORDER BY IndicatorCode, ComponentCode;

-- Expected: one active VALUE row per indicator, CUMULATIVE_FLOW / VOLUME.

-- 3) Complete enabled D/W/M families.
SELECT
    IndicatorCode,
    ConfigCode,
    Timeframe,
    Parameters,
    WarmupBars,
    IsEnabled
FROM "CherryMon"."main"."dim_indicator_config"
WHERE IndicatorCode IN ('OBV', 'AD')
ORDER BY IndicatorCode, Timeframe;

-- Expected exactly: AD_D/W/M and OBV_D/W/M, all enabled.

-- 4) Historical output coverage.
SELECT
    cfg.IndicatorCode,
    cfg.ConfigCode,
    cfg.Timeframe,
    val.ComponentCode,
    COUNT(val.Ticker) AS Records,
    COUNT(DISTINCT val.Ticker) AS Tickers,
    MIN(val.Date) AS MinDate,
    MAX(val.Date) AS MaxDate,
    SUM(CASE WHEN val.Value IS NULL THEN 1 ELSE 0 END) AS NullValues
FROM "CherryMon"."main"."dim_indicator_config" AS cfg
LEFT JOIN "CherryMon"."main"."cal_indicator_values" AS val
    ON val.ConfigId = cfg.ConfigId
WHERE cfg.IndicatorCode IN ('OBV', 'AD')
  AND cfg.IsEnabled = TRUE
GROUP BY cfg.IndicatorCode, cfg.ConfigCode, cfg.Timeframe, val.ComponentCode
ORDER BY cfg.IndicatorCode, cfg.ConfigCode, val.ComponentCode;

-- PASS: each enabled config has VALUE output and Records > 0.

-- 5) Duplicate logical keys in the affected scope.
SELECT
    val.Ticker,
    val.Date,
    val.ConfigId,
    val.ComponentCode,
    COUNT(*) AS cnt
FROM "CherryMon"."main"."cal_indicator_values" AS val
INNER JOIN "CherryMon"."main"."dim_indicator_config" AS cfg
    ON cfg.ConfigId = val.ConfigId
WHERE cfg.IndicatorCode IN ('OBV', 'AD')
GROUP BY val.Ticker, val.Date, val.ConfigId, val.ComponentCode
HAVING COUNT(*) > 1;

-- PASS: 0 rows.

-- 6) Unexpected components.
SELECT DISTINCT
    cfg.IndicatorCode,
    val.ComponentCode
FROM "CherryMon"."main"."cal_indicator_values" AS val
INNER JOIN "CherryMon"."main"."dim_indicator_config" AS cfg
    ON cfg.ConfigId = val.ConfigId
LEFT JOIN "CherryMon"."main"."dim_indicator_component" AS comp
    ON comp.IndicatorCode = cfg.IndicatorCode
   AND comp.ComponentCode = val.ComponentCode
WHERE cfg.IndicatorCode IN ('OBV', 'AD')
  AND comp.ComponentCode IS NULL;

-- PASS: 0 rows.

-- 7) Public-view sample for SmartMoney consumption.
SELECT
    Ticker,
    Date,
    ConfigCode,
    IndicatorCode,
    ComponentCode,
    Value
FROM "CherryMon"."main"."vw_Ticker_indicators"
WHERE Ticker = 'MWG'
  AND ConfigCode IN ('OBV_D', 'AD_D')
ORDER BY Date DESC, ConfigCode
LIMIT 40;

-- PASS: numeric VALUE rows exist for both daily configs.
