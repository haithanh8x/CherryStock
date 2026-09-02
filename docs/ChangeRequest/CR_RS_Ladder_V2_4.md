# CR_RS_Ladder_V2_4

## 1. Change Summary

- **Change ID:** CR-RS-V2.4-20260902
- **Release:** R/S Ladder V2.4
- **Title:** Source Effectiveness & Indicator Promotion Framework
- **Date:** 2026-09-02
- **Status:** PRODUCTION DEPLOYED / VALIDATED
- **Final Verdict:** PASS
- **Action:** KEEP
- **Requirement:** REQ-0022
- **Architecture:** docs/architecture/RS_Source_Effectiveness.md
- **ADR:** docs/adr/ADR-008-rs-v2-4-source-effectiveness-promotion.md
- **Test runbook:** tests/test_R_S_V2_4.md
- **Pull Request:** PR #8
- **Merge commit:** `45a7324825afc0e2d32a166a90dcbc17fe5fb1ac`
- **Production date:** 2026-09-02

## 2. Objective

R/S V2.4 adds historical source-level evidence and promotion governance so CherryStock can decide whether an indicator/source should be considered for R/S integration using reproducible out-of-sample evidence rather than runtime Strength alone.

Core distinction:

```text
Runtime Strength
    !=
Source Effectiveness
    !=
Model Promotion Gate
    !=
Source Promotion Gate
```

## 3. Scope Delivered

### Source Effectiveness

- per ticker;
- per source/config;
- per source family;
- per horizon;
- VALIDATION/TEST marginal lift;
- temporal stability;
- regime stability;
- complexity penalty;
- role-aware recommendation.

### Recommendations

```text
CORE
SUPPORTING
CONFIRM_ONLY
CONTEXT_ONLY
RESEARCH
DROP
```

### Source Promotion Gate outcomes

```text
APPROVED_FOR_INTEGRATION
TICKER_SELECTIVE
RESEARCH
REJECTED
```

Promotion approval is non-deploying.

## 4. Source Identity and Research Controls

Created:

```text
src/calcEngine/rsSourceIdentity.py
```

Historical R/S evaluation now supports research-only controls:

```text
--include-source-keys
--exclude-source-keys
--research-indicator-specs-json
```

Dynamic source codes are canonicalized for stable attribution.

## 5. Research-only Indicator Adapter

V2.4 introduces explicit research support for Indicator Engine configs before they are registered as production R/S providers.

Flow:

```text
Indicator Management
    ↓
config/backfill candidate in Indicator Engine
    ↓
ResearchIndicatorSpec
    ↓
historical V2.4 evaluation
    ↓
Source Effectiveness
    ↓
Source Promotion Gate
    ↓
separate R/S integration release if approved
```

The generic research adapter is intentionally limited to:

```text
SourceRole = LEVEL
ValueSemantic = PRICE_LEVEL
```

New CONTEXT/CONFIRMATION candidates require source-specific research behavior rather than inferred semantics.

## 6. Role-aware Attribution

### LEVEL

Uses historical level lineage plus baseline-vs-ablation marginal lift.

### CONTEXT

Uses marginal LEVEL_QUALITY evidence where the context can affect level geometry.

### CONFIRMATION

Uses:

```text
STRENGTH_BRIER
```

to measure whether Strength predicts hold-after-touch better with the confirmation source present.

This prevents confirmation sources such as RSI from being incorrectly judged as zero-value only because S/R prices remain unchanged.

## 7. Promotion Guardrails

Source Promotion Gate includes:

- minimum ticker coverage;
- minimum VALIDATION events per ticker;
- minimum TEST events per ticker;
- positive ticker ratio;
- minimum Effectiveness Score;
- minimum VALIDATION lift;
- non-negative TEST lift;
- temporal stability;
- regime breadth/stability;
- complexity limit;
- material negative TEST protection.

Insufficient sample or regime breadth produces:

```text
RESEARCH
```

instead of a false rejection or approval.

## 8. DuckDB Changes

Migration:

```text
src/DuckDB/sql/rs_v2_4_source_effectiveness.sql
```

Runner:

```text
scripts/run_rs_v2_4_migration.py
```

Preflight:

```text
src/DuckDB/sql/rs_v2_4_preflight.sql
```

