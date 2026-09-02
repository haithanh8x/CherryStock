-- R/S V2.4 Source Effectiveness read-only preflight.
-- Run AFTER scripts/run_rs_v2_4_migration.py.
-- No DDL/DML.

-- 1. Required V2.4 tables.
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

-- Expected: 3 rows.

-- 2. Required V2.4 public view.
SELECT table_name
FROM information_schema.views
WHERE lower(table_catalog) = 'cherrymon'
  AND lower(table_schema) = 'main'
  AND lower(table_name) = 'vw_rs_source_effectiveness';

-- Expected: 1 row.

-- 3. V2.3 evaluation-run filter metadata added by V2.4.
SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE lower(table_catalog) = 'cherrymon'
  AND lower(table_schema) = 'main'
  AND lower(table_name) = 'cal_rs_evaluation_run'
  AND lower(column_name) IN (
      'includesourcekeysjson',
      'excludesourcekeysjson'
  )
ORDER BY column_name;

-- Expected: 2 VARCHAR columns.

-- 4. V2.4 baseline model registry.
SELECT
    "ModelVersion",
    "ParentVersion",
    "Status",
    "Signature",
    "CreatedAt"
FROM "CherryMon"."main"."dim_rs_model_version"
WHERE "ModelVersion" = 'RS_V2_4_BASELINE';

-- Expected: one row, Status=BASELINE.

-- 5. V2.3 historical evidence remains available.
SELECT
    COUNT(*) AS CompletedEvaluationRuns,
    COUNT(DISTINCT "ModelVersion") AS Models,
    MIN("DatasetStart") AS MinDatasetStart,
    MAX("DatasetEnd") AS MaxDatasetEnd
FROM "CherryMon"."main"."cal_rs_evaluation_run"
WHERE "Status" = 'COMPLETED';

-- 6. Historical events contain source lineage needed for LEVEL attribution.
SELECT
    COUNT(*) AS Events,
    SUM(CASE WHEN "SourcesJson" IS NULL THEN 1 ELSE 0 END) AS NullSourcesJson,
    SUM(CASE WHEN "SourceFamiliesJson" IS NULL THEN 1 ELSE 0 END) AS NullFamiliesJson,
    COUNT(DISTINCT "Ticker") AS Tickers
FROM "CherryMon"."main"."cal_rs_evaluation_event";

-- 7. Latest public view can be queried even before first V2.4 effectiveness run.
SELECT COUNT(*) AS LatestEffectivenessRows
FROM "CherryMon"."main"."vw_RS_Source_Effectiveness";

-- PASS criteria:
-- - all 3 V2.4 tables exist;
-- - vw_RS_Source_Effectiveness exists;
-- - both evaluation-run source-filter columns exist;
-- - RS_V2_4_BASELINE exists with Status=BASELINE;
-- - V2.3 completed runs/events remain queryable;
-- - public view query succeeds (0 rows is valid before first effectiveness run).
