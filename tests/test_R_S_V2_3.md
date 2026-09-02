# R/S V2.3 Local Cross-check Runbook

## Objective

Validate one release objective:

> R/S V2.3 adds reproducible historical evaluation, ablation/calibration, model versioning and a fail-safe Promotion Gate without changing V2.2 runtime behavior or introducing look-ahead.

## Scope

In scope:

- R/S model-version tag
- DuckDB evaluation/governance schema
- touch/break/retest/hold labels
- favorable/adverse excursion
- chronological TRAIN/VALIDATION/TEST split
- cross-ticker metrics
- point-in-time market regime
- source/family ablation
- calibration complexity penalty
- Promotion Gate
- golden regression benchmark
- batch/idempotent evaluation persistence
- NiceGUI V2.3 model-version presentation

Out of scope:

- automatic deployment of an approved challenger
- intraday/tick event labels
- changing the V2.2 runtime default source/weight behavior
- production tuning to maximize a particular challenger score

## Allowed Fix Scope

If a test fails because of V2.3 implementation, fixes are limited to:

```text
src/calcEngine/levelLadder.py
src/calcEngine/rsEvaluation.py
src/cherrystock/infrastructure/database/repositories/rs_evaluation_repository.py
src/cherrystock/infrastructure/database/unit_of_work.py
src/cherrystock/infrastructure/database/repositories/__init__.py
scripts/run_rs_v2_3_evaluation.py
scripts/run_rs_v2_3_migration.py
scripts/promote_rs_v2_3_model.py
scripts/run_rs_v2_3_golden.py
src/webapp/NiceGUI_chart.py
src/Chart/levelLadderChart.py
tests/test_rs_ladder.py
tests/test_rs_evaluation.py
```

Maximum two focused repair attempts for one defect.

Do not investigate unrelated failures.

---

## Seq 1 — Git sync

```powershell
git pull origin main
git status
```

PASS:

- working tree contains the V2.3 merge commit;
- no unexpected local conflict.

---

## Seq 2 — Execute DuckDB migration

Preferred write-capable entry point:

```powershell
python scripts/run_rs_v2_3_migration.py
```

The helper executes:

```text
src/DuckDB/sql/rs_v2_3_evaluation_governance.sql
```

directly against CherryMon. Use this helper when MCP is read-only and cannot execute DDL.

This migration is additive/idempotent.

It creates:

```text
dim_rs_model_version
cal_rs_evaluation_run
cal_rs_evaluation_event
cal_rs_evaluation_metric
sys_rs_model_promotion_audit
```

PASS:

- script completes;
- validation SELECT returns all five objects;
- `RS_V2_3_BASELINE` exists with `Status=BASELINE`.

FAIL:

- any destructive schema behavior;
- duplicate/object conflict;
- baseline row missing.

STOP on FAIL.

---

## Seq 3 — Read-only preflight

Run:

```text
src/DuckDB/sql/rs_v2_3_preflight.sql
```

PASS:

1. all five V2.3 objects exist;
2. baseline model row exists;
3. raw EOD historical coverage exists;
4. MA/BB/RSI/ATR PIT history exists;
5. MWG/FPT/HPG have usable history;
6. each benchmark ticker has at least 20 forward bars after 2026-07-31.

STOP if the required historical/future coverage is BLOCKED.

---

## Seq 4 — Focused automated tests

```powershell
python -m pytest tests/test_rs_ladder.py tests/test_rs_evaluation.py -v
```

Expected current test count after V2.3 implementation:

```text
36 passed
```

PASS:

- all runtime regressions V2.0–V2.2 pass;
- V2.3 evaluation tests pass;
- model-version tag test passes;
- Promotion Gate accept/reject tests both pass;
- retest-specific tolerance test passes.

If the exact count changes because additional relevant tests were added, use all-collected PASS as the criterion.

---

## Seq 5 — Golden regression benchmark

```powershell
python scripts/run_rs_v2_3_golden.py
```

PASS when output contains:

```text
"passed": true
"model_version": "RS_V2_3_BASELINE"
```

for the benchmark as a whole.

Every case must satisfy:

- support proximity ordering;
- resistance proximity ordering;
- Strength in [0,100];
- family_count <= source_count;
- no future source_date;
- no future confirmed_at;
- support < current price;
- resistance > current price.

---

## Seq 6 — Baseline multi-ticker historical evaluation

Use an endpoint with enough forward outcome bars:

```powershell
python scripts/run_rs_v2_3_evaluation.py --tickers MWG,FPT,HPG --start 2026-01-01 --end 2026-07-31 --snapshot-step 5 --horizon-bars 20 --model-version RS_V2_3_BASELINE --run-id RSV23_BASELINE_20260902
```

PASS when:

- command completes;
- model signature is printed;
- ticker count = 3;
- snapshot count > 0;
- event count > 0;
- metric count > 0.

Important:

- historical calculation must use read-only connection;
- writer lock is only used during final persistence.

---

## Seq 7 — Validate persisted evaluation

Run read-only:

