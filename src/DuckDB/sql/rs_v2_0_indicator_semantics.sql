-- R/S V2.0 indicator semantic metadata migration.
-- Run manually against CherryMon.duckdb BEFORE using the V2.0 R/S runtime.
-- Idempotent for existing environments.

BEGIN TRANSACTION;

ALTER TABLE "CherryMon"."main"."dim_indicator_component"
    ADD COLUMN IF NOT EXISTS ValueSemantic VARCHAR;

ALTER TABLE "CherryMon"."main"."dim_indicator_component"
    ADD COLUMN IF NOT EXISTS Unit VARCHAR;

UPDATE "CherryMon"."main"."dim_indicator_component"
SET
    ValueSemantic = CASE
        WHEN IndicatorCode = 'MA'  AND ComponentCode = 'VALUE' THEN 'PRICE_LEVEL'
        WHEN IndicatorCode = 'BB'  AND ComponentCode IN ('LOWER', 'MIDDLE', 'UPPER') THEN 'PRICE_LEVEL'
        WHEN IndicatorCode = 'BB'  AND ComponentCode = 'WIDTH' THEN 'VOLATILITY'
        WHEN IndicatorCode = 'BB'  AND ComponentCode = 'PERCENT' THEN 'RATIO'
        WHEN IndicatorCode = 'RSI' AND ComponentCode = 'VALUE' THEN 'OSCILLATOR'
        WHEN IndicatorCode = 'ATR' AND ComponentCode = 'VALUE' THEN 'VOLATILITY_DISTANCE'
        ELSE ValueSemantic
    END,
    Unit = CASE
        WHEN IndicatorCode = 'MA'  AND ComponentCode = 'VALUE' THEN 'PRICE'
        WHEN IndicatorCode = 'BB'  AND ComponentCode IN ('LOWER', 'MIDDLE', 'UPPER') THEN 'PRICE'
        WHEN IndicatorCode = 'BB'  AND ComponentCode = 'WIDTH' THEN 'PERCENT'
        WHEN IndicatorCode = 'BB'  AND ComponentCode = 'PERCENT' THEN 'RATIO'
        WHEN IndicatorCode = 'RSI' AND ComponentCode = 'VALUE' THEN 'INDEX'
        WHEN IndicatorCode = 'ATR' AND ComponentCode = 'VALUE' THEN 'PRICE'
        ELSE Unit
    END
WHERE IndicatorCode IN ('MA', 'BB', 'RSI', 'ATR');

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Indicator_config" AS
SELECT
    cfg.ConfigId,
    cfg.ConfigCode,
    cfg.IndicatorCode,
    cfg.Timeframe,
    cfg.Parameters,
    cfg.WarmupBars,
    cfg.IsEnabled                    AS ConfigIsEnabled,
    cfg.Description                  AS ConfigDescription,
    cfg.CreatedAt                    AS ConfigCreatedAt,
    cfg.UpdatedAt                    AS ConfigUpdatedAt,
    ind.IndicatorName,
    ind.Category,
    ind.Engine,
    ind.FunctionName,
    ind.RequiredInputs,
    ind.ParameterSchema,
    ind.Description                  AS IndicatorDescription,
    ind.IsActive                     AS IndicatorIsActive,
    ind.CreatedAt                    AS IndicatorCreatedAt,
    ind.UpdatedAt                    AS IndicatorUpdatedAt,
    comp.ComponentCode,
    comp.ComponentName,
    comp.OutputPrefix,
    comp.SortOrder,
    comp.ValueSemantic,
    comp.Unit,
    comp.IsPrimary,
    comp.IsActive                    AS ComponentIsActive
FROM "CherryMon"."main"."dim_indicator_config" cfg
INNER JOIN "CherryMon"."main"."dim_indicator" ind
    ON ind.IndicatorCode = cfg.IndicatorCode
LEFT JOIN "CherryMon"."main"."dim_indicator_component" comp
    ON comp.IndicatorCode = cfg.IndicatorCode;

COMMIT;

-- Validation: R/S V2.0 metadata plus ATR prerequisite for V2.1.
SELECT
    IndicatorCode,
    ComponentCode,
    ValueSemantic,
    Unit,
    IsActive
FROM "CherryMon"."main"."dim_indicator_component"
WHERE IndicatorCode IN ('MA', 'BB', 'RSI', 'ATR')
ORDER BY IndicatorCode, SortOrder, ComponentCode;

-- Validation: public config SSOT exposes semantic fields.
SELECT
    ConfigCode,
    IndicatorCode,
    Timeframe,
    ComponentCode,
    ValueSemantic,
    Unit,
    ConfigIsEnabled,
    IndicatorIsActive,
    ComponentIsActive
FROM "CherryMon"."main"."vw_Indicator_config"
WHERE IndicatorCode IN ('MA', 'BB', 'RSI', 'ATR')
ORDER BY IndicatorCode, ConfigCode, ComponentCode;
