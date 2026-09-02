# ADR-008 — R/S V2.4 Source Effectiveness and Indicator Promotion Governance

- **Status:** Accepted
- **Date:** 2026-09-02
- **Requirement:** REQ-0022
- **Scope:** R/S V2.4

## Context

R/S V2.3 can evaluate whole model variants but does not provide a stable per-ticker/per-source effectiveness contract. Runtime Strength cannot be reused as source-selection evidence because that would be circular and would over-reward correlated sources.

V2.4 must determine whether a source/config adds incremental out-of-sample value and whether that evidence is broad/stable enough for future R/S integration.

## Decision

### 1. Source Effectiveness is separate from runtime Strength

```text
Runtime Strength        = current zone confidence
Source Effectiveness    = historical source/config evidence
Model Promotion Gate    = whole-model governance
Source Promotion Gate   = source/config governance
```

None of these concepts may silently overwrite another.

### 2. Stable canonical source identity is required

Dynamic runtime codes such as dated swings and numbered Volume Profile nodes are normalized to stable research keys. Unknown non-empty codes remain exact normalized keys.

### 3. Source-config research filtering is backward compatible

`build_level_ladder()` may receive optional include/exclude source keys for historical research. When omitted, runtime behavior is identical to V2.3.

Research filters apply consistently across LEVEL, CONTEXT and CONFIRMATION objects and participate in evaluation model signatures.

### 4. LEVEL and non-LEVEL sources use different attribution methods

LEVEL sources may use direct event lineage plus marginal baseline-vs-ablation lift.

CONTEXT and CONFIRMATION sources use marginal-only attribution. V2.4 must not fabricate price-level touch/hold/retest statistics for non-LEVEL roles.

### 5. Incremental OOS lift is the primary promotion evidence

Standalone source quality is supplementary. Global promotion requires VALIDATION/TEST evidence and cannot be authorized from TRAIN-only performance.

### 6. Effectiveness remains per ticker and per horizon

Results are keyed by ticker/source/horizon. V2.4 does not automatically convert these results into ticker-specific production weights.

### 7. Source family correlation remains explicit

Source-level and source-family effectiveness/ablation are separate scopes. Multiple configs in one family must not be interpreted as independent family evidence.

### 8. Source Promotion Gate is non-deploying

Possible outcomes:

```text
APPROVED_FOR_INTEGRATION
TICKER_SELECTIVE
RESEARCH
REJECTED
```

Even an applied approval writes audit/governance metadata only.

It does not modify:

- Indicator Engine dimensions/configuration;
- R/S provider registry;
- runtime source set;
- Strength weights;
- production model status.

Concrete indicator lifecycle operations remain owned by Indicator Management, and any runtime integration requires a separate release/change request.

### 9. Public read SSOT is a view

Latest source-effectiveness consumers use:

```text
vw_RS_Source_Effectiveness
```

Internal calculated tables remain implementation persistence and are not the latest-result public contract.

### 10. V2.4 persistence is additive and idempotent

V2.4 adds source-effectiveness run/results and promotion audit objects plus source-filter metadata on V2.3 evaluation runs.

Rerunning the same effectiveness run replaces rows at the same stable grain instead of accumulating duplicates.

## Consequences

### Positive

- per-ticker evidence becomes auditable;
- correlated/redundant sources can be detected through marginal lift;
- non-LEVEL indicators are evaluated using correct semantics;
- multi-horizon and regime behavior remain visible;
- promotion cannot silently mutate production;
- V2.3 evaluation artifacts are reused rather than replaced.

### Trade-offs

- exact source-config ablation can require additional historical runs;
- sparse ticker/regime samples may remain RESEARCH;
- source identity canonicalization becomes a maintained contract;
- V2.4 creates additional DuckDB governance/effectiveness objects.

## Migration

Generate and execute externally:

```text
src/DuckDB/sql/rs_v2_4_source_effectiveness.sql
scripts/run_rs_v2_4_migration.py
```

## Validation

Required validation includes focused unit tests, V2.3 golden regression, source-config baseline/ablation effectiveness persistence, public-view lookup, idempotency and Source Promotion Gate dry-run.

## Status

```text
APPROVED_FOR_IMPLEMENTATION
```