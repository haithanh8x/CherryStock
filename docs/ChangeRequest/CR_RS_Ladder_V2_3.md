# Change Request — R/S Ladder V2.3

- **Change ID:** CR-RS-V2.3-20260902
- **Release:** R/S Ladder V2.3
- **Date:** 2026-09-02
- **Status:** **CODE MERGED / DB MIGRATION PENDING / PRODUCTION VALIDATION PENDING**
- **Repository:** CherryStock
- **Pull Request:** #7 — feat: upgrade R/S Ladder to V2.3 evaluation and model governance
- **Main merge commit:** `74da4ec8ed9f733de6849883e9ee6942a71a2508`

---

## 1. Change Summary

V2.3 không thêm một loại Support/Resistance source mới.

V2.3 bổ sung lớp:

```text
Historical Evaluation
Calibration
Ablation
Model Versioning
Promotion Governance
Golden Regression Benchmark
```

bao quanh runtime V2.2 hiện hữu.

Runtime baseline:

```text
RS_V2_3_BASELINE
```

giữ hành vi source/scoring của V2.2 và chỉ thêm model-version traceability.

---

## 2. Target Flow

```text
R/S Runtime Snapshot
      │
      ▼
Historical Evaluation
      │
      ├── Touch / Hit
      ├── Break
      ├── Retest
      ├── Hold
      ├── Favorable / Adverse excursion
      ├── Temporal split
      ├── Ticker
      └── Market regime
      │
      ▼
Ablation / Calibration
      │
      ├── Source ablation
      ├── Family ablation
      ├── Config challengers
      └── Complexity penalty
      │
      ▼
Incremental Promotion Gate
      │
      ▼
PROMOTION_APPROVED
      │
      └── explicit later deployment required
```

Critical rule:

```text
PROMOTION_APPROVED != automatic production deployment
```

---

## 3. Runtime Model Version

`LevelLadderResult` now includes:

```text
model_version
```

Default:

```text
RS_V2_3_BASELINE
```

The V2.3 baseline preserves V2.2 runtime behavior.

No runtime source, rank or Strength formula is automatically changed by historical calibration.

---

## 4. Historical Evaluation Event

Each historical S/R level may produce:

```text
LevelEvaluationEvent

model_version
ticker
as_of_date

level_rank
level_type
level_price
strength_score

horizon_end_date

touched
touch_date

broken
break_date

retested
retest_date

held
bars_to_touch

max_favorable_pct
max_adverse_pct

source_count
source_family_count
sources
source_families

regime
split
```

Default outcome horizon:

```text
20 trading bars
```

Future bars are allowed only for outcome labeling.

Historical R/S snapshot generation remains bounded by `as_of_date`.

---

## 5. Hit / Break / Retest Contract

### Touch

```text
future High/Low intersects
level ± touch_tolerance_pct
```

Default:

```text
0.5%
```

### Break

Support:

```text
Close < Level × (1 - break_tolerance_pct)
```

Resistance:

```text
Close > Level × (1 + break_tolerance_pct)
```

Default break tolerance:

```text
0.5%
```

### Retest

After break:

```text
future bar intersects
level ± retest_tolerance_pct
```

Retest uses its own tolerance contract.

### Hold

```text
Touched = TRUE
Broken = FALSE
within horizon
```

---

## 6. Evaluation Metrics

V2.3 calculates:

```text
event_count
touch_count
break_count
retest_count
hold_count

touch_rate
break_rate_given_touch
retest_rate_given_break
hold_rate_given_touch

avg_bars_to_touch

avg_favorable_pct
avg_adverse_pct
directional_edge_pct

quality_score
```

Current evaluation quality objective:

```text
35% Touch Rate
35% Hold Rate Given Touch
10% Retest Rate Given Break
20% Directional Edge Component
```

This is an evaluation metric.

It does not replace runtime Strength.

---

## 7. Temporal Validation

Default chronological split:

```text
TRAIN       60%
VALIDATION  20%
TEST        20%
```

No random shuffle.

Promotion decisions must use VALIDATION and TEST evidence separately.

---

## 8. Market Regime

Regime is calculated point-in-time using data at/before each historical snapshot.

Current regimes:

```text
BULL_LOW_VOL
BULL_HIGH_VOL
BEAR_LOW_VOL
BEAR_HIGH_VOL
RANGE_LOW_VOL
RANGE_HIGH_VOL
UNKNOWN
```

Metrics can be compared by regime to detect hidden challenger degradation.

---

## 9. Cross-Ticker Evaluation

Historical evaluator accepts multiple tickers:

