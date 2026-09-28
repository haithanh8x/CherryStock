# Yahoo Source-Specific Data Quality Policy

- **Requirement:** REQ-0035
- **Status:** IMPLEMENTED_PENDING_VALIDATION
- **Decision:** ADR-019
- **Runtime owner:** src/Ults/DataQualityOrchestration.py
- **Generic rule owner:** src/Ults/DataValidation.py
- **Daily caller:** src/cherrystock/application/services/sync_write_pipeline.py
- **Target table:** raw_other_eod

## 1. Purpose

CherryStock must distinguish between:

1. **data integrity rules** — what constitutes invalid OHLC geometry; and
2. **source-specific failure policy** — whether a known upstream anomaly should block the whole pipeline.

REQ-0035 changes only the second concern for Yahoo `VND=X`.

## 2. Responsibility Boundary

~~~text
DataValidation.validate_data_quality()
        │
        │ owns generic facts:
        │ invalid_ohlc_count
        │ duplicates / NULL / numeric / freshness / negative values
        ↓
DataQualityOrchestration.validate_and_persist_yahoo_eod_quality()
        │
        │ owns Yahoo source policy:
        │ split invalid OHLC by ticker
        │ VND=X → warning
        │ all others → blocking
        ↓
sys_data_quality_audit
        ↓
SyncWritePipelineService
        │
        ├─ PASS / WARNING → continue
        └─ FAIL → raise → core UoW rollback
~~~

Generic validation does not know that `VND=X` is exceptional.

## 3. Source of Truth

### Generic OHLC validity

Owned by:

~~~text
src/Ults/DataValidation.py
~~~

Predicate remains:

~~~text
High < Low
OR High < Open
OR High < Close
OR Low > Open
OR Low > Close
~~~

### Yahoo severity policy

Owned by:

~~~text
src/Ults/DataQualityOrchestration.py
YAHOO_OHLC_WARNING_TICKERS = ("VND=X",)
validate_and_persist_yahoo_eod_quality()
~~~

### Source values

Owned by:

~~~text
raw_other_eod
~~~

The policy never mutates source values.

## 4. Validation Flow

~~~text
raw_other_eod
    ↓ filter configured Yahoo scope
temporary Yahoo validation view
    ↓
validate_data_quality(
    check_count_anomalies=False
)
    ↓
generic result
    │
    ├─ invalid_ohlc_count = 0
    │      → unchanged PASS/FAIL semantics
    │
    └─ invalid_ohlc_count > 0
           ↓
       exact same OHLC predicate
       GROUP BY Ticker
           ↓
       reconcile total
           │
           ├─ VND=X count
           │      → warning bucket
           │
           └─ all other tickers
                  → blocking bucket
           ↓
       recompute status
           ↓
       persist one audit event
           ↓
       raise only if final status = FAIL
~~~

## 5. Fail-Safe Reconciliation

The generic total and per-symbol breakdown must match:

~~~text
sum(invalid_ohlc_by_symbol.values())
==
invalid_ohlc_count
~~~

If not, the wrapper adds a blocking reconciliation error.

No anomaly may silently disappear during severity transformation.

## 6. Audit Contract

Existing `sys_data_quality_audit` schema is reused.

Detailed policy evidence is stored in the existing metrics JSON:

~~~text
ohlc_policy = YAHOO_SOURCE_SPECIFIC_V1
ohlc_warning_tickers = ["VND=X"]

invalid_ohlc_count
invalid_ohlc_warning_count
invalid_ohlc_blocking_count

invalid_ohlc_warning_symbols
invalid_ohlc_blocking_symbols
invalid_ohlc_by_symbol
~~~

Examples:

### VND=X only

~~~text
invalid_ohlc_count=1
warning_count=1
blocking_count=0
status=WARNING
~~~

### VND=X + GC=F

~~~text
invalid_ohlc_count=2
warning_count=1
blocking_count=1
status=FAIL
~~~

## 7. Non-OHLC Failures

The wrapper removes only the generic error string representing `invalid_ohlc_count` so it can
replace that one severity using per-symbol evidence.

All other generic errors remain untouched.

Therefore:

~~~text
VND=X duplicate       → FAIL
VND=X required NULL   → FAIL
VND=X invalid numeric → FAIL
VND=X stale dataset   → FAIL
VND=X OHLC anomaly    → WARNING
~~~

## 8. Mixed Calendar

Existing Yahoo behavior remains:

~~~text
check_count_anomalies=False
~~~

The policy does not block merely because weekend/weekday symbol counts differ.

Freshness, duplicates, required fields, numeric validity and OHLC checks still run.

## 9. Daily Integration

Before:

~~~text
SyncWritePipelineService
→ validate_and_persist_data_quality(Yahoo scope)
~~~

After:

~~~text
SyncWritePipelineService
→ validate_and_persist_yahoo_eod_quality(Yahoo scope)
~~~

All non-Yahoo stages continue using their existing validators.

No run.py ordering change is required.

## 10. Transaction Semantics

Yahoo validation still runs inside the Phase A shared core UoW.

~~~text
Yahoo warning only
    → no raise
    → core pipeline continues
    → audit commits if later stages succeed

Yahoo blocking error
    → audit result written in current transaction
    → raise
    → shared UoW rolls back
~~~

The existing audit rollback caveat remains: a FAIL audit written in the same failed transaction
may roll back with the UoW. Diagnostic scripts remain necessary for failed-source evidence.

## 11. Compatibility / Migration

No schema migration.

No backfill.

No historical raw-data rewrite.

No generic validation change.

Only daily Yahoo orchestration routing changes.

Rollback is code-only:

~~~text
restore Yahoo stage to validate_and_persist_data_quality()
~~~

## 12. Validation Strategy

Minimum evidence:

- unit test: VND=X OHLC anomaly → WARNING;
- raw values unchanged;
- audit metrics split correctly;
- strict Yahoo ticker anomaly → FAIL;
- VND=X duplicate + OHLC anomaly → FAIL;
- pipeline routing test uses dedicated Yahoo validator;
- existing DataValidation/DataQuality tests regress cleanly;
- diagnostic evidence remains available;
- current Yahoo daily run can progress when only VND=X OHLC anomaly occurs;
- high-level Archify remains synchronized.

## 13. Handoff

~~~text
DESIGN HANDOFF
Requirement: REQ-0035
Outcome: IMPLEMENTED_PENDING_VALIDATION
ADR: docs/adr/ADR-019-yahoo-vndx-source-specific-ohlc-dq-policy.md
Affected runtime:
- src/Ults/DataQualityOrchestration.py
- src/cherrystock/application/services/sync_write_pipeline.py
Migration: none
Raw mutation: forbidden
Next owner: TestEngineer
~~~
