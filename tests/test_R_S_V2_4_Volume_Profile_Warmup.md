# R/S V2.4 Volume Profile Warm-up — Fast Bug Validation

## Objective

Validate only the warm-up defect fixed by PR #12:

```text
insufficient Volume Profile history: < 30
```

Bug acceptance target:

```text
sampled snapshot not mature for VOLUME_PROFILE
    -> skip snapshot
    -> do not shift sampling cadence
    -> do not weaken live Volume Profile runtime validation
```

This runbook is a **bug gate**, not a full V2.4 release validation.

Full 340-ticker / multi-horizon execution is explicitly out of scope here and belongs to post-merge monthly validation.

## Branch Workflow

Runbook lives on `main`.

Synchronize main first:

```powershell
git fetch origin
git switch main
git pull origin main
```

Switch to bug branch:

```powershell
git fetch origin
git switch fix/rs-evaluation-volume-profile-warmup-code
git pull origin fix/rs-evaluation-volume-profile-warmup-code
```

## Files Under Test

Production:

```text
src/calcEngine/rsEvaluation.py
scripts/run_rs_v2_3_evaluation.py
src/Orchestrator/rs_v2_4_full_evaluation.py
```

Automated tests:

```text
tests/test_rs_evaluation.py
tests/test_rs_v2_4_full_evaluation.py
```

Must remain unchanged:

```text
src/calcEngine/volumeProfile.py
src/calcEngine/levelLadder.py
```

## Sequence 1 — Compile

```powershell
python -m py_compile src/calcEngine/rsEvaluation.py scripts/run_rs_v2_3_evaluation.py src/Orchestrator/rs_v2_4_full_evaluation.py
```

PASS: no SyntaxError.

## Sequence 2 — Focused Automated Tests

```powershell
python -m pytest tests/test_rs_evaluation.py tests/test_rs_v2_4_full_evaluation.py -v
```

PASS must cover:

```text
warm-up snapshot filtering
sampling cadence does not shift
no warm-up gate when VOLUME_PROFILE disabled
monthly expected_snapshot_count alignment
active ticker status='Y'
resume compatibility
```

## Sequence 3 — Golden Regression

```powershell
python scripts/run_rs_v2_3_golden.py
```

PASS:

```text
passed = true
```

If golden fails:

```text
Final Verdict = REGRESSION
Action = STOP
```

## Sequence 4 — Minimal Real-data Smoke

Do NOT run 340 tickers.

Use a small real-data ticker set and short window that is sufficient to exercise historical snapshot selection:

```powershell
python scripts/run_rs_v2_3_evaluation.py `
  --tickers AAH,MWG `
  --start 2023-07-04 `
  --end 2023-10-31 `
  --snapshot-step 5 `
  --horizon-bars 5 `
  --model-version RS_V2_4_BASELINE `
  --run-id RSV24_WARMUP_FAST_SMOKE
```

PASS when:

- command does not fail with `insufficient Volume Profile history`;
- command reaches evaluation summary/persistence;
- output contains `warmup_skipped_snapshots`;
- snapshots > 0.

If the selected short-history ticker no longer reproduces warm-up conditions because local data changed, unit tests remain the authoritative defect proof; use any one active ticker known to have <30 valid VP bars at an early sampled date.

## Sequence 5 — Runtime Safety / Diff Scope

```powershell
Select-String -Path .\src\calcEngine\volumeProfile.py -Pattern "min_records: int = 30"
```

Expected:

```text
min_records: int = 30
```

Then:

```powershell
git diff --name-only origin/main...HEAD
```

Expected production/test scope is limited to PR #12 files.

No change is allowed to live Volume Profile validation.

## Acceptance Criteria

```text
[ ] compile PASS
[ ] focused pytest PASS
[ ] golden regression PASS
[ ] minimal real-data smoke PASS
[ ] warmup_skipped_snapshots observable
[ ] VolumeProfile min_records remains 30
[ ] sampling cadence unchanged
[ ] no runtime scoring change
[ ] no unrelated production-code change
```

## Explicitly Not Required for PR #12

Do NOT run as a PR gate:

```text
340-ticker H5 baseline
H5/H10/H20/H40 matrix
SOURCE_CONFIG ablation matrix
SOURCE_FAMILY ablation matrix
full Source Effectiveness refresh
Promotion Gate matrix
NiceGUI
full monthly resume verification
```

These belong to post-merge monthly validation.

## Final Report

```text
## Final Verdict: PASS | FAIL | BLOCKED | REGRESSION

Action: KEEP | FIX ONCE | REVERT | STOP

### Evidence
- Compile:
- Focused pytest:
- Golden regression:
- Minimal real-data smoke:
- warmup_skipped_snapshots:
- VolumeProfile min_records:
- Diff scope:
- Production code changed during test: YES | NO
```

Expected:

```text
## Final Verdict: PASS

Action: KEEP
```

## Final Step — Return to main

Always finish with:

```powershell
git fetch origin
git switch main
git pull origin main
git branch --show-current
git status
```

Expected branch:

```text
main
```