```text
MWG,FPT,HPG,...
```

Metric scopes persisted:

```text
OVERALL
SPLIT
TICKER
REGIME
LEVEL_TYPE
```

This avoids making a promotion decision from aggregate performance alone.

---

## 10. Source / Family Ablation

V2.3 provides reproducible variants:

```text
FULL
DROP_SOURCE_<SOURCE>
DROP_FAMILY_<FAMILY>
```

Canonical mapping includes:

```text
MA              → TREND_AVERAGE
BB              → VOLATILITY_BAND
SWING           → MARKET_STRUCTURE
PREVIOUS_HL     → MARKET_STRUCTURE
52W_HL          → MARKET_STRUCTURE
VOLUME_PROFILE  → VOLUME_STRUCTURE
ATR             → VOLATILITY_CONTEXT
RSI             → MOMENTUM_CONFIRMATION
```

Ablation comparisons must use the same historical dataset, horizon and temporal split.

---

## 11. Calibration and Complexity Penalty

Model config is represented by:

```text
RSModelSpec
```

with deterministic canonical JSON + signature.

Calibration candidate ranking:

```text
PenalizedScore
=
QualityScore
-
ComplexityLambda × ComplexityScore
```

Complexity considers:

- enabled sources;
- Strength overrides;
- Volume Profile config overrides;
- structural config overrides.

Purpose:

> marginal performance improvement must not automatically justify materially more model complexity.

---

## 12. Incremental Promotion Gate

Default gate:

```text
min_validation_events = 200
min_test_events       = 100

min_validation_quality_delta = +0.02
min_test_quality_delta       =  0.00

max_regime_quality_degradation = 0.05
max_complexity_delta           = 0.15
```

Decision includes:

```text
promote
validation_quality_delta
test_quality_delta
complexity_delta
worst_regime_delta
reasons
```

Script:

```text
scripts/promote_rs_v2_3_model.py
```

Default behavior:

```text
DRY RUN
```

With `--apply` and a passing gate:

```text
challenger status = PROMOTION_APPROVED
```

It does not switch production runtime automatically.

---

## 13. DuckDB Migration

V2.3 requires a new additive persistence schema.

Execute externally:

```text
src/DuckDB/sql/rs_v2_3_evaluation_governance.sql
```

Objects:

```text
dim_rs_model_version
cal_rs_evaluation_run
cal_rs_evaluation_event
cal_rs_evaluation_metric
sys_rs_model_promotion_audit
```

Object ownership:

```text
dim_* = model/version registry
cal_* = historical calculated evaluation artifacts
sys_* = governance/audit
```

Migration characteristics:

```text
additive
idempotent
no destructive DDL
```

---

## 14. Evaluation Persistence Keys

Event grain:

```text
EvaluationRunId
Ticker
AsOfDate
LevelRank
```

Metric grain:

```text
EvaluationRunId
ScopeType
ScopeKey
MetricCode
```

Rerunning the same evaluation run replaces that run's events/metrics and does not accumulate duplicates.

---

## 15. DuckDB Writer Lock Behavior

Historical evaluation may be long-running.

V2.3 explicitly separates:

```text
historical calculation
    → read-only connection

final persistence
    → short writer UnitOfWork
```

The historical loop must not hold a writer lock.

---

## 16. Golden Regression Benchmark

Fixture:

```text
tests/fixtures/rs_v2_3_golden_cases.json
```

Runner:

```text
scripts/run_rs_v2_3_golden.py
```

Golden invariants:

- proximity rank order;
- Strength in [0,100];
- `source_family_count <= source_count`;
- source_date point-in-time;
- confirmed_at point-in-time;
- support below current price;
- resistance above current price.

Golden regression protects runtime contracts.

Historical evaluation separately measures statistical effectiveness.

---

## 17. Source Code Changes

Runtime:

```text
src/calcEngine/levelLadder.py
src/webapp/NiceGUI_chart.py
src/Chart/levelLadderChart.py
```

Evaluation:

```text
src/calcEngine/rsEvaluation.py
```

Persistence:

```text
src/cherrystock/infrastructure/database/repositories/rs_evaluation_repository.py
src/cherrystock/infrastructure/database/repositories/__init__.py
src/cherrystock/infrastructure/database/unit_of_work.py
```

Scripts:

```text
scripts/run_rs_v2_3_evaluation.py
scripts/promote_rs_v2_3_model.py
scripts/run_rs_v2_3_golden.py
```

DuckDB:

```text
src/DuckDB/sql/rs_v2_3_evaluation_governance.sql
src/DuckDB/sql/rs_v2_3_preflight.sql
```

