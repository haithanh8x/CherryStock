---
id: REQ-0035
title: Yahoo VND=X Source-Specific OHLC Data Quality Policy
status: IMPLEMENTED_PENDING_VALIDATION
priority: P0
owner: BusinessAnalyst
primary_next_owner: TestEngineer
related:
  prerequisite:
    - docs/runbook/Yahoo_Raw_Other_EOD_Diagnostic.md
    - docs/reference/data/data_quality/yahoo_raw_other_eod/
  architecture:
    - docs/architecture/Yahoo_Source_Specific_DQ_Policy.md
  adr:
    - docs/adr/ADR-019-yahoo-vndx-source-specific-ohlc-dq-policy.md
  implementation:
    - src/Ults/DataQualityOrchestration.py
    - src/cherrystock/application/services/sync_write_pipeline.py
  test:
    - tests/test_yahoo_source_specific_dq_policy.py
    - tests/test_sync_write_pipeline_service.py
    - docs/runbook/Yahoo_VNDX_Source_Specific_DQ_Policy.md
---

# REQ-0035 — Yahoo VND=X Source-Specific OHLC Data Quality Policy

## Business Objective

Prevent recurrent upstream OHLC envelope anomalies from Yahoo's `VND=X` instrument from
rolling back the entire CherryStock core daily transaction, while preserving strict blocking
Data Quality behavior for all other Yahoo instruments and all non-OHLC integrity failures.

## Evidence / Problem Statement

The approved diagnostic established:

- Yahoo EOD scope: `DX-Y.NYB`, `BTC-USD`, `VND=X`, `GC=F`;
- 55 historical OHLC envelope violations exist in `raw_other_eod`;
- all 55 belong to `VND=X`;
- violations are material, not floating-point noise;
- fresh Yahoo historical refetch reproduces the invalid `VND=X` OHLC geometry;
- the 2026-09-22 blocker itself was transient because Yahoo later returned a clean row;
- raw source values must not be clamped or silently repaired.

The current generic validator has one blocking `invalid_ohlc_count` metric for the complete
Yahoo scope, so a single `VND=X` source anomaly aborts and rolls back the entire core daily UoW.

## Functional Requirements

1. Generic `validate_data_quality()` OHLC rules MUST remain unchanged.
2. Yahoo EOD MUST be validated through a dedicated source-specific orchestration wrapper.
3. Yahoo validation MUST still cover the complete configured Yahoo ticker scope in one validation event.
4. Current-date OHLC violations MUST be reconciled by ticker using the same envelope predicate as the generic validator.
5. OHLC violations attributable to `VND=X` MAY be downgraded from ERROR to WARNING.
6. OHLC violations for any other Yahoo ticker MUST remain blocking ERROR.
7. Any non-OHLC error affecting `VND=X` MUST remain blocking, including duplicates, required NULLs,
   invalid numeric/date values, negative prices where applicable, and freshness failures.
8. Raw Yahoo values MUST remain unchanged. The policy MUST NOT clamp, round, overwrite or delete OHLC.
9. Audit metrics MUST retain the original total `invalid_ohlc_count` and add:
   - `ohlc_policy`;
   - `ohlc_warning_tickers`;
   - `invalid_ohlc_warning_count`;
   - `invalid_ohlc_blocking_count`;
   - `invalid_ohlc_warning_symbols`;
   - `invalid_ohlc_blocking_symbols`;
   - `invalid_ohlc_by_symbol`.
10. A warning-only `VND=X` anomaly MUST persist audit status `WARNING` and allow the core daily UoW to continue.
11. Any blocking Yahoo error MUST persist audit status `FAIL` before orchestration raises.
12. The daily pipeline MUST use the new Yahoo-specific validator only for the Yahoo EOD stage;
    all other datasets continue using existing validators.
13. Existing mixed-calendar policy `check_count_anomalies=False` MUST remain in effect for Yahoo.
14. No database schema migration is required.
15. Existing diagnostic tooling remains read-only and is not replaced by this policy.

