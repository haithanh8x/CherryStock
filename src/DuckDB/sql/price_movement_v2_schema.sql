-- REQ-0031 Price Movement Characterization V2
-- Additive/idempotent. ZigZag remains segmentation SSOT.

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."dim_price_movement_config" (
    ConfigId BIGINT NOT NULL,
    ConfigCode VARCHAR NOT NULL,
    ModelVersion VARCHAR NOT NULL,
    Timeframe VARCHAR NOT NULL,
    ZigZagConfigCode VARCHAR NOT NULL,
    ProfileLookbackSwings INTEGER NOT NULL,
    MinimumProfileSwings INTEGER NOT NULL,
    TrendBiasThreshold DOUBLE NOT NULL,
    RangeBiasThreshold DOUBLE NOT NULL,
    EfficiencyThreshold DOUBLE NOT NULL,
    ATRPeriod INTEGER NOT NULL,
    EffectiveFrom DATE NOT NULL DEFAULT DATE '2000-01-01',
    EffectiveTo DATE,
    IsEnabled BOOLEAN NOT NULL DEFAULT TRUE,
    CreatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ConfigId),
    UNIQUE (ConfigCode),
    CHECK (Timeframe = 'D'),
    CHECK (ProfileLookbackSwings >= 1),
    CHECK (MinimumProfileSwings >= 1),
    CHECK (MinimumProfileSwings <= ProfileLookbackSwings),
    CHECK (TrendBiasThreshold >= 0 AND TrendBiasThreshold <= 1),
    CHECK (RangeBiasThreshold >= 0 AND RangeBiasThreshold <= 1),
    CHECK (RangeBiasThreshold <= TrendBiasThreshold),
    CHECK (EfficiencyThreshold >= 0 AND EfficiencyThreshold <= 1),
    CHECK (ATRPeriod >= 2)
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_price_movement_swing" (
    PriceMovementConfigId BIGINT NOT NULL,
    ZigZagConfigId BIGINT NOT NULL,
    ZigZagConfigCode VARCHAR NOT NULL,
    Ticker VARCHAR NOT NULL,
    SwingSeq BIGINT NOT NULL,
    Direction VARCHAR NOT NULL,
    StartPivotSeq BIGINT NOT NULL,
    StartDate DATE NOT NULL,
    StartPrice DOUBLE NOT NULL,
    EndPivotSeq BIGINT NOT NULL,
    EndDate DATE NOT NULL,
    EndPrice DOUBLE NOT NULL,
    ConfirmedAtDate DATE NOT NULL,
    SwingPct DOUBLE NOT NULL,
    TradingBars INTEGER NOT NULL,
    CalendarDays INTEGER NOT NULL,
    VelocityPctPerBar DOUBLE NOT NULL,
    AvgATRPct DOUBLE,
    ATRNormalizedMove DOUBLE,
    PathEfficiency DOUBLE NOT NULL,
    DirectionalPersistenceRate DOUBLE NOT NULL,
    CalculatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (
        PriceMovementConfigId,
        ZigZagConfigId,
        Ticker,
        SwingSeq
    ),
    CHECK (Direction IN ('UP', 'DOWN')),
    CHECK (StartPrice > 0),
    CHECK (EndPrice > 0),
    CHECK (StartDate < EndDate),
    CHECK (EndDate < ConfirmedAtDate),
    CHECK (TradingBars >= 1),
    CHECK (CalendarDays >= 1),
    CHECK (PathEfficiency >= 0 AND PathEfficiency <= 1),
    CHECK (
        DirectionalPersistenceRate >= 0
        AND DirectionalPersistenceRate <= 1
    ),
    CHECK (AvgATRPct IS NULL OR AvgATRPct > 0),
    CHECK (ATRNormalizedMove IS NULL OR ATRNormalizedMove >= 0)
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_price_movement_profile" (
    PriceMovementConfigId BIGINT NOT NULL,
    ZigZagConfigId BIGINT NOT NULL,
    ZigZagConfigCode VARCHAR NOT NULL,
    Ticker VARCHAR NOT NULL,
    AsOfConfirmedAtDate DATE NOT NULL,
    ProfileLookbackSwings INTEGER NOT NULL,
    ConfirmedSwingCount INTEGER NOT NULL,
    LastSwingSeq BIGINT NOT NULL,
    LastSwingDirection VARCHAR NOT NULL,
    LastSwingPct DOUBLE NOT NULL,
    MedianUpSwingPct DOUBLE,
    MedianDownSwingAbsPct DOUBLE,
    MedianAbsSwingPct DOUBLE NOT NULL,
    MedianTradingBars DOUBLE NOT NULL,
    MedianAbsVelocityPctPerBar DOUBLE NOT NULL,
    MedianATRNormalizedMove DOUBLE,
    MedianPathEfficiency DOUBLE NOT NULL,
    MedianDirectionalPersistenceRate DOUBLE NOT NULL,
    DirectionalBias DOUBLE NOT NULL,
    MovementCharacter VARCHAR NOT NULL,
    CalculatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (
        PriceMovementConfigId,
        ZigZagConfigId,
        Ticker
    ),
    CHECK (ProfileLookbackSwings >= 1),
    CHECK (ConfirmedSwingCount >= 1),
    CHECK (LastSwingDirection IN ('UP', 'DOWN')),
    CHECK (MedianAbsSwingPct >= 0),
    CHECK (MedianTradingBars >= 1),
    CHECK (MedianAbsVelocityPctPerBar >= 0),
    CHECK (MedianATRNormalizedMove IS NULL OR MedianATRNormalizedMove >= 0),
    CHECK (MedianPathEfficiency >= 0 AND MedianPathEfficiency <= 1),
    CHECK (
        MedianDirectionalPersistenceRate >= 0
        AND MedianDirectionalPersistenceRate <= 1
    ),
    CHECK (DirectionalBias >= -1 AND DirectionalBias <= 1),
    CHECK (MovementCharacter IN (
        'INSUFFICIENT_HISTORY',
        'TRENDING_UP',
        'TRENDING_DOWN',
        'RANGE_BOUND',
        'MIXED'
    ))
);

