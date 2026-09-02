# R/S V2.4 BB Negative LOWER — Local Agent Validation

## 1. Objective

Validate the focused BB provider bug fix:

```text
finite Bollinger Band PRICE_LEVEL <= 0
    -> skip candidate
    -> do not crash the whole ladder/evaluation
```

This is an independent defect from the Volume Profile warm-up fix.

The original H5 full-evaluation failure was:

```text
ValueError: Invalid BB value for ConfigId=2: -0.41172686931244584
```

## 2. Runbook Location and Branch Workflow

This runbook lives on `main`.

Start from repository root:

```powershell
git fetch origin
git switch main
git pull origin main
```

Then switch to the BB bug branch created for this fix:

```powershell
git fetch origin
git switch fix/rs-v2-4-bb-negative-lower
git pull origin fix/rs-v2-4-bb-negative-lower
```

Execute Sequences 1-8 on the bug branch.

After validation, always return local repository to `main`:

```powershell
git fetch origin
git switch main
git pull origin main
```

## 3. Files Under Test

Allowed production file:

```text
src/calcEngine/levelLadder.py
```

Allowed automated test file:

```text
tests/test_rs_ladder.py
```

Reference change request:

```text
docs/ChangeRequest/CR_RS_V2_4_BB_Negative_Lower_Handling.md
```

Do not change:

```text
src/calcEngine/volumeProfile.py
src/calcEngine/rsEvaluation.py
src/calcEngine/rsSourceEffectiveness.py
scripts/promote_rs_v2_4_source.py
```

unless a new independent defect is proven.

## 4. Expected Domain Contract

For Bollinger Band LEVEL values:

```text
finite value > 0
    -> valid LEVEL candidate

finite value <= 0
    -> invalid tradable PRICE_LEVEL
    -> SKIP candidate

NaN / Infinity
    -> data defect
    -> RAISE

invalid ValueSemantic
    -> contract defect
    -> RAISE
```

Do not change the BB formula itself.

## 5. Sequence 1 — Working Tree

```powershell
git status
git branch --show-current
```

Expected:

```text
fix/rs-v2-4-bb-negative-lower
```

Pre-existing untracked diagnostic scripts may remain. Do not add them.

## 6. Sequence 2 — Compile

```powershell
python -m py_compile src/calcEngine/levelLadder.py
```

Expected: PASS.

## 7. Sequence 3 — Focused BB Tests

Run:

```powershell
python -m pytest tests/test_rs_ladder.py -v
```

PASS criteria include:

- positive LOWER/MIDDLE/UPPER candidates still load;
- negative LOWER is skipped;
- zero BB level is skipped;
- NaN/Infinity still raises;
- semantic validation still raises where expected;
- existing ladder tests remain PASS.

## 8. Sequence 4 — Golden Runtime Regression

Run:

```powershell
python scripts/run_rs_v2_3_golden.py
```

Expected:

```text
passed = true
```

If golden regression fails:

```text
Final Verdict = REGRESSION
Action = STOP
```

## 9. Sequence 5 — Confirm Production Diff Scope

Run:

```powershell
git diff origin/main...HEAD -- src/calcEngine/levelLadder.py tests/test_rs_ladder.py
```

Then:

```powershell
git diff --name-only origin/main...HEAD
```

Expected bug PR scope:

```text
src/calcEngine/levelLadder.py
tests/test_rs_ladder.py
```

No unrelated production files.

## 10. Sequence 6 — Retry Historical Evaluation Path

Important: the BB fix depends on the Volume Profile warm-up fix to reach this point.

Use the branch that contains the BB fix after it has been based on the latest required evaluation fix. If the H5 command hits the old Volume Profile history error instead of BB behavior, classify as dependency BLOCKED, not BB failure.

Stop MCP/DuckDB writer if needed.

Run the same bounded H5 monthly validation command:

```powershell
python scripts/run_rs_v2_4_full_evaluation.py `
  --start 2023-07-04 `
  --end 2026-07-03 `
  --horizons 5 `
  --snapshot-step 5 `
  --promotion-mode skip `
  --run-month 2026-09 `
  --run-prefix RSV24FULL_202609_E20260703_S5_U75673AFB
```

PASS for the BB defect when the process does NOT fail with:

```text
Invalid BB value for ConfigId=...
```

The expected behavior is that non-positive BB candidates are skipped and processing continues.

If another independent defect appears later, report it separately.

## 11. Sequence 7 — Diagnostic Log / Evidence

Capture at least one evidence item proving a negative BB row was skipped rather than raised.

Acceptable evidence:

```text
log line containing ticker/config/component/value
```

or a focused unit test showing candidate list excludes the non-positive component while preserving valid components.

Affected examples previously observed:

```text
CTP
GEE
L40
THD
VIC
VIW
VVS
```

## 12. Sequence 8 — Re-run H5 if Completed Run Exists

If the previous command reaches a completed H5 baseline, rerun the exact same command.

Expected:

```text
[RS-V2.4-FULL] REUSE baseline H5
```

This proves the bug fix did not break persistence/resume.

## 13. Acceptance Criteria

All required:

```text
[ ] compile PASS
[ ] tests/test_rs_ladder.py PASS
[ ] negative BB LOWER no longer crashes provider
[ ] finite BB <= 0 is skipped
[ ] positive BB components remain candidates
[ ] NaN/Infinity still raises
[ ] ValueSemantic validation remains strict
[ ] golden regression PASS
[ ] diff scope limited to levelLadder.py + test_rs_ladder.py
[ ] H5 historical path no longer fails on Invalid BB value
[ ] no scoring/effectiveness/promotion formula change
```

## 14. Failure Classification

FAIL:
- negative/zero BB still raises;
- positive valid BB is accidentally removed;
- malformed values become silently swallowed.

REGRESSION:
- golden runtime changes unexpectedly;
- R/S scoring behavior outside invalid-BB candidate removal changes.

BLOCKED:
- Volume Profile warm-up dependency not yet merged;
- DuckDB lock;
- environment/dependency issue.

## 15. Final Report Format

Return exactly:

```text
## Final Verdict: PASS | FAIL | BLOCKED | REGRESSION

Action: KEEP | FIX ONCE | REVERT | STOP

### Evidence
- Compile:
- Focused pytest:
- Golden regression:
- Negative BB skip test:
- NaN/Infinity guard:
- H5 baseline:
- Resume:
- Diff scope:
- Production code changed during test: YES | NO

### Notes
- ...
```

Expected success:

```text
## Final Verdict: PASS

Action: KEEP
```

Do not merge the BB bug PR before local validation PASS.

## 16. Final Step — Return to main

After reporting the verdict:

```powershell
git fetch origin
git switch main
git pull origin main
```

Verify:

```powershell
git branch --show-current
git status
```

Expected current branch:

```text
main
```