## Business Rules

- Warning ticker V1: `VND=X` only.
- Strict Yahoo OHLC tickers V1: `DX-Y.NYB`, `BTC-USD`, `GC=F`.
- The policy changes failure severity, not source values and not the OHLC predicate.
- If generic invalid count and per-symbol reconciliation disagree, validation MUST fail safe.
- If both `VND=X` and a strict Yahoo ticker are invalid on the same date:
  - `VND=X` anomaly is recorded as warning evidence;
  - strict ticker anomaly remains an error;
  - final status is `FAIL`.
- If `VND=X` has an OHLC warning plus another generic DQ error, final status is `FAIL`.
- The configured warning-ticker list must be a subset of Yahoo scope.

## Scope

### In Scope

- source-specific Yahoo EOD validator orchestration;
- per-symbol current-date OHLC reconciliation;
- warning/blocking audit split;
- daily pipeline integration;
- focused deterministic tests;
- runbook and durable architecture/ADR updates.

### Out of Scope

- changing Yahoo provider;
- replacing `VND=X` with another FX source;
- correcting historical Yahoo rows;
- clamping/normalizing OHLC;
- generic tolerance changes;
- database schema changes;
- changes to Movement/SmartMoney/Strategy semantics.

## Acceptance Criteria

### AC-01
Given only `VND=X` has a current-date OHLC envelope violation, Yahoo DQ returns `WARNING`
and does not raise when `raise_on_fail=True`.

### AC-02
The raw `VND=X` OHLC row is byte/value-equivalent before and after validation.

### AC-03
Audit metrics preserve `invalid_ohlc_count` and split the same count into warning and blocking totals.

### AC-04
Given a strict Yahoo ticker has an OHLC violation, Yahoo DQ returns/persists `FAIL` and raises.

### AC-05
Given both `VND=X` and a strict ticker are invalid, warning evidence for `VND=X` is retained
while the strict error blocks the pipeline.

### AC-06
Given `VND=X` has a duplicate key, final status remains `FAIL` even if its OHLC anomaly is warning-only.

### AC-07
Given a clean Yahoo date, final status remains `PASS`.

### AC-08
If per-symbol OHLC reconciliation does not equal generic `invalid_ohlc_count`, the validator fails.

### AC-09
The daily pipeline routes Yahoo through the Yahoo-specific validator and does not change validation routing for other stages.

### AC-10
Yahoo count-anomaly checks remain disabled for mixed calendars.

### AC-11
No code path mutates Yahoo OHLC to satisfy DQ.

### AC-12
Diagnostic evidence and policy decision are documented and traceable from requirement/ADR/runbook.

## Non-functional Requirements

- Reliability: fail-safe on reconciliation mismatch.
- Auditability: warning vs blocking OHLC counts/symbols must be persisted in existing JSON metrics.
- Compatibility: no audit schema migration and no generic validator behavior change.
- Testability: Yahoo validator is injectable in `SyncWritePipelineService`.
- Maintainability: source-specific policy lives in orchestration, not generic data rules.

## Dependencies

- diagnostic evidence commit `87d1e4074c7769c9bfa1679fe8b74be75a83d57d`;
- existing `validate_data_quality()`;
- existing `sys_data_quality_audit`;
- existing Yahoo scope `YAHOO_OTHER_TICKERS`.

## Risks

- Yahoo may later change `VND=X` behavior; warning policy must remain observable so it can be retired.
- Other Yahoo instruments may develop source anomalies; they remain blocking until separately evidenced/approved.
- A warning means source geometry is known-invalid; downstream consumers must not reinterpret warning as repaired data.

## Handoff

~~~text
Status: IMPLEMENTED_PENDING_VALIDATION
Primary next owner: TestEngineer
Acceptance criteria count: 12
Blocking questions: none
~~~