INSERT INTO "CherryMon"."main"."dim_price_movement_config" (
    ConfigId,
    ConfigCode,
    ModelVersion,
    Timeframe,
    ZigZagConfigCode,
    ProfileLookbackSwings,
    MinimumProfileSwings,
    TrendBiasThreshold,
    RangeBiasThreshold,
    EfficiencyThreshold,
    ATRPeriod,
    EffectiveFrom,
    EffectiveTo,
    IsEnabled,
    UpdatedAt
)
VALUES (
    1,
    'PM_ZZ_D_V2',
    'V2.0',
    'D',
    'ZZ_D_5_MVP',
    20,
    6,
    0.20,
    0.15,
    0.30,
    20,
    DATE '2000-01-01',
    NULL,
    TRUE,
    CURRENT_TIMESTAMP
)
ON CONFLICT (ConfigId) DO UPDATE SET
    ConfigCode = EXCLUDED.ConfigCode,
    ModelVersion = EXCLUDED.ModelVersion,
    Timeframe = EXCLUDED.Timeframe,
    ZigZagConfigCode = EXCLUDED.ZigZagConfigCode,
    ProfileLookbackSwings = EXCLUDED.ProfileLookbackSwings,
    MinimumProfileSwings = EXCLUDED.MinimumProfileSwings,
    TrendBiasThreshold = EXCLUDED.TrendBiasThreshold,
    RangeBiasThreshold = EXCLUDED.RangeBiasThreshold,
    EfficiencyThreshold = EXCLUDED.EfficiencyThreshold,
    ATRPeriod = EXCLUDED.ATRPeriod,
    EffectiveFrom = EXCLUDED.EffectiveFrom,
    EffectiveTo = EXCLUDED.EffectiveTo,
    IsEnabled = EXCLUDED.IsEnabled,
    UpdatedAt = EXCLUDED.UpdatedAt;

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Ticker_Price_Movement_Swings" AS
SELECT
    pm.ConfigCode AS PriceMovementConfigCode,
    pm.ModelVersion AS PriceMovementModelVersion,
    pm.Timeframe,
    s.PriceMovementConfigId,
    s.ZigZagConfigId,
    s.ZigZagConfigCode,
    s.Ticker,
    s.SwingSeq,
    s.Direction,
    s.StartPivotSeq,
    s.StartDate,
    s.StartPrice,
    s.EndPivotSeq,
    s.EndDate,
    s.EndPrice,
    s.ConfirmedAtDate,
    s.SwingPct,
    s.TradingBars,
    s.CalendarDays,
    s.VelocityPctPerBar,
    s.AvgATRPct,
    s.ATRNormalizedMove,
    s.PathEfficiency,
    s.DirectionalPersistenceRate,
    s.CalculatedAt
FROM "CherryMon"."main"."cal_price_movement_swing" AS s
INNER JOIN "CherryMon"."main"."dim_price_movement_config" AS pm
    ON pm.ConfigId = s.PriceMovementConfigId
WHERE pm.IsEnabled = TRUE
  AND s.EndDate >= pm.EffectiveFrom
  AND (pm.EffectiveTo IS NULL OR s.EndDate <= pm.EffectiveTo);

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Ticker_Movement_Profile" AS
SELECT
    pm.ConfigCode AS PriceMovementConfigCode,
    pm.ModelVersion AS PriceMovementModelVersion,
    pm.Timeframe,
    p.PriceMovementConfigId,
    p.ZigZagConfigId,
    p.ZigZagConfigCode,
    p.Ticker,
    p.AsOfConfirmedAtDate,
    p.ProfileLookbackSwings,
    p.ConfirmedSwingCount,
    p.LastSwingSeq,
    p.LastSwingDirection,
    p.LastSwingPct,
    p.MedianUpSwingPct,
    p.MedianDownSwingAbsPct,
    p.MedianAbsSwingPct,
    p.MedianTradingBars,
    p.MedianAbsVelocityPctPerBar,
    p.MedianATRNormalizedMove,
    p.MedianPathEfficiency,
    p.MedianDirectionalPersistenceRate,
    p.DirectionalBias,
    p.MovementCharacter,
    p.CalculatedAt
FROM "CherryMon"."main"."cal_price_movement_profile" AS p
INNER JOIN "CherryMon"."main"."dim_price_movement_config" AS pm
    ON pm.ConfigId = p.PriceMovementConfigId
WHERE pm.IsEnabled = TRUE;
