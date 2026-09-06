-- SmartMoneyScore V1 storage, metadata seed and public view.
-- Additive/idempotent. Does not mutate raw market or Indicator Engine tables.

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."dim_smart_money_model" (
    ModelId BIGINT NOT NULL,
    ModelCode VARCHAR NOT NULL,
    ModelVersion VARCHAR NOT NULL,
    Description VARCHAR,
    IsEnabled BOOLEAN NOT NULL DEFAULT TRUE,
    EffectiveFrom DATE NOT NULL DEFAULT DATE '2000-01-01',
    EffectiveTo DATE,
    CreatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ModelId),
    UNIQUE (ModelCode, ModelVersion)
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."dim_smart_money_factor" (
    FactorId BIGINT NOT NULL,
    FactorCode VARCHAR NOT NULL,
    FactorName VARCHAR NOT NULL,
    Category VARCHAR NOT NULL,
    NormalizationMethod VARCHAR NOT NULL,
    ContributionType VARCHAR NOT NULL,
    IsEnabled BOOLEAN NOT NULL DEFAULT TRUE,
    Description VARCHAR,
    PRIMARY KEY (FactorId),
    UNIQUE (FactorCode)
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."dim_smart_money_config" (
    ModelId BIGINT NOT NULL,
    ConfigKey VARCHAR NOT NULL,
    ConfigValue VARCHAR NOT NULL,
    ValueType VARCHAR NOT NULL,
    EffectiveFrom DATE NOT NULL DEFAULT DATE '2000-01-01',
    EffectiveTo DATE,
    UpdatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ModelId, ConfigKey, EffectiveFrom)
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."dim_smart_money_state_weight" (
    ModelId BIGINT NOT NULL,
    MarketState VARCHAR NOT NULL,
    FactorId BIGINT NOT NULL,
    Weight DOUBLE NOT NULL,
    EffectiveFrom DATE NOT NULL DEFAULT DATE '2000-01-01',
    EffectiveTo DATE,
    UpdatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ModelId, MarketState, FactorId, EffectiveFrom),
    CHECK (Weight >= 0.0)
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_smart_money_factor_values" (
    ModelId BIGINT NOT NULL,
    Ticker VARCHAR NOT NULL,
    Date DATE NOT NULL,
    FactorId BIGINT NOT NULL,
    RawValue DOUBLE,
    NormalizedValue DOUBLE,
    DataQuality VARCHAR NOT NULL,
    SourceCode VARCHAR,
    CalculatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ModelId, Ticker, Date, FactorId),
    CHECK (NormalizedValue IS NULL OR (NormalizedValue >= 0.0 AND NormalizedValue <= 100.0))
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_smart_money_ticker_score" (
    ModelId BIGINT NOT NULL,
    Ticker VARCHAR NOT NULL,
    Date DATE NOT NULL,
    SmartMoneyScore DOUBLE NOT NULL,
    ConfidenceScore DOUBLE NOT NULL,
    MarketState VARCHAR NOT NULL,
    FactorCoverage DOUBLE NOT NULL,
    DataQualityStatus VARCHAR NOT NULL,
    CalculatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ModelId, Ticker, Date),
    CHECK (SmartMoneyScore >= 0.0 AND SmartMoneyScore <= 100.0),
    CHECK (ConfidenceScore >= 0.0 AND ConfidenceScore <= 100.0),
    CHECK (FactorCoverage >= 0.0 AND FactorCoverage <= 1.0)
);

INSERT INTO "CherryMon"."main"."dim_smart_money_model" (
    ModelId, ModelCode, ModelVersion, Description, IsEnabled,
    EffectiveFrom, EffectiveTo, UpdatedAt
)
VALUES (
    1,
    'SMART_MONEY_V1',
    '1.0.0',
    'State-aware SmartMoneyScore V1. Limit-up evidence remains optional until the point-in-time as-traded market-limit source passes validation.',
    TRUE,
    DATE '2000-01-01',
    NULL,
    CURRENT_TIMESTAMP
)
ON CONFLICT (ModelId) DO UPDATE SET
    ModelCode = EXCLUDED.ModelCode,
    ModelVersion = EXCLUDED.ModelVersion,
    Description = EXCLUDED.Description,
    IsEnabled = EXCLUDED.IsEnabled,
    EffectiveFrom = EXCLUDED.EffectiveFrom,
    EffectiveTo = EXCLUDED.EffectiveTo,
    UpdatedAt = CURRENT_TIMESTAMP;

