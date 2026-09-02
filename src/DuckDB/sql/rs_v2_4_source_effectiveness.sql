-- R/S V2.4 Source Effectiveness & Indicator Promotion migration.
-- Execute manually/outside read-only MCP.
-- Additive and idempotent. No destructive DDL.

ALTER TABLE "CherryMon"."main"."cal_rs_evaluation_run"
    ADD COLUMN IF NOT EXISTS "IncludeSourceKeysJson" VARCHAR;

ALTER TABLE "CherryMon"."main"."cal_rs_evaluation_run"
    ADD COLUMN IF NOT EXISTS "ExcludeSourceKeysJson" VARCHAR;

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_rs_source_effectiveness_run" (
    "EffectivenessRunId" VARCHAR PRIMARY KEY,
    "ScopeType" VARCHAR NOT NULL,
    "SourceKey" VARCHAR NOT NULL,
    "SourceFamily" VARCHAR NOT NULL,
    "SourceRole" VARCHAR NOT NULL,
    "HorizonBars" INTEGER NOT NULL,
    "BaselineRunId" VARCHAR NOT NULL,
    "AblationRunId" VARCHAR NOT NULL,
    "StandaloneRunId" VARCHAR,
    "PolicyJson" VARCHAR NOT NULL,
    "Status" VARCHAR NOT NULL,
    "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "CompletedAt" TIMESTAMP,
    "Notes" VARCHAR
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_rs_source_effectiveness" (
    "EffectivenessRunId" VARCHAR NOT NULL,
    "Ticker" VARCHAR NOT NULL,
    "ScopeType" VARCHAR NOT NULL,
    "SourceKey" VARCHAR NOT NULL,
    "SourceFamily" VARCHAR NOT NULL,
    "SourceRole" VARCHAR NOT NULL,
    "HorizonBars" INTEGER NOT NULL,
    "AttributionMode" VARCHAR NOT NULL,
    "MarginalMetric" VARCHAR NOT NULL,
    "LineageEventCount" INTEGER,
    "ValidationEventCount" INTEGER,
    "TestEventCount" INTEGER,
    "TouchRate" DOUBLE,
    "HoldRateGivenTouch" DOUBLE,
    "BreakRateGivenTouch" DOUBLE,
    "RetestRateGivenBreak" DOUBLE,
    "DirectionalEdgePct" DOUBLE,
    "ValidationQuality" DOUBLE,
    "TestQuality" DOUBLE,
    "ValidationMarginalLift" DOUBLE,
    "TestMarginalLift" DOUBLE,
    "TemporalStability" DOUBLE,
    "RegimeStability" DOUBLE,
    "ComplexityDelta" DOUBLE,
    "EffectivenessScore" DOUBLE,
    "Recommendation" VARCHAR NOT NULL,
    "EvidenceJson" VARCHAR,
    "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (
        "EffectivenessRunId",
        "Ticker",
        "ScopeType",
        "SourceKey",
        "HorizonBars"
    )
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."sys_rs_source_promotion_audit" (
    "DecisionId" VARCHAR PRIMARY KEY,
    "EffectivenessRunId" VARCHAR NOT NULL,
    "SourceKey" VARCHAR NOT NULL,
    "SourceFamily" VARCHAR NOT NULL,
    "SourceRole" VARCHAR NOT NULL,
    "HorizonBars" INTEGER NOT NULL,
    "Outcome" VARCHAR NOT NULL,
    "TickerCount" INTEGER,
    "PositiveTickerCount" INTEGER,
    "PositiveTickerRatio" DOUBLE,
    "AvgEffectivenessScore" DOUBLE,
    "AvgValidationLift" DOUBLE,
    "AvgTestLift" DOUBLE,
    "AvgTemporalStability" DOUBLE,
    "AvgRegimeStability" DOUBLE,
    "MaxComplexityDelta" DOUBLE,
    "ReasonsJson" VARCHAR,
    "PolicyJson" VARCHAR NOT NULL,
    "Applied" BOOLEAN NOT NULL DEFAULT FALSE,
    "DecidedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "Notes" VARCHAR
);

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_RS_Source_Effectiveness" AS
WITH completed AS (
    SELECT
        e.*,
        r."CompletedAt",
        ROW_NUMBER() OVER (
            PARTITION BY
                e."Ticker",
                e."ScopeType",
                e."SourceKey",
                e."HorizonBars"
            ORDER BY
                r."CompletedAt" DESC NULLS LAST,
                e."EffectivenessRunId" DESC
        ) AS rn
    FROM "CherryMon"."main"."cal_rs_source_effectiveness" e
    INNER JOIN "CherryMon"."main"."cal_rs_source_effectiveness_run" r
        ON r."EffectivenessRunId" = e."EffectivenessRunId"
    WHERE r."Status" = 'COMPLETED'
)
SELECT
    "Ticker",
    "ScopeType",
    "SourceKey",
    "SourceFamily",
    "SourceRole",
    "HorizonBars",
    "AttributionMode",
    "MarginalMetric",
    "LineageEventCount",
    "ValidationEventCount",
    "TestEventCount",
    "TouchRate",
    "HoldRateGivenTouch",
    "BreakRateGivenTouch",
    "RetestRateGivenBreak",
    "DirectionalEdgePct",
    "ValidationQuality",
    "TestQuality",
    "ValidationMarginalLift",
    "TestMarginalLift",
    "TemporalStability",
    "RegimeStability",
    "ComplexityDelta",
    "EffectivenessScore",
    "Recommendation",
    "EvidenceJson",
    "EffectivenessRunId",
    "CompletedAt"
FROM completed
WHERE rn = 1;

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
    'RS_V2_4_BASELINE',
    'RS_V2_3_BASELINE',
    'BASELINE',
    'RUNTIME_DEFAULT_V24',
    '{"enabled_sources":["52W_HL","ATR","BB","MA","PREVIOUS_HL","RSI","SWING","VOLUME_PROFILE"],"included_source_keys":[],"excluded_source_keys":[]}',
    NULL,
    'V2.4 preserves V2.3 runtime behavior and adds Source Effectiveness research filters/governance.'
WHERE NOT EXISTS (
    SELECT 1
    FROM "CherryMon"."main"."dim_rs_model_version"
    WHERE "ModelVersion" = 'RS_V2_4_BASELINE'
);

-- Validation
SELECT table_name
FROM information_schema.tables
WHERE lower(table_catalog) = 'cherrymon'
  AND lower(table_schema) = 'main'
  AND lower(table_name) IN (
      'cal_rs_source_effectiveness_run',
      'cal_rs_source_effectiveness',
      'sys_rs_source_promotion_audit'
  )
ORDER BY table_name;

SELECT table_name
FROM information_schema.views
WHERE lower(table_catalog) = 'cherrymon'
  AND lower(table_schema) = 'main'
  AND lower(table_name) = 'vw_rs_source_effectiveness';

SELECT
    "ModelVersion",
    "ParentVersion",
    "Status"
FROM "CherryMon"."main"."dim_rs_model_version"
WHERE "ModelVersion" = 'RS_V2_4_BASELINE';