```sql
SELECT
    "EvaluationRunId",
    "ModelVersion",
    "DatasetStart",
    "DatasetEnd",
    "HorizonBars",
    "TickerCount",
    "SnapshotCount",
    "Status",
    "CompletedAt"
FROM "CherryMon"."main"."cal_rs_evaluation_run"
WHERE "EvaluationRunId" = 'RSV23_BASELINE_20260902';

SELECT
    COUNT(*) AS Events,
    COUNT(DISTINCT "Ticker") AS Tickers,
    COUNT(DISTINCT "AsOfDate") AS SnapshotDates,
    SUM(CASE WHEN "Split" = 'TRAIN' THEN 1 ELSE 0 END) AS TrainEvents,
    SUM(CASE WHEN "Split" = 'VALIDATION' THEN 1 ELSE 0 END) AS ValidationEvents,
    SUM(CASE WHEN "Split" = 'TEST' THEN 1 ELSE 0 END) AS TestEvents,
    SUM(CASE WHEN "Regime" IS NULL THEN 1 ELSE 0 END) AS NullRegime
FROM "CherryMon"."main"."cal_rs_evaluation_event"
WHERE "EvaluationRunId" = 'RSV23_BASELINE_20260902';

SELECT
    "ScopeType",
    COUNT(*) AS Metrics
FROM "CherryMon"."main"."cal_rs_evaluation_metric"
WHERE "EvaluationRunId" = 'RSV23_BASELINE_20260902'
GROUP BY "ScopeType"
ORDER BY "ScopeType";
```

PASS:

- run Status = COMPLETED;
- events > 0;
- 3 tickers represented;
- TRAIN / VALIDATION / TEST all represented;
- metric scopes include OVERALL, SPLIT, TICKER, REGIME, LEVEL_TYPE.

`UNKNOWN` regime is allowed for snapshots without enough lookback.

---

## Seq 8 — Persistence idempotency

Run the exact baseline command from Seq 6 again with the **same run-id**:

```text
RSV23_BASELINE_20260902
```

Then rerun the event/metric counts from Seq 7.

PASS:

- no PK/duplicate error;
- event count is unchanged;
- metric count is unchanged;
- only one evaluation-run row exists for the run ID.

This unchanged rerun is intentional because idempotency is the target behavior.

---

## Seq 9 — Source ablation challenger

Run a challenger without Volume Profile on the same dataset/split/horizon:

```powershell
python scripts/run_rs_v2_3_evaluation.py --tickers MWG,FPT,HPG --start 2026-01-01 --end 2026-07-31 --snapshot-step 5 --horizon-bars 20 --model-version RS_V2_3_ABL_NO_VOLUME --enabled-sources MA,BB,SWING,PREVIOUS_HL,52W_HL,ATR,RSI --run-id RSV23_ABL_NO_VOLUME_20260902
```

PASS:

- challenger model is registered as CANDIDATE;
- challenger evaluation completes;
- same DatasetStart/DatasetEnd/HorizonBars as baseline;
- metrics exist for SPLIT/TICKER/REGIME.

This is a source-ablation smoke, not a requirement that the challenger beat baseline.

Family ablations can be generated using `build_ablation_variants()` with the canonical source-family map.

---

## Seq 10 — Promotion Gate dry-run

```powershell
python scripts/promote_rs_v2_3_model.py --baseline-run RSV23_BASELINE_20260902 --challenger-run RSV23_ABL_NO_VOLUME_20260902
```

PASS when:

- command returns a deterministic decision;
- output includes validation_quality_delta;
- output includes test_quality_delta;
- output includes complexity_delta;
- output includes worst_regime_delta;
- output includes reasons;
- `apply_requested=false`.

The decision may be either:

```text
promote=true
```

or:

```text
promote=false
```

depending on evidence.

A rejection because the smoke dataset is below the default minimum sample size is valid fail-safe behavior.

Verify dry-run did not mutate deployment status:

```sql
SELECT "ModelVersion", "Status", "PromotedAt"
FROM "CherryMon"."main"."dim_rs_model_version"
WHERE "ModelVersion" IN (
    'RS_V2_3_BASELINE',
    'RS_V2_3_ABL_NO_VOLUME'
)
ORDER BY "ModelVersion";

SELECT COUNT(*) AS PromotionAuditRows
FROM "CherryMon"."main"."sys_rs_model_promotion_audit";
```

PASS:

- baseline remains BASELINE;
- challenger remains CANDIDATE;
- dry-run does not create a promotion audit row.

Do **not** use `--apply` as part of production-release validation.

---

## Seq 11 — NiceGUI smoke

Run:

```powershell
python src\webapp\NiceGUI_chart.py
```

Open CherryStock → R/S.

PASS:

- header shows V2.3 model/evaluation governance;
- Refresh works;
- notification includes `RS_V2_3_BASELINE`;
- chart renders;
- existing V2.2 Volume Profile/structural levels still render;
- no stale V2.2 empty-state/header text remains.

---

## Final Verdict

Use exactly one:

```text
PASS
FAIL
BLOCKED
REGRESSION
```

Action:

```text
PASS       → KEEP and STOP
FAIL       → record exact V2.3 failure and STOP
BLOCKED    → record dependency/data/environment blocker and STOP
REGRESSION → revert V2.3 rollout and STOP
```

## Required Result Summary

Report:

```text
Seq 1  Git sync
Seq 2  Migration
Seq 3  Preflight
Seq 4  Pytest
Seq 5  Golden benchmark
Seq 6  Baseline historical evaluation
Seq 7  Persistence validation
Seq 8  Idempotency
Seq 9  Ablation challenger
Seq 10 Promotion Gate dry-run
Seq 11 NiceGUI

Final Verdict
Action
Notes
```
