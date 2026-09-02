-- R/S V2.3 evaluation/model-governance migration.
-- Execute manually against CherryMon before running V2.3 persistence workflows.
-- Idempotent CREATE TABLE IF NOT EXISTS only. No destructive DDL.

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."dim_rs_model_version" (
    "ModelVersion" VARCHAR PRIMARY KEY,
    "ParentVersion" VARCHAR,
    "Status" VARCHAR NOT NULL,
    "Signature" VARCHAR NOT NULL,
    "ConfigJson" VARCHAR NOT NULL,
    "ComplexityScore" DOUBLE,
    "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "PromotedAt" TIMESTAMP,
    "Notes" VARCHAR
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_rs_evaluation_run" (
    "EvaluationRunId" VARCHAR PRIMARY KEY,
    "ModelVersion" VARCHAR NOT NULL,
    "DatasetStart" DATE,
    "DatasetEnd" DATE,
    "HorizonBars" INTEGER NOT NULL,
    "TickerCount" INTEGER,
    "SnapshotCount" INTEGER,
    "SplitConfigJson" VARCHAR,
    "Status" VARCHAR NOT NULL,
    "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "CompletedAt" TIMESTAMP,
    "Notes" VARCHAR
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_rs_evaluation_event" (
    "EvaluationRunId" VARCHAR NOT NULL,
    "ModelVersion" VARCHAR NOT NULL,
    "Ticker" VARCHAR NOT NULL,
    "AsOfDate" DATE NOT NULL,
    "LevelRank" VARCHAR NOT NULL,
    "LevelType" VARCHAR NOT NULL,
    "LevelPrice" DOUBLE NOT NULL,
    "StrengthScore" DOUBLE,
    "HorizonEndDate" DATE,
    "Touched" BOOLEAN,
    "TouchDate" DATE,
    "Broken" BOOLEAN,
    "BreakDate" DATE,
    "Retested" BOOLEAN,
    "RetestDate" DATE,
    "Held" BOOLEAN,
    "BarsToTouch" INTEGER,
    "MaxFavorablePct" DOUBLE,
    "MaxAdversePct" DOUBLE,
    "SourceCount" INTEGER,
    "SourceFamilyCount" INTEGER,
    "SourcesJson" VARCHAR,
    "SourceFamiliesJson" VARCHAR,
    "Regime" VARCHAR,
    "Split" VARCHAR,
    "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("EvaluationRunId", "Ticker", "AsOfDate", "LevelRank")
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_rs_evaluation_metric" (
    "EvaluationRunId" VARCHAR NOT NULL,
    "ScopeType" VARCHAR NOT NULL,
    "ScopeKey" VARCHAR NOT NULL,
    "MetricCode" VARCHAR NOT NULL,
    "MetricValue" DOUBLE,
    "SampleSize" INTEGER,
    "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("EvaluationRunId", "ScopeType", "ScopeKey", "MetricCode")
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."sys_rs_model_promotion_audit" (
    "DecisionId" VARCHAR PRIMARY KEY,
    "BaselineVersion" VARCHAR NOT NULL,
    "ChallengerVersion" VARCHAR NOT NULL,
    "EvaluationRunId" VARCHAR,
    "Promote" BOOLEAN NOT NULL,
    "ValidationQualityDelta" DOUBLE,
    "TestQualityDelta" DOUBLE,
    "ComplexityDelta" DOUBLE,
    "WorstRegimeDelta" DOUBLE,
    "ReasonsJson" VARCHAR,
    "PolicyJson" VARCHAR,
    "DecidedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "Notes" VARCHAR
);

-- Seed/ensure the V2.3 baseline registry entry only if absent.
INSERT INTO "CherryMon"."main"."dim_rs_model_version" (
    "ModelVersion",
    "ParentVersion",
    "Status",
    "Signature",
    "ConfigJson",
    "ComplexityScore",
    "Notes"
)
SELECT
    'RS_V2_3_BASELINE',
    'RS_V2_2_PROD',
    'PRODUCTION',
    'RUNTIME_DEFAULT',
    '{"enabled_sources":["52W_HL","ATR","BB","MA","PREVIOUS_HL","RSI","SWING","VOLUME_PROFILE"]}',
    NULL,
    'V2.3 baseline keeps V2.2 runtime behavior and adds evaluation/model-governance contracts.'
WHERE NOT EXISTS (
    SELECT 1
    FROM "CherryMon"."main"."dim_rs_model_version"
    WHERE "ModelVersion" = 'RS_V2_3_BASELINE'
);

-- Validation.
SELECT
    "ModelVersion",
    "ParentVersion",
    "Status",
    "Signature",
    "CreatedAt"
FROM "CherryMon"."main"."dim_rs_model_version"
WHERE "ModelVersion" = 'RS_V2_3_BASELINE';

SELECT
    table_name
FROM information_schema.tables
WHERE table_catalog = 'CherryMon'
  AND table_schema = 'main'
  AND table_name IN (
      'dim_rs_model_version',
      'cal_rs_evaluation_run',
      'cal_rs_evaluation_event',
      'cal_rs_evaluation_metric',
      'sys_rs_model_promotion_audit'
  )
ORDER BY table_name;
