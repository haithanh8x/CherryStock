# R/S V2.4 Local Cross-check Runbook

## Target

Validate one release objective:

> R/S V2.4 adds Source Effectiveness & Indicator Promotion governance using per-ticker, role-aware, out-of-sample evidence without changing default R/S runtime behavior or auto-deploying approved sources.

## Scope

In scope:
- stable canonical source identity;
- source-config include/exclude research filters;
- V2.3 evaluation-run reproducibility metadata;
- per-ticker Source Effectiveness;
- SOURCE_CONFIG and SOURCE_FAMILY scopes;
- LEVEL lineage attribution;
- CONTEXT/CONFIRMATION marginal-only attribution;
- temporal/regime stability;
- VALIDATION/TEST marginal lift;
- 5/10/20/40-bar horizon support;
- role-aware recommendations;
- Source Promotion Gate;
- effectiveness persistence and public view;
- idempotency;
- V2.3 golden regression;
- NiceGUI V2.4 runtime smoke.

Out of scope:
- onboarding a new concrete technical indicator;
- modifying Indicator Engine metadata/config;
- changing runtime R/S weights;
- changing provider registry;
- applying ticker-specific production weights;
- automatic production deployment after source promotion.

## Allowed Fix Scope

```text
src/calcEngine/levelLadder.py
src/calcEngine/rsEvaluation.py
src/calcEngine/rsSourceIdentity.py
src/calcEngine/rsSourceEffectiveness.py
src/cherrystock/infrastructure/database/repositories/rs_evaluation_repository.py
scripts/run_rs_v2_3_evaluation.py
scripts/run_rs_v2_4_migration.py
scripts/run_rs_v2_4_source_effectiveness.py
scripts/promote_rs_v2_4_source.py
src/webapp/NiceGUI_chart.py
src/Chart/levelLadderChart.py
tests/test_rs_ladder.py
tests/test_rs_evaluation.py
tests/test_rs_source_effectiveness.py
```

Maximum two focused repair attempts for the same defect.
Do not investigate unrelated failures.

---

## Seq 1 — Git sync

```powershell
git pull origin main
git status
```

PASS when V2.4 merge commit is present and there are no unresolved conflict markers or unexpected conflicts.

---

## Seq 2 — DuckDB migration

Run:

```powershell
python scripts/run_rs_v2_4_migration.py
```

This executes:

```text
src/DuckDB/sql/rs_v2_4_source_effectiveness.sql
```

Expected new objects:

```text
cal_rs_source_effectiveness_run
cal_rs_source_effectiveness
sys_rs_source_promotion_audit
vw_RS_Source_Effectiveness
```

Expected added columns:

```text
cal_rs_evaluation_run.IncludeSourceKeysJson
cal_rs_evaluation_run.ExcludeSourceKeysJson
```

Expected baseline model:

```text
RS_V2_4_BASELINE
Status = BASELINE
```

Run the migration a second time once.

PASS when no duplicate/object error occurs and the same objects remain available.

---

## Seq 3 — Read-only preflight

Run:

```text
src/DuckDB/sql/rs_v2_4_preflight.sql
```

PASS when:
1. all V2.4 tables exist;
2. public view exists;
3. include/exclude evaluation columns exist;
4. RS_V2_4_BASELINE exists;
5. V2.3 completed evaluation evidence remains queryable;
6. historical event source lineage remains available;
7. public view can be queried even if it initially returns zero rows.

---

## Seq 4 — Focused automated tests

```powershell
python -m pytest tests/test_rs_ladder.py tests/test_rs_evaluation.py tests/test_rs_source_effectiveness.py -v
```

PASS when all collected tests pass. Exact count is not the criterion if relevant tests were added.

---

## Seq 5 — V2.3 golden regression

```powershell
python scripts/run_rs_v2_3_golden.py
```

PASS when output contains:

```text
"passed": true
```

This confirms V2.4 default research filters do not alter V2.3 runtime invariants.

---

## Seq 6 — V2.4 baseline historical run, H20

```powershell
python scripts/run_rs_v2_3_evaluation.py --tickers MWG,FPT,HPG --start 2026-01-01 --end 2026-07-31 --snapshot-step 5 --horizon-bars 20 --model-version RS_V2_4_BASELINE --run-id RSV24_BASE_H20
```

PASS when:
- run completes;
- Status=COMPLETED;
- IncludeSourceKeysJson=[];
- ExcludeSourceKeysJson=[];
- events/metrics > 0;
- TRAIN/VALIDATION/TEST all exist.

---

## Seq 7 — MA50_D source-config ablation, H20

```powershell
python scripts/run_rs_v2_3_evaluation.py --tickers MWG,FPT,HPG --start 2026-01-01 --end 2026-07-31 --snapshot-step 5 --horizon-bars 20 --model-version RS_V2_4_ABL_MA50_D_H20 --exclude-source-keys MA50_D --run-id RSV24_ABL_MA50_D_H20
```

PASS when:
- run completes;
- ExcludeSourceKeysJson contains MA50_D;
- model signature differs from baseline;
- dataset dates, horizon and split config match baseline.

---

## Seq 8 — Calculate MA50_D per-ticker effectiveness

```powershell
python scripts/run_rs_v2_4_source_effectiveness.py --baseline-run RSV24_BASE_H20 --ablation-run RSV24_ABL_MA50_D_H20 --source-key MA50_D --source-family TREND_AVERAGE --source-role LEVEL --scope-type SOURCE_CONFIG --run-id RSEFF_MA50_D_H20
```

