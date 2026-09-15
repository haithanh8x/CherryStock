-- Price Movement Character V1 profile contract.
-- Uses only the most recent ProfileMaxSwings confirmed events per ticker/config/direction.

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Ticker_Movement_Profile" AS
WITH ranked AS (
    SELECT
        s.ConfigId,
        s.ModelCode,
        s.ModelVersion,
        s.Ticker,
        s.Direction,
        s.SwingPct,
        s.DurationBars,
        s.VelocityLogPerBar,
        s.ATRNormMagnitude,
        s.PersistenceScore,
        s.ConfirmedAtDate,
        c.ProfileMaxSwings,
        ROW_NUMBER() OVER (
            PARTITION BY s.ConfigId, s.Ticker, s.Direction
            ORDER BY s.ConfirmedAtDate DESC, s.SwingSeq DESC, s.PivotEndDate DESC
        ) AS rn
    FROM "CherryMon"."main"."vw_Ticker_Movement_Swings" AS s
    INNER JOIN "CherryMon"."main"."dim_price_movement_config" AS c
        ON c.ConfigId = s.ConfigId
)
SELECT
    ConfigId,
    ModelCode,
    ModelVersion,
    Ticker,
    Direction,
    COUNT(*) AS SwingCount,
    MEDIAN(ABS(SwingPct)) AS MagnitudeMedian,
    QUANTILE_CONT(ABS(SwingPct), 0.75) AS MagnitudeP75,
    QUANTILE_CONT(ABS(SwingPct), 0.90) AS MagnitudeP90,
    MEDIAN(DurationBars) AS DurationBarsMedian,
    QUANTILE_CONT(DurationBars, 0.75) AS DurationBarsP75,
    MEDIAN(ABS(VelocityLogPerBar)) AS VelocityMedian,
    QUANTILE_CONT(ABS(VelocityLogPerBar), 0.75) AS VelocityP75,
    MEDIAN(ATRNormMagnitude) AS ATRNormMagnitudeMedian,
    MEDIAN(PersistenceScore) AS PersistenceMedian,
    MAX(ConfirmedAtDate) AS LatestConfirmedAtDate
FROM ranked
WHERE rn <= ProfileMaxSwings
GROUP BY
    ConfigId,
    ModelCode,
    ModelVersion,
    Ticker,
    Direction;
