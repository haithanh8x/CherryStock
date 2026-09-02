# R/S V2.4 BB Negative LOWER — Fast Bug Validation

## Objective

Validate only the BB provider defect fixed by PR #13:

```text
finite BB PRICE_LEVEL <= 0
    -> skip candidate
    -> do not crash ladder/evaluation
```

This runbook is a **bug gate**, not a full V2.4/monthly validation.

Full 340-ticker evaluation is out of scope and will run once after PR #12 + PR #13 are merged.

## Branch Workflow

Runbook lives on `main`.

Synchronize main:

```powershell
git fetch origin
git switch main
git pull origin main
```

Switch to stacked BB branch:

```powershell
git fetch origin
git switch fix/rs-v2-4-bb-negative-lower
git pull origin fix/rs-v2-4-bb-negative-lower
```

PR #13 is stacked on the PR #12 warm-up branch so the minimal historical smoke can exercise both fixes.

## Files Under Test

Production:

```text
src/calcEngine/levelLadder.py
```

Automated test:

```text
tests/test_rs_ladder.py
```

Expected domain contract:

```text
finite BB > 0
    -> KEEP candidate

finite BB <= 0
    -> SKIP candidate

NaN / Infinity
    -> RAISE

invalid ValueSemantic
    -> RAISE
```

## Sequence 1 — Compile

```powershell
python -m py_compile src/calcEngine/levelLadder.py
```

PASS: no SyntaxError.

## Sequence 2 — Focused BB Tests Only

Do not run the full ladder suite unless needed.

```powershell
python -m pytest tests/test_rs_ladder.py -k "bb_provider" -v
```

PASS must prove:

```text
negative LOWER skipped
zero level skipped
positive MIDDLE/UPPER preserved
NaN/+Inf/-Inf still rejected
invalid ValueSemantic still rejected
```

If focused tests pass, optionally run full `tests/test_rs_ladder.py` only if the local agent detects shared helper changes.

## Sequence 3 — Golden Regression

```powershell
python scripts/run_rs_v2_3_golden.py
```

PASS:

```text
passed = true
```

## Sequence 4 — Minimal Real-data Reproduction

Use one ticker previously proven to contain a negative BB LOWER and a short window around the observed condition.

Primary ticker:

```text
THD
```

Run:

```powershell
python scripts/run_rs_v2_3_evaluation.py `
  --tickers THD `
  --start 2026-04-01 `
  --end 2026-06-30 `
  --snapshot-step 5 `
  --horizon-bars 5 `
  --model-version RS_V2_4_BASELINE `
  --run-id RSV24_BB_NEGATIVE_FAST_SMOKE
```

PASS when:

- command does not fail with `Invalid BB value for ConfigId=...`;
- evaluation continues after a non-positive BB value;
- at least one negative-BB skip is proven by log or focused unit-test evidence.

Fallback tickers if local data differs:

```text
CTP,GEE,L40,VIC,VIW,VVS
```

Do NOT broaden to 340 tickers just to reproduce this defect.

## Sequence 5 — Diff Scope

Because PR #13 is stacked, compare specifically against its base branch:

```powershell
git diff --name-only origin/fix/rs-evaluation-volume-profile-warmup-code...HEAD
```

Expected:

```text
src/calcEngine/levelLadder.py
tests/test_rs_ladder.py
```

No unrelated production changes.

## Acceptance Criteria

```text
[ ] compile PASS
[ ] focused bb_provider pytest PASS
[ ] negative BB <= 0 skipped
[ ] positive BB candidates preserved
[ ] NaN/Infinity still raises
[ ] ValueSemantic validation still strict
[ ] golden regression PASS
[ ] THD minimal real-data smoke does not fail on negative BB
[ ] diff scope limited to levelLadder.py + test_rs_ladder.py
[ ] no scoring/effectiveness/promotion formula change
```

## Explicitly Not Required for PR #13

Do NOT run as a PR gate:

```text
340-ticker H5 baseline
full H5/H10/H20/H40 matrix
ablation matrix
Source Effectiveness matrix
Promotion Gate matrix
NiceGUI
full monthly resume test
```

These are release/monthly validation responsibilities.

## Final Report

```text
## Final Verdict: PASS | FAIL | BLOCKED | REGRESSION

Action: KEEP | FIX ONCE | REVERT | STOP

### Evidence
- Compile:
- Focused BB pytest:
- Negative BB skip:
- NaN/Infinity guard:
- Golden regression:
- THD real-data smoke:
- Diff scope:
- Production code changed during test: YES | NO
```

Expected:

```text
## Final Verdict: PASS

Action: KEEP
```

## Merge Order After PASS

```text
1. PR #12 — warm-up fix
2. PR #13 — BB negative LOWER fix
3. Full monthly validation once on main
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
