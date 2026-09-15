-- Price Movement Character V1 storage, metadata seed and public views.
-- Additive/idempotent. Does not mutate OHLC or Indicator Engine persistence.

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."dim_price_movement_model" (
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

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."dim_price_movement_config" (
    ConfigId BIGINT NOT NULL,
    ModelId BIGINT NOT NULL,
    Timeframe VARCHAR NOT NULL,
    PivotPriceSource VARCHAR NOT NULL,
    ConfirmationPriceSource VARCHAR NOT NULL,
    ATRIndicatorCode VARCHAR NOT NULL,
    ATRLength INTEGER NOT NULL,
    ATRMultiplier DOUBLE NOT NULL,
    MinReversalPct DOUBLE NOT NULL,
    MaxReversalPct DOUBLE,
    MinimumSwingBars INTEGER NOT NULL,
    MinHistoricalSameDir INTEGER NOT NULL,
    ProfileMaxSwings INTEGER NOT NULL,
    MagnitudeRawWeight DOUBLE NOT NULL,
    MagnitudeATRWeight DOUBLE NOT NULL,
    PersistenceERWeight DOUBLE NOT NULL,
    PersistenceR2Weight DOUBLE NOT NULL,
    PersistenceSmoothnessWeight DOUBLE NOT NULL,
    PersistenceDirectionalDayWeight DOUBLE NOT NULL,
    HighMagnitudeThreshold DOUBLE NOT NULL,
    HighVelocityThreshold DOUBLE NOT NULL,
    HighPersistenceThreshold DOUBLE NOT NULL,
    LowPersistenceThreshold DOUBLE NOT NULL,
    MidMagnitudeThreshold DOUBLE NOT NULL,
    EffectiveFrom DATE NOT NULL DEFAULT DATE '2000-01-01',
    EffectiveTo DATE,
    IsEnabled BOOLEAN NOT NULL DEFAULT TRUE,
    CreatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ConfigId),
    UNIQUE (ModelId, Timeframe, EffectiveFrom),
    CHECK (Timeframe IN ('D', 'W', 'M')),
    CHECK (ATRLength > 0),
    CHECK (ATRMultiplier > 0),
    CHECK (MinReversalPct > 0 AND MinReversalPct < 1),
    CHECK (MaxReversalPct IS NULL OR (MaxReversalPct > MinReversalPct AND MaxReversalPct < 1)),
    CHECK (MinimumSwingBars >= 1),
    CHECK (MinHistoricalSameDir >= 1),
    CHECK (ProfileMaxSwings >= MinHistoricalSameDir),
    CHECK (ABS((MagnitudeRawWeight + MagnitudeATRWeight) - 1.0) < 0.000001),
    CHECK (ABS((
        PersistenceERWeight
        + PersistenceR2Weight
        + PersistenceSmoothnessWeight
        + PersistenceDirectionalDayWeight
    ) - 1.0) < 0.000001)
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_price_movement_swing" (
    ConfigId BIGINT NOT NULL,
    Ticker VARCHAR NOT NULL,
    Direction VARCHAR NOT NULL,
    SwingSeq BIGINT NOT NULL,
    PivotStartDate DATE NOT NULL,
    PivotEndDate DATE NOT NULL,
    ConfirmedAtDate DATE NOT NULL,
    StartPrice DOUBLE NOT NULL,
    EndPrice DOUBLE NOT NULL,
    SwingPct DOUBLE NOT NULL,
    DurationBars INTEGER NOT NULL,
    DurationCalendarDays INTEGER NOT NULL,
    VelocityLogPerBar DOUBLE NOT NULL,
    VelocityPctPerBar DOUBLE NOT NULL,
    MeanATR DOUBLE,
    ATRNormMagnitude DOUBLE,
    EfficiencyRatio DOUBLE NOT NULL,
    RegressionSlopePerBar DOUBLE,
    RegressionR2 DOUBLE,
    MaxAdverseExcursionPct DOUBLE NOT NULL,
    DirectionalDayRatio DOUBLE NOT NULL,
    PersistenceScore DOUBLE NOT NULL,
    ThresholdPct DOUBLE NOT NULL,
    ThresholdSource VARCHAR NOT NULL,
    QualityStatus VARCHAR NOT NULL,
    CalculatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ConfigId, Ticker, PivotStartDate, Direction),
    CHECK (Direction IN ('UP', 'DOWN')),
    CHECK (PivotStartDate <= PivotEndDate),
    CHECK (PivotEndDate <= ConfirmedAtDate),
    CHECK (DurationBars >= 1),
    CHECK (EfficiencyRatio >= 0 AND EfficiencyRatio <= 1),
    CHECK (RegressionR2 IS NULL OR (RegressionR2 >= 0 AND RegressionR2 <= 1)),
    CHECK (DirectionalDayRatio >= 0 AND DirectionalDayRatio <= 1),
    CHECK (PersistenceScore >= 0 AND PersistenceScore <= 100),
    CHECK (ThresholdSource IN ('ATR_PLUS_FLOOR', 'PCT_FALLBACK')),
    CHECK (QualityStatus IN ('OK', 'PARTIAL'))
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_price_movement_daily" (
    ConfigId BIGINT NOT NULL,
    Ticker VARCHAR NOT NULL,
    Date DATE NOT NULL,
    Direction VARCHAR,
    SwingStatus VARCHAR NOT NULL,
    CurrentSwingStartDate DATE,
    CandidateEndDate DATE,
    StartPrice DOUBLE,
    CandidateEndPrice DOUBLE,
    CurrentSwingPct DOUBLE,
    DurationBars INTEGER,
    VelocityLogPerBar DOUBLE,
    VelocityPctPerBar DOUBLE,
    ATRNormMagnitude DOUBLE,
    EfficiencyRatio DOUBLE,
    RegressionSlopePerBar DOUBLE,
    RegressionR2 DOUBLE,
    MaxAdverseExcursionPct DOUBLE,
    DirectionalDayRatio DOUBLE,
    HistoricalSameDirSwingCount INTEGER NOT NULL DEFAULT 0,
    MagnitudePercentile DOUBLE,
    ATRNormMagnitudePercentile DOUBLE,
    VelocityPercentile DOUBLE,
    PersistencePercentile DOUBLE,
    MagnitudeScore DOUBLE,
    VelocityScore DOUBLE,
    PersistenceScore DOUBLE,
    MovementCharacter VARCHAR NOT NULL,
    ScoreBasis VARCHAR NOT NULL,
    ThresholdPct DOUBLE,
    ThresholdSource VARCHAR,
    QualityStatus VARCHAR NOT NULL,
    CalculatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ConfigId, Ticker, Date),
    CHECK (Direction IS NULL OR Direction IN ('UP', 'DOWN')),
    CHECK (SwingStatus IN ('PROVISIONAL', 'TRANSITION')),
    CHECK (EfficiencyRatio IS NULL OR (EfficiencyRatio >= 0 AND EfficiencyRatio <= 1)),
    CHECK (RegressionR2 IS NULL OR (RegressionR2 >= 0 AND RegressionR2 <= 1)),
    CHECK (DirectionalDayRatio IS NULL OR (DirectionalDayRatio >= 0 AND DirectionalDayRatio <= 1)),
    CHECK (MagnitudePercentile IS NULL OR (MagnitudePercentile >= 0 AND MagnitudePercentile <= 100)),
    CHECK (ATRNormMagnitudePercentile IS NULL OR (ATRNormMagnitudePercentile >= 0 AND ATRNormMagnitudePercentile <= 100)),
    CHECK (VelocityPercentile IS NULL OR (VelocityPercentile >= 0 AND VelocityPercentile <= 100)),
    CHECK (PersistencePercentile IS NULL OR (PersistencePercentile >= 0 AND PersistencePercentile <= 100)),
    CHECK (MagnitudeScore IS NULL OR (MagnitudeScore >= 0 AND MagnitudeScore <= 100)),
    CHECK (VelocityScore IS NULL OR (VelocityScore >= 0 AND VelocityScore <= 100)),
    CHECK (PersistenceScore IS NULL OR (PersistenceScore >= 0 AND PersistenceScore <= 100)),
    CHECK (ThresholdSource IS NULL OR ThresholdSource IN ('ATR_PLUS_FLOOR', 'PCT_FALLBACK')),
    CHECK (QualityStatus IN ('OK', 'PARTIAL'))
);

