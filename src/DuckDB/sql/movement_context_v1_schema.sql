-- REQ-0032 MovementContext V1
-- Additive/idempotent semantic context layer.
-- Sources of Truth remain Price Movement profile, ZigZag current leg and daily OHLC.

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."dim_movement_context_config" (
    MovementContextConfigId BIGINT NOT NULL,
    ConfigCode VARCHAR NOT NULL,
    ModelVersion VARCHAR NOT NULL,
    Timeframe VARCHAR NOT NULL,
    PriceMovementConfigCode VARCHAR NOT NULL,
    ZigZagConfigCode VARCHAR NOT NULL,

    LastSwingShallowMaxRatio DOUBLE NOT NULL,
    LastSwingBelowTypicalMaxRatio DOUBLE NOT NULL,
    LastSwingTypicalMaxRatio DOUBLE NOT NULL,
    LastSwingExtendedMaxRatio DOUBLE NOT NULL,

    TrendQualityModerateEfficiency DOUBLE NOT NULL,
    TrendQualityModeratePersistence DOUBLE NOT NULL,
    TrendQualityModerateHighEfficiency DOUBLE NOT NULL,
    TrendQualityModerateHighPersistence DOUBLE NOT NULL,
    TrendQualityHighEfficiency DOUBLE NOT NULL,
    TrendQualityHighPersistence DOUBLE NOT NULL,

    SpeedVerySlowMaxRatio DOUBLE NOT NULL,
    SpeedSlowMaxRatio DOUBLE NOT NULL,
    SpeedNormalMaxRatio DOUBLE NOT NULL,
    SpeedFastMaxRatio DOUBLE NOT NULL,

    EffectiveFrom DATE NOT NULL DEFAULT DATE '2000-01-01',
    EffectiveTo DATE,
    IsEnabled BOOLEAN NOT NULL DEFAULT TRUE,
    CreatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (MovementContextConfigId),
    UNIQUE (ConfigCode),

    CHECK (Timeframe = 'D'),

    CHECK (LastSwingShallowMaxRatio > 0),
    CHECK (LastSwingBelowTypicalMaxRatio > LastSwingShallowMaxRatio),
    CHECK (LastSwingTypicalMaxRatio > LastSwingBelowTypicalMaxRatio),
    CHECK (LastSwingExtendedMaxRatio > LastSwingTypicalMaxRatio),

    CHECK (
        TrendQualityModerateEfficiency >= 0
        AND TrendQualityModerateEfficiency <= 1
    ),
    CHECK (
        TrendQualityModerateHighEfficiency >= TrendQualityModerateEfficiency
        AND TrendQualityModerateHighEfficiency <= 1
    ),
    CHECK (
        TrendQualityHighEfficiency >= TrendQualityModerateHighEfficiency
        AND TrendQualityHighEfficiency <= 1
    ),
    CHECK (
        TrendQualityModeratePersistence >= 0
        AND TrendQualityModeratePersistence <= 1
    ),
    CHECK (
        TrendQualityModerateHighPersistence >= TrendQualityModeratePersistence
        AND TrendQualityModerateHighPersistence <= 1
    ),
    CHECK (
        TrendQualityHighPersistence >= TrendQualityModerateHighPersistence
        AND TrendQualityHighPersistence <= 1
    ),

    CHECK (SpeedVerySlowMaxRatio > 0),
    CHECK (SpeedSlowMaxRatio > SpeedVerySlowMaxRatio),
    CHECK (SpeedNormalMaxRatio > SpeedSlowMaxRatio),
    CHECK (SpeedFastMaxRatio > SpeedNormalMaxRatio),

    CHECK (EffectiveTo IS NULL OR EffectiveTo >= EffectiveFrom)
);