Tests:

```text
tests/test_rs_ladder.py
tests/test_rs_evaluation.py
tests/test_R_S_V2_3.md
tests/fixtures/rs_v2_3_golden_cases.json
```

Docs:

```text
docs/architecture/RS_Ladder.md
docs/adr/ADR-007-rs-v2-3-evaluation-governance.md
docs/00_HOME.md
```

---

## 18. Validation Required

### Migration

Execute:

```text
src/DuckDB/sql/rs_v2_3_evaluation_governance.sql
```

### Preflight

Run read-only:

```text
src/DuckDB/sql/rs_v2_3_preflight.sql
```

### Focused pytest

```powershell
python -m pytest tests/test_rs_ladder.py tests/test_rs_evaluation.py -v
```

Current expected suite size:

```text
36 tests
```

Use all-collected PASS as the authoritative criterion if more relevant tests are added.

### Golden benchmark

```powershell
python scripts/run_rs_v2_3_golden.py
```

### Full local production cross-check

```text
tests/test_R_S_V2_3.md
```

---

## 19. Current Release Status

| Item | Status |
|---|---|
| Architecture contract | PASS |
| ADR | PASS |
| Source code merged to main | PASS |
| PR #7 | MERGED |
| Runtime V2.2 behavioral compatibility design | PASS |
| DuckDB migration SQL generated | PASS |
| DuckDB migration execution | PENDING |
| Read-only preflight | PENDING |
| Automated tests added | PASS |
| Local pytest execution | PENDING |
| Golden benchmark | PENDING |
| Multi-ticker historical evaluation | PENDING |
| Persistence/idempotency validation | PENDING |
| Ablation smoke | PENDING |
| Promotion Gate dry-run | PENDING |
| NiceGUI V2.3 smoke | PENDING |
| Production deployment | PENDING |

Current state:

```text
CODE MERGED
DB MIGRATION REQUIRED
DB MIGRATION PENDING
PRODUCTION PREFLIGHT PENDING
PRODUCTION VALIDATION PENDING
```

Do not classify V2.3 as Production Ready until `tests/test_R_S_V2_3.md` returns PASS.

---

## 20. Deployment Sequence

```text
1. git pull origin main
2. execute rs_v2_3_evaluation_governance.sql
3. execute rs_v2_3_preflight.sql
4. pytest runtime + evaluation suites
5. golden benchmark
6. baseline multi-ticker historical evaluation
7. persisted event/metric validation
8. idempotency rerun
9. ablation challenger smoke
10. Promotion Gate dry-run
11. NiceGUI smoke
12. update CR/master tracking only when all PASS
```

---

## 21. Rollback

### Runtime fallback

V2.3 baseline preserves V2.2 behavior.

The main runtime change is model-version metadata.

If V2.3 evaluation/governance validation fails, the evaluation layer can be rolled back without requiring a price/indicator data rollback.

### Database rollback

The migration is additive.

Normal rollback does not require dropping V2.3 tables immediately because V2.2 runtime does not depend on them.

If strict schema rollback is required, drop evaluation/governance objects only after confirming no evaluation process is using them.

### Code rollback target

```text
74da4ec8ed9f733de6849883e9ee6942a71a2508
```

---

## 22. Risks

### Statistical overfit

Mitigation:

```text
chronological split
TEST gate
regime gate
complexity penalty
```

### Look-ahead

Mitigation:

- historical ladder uses `as_of_date`;
- regime uses data at/before `as_of_date`;
- future data is used only for outcome labels.

### Long DuckDB lock

Mitigation:

```text
read-only calculation
short writer UoW persistence
```

### Silent production mutation

Mitigation:

```text
PROMOTION_APPROVED != auto-deploy
```

### Duplicate evaluation artifacts

Mitigation:

stable run/event/metric keys and replace-on-rerun persistence.

---

## 23. References

Architecture:

```text
docs/architecture/RS_Ladder.md
```

ADR:

```text
docs/adr/ADR-007-rs-v2-3-evaluation-governance.md
```

Migration:

```text
src/DuckDB/sql/rs_v2_3_evaluation_governance.sql
```

Preflight:

```text
src/DuckDB/sql/rs_v2_3_preflight.sql
```

Validation:

```text
tests/test_rs_ladder.py
tests/test_rs_evaluation.py
tests/test_R_S_V2_3.md
tests/fixtures/rs_v2_3_golden_cases.json
```

GitHub:

```text
PR #7
Merge commit: 74da4ec8ed9f733de6849883e9ee6942a71a2508
```