PASS when:
- one result exists per common ticker;
- SourceRole=LEVEL;
- AttributionMode=LEVEL_LINEAGE;
- EffectivenessScore is within [0,100];
- VALIDATION and TEST marginal lift are separate;
- LEVEL lineage metrics are populated when lineage exists;
- Recommendation is CORE/SUPPORTING/RESEARCH/DROP.

Read public SSOT:

```sql
SELECT
    "Ticker",
    "SourceKey",
    "SourceRole",
    "HorizonBars",
    "ValidationMarginalLift",
    "TestMarginalLift",
    "TemporalStability",
    "RegimeStability",
    "EffectivenessScore",
    "Recommendation"
FROM "CherryMon"."main"."vw_RS_Source_Effectiveness"
WHERE "SourceKey" = 'MA50_D'
  AND "HorizonBars" = 20
ORDER BY "Ticker";
```

PASS when the latest completed run is visible through the view.

---

## Seq 9 — Effectiveness persistence idempotency

Rerun Seq 8 with the same run ID:

```text
RSEFF_MA50_D_H20
```

Then:

```sql
SELECT COUNT(*) AS Rows
FROM "CherryMon"."main"."cal_rs_source_effectiveness"
WHERE "EffectivenessRunId" = 'RSEFF_MA50_D_H20';

SELECT COUNT(*) AS Runs
FROM "CherryMon"."main"."cal_rs_source_effectiveness_run"
WHERE "EffectivenessRunId" = 'RSEFF_MA50_D_H20';
```

PASS when there is no duplicate error, row count is unchanged and Runs=1.

---

## Seq 10 — CONFIRMATION role real-data smoke

Create RSI14_D ablation:

```powershell
python scripts/run_rs_v2_3_evaluation.py --tickers MWG,FPT,HPG --start 2026-01-01 --end 2026-07-31 --snapshot-step 5 --horizon-bars 20 --model-version RS_V2_4_ABL_RSI14_D_H20 --exclude-source-keys RSI14_D --run-id RSV24_ABL_RSI14_D_H20
```

Calculate effectiveness:

```powershell
python scripts/run_rs_v2_4_source_effectiveness.py --baseline-run RSV24_BASE_H20 --ablation-run RSV24_ABL_RSI14_D_H20 --source-key RSI14_D --source-family MOMENTUM_CONFIRMATION --source-role CONFIRMATION --scope-type SOURCE_CONFIG --run-id RSEFF_RSI14_D_H20
```

PASS when:
- AttributionMode=MARGINAL_ONLY;
- TouchRate/HoldRateGivenTouch/BreakRateGivenTouch/RetestRateGivenBreak/DirectionalEdgePct are NULL;
- recommendation is CONFIRM_ONLY/RESEARCH/DROP;
- RSI is never reclassified to LEVEL.

---

## Seq 11 — Multi-horizon contract

Use the MA50_D baseline/ablation/effectiveness pattern for:

```text
5
10
20
40
trading bars
```

H20 is already validated above. Use horizon-specific run IDs for H5/H10/H40.

PASS query:

```sql
SELECT DISTINCT "HorizonBars"
FROM "CherryMon"."main"."vw_RS_Source_Effectiveness"
WHERE "SourceKey" = 'MA50_D'
ORDER BY "HorizonBars";
```

Expected after matrix completion:

```text
5
10
20
40
```

No averaging into one runtime weight is allowed.

---

## Seq 12 — Source Promotion Gate dry-run

```powershell
python scripts/promote_rs_v2_4_source.py --effectiveness-run RSEFF_MA50_D_H20
```

PASS when output includes outcome, ticker coverage, positive ticker ratio, average score/lifts/stability, reasons, apply_requested=false and runtime_mutation=false.

Any evidence-driven outcome is valid:

```text
APPROVED_FOR_INTEGRATION
TICKER_SELECTIVE
RESEARCH
REJECTED
```

Verify dry-run creates no audit mutation by comparing before/after count in sys_rs_source_promotion_audit.

Do NOT use --apply during release validation.

---

## Seq 13 — Default runtime compatibility smoke

```powershell
python -c "from datetime import date; from src.calcEngine.levelLadder import build_level_ladder; r=build_level_ladder('MWG',as_of_date=date(2026,8,28)); print(r.model_version,r.current_price,[(x.rank,x.price,x.strength_score) for x in r.support_levels],[(x.rank,x.price,x.strength_score) for x in r.resistance_levels])"
```

PASS when:
- model_version=RS_V2_4_BASELINE;
- runtime builds successfully;
- no research filter is applied by default;
- proximity/Strength invariants remain valid.

---

## Seq 14 — NiceGUI smoke

```powershell
python src\webapp\NiceGUI_chart.py
```

PASS when:
- header shows V2.4 Source Effectiveness / Indicator Promotion governance;
- Refresh works;
- notification shows RS_V2_4_BASELINE;
- existing MA/BB/structural/Volume Profile ladder remains visible;
- effectiveness results are not automatically used as runtime weights;
- no stale V2.3 header/empty-state remains.

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
FAIL       → record exact V2.4 failure and STOP
BLOCKED    → record dependency/data/environment blocker and STOP
REGRESSION → revert V2.4 release and STOP
```

## Required Result Summary

```text
Seq 1   Git sync
Seq 2   Migration + idempotency
Seq 3   Preflight
Seq 4   Pytest
Seq 5   V2.3 golden regression
Seq 6   V2.4 baseline H20
Seq 7   MA50_D ablation H20
Seq 8   Source Effectiveness + public view
Seq 9   Effectiveness idempotency
Seq 10  CONFIRMATION role smoke
Seq 11  Multi-horizon
Seq 12  Source Promotion Gate dry-run
Seq 13  Default runtime compatibility
Seq 14  NiceGUI

Final Verdict:
Action:
Notes:
```