INSERT INTO "CherryMon"."main"."dim_price_movement_model" (
    ModelId, ModelCode, ModelVersion, Description, IsEnabled,
    EffectiveFrom, EffectiveTo, UpdatedAt
)
VALUES (
    1,
    'PRICE_MOVEMENT_CHARACTER',
    'V1',
    'Point-in-time safe daily price-path characterization using adaptive swing segmentation, magnitude, velocity and persistence.',
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
    UpdatedAt = EXCLUDED.UpdatedAt;

INSERT INTO "CherryMon"."main"."dim_price_movement_config" (
    ConfigId, ModelId, Timeframe,
    PivotPriceSource, ConfirmationPriceSource,
    ATRIndicatorCode, ATRLength, ATRMultiplier,
    MinReversalPct, MaxReversalPct, MinimumSwingBars,
    MinHistoricalSameDir, ProfileMaxSwings,
    MagnitudeRawWeight, MagnitudeATRWeight,
    PersistenceERWeight, PersistenceR2Weight,
    PersistenceSmoothnessWeight, PersistenceDirectionalDayWeight,
    HighMagnitudeThreshold, HighVelocityThreshold,
    HighPersistenceThreshold, LowPersistenceThreshold, MidMagnitudeThreshold,
    EffectiveFrom, EffectiveTo, IsEnabled, UpdatedAt
)
VALUES (
    1, 1, 'D',
    'HIGH_LOW', 'CLOSE',
    'ATR', 14, 2.0,
    0.03, NULL, 2,
    8, 50,
    0.60, 0.40,
    0.35, 0.35, 0.20, 0.10,
    75.0, 75.0, 70.0, 55.0, 40.0,
    DATE '2000-01-01', NULL, TRUE, CURRENT_TIMESTAMP
)
ON CONFLICT (ConfigId) DO UPDATE SET
    ModelId = EXCLUDED.ModelId,
    Timeframe = EXCLUDED.Timeframe,
    PivotPriceSource = EXCLUDED.PivotPriceSource,
    ConfirmationPriceSource = EXCLUDED.ConfirmationPriceSource,
    ATRIndicatorCode = EXCLUDED.ATRIndicatorCode,
    ATRLength = EXCLUDED.ATRLength,
    ATRMultiplier = EXCLUDED.ATRMultiplier,
    MinReversalPct = EXCLUDED.MinReversalPct,
    MaxReversalPct = EXCLUDED.MaxReversalPct,
    MinimumSwingBars = EXCLUDED.MinimumSwingBars,
    MinHistoricalSameDir = EXCLUDED.MinHistoricalSameDir,
    ProfileMaxSwings = EXCLUDED.ProfileMaxSwings,
    MagnitudeRawWeight = EXCLUDED.MagnitudeRawWeight,
    MagnitudeATRWeight = EXCLUDED.MagnitudeATRWeight,
    PersistenceERWeight = EXCLUDED.PersistenceERWeight,
    PersistenceR2Weight = EXCLUDED.PersistenceR2Weight,
    PersistenceSmoothnessWeight = EXCLUDED.PersistenceSmoothnessWeight,
    PersistenceDirectionalDayWeight = EXCLUDED.PersistenceDirectionalDayWeight,
    HighMagnitudeThreshold = EXCLUDED.HighMagnitudeThreshold,
    HighVelocityThreshold = EXCLUDED.HighVelocityThreshold,
    HighPersistenceThreshold = EXCLUDED.HighPersistenceThreshold,
    LowPersistenceThreshold = EXCLUDED.LowPersistenceThreshold,
    MidMagnitudeThreshold = EXCLUDED.MidMagnitudeThreshold,
    EffectiveFrom = EXCLUDED.EffectiveFrom,
    EffectiveTo = EXCLUDED.EffectiveTo,
    IsEnabled = EXCLUDED.IsEnabled,
    UpdatedAt = EXCLUDED.UpdatedAt;

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Ticker_Movement_Swings" AS
SELECT
    s.ConfigId,
    m.ModelCode,
    m.ModelVersion,
    s.Ticker,
    s.Direction,
    s.SwingSeq,
    s.PivotStartDate,
    s.PivotEndDate,
    s.ConfirmedAtDate,
    s.StartPrice,
    s.EndPrice,
    s.SwingPct,
    s.DurationBars,
    s.DurationCalendarDays,
    s.VelocityLogPerBar,
    s.VelocityPctPerBar,
    s.MeanATR,
    s.ATRNormMagnitude,
    s.EfficiencyRatio,
    s.RegressionSlopePerBar,
    s.RegressionR2,
    s.MaxAdverseExcursionPct,
    s.DirectionalDayRatio,
    s.PersistenceScore,
    s.ThresholdPct,
    s.ThresholdSource,
    s.QualityStatus,
    s.CalculatedAt
FROM "CherryMon"."main"."cal_price_movement_swing" AS s
INNER JOIN "CherryMon"."main"."dim_price_movement_config" AS c
    ON c.ConfigId = s.ConfigId
INNER JOIN "CherryMon"."main"."dim_price_movement_model" AS m
    ON m.ModelId = c.ModelId
WHERE c.IsEnabled = TRUE
  AND m.IsEnabled = TRUE
  AND s.PivotEndDate >= c.EffectiveFrom
  AND (c.EffectiveTo IS NULL OR s.PivotEndDate <= c.EffectiveTo)
  AND s.PivotEndDate >= m.EffectiveFrom
  AND (m.EffectiveTo IS NULL OR s.PivotEndDate <= m.EffectiveTo);

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Ticker_Movement_D" AS
SELECT
    d.ConfigId,
    m.ModelCode,
    m.ModelVersion,
    d.Ticker,
    d.Date,
    d.Direction,
    d.SwingStatus,
    d.CurrentSwingStartDate,
    d.CandidateEndDate,
    d.StartPrice,
    d.CandidateEndPrice,
    d.CurrentSwingPct,
    d.DurationBars,
    d.VelocityLogPerBar,
    d.VelocityPctPerBar,
    d.ATRNormMagnitude,
    d.EfficiencyRatio,
    d.RegressionSlopePerBar,
    d.RegressionR2,
    d.MaxAdverseExcursionPct,
    d.DirectionalDayRatio,
    d.HistoricalSameDirSwingCount,
    d.MagnitudePercentile,
    d.ATRNormMagnitudePercentile,
    d.VelocityPercentile,
    d.PersistencePercentile,
    d.MagnitudeScore,
    d.VelocityScore,
    d.PersistenceScore,
    d.MovementCharacter,
    d.ScoreBasis,
    d.ThresholdPct,
    d.ThresholdSource,
    d.QualityStatus,
    d.CalculatedAt
FROM "CherryMon"."main"."cal_price_movement_daily" AS d
INNER JOIN "CherryMon"."main"."dim_price_movement_config" AS c
    ON c.ConfigId = d.ConfigId
INNER JOIN "CherryMon"."main"."dim_price_movement_model" AS m
    ON m.ModelId = c.ModelId
WHERE c.IsEnabled = TRUE
  AND m.IsEnabled = TRUE
  AND d.Date >= c.EffectiveFrom
  AND (c.EffectiveTo IS NULL OR d.Date <= c.EffectiveTo)
  AND d.Date >= m.EffectiveFrom
  AND (m.EffectiveTo IS NULL OR d.Date <= m.EffectiveTo);

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Ticker_Movement_Profile" AS
SELECT
    s.ConfigId,
    s.ModelCode,
    s.ModelVersion,
    s.Ticker,
    s.Direction,
    COUNT(*) AS SwingCount,
    MEDIAN(ABS(s.SwingPct)) AS MagnitudeMedian,
    QUANTILE_CONT(ABS(s.SwingPct), 0.75) AS MagnitudeP75,
    QUANTILE_CONT(ABS(s.SwingPct), 0.90) AS MagnitudeP90,
    MEDIAN(s.DurationBars) AS DurationBarsMedian,
    QUANTILE_CONT(s.DurationBars, 0.75) AS DurationBarsP75,
    MEDIAN(ABS(s.VelocityLogPerBar)) AS VelocityMedian,
    QUANTILE_CONT(ABS(s.VelocityLogPerBar), 0.75) AS VelocityP75,
    MEDIAN(s.ATRNormMagnitude) AS ATRNormMagnitudeMedian,
    MEDIAN(s.PersistenceScore) AS PersistenceMedian,
    MAX(s.ConfirmedAtDate) AS LatestConfirmedAtDate
FROM "CherryMon"."main"."vw_Ticker_Movement_Swings" AS s
GROUP BY
    s.ConfigId,
    s.ModelCode,
    s.ModelVersion,
    s.Ticker,
    s.Direction;
