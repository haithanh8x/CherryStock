# Runbook — REQ-0035 Yahoo VND=X Source-Specific DQ Policy

- Requirement: REQ-0035
- Architecture: docs/architecture/Yahoo_Source_Specific_DQ_Policy.md
- ADR: ADR-019
- Branch: feature/yahoo-vndx-source-specific-dq-policy
- Final validation owner: TestEngineer

## 1. Objective

Validate this exact severity contract:

~~~text
VND=X OHLC envelope anomaly
→ WARNING
→ raw values unchanged
→ daily pipeline continues

Other Yahoo OHLC anomaly
→ FAIL

Any other VND=X DQ failure
→ FAIL
~~~

Do not modify the generic OHLC predicate during validation.

## 2. Phase 0 — Sync Branch

~~~powershell
cd C:\Github\CherryStock
git status --short
git fetch origin
git switch feature/yahoo-vndx-source-specific-dq-policy
git pull origin feature/yahoo-vndx-source-specific-dq-policy
~~~

Preserve unrelated local changes.

## 3. Phase 1 — Compile + Focused Tests

~~~powershell
python -m compileall src\Ults\DataQualityOrchestration.py src\cherrystock\application\services\sync_write_pipeline.py

python -m pytest tests\test_yahoo_source_specific_dq_policy.py tests\test_sync_write_pipeline_service.py tests\test_data_validation.py tests\test_data_quality_orchestration.py tests\test_yahoo_eod_diagnostic.py -v
~~~

PASS requires all tests PASS.

Key assertions must prove:

- VND=X OHLC → WARNING;
- raw OHLC unchanged;
- strict ticker OHLC → FAIL;
- VND=X duplicate → FAIL;
- Yahoo routing uses dedicated validator;
- generic validator regression remains PASS.

## 4. Phase 2 — Reconfirm Diagnostic Evidence

~~~powershell
python scripts\diagnose_yahoo_raw_other_eod.py --allow-invalid
~~~

The latest date may now be CLEAN because the 2026-09-22 transient row was corrected by Yahoo.

The evidence basis for the policy is historical/reproducible VND=X behavior already committed under:

~~~text
docs/reference/data/data_quality/yahoo_raw_other_eod/
~~~

Do not require the current latest Yahoo row to be invalid in order to validate the deterministic policy tests.

## 5. Phase 3 — Clean-date Daily Yahoo Integration

Run the normal daily pipeline:

~~~powershell
python run.py
~~~

If current Yahoo data is clean, Yahoo DQ may return PASS.

Required result:

- the previous `raw_other_eod invalid_ohlc_count=1` blocker must not recur from an already-corrected Yahoo row;
- core pipeline reaches stages after Yahoo;
- if Movement is already current, Movement may NOOP;
- no new unrelated regression.

If Yahoo returns a fresh VND=X anomaly during this run, expected behavior is a Yahoo WARNING and continued core execution.

If any strict Yahoo ticker is invalid, FAIL remains correct and the runbook should STOP with evidence.

## 6. Phase 4 — Inspect Yahoo Audit

After a successfully committed daily run:

~~~sql
SELECT
    checked_at,
    pipeline_name,
    table_name,
    status,
    CAST(metrics AS VARCHAR) AS metrics,
    CAST(errors AS VARCHAR) AS errors,
    CAST(warnings AS VARCHAR) AS warnings
FROM "CherryMon"."main"."sys_data_quality_audit"
WHERE pipeline_name = 'Yahoo Finance EOD'
ORDER BY checked_at DESC
LIMIT 5;
~~~

For a clean date:

~~~text
status = PASS
invalid_ohlc_count = 0
~~~

For a VND=X warning date:

~~~text
status = WARNING
invalid_ohlc_count > 0
invalid_ohlc_warning_count > 0
invalid_ohlc_blocking_count = 0
invalid_ohlc_warning_symbols includes VND=X
errors = []
~~~

## 7. Phase 5 — Raw Preservation Check

No production test may alter OHLC to make it pass.

Use the deterministic unit test as the primary proof:

~~~powershell
python -m pytest tests\test_yahoo_source_specific_dq_policy.py -v
~~~

For any real warning row, compare stored values before/after validation if available.

## 8. Phase 6 — Daily Regression

~~~powershell
python -m pytest tests\test_sync_write_pipeline_service.py tests\test_run_daily_movement_integration.py -v
python scripts\validate_daily_movement.py
~~~

Expected:

- daily orchestration tests PASS;
- post-commit Movement architecture unchanged;
- Movement structural validation PASS.

## 9. Phase 7 — Archify

The high-level DQ node is updated to express source-aware severity policy.

~~~powershell
.\scripts\render_archify_cherrystock.ps1
~~~

PASS requires current showcase validation `ok=true`.

If repository revision is stale, update only the typed source revision according to
`docs/runbook/Archify_Generation_Guide.md`, then rerender. Do not hand-edit generated HTML.

## 10. Phase 8 — Evidence

If a real VND=X warning is observed, export bounded audit evidence under:

~~~text
docs/reference/data/data_quality/yahoo_vndx_policy/
~~~

If current Yahoo is clean, focused deterministic tests plus the existing historical diagnostic evidence are sufficient for this policy gate; do not wait indefinitely for another provider anomaly.

## 11. TestEngineer Verdict

~~~text
TEST VERDICT
Objective: REQ-0035 Yahoo VND=X Source-Specific OHLC DQ Policy
Validation depth: INTEGRATION VALIDATION

Compile/focused tests:
PASS | FAIL | BLOCKED

Diagnostic evidence:
PASS | FAIL | BLOCKED

Daily Yahoo integration:
PASS | FAIL | BLOCKED

Audit contract:
PASS | FAIL | BLOCKED

Raw preservation:
PASS | FAIL | BLOCKED

Daily/Movement regression:
PASS | FAIL | BLOCKED

Archify:
PASS | FAIL | BLOCKED

Verdict:
PASS | FAIL | BLOCKED | REGRESSION

Action:
KEEP | FIX_ONCE | REVERT | STOP

Evidence:
- generic OHLC predicate unchanged
- VND=X warning path deterministic PASS
- strict Yahoo OHLC blocking path deterministic PASS
- other VND=X DQ failures remain blocking

Residual risk:
- raw VND=X bars can remain geometrically invalid because source fidelity is preserved
~~~

## 12. STOP Rule

PASS → KEEP → STOP.

Do not broaden the warning list or change the generic OHLC rule during validation.