Added evaluation-run metadata:

```text
IncludeSourceKeysJson
ExcludeSourceKeysJson
ResearchIndicatorSpecsJson
```

New objects:

```text
cal_rs_source_effectiveness_run
cal_rs_source_effectiveness
sys_rs_source_promotion_audit
vw_RS_Source_Effectiveness
```

Public latest-result SSOT:

```text
vw_RS_Source_Effectiveness
```

## 9. Execution Scripts

```text
scripts/run_rs_v2_3_evaluation.py
scripts/run_rs_v2_4_source_effectiveness.py
scripts/promote_rs_v2_4_source.py
scripts/run_rs_v2_4_migration.py
```

Source Promotion Gate remains dry-run by default.

Even explicit audit apply does not mutate:

- Indicator Engine metadata;
- R/S provider registry;
- runtime source weights;
- runtime model deployment.

## 10. Validation

Runbook:

```text
tests/test_R_S_V2_4.md
```

User-reported final result:

```text
Final Verdict: PASS
Action: KEEP
```

Validated sequence covers:

1. Git sync;
2. migration + idempotency;
3. read-only preflight;
4. focused pytest;
5. V2.3 golden regression;
6. V2.4 baseline historical evaluation;
7. MA50_D source-config ablation;
8. per-ticker Source Effectiveness + public view;
9. effectiveness persistence idempotency;
10. CONFIRMATION role smoke;
11. multi-horizon contract;
12. Source Promotion Gate dry-run;
13. default runtime compatibility;
14. NiceGUI smoke.

## 11. Validation Fix

Exactly one allowed-scope test-fixture fix was required:

```text
tests/test_rs_source_effectiveness.py::_record
```

Root cause:

```text
fixture ValidationEventCount = 10
new Source Promotion Gate minimum = 20
```

Fix:

```text
ValidationEventCount = 20
TestEventCount = 10
```

Commit:

```text
1a722f82b98167a7644f7bc0f28d5f80b4bf3054
```

The fix synchronizes synthetic test evidence with the new OOS sample gate. It does not change production runtime logic.

Repair budget:

```text
1 focused fix
within allowed scope
KEEP
```

## 12. Evidence-driven MA50_D Result

MA50_D evaluated as:

```text
RESEARCH
```

with the current evaluation evidence due to low OOS sample and negative TEST lift.

This is a valid evidence-driven governance outcome, not a release defect.

No source was automatically promoted or deployed.

## 13. Runtime Compatibility

Validation confirms V2.4 default runtime behavior remains equivalent to V2.3/V2.2 when no research filters/specs are supplied.

Research effectiveness results are not consumed as runtime weights.

No automatic ticker-specific production weighting was introduced.

## 14. Rollback

```text
NOT REQUIRED
```

No runtime regression was detected.

## 15. Governance Boundary

```text
APPROVED_FOR_INTEGRATION
    != production deployment
```

Any future indicator/source that passes V2.4 Source Promotion Gate must still go through a separate implementation/change request before altering production R/S behavior.

## 16. Final Release State

```text
BA                DONE
SA                DONE
DEV               DONE
TEST              PASS
FINAL VERDICT     PASS
ACTION            KEEP
PR                #8 MERGED
MERGE COMMIT      45a7324825afc0e2d32a166a90dcbc17fe5fb1ac
DB MIGRATION      PASS
PREFLIGHT         PASS
GOLDEN REGRESSION PASS
RUNTIME REGRESSION NONE
ROLLBACK          NOT REQUIRED
PRODUCTION READY  YES
PRODUCTION        DEPLOYED
```


## 17. Operational Extension — Monthly Full Evaluation

R/S V2.4 Source Effectiveness is operationalized as a monthly full-universe workflow.

Canonical entry point:

```text
scripts/run_rs_v2_4_full_evaluation.py
```

Detailed operational Change Request:

```text
docs/ChangeRequest/CR_RS_V2_4_Monthly_Full_Evaluation.md
```

Release evidence:

```text
PR             #9
Merge commit   eed1990c7bccc0475eb9ac83c2c187e3bebf2b65
Final Verdict  PASS
Action         KEEP
```

This extension does not change V2.4 runtime scoring, provider registration, source weights, promotion semantics or production deployment boundaries.
