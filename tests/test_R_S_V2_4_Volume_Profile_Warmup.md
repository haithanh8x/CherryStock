# R/S V2.4 Volume Profile Warm-up Fix — Local Agent Validation

## Objective

Validate the focused fix for:

~~~text
ValueError: insufficient Volume Profile history: 1 < 30
~~~

The fix must make historical evaluation skip sampled snapshots that are not yet mature for enabled providers, without changing live R/S runtime behavior.

Must confirm:
- Volume Profile runtime min_records remains 30;
- sampling cadence remains deterministic;
- immature snapshots are skipped, not rebased;
- monthly expected_snapshot_count uses the same warm-up rule;
- the previously failed H5 baseline can complete;
- persisted SnapshotCount matches the plan;
- rerun can REUSE the completed H5 baseline;
- no R/S scoring, Source Effectiveness or Promotion Gate logic changes.

## Branch Setup

The runbook itself lives on `main`. The production bug fix is isolated on:

~~~text
fix/rs-evaluation-volume-profile-warmup
~~~

Start from repository root and synchronize `main` first:

~~~powershell
git fetch origin
git switch main
git pull origin main
~~~

Then fetch and switch to the bug-fix branch:

~~~powershell
git fetch origin
git switch fix/rs-evaluation-volume-profile-warmup
git pull origin fix/rs-evaluation-volume-profile-warmup
~~~

Expected active branch while executing Sequences 1-9:

~~~text
fix/rs-evaluation-volume-profile-warmup
~~~

## Files Under Test

Production:

~~~text
src/calcEngine/rsEvaluation.py
scripts/run_rs_v2_3_evaluation.py
src/Orchestrator/rs_v2_4_full_evaluation.py
~~~

Tests:

~~~text
tests/test_rs_evaluation.py
tests/test_rs_v2_4_full_evaluation.py
~~~

Do not change unless a separate defect is proven:

~~~text
src/calcEngine/volumeProfile.py
src/calcEngine/levelLadder.py
src/calcEngine/rsSourceEffectiveness.py
scripts/promote_rs_v2_4_source.py
~~~

## Expected Contract

Ticker eligibility remains:

~~~text
raw_lstTicker.status = 'Y'
AND raw_stock_eod exists
AND history >= 500 bars
AND freshness gate passes
~~~

Snapshot eligibility is separate:

~~~text
sample every N bars from requested window
        ↓
check enabled-provider warm-up
        ↓
immature snapshot → SKIP
mature snapshot   → EVALUATE
~~~

Current Volume Profile runtime contract:

~~~text
min_records = 30
window_bars = 120
lookback = max(540 calendar days, window_bars * 3)
~~~

The sampling cadence must stay anchored to the original requested window. Warm-up filtering must not shift the sampling phase.

## Sequence 1 — Working Tree

~~~powershell
git status
git log -1 --oneline
~~~

PASS when the branch is correct and there are no unexpected tracked production changes. Existing user diagnostic scripts may remain untracked; do not add them.

## Sequence 2 — Compile

~~~powershell
python -m py_compile src/calcEngine/rsEvaluation.py scripts/run_rs_v2_3_evaluation.py src/Orchestrator/rs_v2_4_full_evaluation.py scripts/run_rs_v2_4_full_evaluation.py
~~~

Expected: PASS, no SyntaxError.

## Sequence 3 — Focused Pytest

~~~powershell
python -m pytest tests/test_rs_evaluation.py tests/test_rs_v2_4_full_evaluation.py -v
~~~

PASS when all collected tests pass.

Required behaviors covered:

~~~text
provider warm-up snapshot filtering
sampling cadence does not shift
no warm-up gate when VOLUME_PROFILE is disabled
monthly expected_snapshot_count alignment
active ticker status='Y' universe
resume compatibility
~~~

Do not proceed if focused pytest fails.

## Sequence 4 — Golden Runtime Regression

~~~powershell
python scripts/run_rs_v2_3_golden.py
~~~

Expected: PASS.

If golden regression fails:

~~~text
Final Verdict = REGRESSION
Action = STOP
~~~

## Sequence 5 — Plan-only

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py --plan-only
~~~

Expected fields:

~~~text
universe_filter = raw_lstTicker.status='Y'
ticker_count = 340
evaluation_end = 2026-07-03
latest_data_date = 2026-08-28
horizons = 5,10,20,40
snapshot_step = 5
promotion_mode = dry-run
resume = true
expected_snapshot_count > 0
~~~

Previous expected_snapshot_count before warm-up filtering was 50784.

PASS criteria:

~~~text
expected_snapshot_count > 0
expected_snapshot_count <= 50784
~~~

Record the new expected_snapshot_count. It must equal the persisted H5 SnapshotCount later.

## Sequence 6 — Retry Previously Failed H5 Baseline