INSERT INTO "CherryMon"."main"."dim_smart_money_factor" (
    FactorId, FactorCode, FactorName, Category,
    NormalizationMethod, ContributionType, IsEnabled, Description
)
VALUES
    (1,  'FRESH_FLOW',             'Fresh Flow',              'FLOW',      'PERCENTILE', 'POSITIVE', TRUE, 'Close strength plus short relative-price impulse under current liquidity.'),
    (2,  'RELATIVE_LIQUIDITY',     'Relative Liquidity',      'LIQUIDITY', 'PERCENTILE', 'POSITIVE', TRUE, 'TradingValue divided by rolling 20-session average.'),
    (3,  'LIQUIDITY_ACCELERATION', 'Liquidity Acceleration',  'LIQUIDITY', 'PERCENTILE', 'POSITIVE', TRUE, 'Rolling 5-session TradingValue divided by rolling 20-session TradingValue.'),
    (4,  'RELATIVE_STRENGTH',      'Relative Strength',       'STRENGTH',  'PERCENTILE', 'POSITIVE', TRUE, 'Weighted RS5/20/60 versus VNINDEX.'),
    (5,  'ACCUMULATION',           'Accumulation',            'FLOW',      'PERCENTILE', 'POSITIVE', TRUE, 'CLV persistence, relative strength and optional OBV/AD slopes.'),
    (6,  'ACCUMULATION_MEMORY',    'Accumulation Memory',     'STATE',     'IDENTITY',   'POSITIVE', TRUE, 'EWMA memory of normalized accumulation evidence.'),
    (7,  'SUPPLY_LOCK',            'Supply Lock',             'STATE',     'IDENTITY',   'POSITIVE', TRUE, 'Conjunctive strong-price / compression / non-distribution evidence.'),
    (8,  'LIMIT_UP',               'Limit Up Evidence',       'STATE',     'IDENTITY',   'POSITIVE', TRUE, 'Trusted point-in-time limit-up evidence; NULL until authoritative/as-traded contract is available.'),
    (9,  'TREND',                  'Trend',                   'STRENGTH',  'PERCENTILE', 'POSITIVE', TRUE, 'Position versus MA20/MA50.'),
    (10, 'DISTRIBUTION',           'Distribution',            'RISK',      'IDENTITY',   'PENALTY',  TRUE, 'High participation with weak close/return/relative strength.')
ON CONFLICT (FactorId) DO UPDATE SET
    FactorCode = EXCLUDED.FactorCode,
    FactorName = EXCLUDED.FactorName,
    Category = EXCLUDED.Category,
    NormalizationMethod = EXCLUDED.NormalizationMethod,
    ContributionType = EXCLUDED.ContributionType,
    IsEnabled = EXCLUDED.IsEnabled,
    Description = EXCLUDED.Description;

