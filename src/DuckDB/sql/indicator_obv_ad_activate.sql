-- Activate OBV and Accumulation/Distribution (AD) in CherryStock Indicator Engine.
-- PHASE 1 metadata only. Idempotent. Does not touch cal_indicator_values.
-- Default production family: D / W / M.

INSERT INTO "CherryMon"."main"."dim_indicator" (
    IndicatorCode,
    IndicatorName,
    Category,
    Engine,
    FunctionName,
    RequiredInputs,
    ParameterSchema,
    Description,
    IsActive,
    UpdatedAt
)
VALUES
    (
        'OBV',
        'On-Balance Volume',
        'VOLUME',
        'PANDAS_TA_CLASSIC',
        'obv',
        '["Close","Volume"]'::JSON,
        NULL,
        'Cumulative signed-volume line used as optional SmartMoney accumulation evidence.',
        TRUE,
        now()
    ),
    (
        'AD',
        'Accumulation/Distribution Line',
        'VOLUME',
        'PANDAS_TA_CLASSIC',
        'ad',
        '["High","Low","Close","Volume"]'::JSON,
        NULL,
        'Cumulative Chaikin accumulation/distribution line based on close location and volume.',
        TRUE,
        now()
    )
ON CONFLICT (IndicatorCode) DO UPDATE SET
    IndicatorName = EXCLUDED.IndicatorName,
    Category = EXCLUDED.Category,
    Engine = EXCLUDED.Engine,
    FunctionName = EXCLUDED.FunctionName,
    RequiredInputs = EXCLUDED.RequiredInputs,
    ParameterSchema = EXCLUDED.ParameterSchema,
    Description = EXCLUDED.Description,
    IsActive = TRUE,
    UpdatedAt = now();

INSERT INTO "CherryMon"."main"."dim_indicator_component" (
    IndicatorCode,
    ComponentCode,
    ComponentName,
    OutputPrefix,
    SortOrder,
    ValueSemantic,
    Unit,
    IsPrimary,
    IsActive
)
VALUES
    ('OBV', 'VALUE', 'On-Balance Volume', NULL, 1, 'CUMULATIVE_FLOW', 'VOLUME', TRUE, TRUE),
    ('AD',  'VALUE', 'Accumulation/Distribution Line', NULL, 1, 'CUMULATIVE_FLOW', 'VOLUME', TRUE, TRUE)
ON CONFLICT (IndicatorCode, ComponentCode) DO UPDATE SET
    ComponentName = EXCLUDED.ComponentName,
    OutputPrefix = EXCLUDED.OutputPrefix,
    SortOrder = EXCLUDED.SortOrder,
    ValueSemantic = EXCLUDED.ValueSemantic,
    Unit = EXCLUDED.Unit,
    IsPrimary = TRUE,
    IsActive = TRUE;

INSERT INTO "CherryMon"."main"."dim_indicator_config" (
    ConfigCode,
    IndicatorCode,
    Timeframe,
    Parameters,
    WarmupBars,
    IsEnabled,
    Description,
    UpdatedAt
)
VALUES
    ('OBV_D', 'OBV', 'D', '{}'::JSON, 1, TRUE, 'Cumulative full-history OBV daily.', now()),
    ('OBV_W', 'OBV', 'W', '{}'::JSON, 1, TRUE, 'Cumulative full-history OBV weekly.', now()),
    ('OBV_M', 'OBV', 'M', '{}'::JSON, 1, TRUE, 'Cumulative full-history OBV monthly.', now()),
    ('AD_D',  'AD',  'D', '{}'::JSON, 1, TRUE, 'Cumulative full-history AD Line daily.', now()),
    ('AD_W',  'AD',  'W', '{}'::JSON, 1, TRUE, 'Cumulative full-history AD Line weekly.', now()),
    ('AD_M',  'AD',  'M', '{}'::JSON, 1, TRUE, 'Cumulative full-history AD Line monthly.', now())
ON CONFLICT (ConfigCode) DO UPDATE SET
    IndicatorCode = EXCLUDED.IndicatorCode,
    Timeframe = EXCLUDED.Timeframe,
    Parameters = EXCLUDED.Parameters,
    WarmupBars = EXCLUDED.WarmupBars,
    IsEnabled = TRUE,
    Description = EXCLUDED.Description,
    UpdatedAt = now();