Before running, stop any MCP/DuckDB process that holds a writer lock.

Run only H5 to validate the failed stage:

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py `
  --start 2023-07-04 `
  --end 2026-07-03 `
  --horizons 5 `
  --snapshot-step 5 `
  --promotion-mode skip `
  --run-month 2026-09 `
  --run-prefix RSV24FULL_202609_E20260703_S5_U75673AFB
~~~

PASS when:
- it does not fail with insufficient Volume Profile history;
- H5 baseline reaches persistence;
- evaluation output contains snapshots;
- evaluation output contains warmup_skipped_snapshots;
- baseline H5 is COMPLETED.

A different independent error must be reported separately.

## Sequence 7 — Verify Persisted H5 Baseline

Run:

~~~sql
SELECT
    "EvaluationRunId",
    "ModelVersion",
    "DatasetStart",
    "DatasetEnd",
    "HorizonBars",
    "TickerCount",
    "SnapshotCount",
    "Status"
FROM "CherryMon"."main"."cal_rs_evaluation_run"
WHERE "EvaluationRunId" =
      'RSV24FULL_202609_E20260703_S5_U75673AFB_BASE_H5';
~~~

Expected:

~~~text
HorizonBars = 5
TickerCount = 340
SnapshotCount > 0
Status = COMPLETED
~~~

Mandatory:

~~~text
persisted SnapshotCount = plan expected_snapshot_count
~~~

If they differ: Final Verdict = FAIL, Action = FIX ONCE.

## Sequence 8 — Resume / REUSE Check

Run the exact same bounded H5 command again:

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py `
  --start 2023-07-04 `
  --end 2026-07-03 `
  --horizons 5 `
  --snapshot-step 5 `
  --promotion-mode skip `
  --run-month 2026-09 `
  --run-prefix RSV24FULL_202609_E20260703_S5_U75673AFB
~~~

Expected near the beginning:

~~~text
[RS-V2.4-FULL] REUSE baseline H5
~~~

PASS when H5 baseline is reused instead of recalculated. The local agent may stop after proving H5 REUSE; do not continue a full source-ablation matrix only for validation.

## Sequence 9 — Runtime Contract Safety

Verify min_records remains 30:

~~~powershell
Select-String -Path .\src\calcEngine\volumeProfile.py -Pattern "min_records: int = 30"
~~~

Then:

~~~powershell
git diff origin/main...HEAD -- src/calcEngine/volumeProfile.py src/calcEngine/levelLadder.py
~~~

Expected: no runtime change in these two files for this fix.

## Acceptance Criteria

~~~text
[ ] compile PASS
[ ] focused pytest PASS
[ ] golden regression PASS
[ ] plan-only PASS
[ ] universe_filter remains raw_lstTicker.status='Y'
[ ] expected_snapshot_count > 0
[ ] expected_snapshot_count <= 50784
[ ] H5 baseline no longer fails on Volume Profile history < 30
[ ] warmup_skipped_snapshots is reported
[ ] H5 baseline persists COMPLETED
[ ] persisted SnapshotCount = plan expected_snapshot_count
[ ] second H5 run reports REUSE baseline H5
[ ] VolumeProfile min_records remains 30
[ ] no R/S scoring change
[ ] no Source Effectiveness formula change
[ ] no Promotion Gate change
~~~

## Failure Classification

FAIL: warm-up selector incorrect, H5 still fails with VP history, SnapshotCount mismatch, or resume broken.

REGRESSION: golden runtime changes, Volume Profile runtime validation weakened, or R/S scoring changed unexpectedly.

BLOCKED: environment-only issue such as DuckDB lock, DB unavailable, or missing dependency.

## Final Report Format

Return exactly:

~~~text
## Final Verdict: PASS | FAIL | BLOCKED | REGRESSION

Action: KEEP | FIX ONCE | REVERT | STOP

### Evidence
- Compile:
- Focused pytest:
- Golden regression:
- Plan ticker_count:
- Plan expected_snapshot_count:
- H5 baseline status:
- H5 persisted SnapshotCount:
- warmup_skipped_snapshots:
- Resume H5:
- VolumeProfile min_records:
- Production code changed during test: YES | NO

### Notes
- ...
~~~

Expected success:

~~~text
## Final Verdict: PASS

Action: KEEP
~~~

After PASS, PR #11 is eligible to merge. Do not merge before local validation PASS.

## Final Step — Return Local Repository to main

After the local agent has completed the validation and captured the Final Verdict, always return the local working copy to `main`.

Run:

~~~powershell
git fetch origin
git switch main
git pull origin main
~~~

Final expected state:

~~~text
current branch = main
working tree = clean, except pre-existing user diagnostic files if any
~~~

Do not leave the local repository on the bug-fix branch after validation.