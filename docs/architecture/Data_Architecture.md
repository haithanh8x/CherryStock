# CherryStock Data Architecture

## Purpose
High-level map of CherryStock data layers and data-contract ownership.

## Layer model

```text
External Sources
      ↓
Crawler / Import
      ↓
raw_*                source/raw datasets
      ↓
Validation
      ↓
cal_* / dim_*        calculated + master/config data
      ↓
vw_*                 consumer-oriented read contracts
      ↓
Chart / Screener / API / Analytics / ML

sys_*                operational audit / monitoring
```

## Core principles
- `raw_*` preserves normalized source facts as close to source semantics as practical.
- `dim_*` owns dimensions, metadata and executable configuration.
- `cal_*` is calculated/internal persistence and is not automatically the preferred public contract.
- `vw_*` should expose stable consumer-oriented contracts when a public read layer is needed.
- `sys_*` stores operational/audit history and must not replace validation of source data.
- Write workflows requiring atomicity should share one writer transaction.
- Data pipelines should be idempotent and explicit about logical keys.

## Database access policy
See [[../../.github/instructions/database.instructions|Database Instructions]].

## Metadata reference
See [[../../.github/agents/DB_Metadata|DB Metadata]].

## Related architecture
- [[Indicator_Engine|Indicator Engine]]
- [[../adr/ADR-001-duckdb-connection|ADR-001 DuckDB Connection]]
- [[../00_HOME|Knowledge Home]]