-- ZigZag research/calibration persistence for V1.1, V1.2 and V2.
-- Additive/idempotent. These tables are research evidence, not production pivot SSOT.

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_zigzag_deviation_evaluation" (
    CalibrationVersion VARCHAR NOT NULL,
    Ticker VARCHAR NOT NULL,
    SplitName VARCHAR NOT NULL,
    DeviationPct DOUBLE NOT NULL,
    SourceBars BIGINT NOT NULL,
    PivotCount BIGINT NOT NULL,
    SwingCount BIGINT NOT NULL,
    PivotDensityPer100Bars DOUBLE NOT NULL,
    MedianSwingBars DOUBLE NOT NULL,
    MedianAbsSwingPct DOUBLE NOT NULL,
    ShortSwingRate DOUBLE NOT NULL,
    StructuralValid BOOLEAN NOT NULL,
    IsEligible BOOLEAN NOT NULL,
    CalibrationScore DOUBLE NOT NULL,
    EvaluatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (CalibrationVersion, Ticker, SplitName, DeviationPct),
    CHECK (SplitName IN ('TRAIN', 'VALIDATION', 'TEST')),
    CHECK (DeviationPct > 0 AND DeviationPct < 1)
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."dim_zigzag_ticker_config" (
    CalibrationVersion VARCHAR NOT NULL,
    Ticker VARCHAR NOT NULL,
    Timeframe VARCHAR NOT NULL,
    BaseDeviationPct DOUBLE NOT NULL,
    SelectionMethod VARCHAR NOT NULL,
    TrainScore DOUBLE NOT NULL,
    ValidationScore DOUBLE NOT NULL,
    TestScore DOUBLE NOT NULL,
    Status VARCHAR NOT NULL DEFAULT 'RECOMMENDED',
    IsActive BOOLEAN NOT NULL DEFAULT FALSE,
    EffectiveFrom DATE,
    EffectiveTo DATE,
    UpdatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (CalibrationVersion, Ticker, Timeframe),
    CHECK (Timeframe = 'D'),
    CHECK (BaseDeviationPct > 0 AND BaseDeviationPct < 1),
    CHECK (Status IN ('RECOMMENDED', 'PILOT_APPROVED', 'REJECTED'))
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_zigzag_pilot_evaluation" (
    PilotVersion VARCHAR NOT NULL,
    CalibrationVersion VARCHAR NOT NULL,
    Ticker VARCHAR NOT NULL,
    BaselineDeviationPct DOUBLE NOT NULL,
    CalibratedDeviationPct DOUBLE NOT NULL,
    BaselineSwingCount BIGINT NOT NULL,
    CalibratedSwingCount BIGINT NOT NULL,
    BaselinePivotDensity DOUBLE NOT NULL,
    CalibratedPivotDensity DOUBLE NOT NULL,
    BaselineMedianSwingBars DOUBLE NOT NULL,
    CalibratedMedianSwingBars DOUBLE NOT NULL,
    BaselineMedianAbsSwingPct DOUBLE NOT NULL,
    CalibratedMedianAbsSwingPct DOUBLE NOT NULL,
    BaselineShortSwingRate DOUBLE NOT NULL,
    CalibratedShortSwingRate DOUBLE NOT NULL,
    BaselineStructuralValid BOOLEAN NOT NULL,
    CalibratedStructuralValid BOOLEAN NOT NULL,
    BaselineScore DOUBLE NOT NULL,
    CalibratedScore DOUBLE NOT NULL,
    Decision VARCHAR NOT NULL,
    EvaluatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (PilotVersion, Ticker),
    CHECK (Decision IN (
        'BASELINE_SUFFICIENT',
        'KEEP_5_BASELINE',
        'PROMOTE_CALIBRATED'
    ))
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_zigzag_regime_evaluation" (
    RegimeVersion VARCHAR NOT NULL,
    CalibrationVersion VARCHAR NOT NULL,
    Ticker VARCHAR NOT NULL,
    BaseDeviationPct DOUBLE NOT NULL,
    StaticSwingCount BIGINT NOT NULL,
    RegimeSwingCount BIGINT NOT NULL,
    StaticShortSwingRate DOUBLE NOT NULL,
    RegimeShortSwingRate DOUBLE NOT NULL,
    StaticMedianSwingBars DOUBLE NOT NULL,
    RegimeMedianSwingBars DOUBLE NOT NULL,
    StaticMedianAbsSwingPct DOUBLE NOT NULL,
    RegimeMedianAbsSwingPct DOUBLE NOT NULL,
    StaticStructuralValid BOOLEAN NOT NULL,
    RegimeStructuralValid BOOLEAN NOT NULL,
    StaticScore DOUBLE NOT NULL,
    RegimeScore DOUBLE NOT NULL,
    LowVolBars BIGINT NOT NULL,
    NormalBars BIGINT NOT NULL,
    HighVolBars BIGINT NOT NULL,
    EvaluatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (RegimeVersion, Ticker)
);

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_ZigZag_Ticker_Config" AS
SELECT
    CalibrationVersion,
    Ticker,
    Timeframe,
    BaseDeviationPct,
    SelectionMethod,
    TrainScore,
    ValidationScore,
    TestScore,
    Status,
    IsActive,
    EffectiveFrom,
    EffectiveTo,
    UpdatedAt
FROM "CherryMon"."main"."dim_zigzag_ticker_config";

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_ZigZag_Calibration" AS
SELECT
    CalibrationVersion,
    Ticker,
    SplitName,
    DeviationPct,
    SourceBars,
    PivotCount,
    SwingCount,
    PivotDensityPer100Bars,
    MedianSwingBars,
    MedianAbsSwingPct,
    ShortSwingRate,
    StructuralValid,
    IsEligible,
    CalibrationScore,
    EvaluatedAt
FROM "CherryMon"."main"."cal_zigzag_deviation_evaluation";

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_ZigZag_Pilot" AS
SELECT
    PilotVersion,
    CalibrationVersion,
    Ticker,
    BaselineDeviationPct,
    CalibratedDeviationPct,
    BaselineSwingCount,
    CalibratedSwingCount,
    BaselineShortSwingRate,
    CalibratedShortSwingRate,
    BaselineMedianSwingBars,
    CalibratedMedianSwingBars,
    BaselineScore,
    CalibratedScore,
    Decision,
    EvaluatedAt
FROM "CherryMon"."main"."cal_zigzag_pilot_evaluation";

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_ZigZag_Regime_Evaluation" AS
SELECT
    RegimeVersion,
    CalibrationVersion,
    Ticker,
    BaseDeviationPct,
    StaticSwingCount,
    RegimeSwingCount,
    StaticShortSwingRate,
    RegimeShortSwingRate,
    StaticMedianSwingBars,
    RegimeMedianSwingBars,
    StaticMedianAbsSwingPct,
    RegimeMedianAbsSwingPct,
    StaticStructuralValid,
    RegimeStructuralValid,
    StaticScore,
    RegimeScore,
    LowVolBars,
    NormalBars,
    HighVolBars,
    EvaluatedAt
FROM "CherryMon"."main"."cal_zigzag_regime_evaluation";
