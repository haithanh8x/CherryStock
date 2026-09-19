-- ZigZag Swing Engine MWG MVP
-- Additive/idempotent. Event-first persistence only.

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."dim_zigzag_config" (
    ConfigId BIGINT NOT NULL,
    ConfigCode VARCHAR NOT NULL,
    ModelVersion VARCHAR NOT NULL,
    Timeframe VARCHAR NOT NULL,
    DeviationPct DOUBLE NOT NULL,
    PivotPriceSource VARCHAR NOT NULL,
    ConfirmationPriceSource VARCHAR NOT NULL,
    MinimumSwingBars INTEGER NOT NULL,
    EffectiveFrom DATE NOT NULL DEFAULT DATE '2000-01-01',
    EffectiveTo DATE,
    IsEnabled BOOLEAN NOT NULL DEFAULT TRUE,
    CreatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ConfigId),
    UNIQUE (ConfigCode),
    CHECK (Timeframe IN ('D')),
    CHECK (DeviationPct > 0 AND DeviationPct < 1),
    CHECK (MinimumSwingBars >= 1),
    CHECK (PivotPriceSource = 'HIGH_LOW'),
    CHECK (ConfirmationPriceSource = 'CLOSE')
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_zigzag_pivot" (
    ConfigId BIGINT NOT NULL,
    Ticker VARCHAR NOT NULL,
    PivotSeq BIGINT NOT NULL,
    PivotType VARCHAR NOT NULL,
    PivotDate DATE NOT NULL,
    PivotPrice DOUBLE NOT NULL,
    ConfirmedAtDate DATE NOT NULL,
    ConfirmationPrice DOUBLE NOT NULL,
    DeviationPct DOUBLE NOT NULL,
    CalculatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ConfigId, Ticker, PivotSeq),
    UNIQUE (ConfigId, Ticker, PivotDate, PivotType),
    CHECK (PivotType IN ('HIGH', 'LOW')),
    CHECK (PivotDate < ConfirmedAtDate),
    CHECK (PivotPrice > 0),
    CHECK (ConfirmationPrice > 0),
    CHECK (DeviationPct > 0 AND DeviationPct < 1)
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_zigzag_current_leg" (
    ConfigId BIGINT NOT NULL,
    Ticker VARCHAR NOT NULL,
    AsOfDate DATE NOT NULL,
    Direction VARCHAR,
    StartPivotSeq BIGINT,
    StartPivotDate DATE,
    StartPivotPrice DOUBLE,
    CandidatePivotType VARCHAR,
    CandidatePivotDate DATE,
    CandidatePivotPrice DOUBLE,
    LastClose DOUBLE NOT NULL,
    CurrentMovePct DOUBLE,
    ReversalFromCandidatePct DOUBLE,
    Status VARCHAR NOT NULL,
    CalculatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ConfigId, Ticker),
    CHECK (Direction IS NULL OR Direction IN ('UP', 'DOWN')),
    CHECK (CandidatePivotType IS NULL OR CandidatePivotType IN ('HIGH', 'LOW')),
    CHECK (Status IN ('PROVISIONAL', 'TRANSITION')),
    CHECK (StartPivotPrice IS NULL OR StartPivotPrice > 0),
    CHECK (CandidatePivotPrice IS NULL OR CandidatePivotPrice > 0),
    CHECK (LastClose > 0)
);

INSERT INTO "CherryMon"."main"."dim_zigzag_config" (
    ConfigId,
    ConfigCode,
    ModelVersion,
    Timeframe,
    DeviationPct,
    PivotPriceSource,
    ConfirmationPriceSource,
    MinimumSwingBars,
    EffectiveFrom,
    EffectiveTo,
    IsEnabled,
    UpdatedAt
)
VALUES (
    1,
    'ZZ_D_5_MVP',
    'MVP1',
    'D',
    0.05,
    'HIGH_LOW',
    'CLOSE',
    1,
    DATE '2000-01-01',
    NULL,
    TRUE,
    CURRENT_TIMESTAMP
)
ON CONFLICT (ConfigId) DO UPDATE SET
    ConfigCode = EXCLUDED.ConfigCode,
    ModelVersion = EXCLUDED.ModelVersion,
    Timeframe = EXCLUDED.Timeframe,
    DeviationPct = EXCLUDED.DeviationPct,
    PivotPriceSource = EXCLUDED.PivotPriceSource,
    ConfirmationPriceSource = EXCLUDED.ConfirmationPriceSource,
    MinimumSwingBars = EXCLUDED.MinimumSwingBars,
    EffectiveFrom = EXCLUDED.EffectiveFrom,
    EffectiveTo = EXCLUDED.EffectiveTo,
    IsEnabled = EXCLUDED.IsEnabled,
    UpdatedAt = EXCLUDED.UpdatedAt;

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Ticker_ZigZag_Pivots" AS
SELECT
    p.ConfigId,
    c.ConfigCode,
    c.ModelVersion,
    c.Timeframe,
    c.DeviationPct,
    p.Ticker,
    p.PivotSeq,
    p.PivotType,
    p.PivotDate,
    p.PivotPrice,
    p.ConfirmedAtDate,
    p.ConfirmationPrice,
    p.CalculatedAt
