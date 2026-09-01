---
applyTo: "**/*.py,**/*.sql"
---

# Database / DuckDB Instructions

This file is the owner of CherryStock database-access, SQL, transaction and data-quality rules.

## Connection policy
- Do not call `duckdb.connect()` / `duckdb.close()` directly in normal application workflow.
- Read-side access: prefer short-lived read-only connections using `DuckDBManager(read_only=True)` when supported by the module.
- Write workflows that span multiple steps and must be atomic: prefer one writer transaction through `DuckDBConnectionFactory` + `DuckDBUnitOfWork` and pass the same connection/repository through the workflow.
- `DuckDBManager.get_connection(...)` / `close_connection(...)` are legacy compatibility patterns only; do not introduce new usages unless required by an unchanged legacy interface.
- Reuse `executeDuckSQL()` for SQL script execution and `returnSQL()` for existing query-helper patterns.

## SQL rules
- Use explicit column lists; avoid `SELECT *` in application/query contracts.
- Prefer set-based/batch operations over query-in-loop patterns.
- Do not hard-code environment-specific DuckDB paths; use project settings/configuration.
- Multi-step writes that must be consistent belong in one transaction.
- Update/upsert workflows should be idempotent where practical.

## Object naming
- `raw_*` raw/source data.
- `cal_*` calculated/internal persistence.
- `dim_*` dimensions/configuration/master data.
- `vw_*` read/public/query views.
- `sys_*` operations, monitoring and audit.

## Data quality
Use `Ults.DataValidation.validate_data_quality()` when the dataset fits its contract.

Rules:
- validation itself is read-only and must not repair/mutate source data;
- persistence of validation results is a separate orchestration/helper responsibility;
- persist PASS, WARNING and FAIL to `"CherryMon"."main"."sys_data_quality_audit"` when the pipeline uses audit persistence;
- WARNING normally does not block; FAIL must be persisted/logged before orchestration decides to raise;
- use CherryStock trading calendar (`dimCalendar` or existing helper) rather than weekday-only assumptions;
- pass dataset-specific `date_col`, `symbol_col`, `key_cols`, `required_cols` instead of duplicating validators;
- rolling indicator columns with legitimate warmup NULLs must use optional-null-rate handling instead of strict required-column thresholds.

## Generated database context for AI
- `docs/reference/DB_Metadata.md`: generated database object/column/type/nullability/default reference.
- `docs/reference/dim_indicator.parquet`: current indicator master definitions.
- `docs/reference/dim_indicator_component.parquet`: current indicator output-component mappings.
- `docs/reference/dim_indicator_config.parquet`: current executable parameter/timeframe configurations.

For database or indicator work, AI agents must read `DB_Metadata.md` first for structure, then load the relevant Parquet snapshots for current dimension values. Join the snapshots by `IndicatorCode`; use `ConfigId` for calculated-value relationships and `ComponentCode` for component relationships.

These four files are one generated reference set produced by `Ults.DuckLib.exportDuckDB_metadata()`. Do not infer current dimension values from the Markdown schema alone.

## Validation before database changes
Confirm:
- read vs write intent;
- transaction boundary;
- expected key / uniqueness constraint;
- rerun behavior and duplicate risk;
- before/after row counts where relevant;
- failure behavior and rollback expectations;
- impact on public views / downstream consumers.

Related references:
- `docs/reference/DB_Metadata.md`
- `docs/adr/ADR-001-duckdb-connection.md`