INSERT INTO "CherryMon"."main"."dim_movement_context_config" (
    MovementContextConfigId,
    ConfigCode,
    ModelVersion,
    Timeframe,
    PriceMovementConfigCode,
    ZigZagConfigCode,
    LastSwingShallowMaxRatio,
    LastSwingBelowTypicalMaxRatio,
    LastSwingTypicalMaxRatio,
    LastSwingExtendedMaxRatio,
    TrendQualityModerateEfficiency,
    TrendQualityModeratePersistence,
    TrendQualityModerateHighEfficiency,
    TrendQualityModerateHighPersistence,
    TrendQualityHighEfficiency,
    TrendQualityHighPersistence,
    SpeedVerySlowMaxRatio,
    SpeedSlowMaxRatio,
    SpeedNormalMaxRatio,
    SpeedFastMaxRatio,
    EffectiveFrom,
    EffectiveTo,
    IsEnabled,
    UpdatedAt
)
VALUES (
    1,
    'MC_PM_ZZ_D_V1',
    'V1.0',
    'D',
    'PM_ZZ_D_V2',
    'ZZ_D_5_MVP',
    0.50,
    0.80,
    1.25,
    1.75,
    0.25,
    0.50,
    0.40,
    0.60,
    0.60,
    0.75,
    0.50,
    0.80,
    1.25,
    1.75,
    DATE '2000-01-01',
    NULL,
    TRUE,
    CURRENT_TIMESTAMP
)
ON CONFLICT (MovementContextConfigId) DO UPDATE SET
    ConfigCode = EXCLUDED.ConfigCode,
    ModelVersion = EXCLUDED.ModelVersion,
    Timeframe = EXCLUDED.Timeframe,
    PriceMovementConfigCode = EXCLUDED.PriceMovementConfigCode,
    ZigZagConfigCode = EXCLUDED.ZigZagConfigCode,
    LastSwingShallowMaxRatio = EXCLUDED.LastSwingShallowMaxRatio,
    LastSwingBelowTypicalMaxRatio = EXCLUDED.LastSwingBelowTypicalMaxRatio,
    LastSwingTypicalMaxRatio = EXCLUDED.LastSwingTypicalMaxRatio,
    LastSwingExtendedMaxRatio = EXCLUDED.LastSwingExtendedMaxRatio,
    TrendQualityModerateEfficiency = EXCLUDED.TrendQualityModerateEfficiency,
    TrendQualityModeratePersistence = EXCLUDED.TrendQualityModeratePersistence,
    TrendQualityModerateHighEfficiency = EXCLUDED.TrendQualityModerateHighEfficiency,
    TrendQualityModerateHighPersistence = EXCLUDED.TrendQualityModerateHighPersistence,
    TrendQualityHighEfficiency = EXCLUDED.TrendQualityHighEfficiency,
    TrendQualityHighPersistence = EXCLUDED.TrendQualityHighPersistence,
    SpeedVerySlowMaxRatio = EXCLUDED.SpeedVerySlowMaxRatio,
    SpeedSlowMaxRatio = EXCLUDED.SpeedSlowMaxRatio,
    SpeedNormalMaxRatio = EXCLUDED.SpeedNormalMaxRatio,
    SpeedFastMaxRatio = EXCLUDED.SpeedFastMaxRatio,
    EffectiveFrom = EXCLUDED.EffectiveFrom,
    EffectiveTo = EXCLUDED.EffectiveTo,
    IsEnabled = EXCLUDED.IsEnabled,
    UpdatedAt = EXCLUDED.UpdatedAt;

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Ticker_Movement_Context" AS
WITH enabled_context AS (
    SELECT
        MovementContextConfigId,
        ConfigCode,
        ModelVersion,
        Timeframe,
        PriceMovementConfigCode,
        ZigZagConfigCode,
        LastSwingShallowMaxRatio,
        LastSwingBelowTypicalMaxRatio,
        LastSwingTypicalMaxRatio,
        LastSwingExtendedMaxRatio,
        TrendQualityModerateEfficiency,
        TrendQualityModeratePersistence,
        TrendQualityModerateHighEfficiency,
        TrendQualityModerateHighPersistence,
        TrendQualityHighEfficiency,
        TrendQualityHighPersistence,
        SpeedVerySlowMaxRatio,
        SpeedSlowMaxRatio,
        SpeedNormalMaxRatio,
        SpeedFastMaxRatio,
        EffectiveFrom,
        EffectiveTo
    FROM "CherryMon"."main"."dim_movement_context_config"
    WHERE IsEnabled = TRUE
),
profile_context AS (
    SELECT
        c.MovementContextConfigId,
        c.ConfigCode AS MovementContextConfigCode,
        c.ModelVersion AS MovementContextModelVersion,
        c.Timeframe,
        c.PriceMovementConfigCode,
        p.PriceMovementModelVersion,
        c.ZigZagConfigCode,
        p.Ticker,
        p.AsOfConfirmedAtDate AS ProfileAsOfConfirmedAtDate,
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

        c.LastSwingShallowMaxRatio,
        c.LastSwingBelowTypicalMaxRatio,
        c.LastSwingTypicalMaxRatio,
        c.LastSwingExtendedMaxRatio,
        c.TrendQualityModerateEfficiency,
        c.TrendQualityModeratePersistence,
        c.TrendQualityModerateHighEfficiency,
        c.TrendQualityModerateHighPersistence,
        c.TrendQualityHighEfficiency,
        c.TrendQualityHighPersistence,
        c.SpeedVerySlowMaxRatio,
        c.SpeedSlowMaxRatio,
        c.SpeedNormalMaxRatio,
        c.SpeedFastMaxRatio,
        c.EffectiveFrom,
        c.EffectiveTo
    FROM enabled_context AS c
    INNER JOIN "CherryMon"."main"."vw_Ticker_Movement_Profile" AS p
        ON p.PriceMovementConfigCode = c.PriceMovementConfigCode
       AND p.ZigZagConfigCode = c.ZigZagConfigCode
),
with_current AS (
    SELECT
        p.*,
        z.AsOfDate AS CurrentLegAsOfDate,
        z.Direction AS CurrentLegDirection,
        z.StartPivotSeq AS CurrentStartPivotSeq,
        z.StartPivotDate AS CurrentStartPivotDate,
        z.StartPivotPrice AS CurrentStartPivotPrice,
        z.CandidatePivotType AS CurrentCandidatePivotType,
        z.CandidatePivotDate AS CurrentCandidatePivotDate,
        z.CandidatePivotPrice AS CurrentCandidatePivotPrice,
        z.LastClose AS CurrentLastClose,
        z.CurrentMovePct,
        z.ReversalFromCandidatePct,
        z.Status AS CurrentLegStatus
    FROM profile_context AS p
    LEFT JOIN "CherryMon"."main"."vw_Ticker_ZigZag_Current" AS z
        ON z.Ticker = p.Ticker
       AND z.ConfigCode = p.ZigZagConfigCode
),
current_bars AS (
    SELECT
        c.MovementContextConfigId,
        c.Ticker,
        GREATEST(COUNT(o.Date) - 1, 0) AS CurrentTradingBars
    FROM with_current AS c
    LEFT JOIN "CherryMon"."main"."vw_Ticker_OHLC_D" AS o
        ON o.Ticker = c.Ticker
       AND c.CurrentStartPivotDate IS NOT NULL
       AND c.CurrentLegAsOfDate IS NOT NULL
       AND o.Date >= c.CurrentStartPivotDate
       AND o.Date <= c.CurrentLegAsOfDate
    GROUP BY
        c.MovementContextConfigId,
        c.Ticker
),
base AS (
    SELECT
        c.*,
        b.CurrentTradingBars,
        CASE
            WHEN c.LastSwingDirection = 'UP' THEN c.MedianUpSwingPct
            WHEN c.LastSwingDirection = 'DOWN' THEN c.MedianDownSwingAbsPct
            ELSE NULL
        END AS LastSwingTypicalPct,
        CASE
            WHEN b.CurrentTradingBars > 0
             AND c.CurrentMovePct IS NOT NULL
            THEN c.CurrentMovePct / b.CurrentTradingBars
            ELSE NULL
        END AS CurrentMoveSpeedPctPerBar
    FROM with_current AS c
    INNER JOIN current_bars AS b
        ON b.MovementContextConfigId = c.MovementContextConfigId
       AND b.Ticker = c.Ticker
),
ratios AS (
    SELECT
        b.*,
        CASE
            WHEN b.LastSwingTypicalPct IS NOT NULL
             AND b.LastSwingTypicalPct > 0
            THEN ABS(b.LastSwingPct) / b.LastSwingTypicalPct
            ELSE NULL
        END AS LastSwingExtentRatio,
        CASE
            WHEN b.CurrentMoveSpeedPctPerBar IS NOT NULL
             AND b.MedianAbsVelocityPctPerBar IS NOT NULL
             AND b.MedianAbsVelocityPctPerBar > 0
            THEN ABS(b.CurrentMoveSpeedPctPerBar) / b.MedianAbsVelocityPctPerBar
            ELSE NULL
        END AS CurrentMoveSpeedRatio
    FROM base AS b
)
SELECT
    MovementContextConfigId,
    MovementContextConfigCode,
    MovementContextModelVersion,
    Timeframe,
    PriceMovementConfigCode,
    PriceMovementModelVersion,
    ZigZagConfigCode,
    Ticker,

    COALESCE(CurrentLegAsOfDate, ProfileAsOfConfirmedAtDate) AS ContextAsOfDate,
    ProfileAsOfConfirmedAtDate,
    CurrentLegAsOfDate,

    CASE
        WHEN MovementCharacter = 'INSUFFICIENT_HISTORY'
            THEN 'INSUFFICIENT_HISTORY'
        WHEN CurrentLegDirection IS NOT NULL
         AND CurrentMovePct IS NOT NULL
         AND CurrentTradingBars >= 1
            THEN 'PROFILE_PLUS_CURRENT'
        ELSE 'PROFILE_ONLY'
    END AS ContextStatus,

    MovementCharacter AS TrendRegime,
    CASE
        WHEN MovementCharacter = 'INSUFFICIENT_HISTORY'
            THEN 'INSUFFICIENT_HISTORY'
        WHEN MedianPathEfficiency >= TrendQualityHighEfficiency
         AND MedianDirectionalPersistenceRate >= TrendQualityHighPersistence
            THEN 'HIGH'
        WHEN MedianPathEfficiency >= TrendQualityModerateHighEfficiency
         AND MedianDirectionalPersistenceRate >= TrendQualityModerateHighPersistence
            THEN 'MODERATE_HIGH'
        WHEN MedianPathEfficiency >= TrendQualityModerateEfficiency
         AND MedianDirectionalPersistenceRate >= TrendQualityModeratePersistence
            THEN 'MODERATE'
        ELSE 'LOW'
    END AS TrendQuality,

    MedianAbsSwingPct AS TypicalSwingPct,
    MedianTradingBars AS TypicalSwingBars,
    MedianAbsVelocityPctPerBar AS TypicalMoveSpeedPctPerBar,
    MedianATRNormalizedMove,
    MedianPathEfficiency,
    MedianDirectionalPersistenceRate,
    DirectionalBias,

    ProfileLookbackSwings,
    ConfirmedSwingCount,
    LastSwingSeq,
    LastSwingDirection,
    LastSwingPct,
    LastSwingTypicalPct,
    LastSwingExtentRatio,
    CASE
        WHEN LastSwingExtentRatio IS NULL
            THEN 'UNKNOWN'
        WHEN LastSwingExtentRatio < LastSwingShallowMaxRatio
            THEN 'SHALLOW_' || LastSwingDirection || '_SWING'
        WHEN LastSwingExtentRatio < LastSwingBelowTypicalMaxRatio
            THEN 'BELOW_TYPICAL_' || LastSwingDirection || '_SWING'
        WHEN LastSwingExtentRatio <= LastSwingTypicalMaxRatio
            THEN 'TYPICAL_' || LastSwingDirection || '_SWING'
        WHEN LastSwingExtentRatio <= LastSwingExtendedMaxRatio
            THEN 'EXTENDED_' || LastSwingDirection || '_SWING'
        ELSE 'EXTREME_' || LastSwingDirection || '_SWING'
    END AS LastSwingState,

    CurrentLegDirection,
    CurrentMovePct,
    CurrentTradingBars,
    CurrentMoveSpeedPctPerBar,
    CurrentMoveSpeedRatio,
    CASE
        WHEN CurrentMoveSpeedRatio IS NULL
            THEN 'UNKNOWN'
        WHEN CurrentMoveSpeedRatio < SpeedVerySlowMaxRatio
            THEN 'VERY_SLOW'
        WHEN CurrentMoveSpeedRatio < SpeedSlowMaxRatio
            THEN 'SLOW'
        WHEN CurrentMoveSpeedRatio <= SpeedNormalMaxRatio
            THEN 'NORMAL'
        WHEN CurrentMoveSpeedRatio <= SpeedFastMaxRatio
            THEN 'FAST'
        ELSE 'EXTREME'
    END AS CurrentMoveSpeedState,
    CurrentLegStatus,
    CurrentStartPivotSeq,
    CurrentStartPivotDate,
    CurrentStartPivotPrice,
    CurrentCandidatePivotType,
    CurrentCandidatePivotDate,
    CurrentCandidatePivotPrice,
    CurrentLastClose,
    ReversalFromCandidatePct

FROM ratios
WHERE COALESCE(CurrentLegAsOfDate, ProfileAsOfConfirmedAtDate) >= EffectiveFrom
  AND (
      EffectiveTo IS NULL
      OR COALESCE(CurrentLegAsOfDate, ProfileAsOfConfirmedAtDate) <= EffectiveTo
  );
