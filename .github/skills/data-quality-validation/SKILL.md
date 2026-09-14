---
name: data-quality-validation
description: "Validate CherryStock dataset and pipeline quality using freshness, completeness, coverage, uniqueness, NULL/range, semantic and rerun checks; persist/audit evidence where the existing Data Quality contract requires it."
---

# CherryStock Data Quality Validation Skill

## Applicable owners

Typical owners:
- Test Engineer for independent validation/verdict;
- General Coding for focused developer verification after a data-pipeline change.

Mandatory constraints:
- `.github/instructions/database.instructions.md`;
- `.github/instructions/testing.instructions.md` when a validation verdict is required.

## Inputs

Resolve before execution:
- dataset/table/view or pipeline stage;
- expected row grain and business key;
- authoritative source/upstream;
- expected latest business/trading date;
- acceptable coverage/null/range behavior;
- comparison baseline or prior-run expectation when relevant;
- whether results must persist to the existing Data Quality audit contract.

## Procedure

### 1. Define quality contract

State:
- dataset and owner;
- grain;
- logical key;
- freshness expectation;
- mandatory columns;
- expected source-to-output population;
- domain-specific validity rules.

Do not infer a key or freshness SLA from row count alone.

### 2. Freshness

Verify data reaches the latest expected business/trading checkpoint. Distinguish:
- calendar date;
- trading date;
- source publication lag;
- intentionally delayed/weekly/monthly datasets.

### 3. Completeness / coverage

Check as applicable:
- expected ticker/entity coverage;
- source vs output coverage;
- missing date partitions;
- material row-count deviations from a reasonable baseline;
- expected D/W/M or other dimensional coverage.

Do not treat any row-count change as a failure without a contract or evidence-based threshold.

### 4. Uniqueness

Validate the logical key has no unintended duplicates. Report duplicate count and examples rather than silently deduplicating during validation.

### 5. NULL / type / range / semantic validity

Check only contract-relevant fields:
- required non-null values;
- numeric/date parseability;
- impossible ranges;
- inconsistent units/semantics;
- invalid category/enumeration values;
- OHLC/market-limit/business invariants where the owning architecture defines them.

### 6. Cross-contract consistency

Where public views exist, verify downstream/public contracts rather than only internal persistence.

Examples:
- canonical public view exposes expected rows/columns;
- current metadata/config matches calculated records;
- source status/active-universe filters are respected;
- transformed values reconcile with upstream sample evidence.

### 7. Idempotency / rerun behavior

For write pipelines, rerun the narrowest safe scope when feasible and verify:
- no duplicate logical keys;
- no uncontrolled row growth;
- deterministic replacement/upsert behavior;
- unaffected partitions remain stable.

### 8. Persist audit result when required

If the existing CherryStock Data Quality architecture requires persistence, use the canonical validation/persistence functions/table rather than inventing a second audit store. Persist structured scope, counts, status and error evidence without credentials or sensitive payloads.

### 9. Verdict / handoff

Return:

```text
DATA QUALITY RESULT
Dataset / pipeline:
Expected grain/key:
Freshness:
Coverage/completeness:
Duplicates:
NULL/range/semantic checks:
Rerun/idempotency:
Audit persistence:
Verdict: PASS | FAIL | BLOCKED | WARNING
Evidence / query or command:
Next owner:
```

When this Skill is executed under Test Engineer, map the result to the Test Engineer terminal verdict contract.

## Stop conditions

- expected dataset contract is undefined and materially affects validation → Solution Architect/Business Analyst as appropriate;
- source unavailable/environment blocked → BLOCKED;
- contract violation found → FAIL and report evidence; do not mutate data as part of validation unless an explicitly authorized focused repair is handed off.

## Anti-patterns

- declaring quality from `pipeline completed` alone;
- comparing raw row counts without grain/universe context;
- hiding duplicates by `DISTINCT` in validation queries;
- modifying production data while pretending to run read-only validation;
- logging credentials or full sensitive payloads.