INSERT INTO "CherryMon"."main"."dim_smart_money_config" (
    ModelId, ConfigKey, ConfigValue, ValueType, EffectiveFrom, EffectiveTo, UpdatedAt
)
VALUES
    (1, 'MEMORY_LAMBDA',                    '0.90', 'FLOAT', DATE '2000-01-01', NULL, CURRENT_TIMESTAMP),
    (1, 'MIN_FACTOR_COVERAGE',              '0.50', 'FLOAT', DATE '2000-01-01', NULL, CURRENT_TIMESTAMP),
    (1, 'PREFERRED_FACTOR_COVERAGE',        '0.80', 'FLOAT', DATE '2000-01-01', NULL, CURRENT_TIMESTAMP),
    (1, 'DISTRIBUTION_PENALTY_DEFAULT',     '0.35', 'FLOAT', DATE '2000-01-01', NULL, CURRENT_TIMESTAMP),
    (1, 'DISTRIBUTION_PENALTY_DISTRIBUTION','0.75', 'FLOAT', DATE '2000-01-01', NULL, CURRENT_TIMESTAMP),
    (1, 'STATE_DISTRIBUTION_THRESHOLD',     '70',   'FLOAT', DATE '2000-01-01', NULL, CURRENT_TIMESTAMP),
    (1, 'STATE_SUPPLY_LOCK_THRESHOLD',      '70',   'FLOAT', DATE '2000-01-01', NULL, CURRENT_TIMESTAMP),
    (1, 'STATE_BREAKOUT_THRESHOLD',         '70',   'FLOAT', DATE '2000-01-01', NULL, CURRENT_TIMESTAMP),
    (1, 'STATE_ACCUMULATION_THRESHOLD',     '65',   'FLOAT', DATE '2000-01-01', NULL, CURRENT_TIMESTAMP),
    (1, 'STATE_MARKUP_THRESHOLD',           '65',   'FLOAT', DATE '2000-01-01', NULL, CURRENT_TIMESTAMP),
    (1, 'STATE_DRYUP_THRESHOLD',            '75',   'FLOAT', DATE '2000-01-01', NULL, CURRENT_TIMESTAMP)
ON CONFLICT (ModelId, ConfigKey, EffectiveFrom) DO UPDATE SET
    ConfigValue = EXCLUDED.ConfigValue,
    ValueType = EXCLUDED.ValueType,
    EffectiveTo = EXCLUDED.EffectiveTo,
    UpdatedAt = CURRENT_TIMESTAMP;