FROM "CherryMon"."main"."cal_zigzag_pivot" AS p
INNER JOIN "CherryMon"."main"."dim_zigzag_config" AS c
    ON c.ConfigId = p.ConfigId
WHERE c.IsEnabled = TRUE
  AND p.PivotDate >= c.EffectiveFrom
  AND (c.EffectiveTo IS NULL OR p.PivotDate <= c.EffectiveTo);

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Ticker_ZigZag_Swings" AS
WITH ordered AS (
    SELECT
        p.ConfigId,
        c.ConfigCode,
        c.ModelVersion,
        c.Timeframe,
        c.DeviationPct,
        p.Ticker,
        p.PivotSeq,
        p.PivotType,
        p.PivotDate,
        p.PivotPrice,
        p.ConfirmedAtDate,
        LAG(p.PivotSeq) OVER (
            PARTITION BY p.ConfigId, p.Ticker
            ORDER BY p.PivotSeq
        ) AS StartPivotSeq,
        LAG(p.PivotType) OVER (
            PARTITION BY p.ConfigId, p.Ticker
            ORDER BY p.PivotSeq
        ) AS StartPivotType,
        LAG(p.PivotDate) OVER (
            PARTITION BY p.ConfigId, p.Ticker
            ORDER BY p.PivotSeq
        ) AS StartDate,
        LAG(p.PivotPrice) OVER (
            PARTITION BY p.ConfigId, p.Ticker
            ORDER BY p.PivotSeq
        ) AS StartPrice
    FROM "CherryMon"."main"."cal_zigzag_pivot" AS p
    INNER JOIN "CherryMon"."main"."dim_zigzag_config" AS c
        ON c.ConfigId = p.ConfigId
    WHERE c.IsEnabled = TRUE
)
SELECT
    ConfigId,
    ConfigCode,
    ModelVersion,
    Timeframe,
    DeviationPct,
    Ticker,
    PivotSeq - 1 AS SwingSeq,
    CASE
        WHEN StartPivotType = 'LOW' AND PivotType = 'HIGH' THEN 'UP'
        WHEN StartPivotType = 'HIGH' AND PivotType = 'LOW' THEN 'DOWN'
        ELSE NULL
    END AS Direction,
    StartPivotSeq,
    StartPivotType,
    StartDate,
    StartPrice,
    PivotSeq AS EndPivotSeq,
    PivotType AS EndPivotType,
    PivotDate AS EndDate,
    PivotPrice AS EndPrice,
    ConfirmedAtDate,
    PivotPrice / StartPrice - 1.0 AS SwingPct,
    DATEDIFF('day', StartDate, PivotDate) AS CalendarDays
FROM ordered
WHERE StartPivotType IS NOT NULL
  AND (
      (StartPivotType = 'LOW' AND PivotType = 'HIGH')
      OR
      (StartPivotType = 'HIGH' AND PivotType = 'LOW')
  );

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Ticker_ZigZag_Current" AS
SELECT
    x.ConfigId,
    c.ConfigCode,
    c.ModelVersion,
    c.Timeframe,
    c.DeviationPct,
    x.Ticker,
    x.AsOfDate,
    x.Direction,
    x.StartPivotSeq,
    x.StartPivotDate,
    x.StartPivotPrice,
    x.CandidatePivotType,
    x.CandidatePivotDate,
    x.CandidatePivotPrice,
    x.LastClose,
    x.CurrentMovePct,
    x.ReversalFromCandidatePct,
    x.Status,
    x.CalculatedAt
FROM "CherryMon"."main"."cal_zigzag_current_leg" AS x
INNER JOIN "CherryMon"."main"."dim_zigzag_config" AS c
    ON c.ConfigId = x.ConfigId
WHERE c.IsEnabled = TRUE;
