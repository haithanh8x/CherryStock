-- SmartMoneyScore V1 read-only preflight.
-- Run after scripts/initload/init_reload_smart_money_score.py.
-- No DDL/DML.

-- 1) Required objects.
SELECT table_name, table_type
FROM information_schema.tables
WHERE lower(table_schema) = 'main'
  AND lower(table_name) IN (
      'dim_smart_money_model',
      'dim_smart_money_factor',
      'dim_smart_money_config',
      'dim_smart_money_state_weight',
      'cal_smart_money_factor_values',
      'cal_smart_money_ticker_score'
  )
ORDER BY table_name;

SELECT table_name
FROM information_schema.views
WHERE lower(table_schema) = 'main'
  AND lower(table_name) = 'vw_ticker_smartmoney';

-- PASS: six base tables + one public view.

-- 2) Enabled model and factor catalog.
SELECT
    ModelId,
    ModelCode,
    ModelVersion,
    IsEnabled,
    EffectiveFrom,
    EffectiveTo
FROM "CherryMon"."main"."dim_smart_money_model"
ORDER BY ModelId;

SELECT
    FactorId,
    FactorCode,
    Category,
    ContributionType,
    IsEnabled
FROM "CherryMon"."main"."dim_smart_money_factor"
ORDER BY FactorId;

-- PASS: SMART_MONEY_V1 enabled; exactly ten V1 factors enabled.

-- 3) Weight profile sums.
SELECT
    w.MarketState,
    SUM(w.Weight) AS TotalWeight,
    COUNT(*) AS FactorCount
FROM "CherryMon"."main"."dim_smart_money_state_weight" AS w
WHERE w.ModelId = 1
GROUP BY w.MarketState
ORDER BY w.MarketState;

-- PASS: each supported state totals approximately 1.0.

-- 4) Score contract.
SELECT
    COUNT(*) AS Rows,
    COUNT(DISTINCT Ticker) AS Tickers,
    MIN(Date) AS MinDate,
    MAX(Date) AS MaxDate,
    SUM(CASE WHEN SmartMoneyScore < 0 OR SmartMoneyScore > 100 THEN 1 ELSE 0 END) AS InvalidScore,
    SUM(CASE WHEN ConfidenceScore < 0 OR ConfidenceScore > 100 THEN 1 ELSE 0 END) AS InvalidConfidence,
    SUM(CASE WHEN FactorCoverage < 0 OR FactorCoverage > 1 THEN 1 ELSE 0 END) AS InvalidCoverage
FROM "CherryMon"."main"."cal_smart_money_ticker_score";

-- PASS: Rows > 0; all Invalid*=0.

-- 5) Duplicate logical keys.
SELECT COUNT(*) AS DuplicateScoreKeys
FROM (
    SELECT ModelId, Ticker, Date, COUNT(*) AS cnt
    FROM "CherryMon"."main"."cal_smart_money_ticker_score"
    GROUP BY ModelId, Ticker, Date
    HAVING COUNT(*) > 1
) AS d;

SELECT COUNT(*) AS DuplicateFactorKeys
FROM (
    SELECT ModelId, Ticker, Date, FactorId, COUNT(*) AS cnt
    FROM "CherryMon"."main"."cal_smart_money_factor_values"
    GROUP BY ModelId, Ticker, Date, FactorId
    HAVING COUNT(*) > 1
) AS d;

-- PASS: both 0.

-- 6) Factor coverage and NULL semantics.
SELECT
    f.FactorCode,
    v.DataQuality,
    COUNT(*) AS Rows,
    SUM(CASE WHEN v.NormalizedValue IS NULL THEN 1 ELSE 0 END) AS NullNormalized
FROM "CherryMon"."main"."cal_smart_money_factor_values" AS v
INNER JOIN "CherryMon"."main"."dim_smart_money_factor" AS f
    ON f.FactorId = v.FactorId
WHERE v.ModelId = 1
GROUP BY f.FactorCode, v.DataQuality
ORDER BY f.FactorCode, v.DataQuality;

-- Expected before As-Traded cutover:
-- LIMIT_UP / UNAVAILABLE rows with NormalizedValue NULL.
-- Missing LimitUp MUST NOT be stored as 0.

-- 7) State distribution.
SELECT
    MarketState,
    COUNT(*) AS Rows,
    AVG(SmartMoneyScore) AS AvgSmartMoneyScore,
    AVG(ConfidenceScore) AS AvgConfidenceScore
FROM "CherryMon"."main"."cal_smart_money_ticker_score"
WHERE ModelId = 1
GROUP BY MarketState
ORDER BY Rows DESC;

-- Review: all states must belong to the approved V1 state set.

-- 8) Public view contract.
SELECT
    Ticker,
    Date,
    ModelCode,
    ModelVersion,
    SmartMoneyScore,
    ConfidenceScore,
    MarketState,
    FactorCoverage,
    DataQualityStatus,
    FreshFlowScore,
    RelativeLiquidityScore,
    LiquidityAccelerationScore,
    RelativeStrengthScore,
    AccumulationScore,
    AccumulationMemoryScore,
    SupplyLockScore,
    LimitUpScore,
    TrendScore,
    DistributionScore
FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
WHERE Ticker = 'MWG'
ORDER BY Date DESC
LIMIT 20;

-- PASS: recent MWG rows exist; scores are numeric; LimitUpScore may be NULL.

-- 9) Factor/score relationship.
SELECT COUNT(*) AS ScoreRowsWithoutFactors
FROM "CherryMon"."main"."cal_smart_money_ticker_score" AS s
WHERE NOT EXISTS (
    SELECT 1
    FROM "CherryMon"."main"."cal_smart_money_factor_values" AS v
    WHERE v.ModelId = s.ModelId
      AND v.Ticker = s.Ticker
      AND v.Date = s.Date
);

-- PASS: 0.

-- 10) Data quality summary.
SELECT
    DataQualityStatus,
    COUNT(*) AS Rows,
    AVG(FactorCoverage) AS AvgCoverage,
    AVG(ConfidenceScore) AS AvgConfidence
FROM "CherryMon"."main"."cal_smart_money_ticker_score"
GROUP BY DataQualityStatus
ORDER BY DataQualityStatus;