-- Weight rows are deliberately explicit and versioned by EffectiveFrom.
-- NEUTRAL
INSERT INTO "CherryMon"."main"."dim_smart_money_state_weight"
(ModelId, MarketState, FactorId, Weight, EffectiveFrom, EffectiveTo, UpdatedAt)
VALUES
    (1,'NEUTRAL',1,0.30,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'NEUTRAL',2,0.15,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'NEUTRAL',3,0.15,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'NEUTRAL',4,0.15,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'NEUTRAL',5,0.15,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'NEUTRAL',9,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    -- ACCUMULATION
    (1,'ACCUMULATION',5,0.30,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'ACCUMULATION',6,0.20,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'ACCUMULATION',4,0.15,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'ACCUMULATION',2,0.075,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'ACCUMULATION',3,0.075,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'ACCUMULATION',1,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'ACCUMULATION',9,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    -- BREAKOUT
    (1,'BREAKOUT',1,0.25,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'BREAKOUT',2,0.20,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'BREAKOUT',3,0.20,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'BREAKOUT',4,0.15,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'BREAKOUT',6,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'BREAKOUT',9,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    -- DEMAND_EXPANSION
    (1,'DEMAND_EXPANSION',1,0.25,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'DEMAND_EXPANSION',2,0.20,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'DEMAND_EXPANSION',3,0.20,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'DEMAND_EXPANSION',4,0.15,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'DEMAND_EXPANSION',6,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'DEMAND_EXPANSION',9,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    -- SUPPLY_LOCK
    (1,'SUPPLY_LOCK',6,0.25,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'SUPPLY_LOCK',7,0.25,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'SUPPLY_LOCK',8,0.20,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'SUPPLY_LOCK',4,0.15,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'SUPPLY_LOCK',9,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'SUPPLY_LOCK',1,0.05,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    -- MARKUP
    (1,'MARKUP',4,0.25,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'MARKUP',9,0.25,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'MARKUP',1,0.20,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'MARKUP',2,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'MARKUP',3,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'MARKUP',6,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    -- DISTRIBUTION
    (1,'DISTRIBUTION',4,0.20,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'DISTRIBUTION',9,0.20,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'DISTRIBUTION',5,0.20,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'DISTRIBUTION',6,0.15,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'DISTRIBUTION',1,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'DISTRIBUTION',2,0.075,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'DISTRIBUTION',3,0.075,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    -- LIQUIDITY_DRYUP
    (1,'LIQUIDITY_DRYUP',6,0.25,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'LIQUIDITY_DRYUP',7,0.20,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'LIQUIDITY_DRYUP',4,0.20,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'LIQUIDITY_DRYUP',9,0.15,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'LIQUIDITY_DRYUP',1,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'LIQUIDITY_DRYUP',5,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    -- SELLING_CLIMAX
    (1,'SELLING_CLIMAX',5,0.20,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'SELLING_CLIMAX',6,0.20,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'SELLING_CLIMAX',4,0.15,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'SELLING_CLIMAX',2,0.15,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'SELLING_CLIMAX',3,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'SELLING_CLIMAX',9,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP),
    (1,'SELLING_CLIMAX',1,0.10,DATE '2000-01-01',NULL,CURRENT_TIMESTAMP)
ON CONFLICT (ModelId, MarketState, FactorId, EffectiveFrom) DO UPDATE SET
    Weight = EXCLUDED.Weight,
    EffectiveTo = EXCLUDED.EffectiveTo,
    UpdatedAt = CURRENT_TIMESTAMP;

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Ticker_SmartMoney" AS
WITH factor_wide AS (
    SELECT
        v.ModelId,
        v.Ticker,
        v.Date,
        MAX(CASE WHEN f.FactorCode = 'FRESH_FLOW' THEN v.NormalizedValue END) AS FreshFlowScore,
        MAX(CASE WHEN f.FactorCode = 'RELATIVE_LIQUIDITY' THEN v.NormalizedValue END) AS RelativeLiquidityScore,
        MAX(CASE WHEN f.FactorCode = 'LIQUIDITY_ACCELERATION' THEN v.NormalizedValue END) AS LiquidityAccelerationScore,
        MAX(CASE WHEN f.FactorCode = 'RELATIVE_STRENGTH' THEN v.NormalizedValue END) AS RelativeStrengthScore,
        MAX(CASE WHEN f.FactorCode = 'ACCUMULATION' THEN v.NormalizedValue END) AS AccumulationScore,
        MAX(CASE WHEN f.FactorCode = 'ACCUMULATION_MEMORY' THEN v.NormalizedValue END) AS AccumulationMemoryScore,
        MAX(CASE WHEN f.FactorCode = 'SUPPLY_LOCK' THEN v.NormalizedValue END) AS SupplyLockScore,
        MAX(CASE WHEN f.FactorCode = 'LIMIT_UP' THEN v.NormalizedValue END) AS LimitUpScore,
        MAX(CASE WHEN f.FactorCode = 'TREND' THEN v.NormalizedValue END) AS TrendScore,
        MAX(CASE WHEN f.FactorCode = 'DISTRIBUTION' THEN v.NormalizedValue END) AS DistributionScore
    FROM "CherryMon"."main"."cal_smart_money_factor_values" AS v
    INNER JOIN "CherryMon"."main"."dim_smart_money_factor" AS f
        ON f.FactorId = v.FactorId
    GROUP BY v.ModelId, v.Ticker, v.Date
)
SELECT
    s.Ticker,
    s.Date,
    m.ModelCode,
    m.ModelVersion,
    s.SmartMoneyScore,
    s.ConfidenceScore,
    s.MarketState,
    s.FactorCoverage,
    s.DataQualityStatus,
    w.FreshFlowScore,
    w.RelativeLiquidityScore,
    w.LiquidityAccelerationScore,
    w.RelativeStrengthScore,
    w.AccumulationScore,
    w.AccumulationMemoryScore,
    w.SupplyLockScore,
    w.LimitUpScore,
    w.TrendScore,
    w.DistributionScore
FROM "CherryMon"."main"."cal_smart_money_ticker_score" AS s
INNER JOIN "CherryMon"."main"."dim_smart_money_model" AS m
    ON m.ModelId = s.ModelId
LEFT JOIN factor_wide AS w
    ON w.ModelId = s.ModelId
   AND w.Ticker = s.Ticker
   AND w.Date = s.Date
WHERE m.IsEnabled = TRUE
  AND s.Date >= m.EffectiveFrom
  AND (m.EffectiveTo IS NULL OR s.Date <= m.EffectiveTo);
