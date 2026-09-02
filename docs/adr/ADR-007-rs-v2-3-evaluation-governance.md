# ADR-007 — R/S V2.3 Evaluation, Calibration and Promotion Governance

- **Status:** Accepted
- **Date:** 2026-09-02
- **Scope:** Support / Resistance Engine V2.3

## Context

R/S V2.0–V2.2 progressively added multi-source levels, adaptive volatility, structural price evidence and Volume Profile.

The remaining architectural gap is not another level provider. It is model evidence and governance:

- historical hit/break/retest evaluation;
- temporal validation;
- cross-ticker and regime robustness;
- source/family ablation;
- calibration without uncontrolled complexity growth;
- model version reproducibility;
- promotion decisions that do not silently mutate production behavior;
- a golden regression benchmark.

Without this layer, every Strength/source change risks becoming a manual, non-reproducible optimization.

## Decision

### 1. V2.3 is an evaluation/governance layer

V2.3 keeps the V2.2 production R/S behavior as its runtime baseline.

The release adds model-version tagging and historical evaluation around that baseline.

### 2. Signal generation and outcome labeling are separate

For each historical snapshot:

```text
R/S snapshot
    = data available at/before as_of_date

Outcome labels
    = future bars after as_of_date
```

Future bars may label whether a level was touched, broken or retested.

Future bars must never influence the historical R/S snapshot itself.

### 3. Evaluation events are persisted

V2.3 adds additive DuckDB objects:

```text
dim_rs_model_version
cal_rs_evaluation_run
cal_rs_evaluation_event
cal_rs_evaluation_metric
sys_rs_model_promotion_audit
```

These objects are evaluation/governance state, not runtime market-data SSOT.

### 4. Temporal split is chronological

Default:

```text
TRAIN       60%
VALIDATION  20%
TEST        20%
```

No random shuffle is allowed for time-series evaluation.

### 5. Evaluation is segmented by ticker and market regime

Metrics must be available by:

```text
OVERALL
SPLIT
TICKER
REGIME
LEVEL_TYPE
```

This prevents aggregate improvements from hiding material ticker/regime degradation.

### 6. Ablation is explicit

The framework supports:

```text
DROP_SOURCE_<SOURCE>
DROP_FAMILY_<FAMILY>
```

Ablations must use the same dataset, split and horizon as the baseline.

### 7. Calibration includes complexity penalty

Candidate ranking uses:

```text
PenalizedScore
=
QualityScore
-
ComplexityLambda × ComplexityScore
```

This prevents marginal metric gains from automatically justifying materially more complex models.

### 8. Promotion Gate is incremental

A challenger must satisfy:

- minimum VALIDATION sample size;
- minimum TEST sample size;
- VALIDATION improvement;
- TEST non-regression;
- regime non-regression;
- complexity guardrail.

### 9. Promotion approval does not auto-deploy

Critical rule:

```text
Promotion Gate PASS
    → PROMOTION_APPROVED
    → explicit later deployment/release

NOT:
Promotion Gate PASS
    → silently change production runtime
```

The database registry is governance metadata, not a hot runtime configuration switch in V2.3.

### 10. Historical evaluation holds no long writer lock

Long-running calculations use a read-only DuckDB connection.

Only final persistence runs inside a short writer UnitOfWork.

### 11. Golden benchmark is invariant-based

The golden regression set protects runtime contracts:

- proximity ranking;
- Strength range;
- point-in-time source dates;
- family-count semantics;
- support/resistance side correctness.

Statistical performance is evaluated separately through historical events/metrics.

## Consequences

### Positive

- reproducible evidence for R/S model changes;
- explicit train/validation/test discipline;
- cross-ticker and regime robustness checks;
- source/family ablation becomes systematic;
- model versions become auditable;
- promotion decisions are explainable and persisted;
- production runtime cannot silently drift after calibration;
- evaluation reruns are idempotent.

### Trade-offs

- V2.3 introduces additional DuckDB persistence objects;
- historical evaluation can be computationally expensive;
- exact model calibration still requires deliberate challenger generation;
- daily EOD history constrains the granularity of event labels;
- Promotion Gate approval requires a separate deployment step before runtime behavior changes.

## Migration

Execute manually:

```text
src/DuckDB/sql/rs_v2_3_evaluation_governance.sql
```

Then validate with:

```text
src/DuckDB/sql/rs_v2_3_preflight.sql
```

## Validation

Required:

```text
python -m pytest tests/test_rs_ladder.py tests/test_rs_evaluation.py -v
python scripts/run_rs_v2_3_golden.py
tests/test_R_S_V2_3.md
```

Production sign-off requires migration, preflight, focused regression, golden benchmark, baseline historical evaluation and NiceGUI smoke to PASS.
