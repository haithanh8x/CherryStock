-- CherryStock: current (latest AmiBroker APX) W/M indicator snapshot.
-- Depends on existing cal_indicator_current, dim_indicator_config,
-- and dim_indicator_component. No INSERT/UPDATE/DELETE and no schema migration.
--
-- Current fact: Ticker, Date, IndicatorName, Timeframe, Value, UpdatedAt.
-- Examples:
--   MA20/W                 -> ConfigCode=MA20_W, ComponentCode=VALUE
--   BB20_2_UPPER/W         -> ConfigCode=BB20_2_W, ComponentCode=UPPER
--   MACD12_26_9_SIGNAL/M  -> ConfigCode=MACD12_26_9_M, ComponentCode=SIGNAL
--
-- LEFT JOIN intentionally preserves fact rows with missing metadata;
-- scripts/create_vw_ticker_indicator_current.py refuses to COMMIT such a view.
CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Ticker_Indicator_Current" AS
WITH indicator_mapping AS (
    SELECT
        cfg.ConfigId,
        cfg.ConfigCode,
        cfg.IndicatorCode,
        cfg.Timeframe,
        cfg.Parameters,
        cfg.WarmupBars,
        cfg.IsEnabled,
        cfg.Description AS ConfigDescription,
        comp.ComponentCode,
        comp.ComponentName,
        comp.OutputPrefix,
        comp.SortOrder,
        comp.ValueSemantic,
        comp.Unit,
        comp.IsPrimary,
        comp.IsActive AS ComponentIsActive,
        CASE
            WHEN comp.ComponentCode = 'VALUE' THEN
                REGEXP_REPLACE(cfg.ConfigCode, '_[DWM]$', '')
            ELSE
                REGEXP_REPLACE(cfg.ConfigCode, '_[DWM]$', '')
                || '_' || comp.ComponentCode
        END AS IndicatorName
    FROM "CherryMon"."main"."dim_indicator_config" AS cfg
    INNER JOIN "CherryMon"."main"."dim_indicator_component" AS comp
        ON comp.IndicatorCode = cfg.IndicatorCode
)
SELECT
    cur.Ticker,
    cur.Date,
    cur.IndicatorName,
    cur.Timeframe,
    map.ConfigId,
    map.ConfigCode,
    map.IndicatorCode,
    map.ComponentCode,
    map.ComponentName,
    map.IsPrimary,
    map.ValueSemantic,
    map.Unit,
    map.Parameters,
    map.WarmupBars,
    map.IsEnabled,
    map.ComponentIsActive,
    map.ConfigDescription,
    map.OutputPrefix,
    map.SortOrder,
    cur.Value,
    cur.UpdatedAt
FROM "CherryMon"."main"."cal_indicator_current" AS cur
LEFT JOIN indicator_mapping AS map
    ON map.IndicatorName = cur.IndicatorName
    AND map.Timeframe = cur.Timeframe;
