# SmartMoney TradeActionConfidence V1 — Historical Initload & Minimal Validation

- **Requirement:** `REQ-0026`
- **Architecture:** `docs/architecture/SmartMoneyStrategy.md`
- **Public view:** `"CherryMon"."main"."vw_Ticker_SmartMoney"`
- **Field:** `TradeActionConfidenceScore`
- **Validation owner:** `TestEngineer`
- **Goal:** full historical SmartMoney initload with minimum sufficient validation for the additive strategy-confidence field.
- **Current rollout state:** `REPAIR_APPLIED_AWAITING_SINGLE_RERUN`

## 0. Resume from current rollout state — execute this now

The first historical run has already finished with a valid terminal failure at:

```text
Failed HEAD: 726a7f092c9470c104995193dc3d36ecf780bc0e
Historical initload: FAIL
ScoreRows = ViewRows = 1113519
Historical range = 2002-05-22 -> 2026-09-11
InvalidRange = 0
AboveUpstreamConfidence = 326894
NonPassConfidenceMismatch = 0
InvalidTradeAction = 0
Verdict = FAIL
Action = STOP
```

Root cause was confirmed as view-level decimal rounding:

```text
ROUND(LEAST(...), 2)
ROUND(ConfidenceScore, 2)
```

which could round upward and violate:

```text
TradeActionConfidenceScore <= ConfidenceScore
```

The owner-approved one repair has already been applied:

```text
schema repair commit: 84fbcf9a710b4e9bba650a1e2890f88b21244922
regression-test commit: 3c9b016c446c039157fb1fbd02f62bb1a49ae754
focused SmartMoney CI run #38: PASS
```

The repaired public view keeps full calculation precision. UI/report layers may round for display only.

### Do not restart the investigation

At this checkpoint, do **not** rerun the failed HEAD, do not rerun pytest by default, do not run preflight separately, and do not perform another code repair before the repaired historical rerun.

Execute only these steps from repository root.

### Step A — sync and verify repaired code is present

```powershell
git status --short
```

If unexpected local changes exist:

```text
Verdict: BLOCKED
Action: STOP
```

If clean:

```powershell
git fetch origin
git checkout main
git pull --ff-only origin main
git log -1 --oneline

git merge-base --is-ancestor 3c9b016c446c039157fb1fbd02f62bb1a49ae754 HEAD
if ($LASTEXITCODE -ne 0) {
    throw "Required TradeActionConfidence precision regression fix is not present in HEAD."
}
```

PASS when the ancestor check exits `0`.

The exact HEAD may be newer than the repair commits because documentation or auto-sync commits can follow them. Do not require HEAD to equal a hard-coded repair SHA; require the repair/test commit to be an ancestor.

### Step B — consume the one permitted repaired historical rerun

Run exactly once:

```powershell
python scripts\initload\init_reload_smart_money_score.py
```

This is the repaired rerun. Set:

```text
Repair rerun: YES
```

Do not use `scripts\run_smart_money.py --days ...` as a substitute.

The initload itself performs full historical recomputation/upsert and validates the public strategy contract before commit.

Required validation evidence:

```text
ScoreRows > 0
ViewRows = ScoreRows
ViewMinDate = ScoreMinDate
ViewMaxDate = ScoreMaxDate
InvalidRange = 0
AboveUpstreamConfidence = 0
NonPassConfidenceMismatch = 0
InvalidTradeAction = 0
```

If the command fails for the same or another strategy-contract defect:

```text
Verdict: FAIL
Action: STOP
Repair rerun: YES
```

There is **no second repair loop** in this runbook.

### Step C — metadata verification after successful initload

Only when Step B passes:

```powershell
Select-String -Path docs\reference\DB_Metadata.md -Pattern "TradeActionConfidenceScore"
```

Required:

```text
Metadata TradeActionConfidenceScore: YES
```

The initload script performs the metadata export. Never hand-edit `docs/reference/DB_Metadata.md`.

### Terminal result for the current checkpoint

Return only:

```text
SMART MONEY ACTION CONFIDENCE — REPAIRED HISTORICAL RERUN

HEAD: <actual pulled HEAD>
Repair commit present: YES | NO
Historical initload: PASS | FAIL | BLOCKED
Score rows: <count>
View rows: <count>
Historical range: <min date> -> <max date>
InvalidRange: <count>
AboveUpstreamConfidence: <count>
NonPassConfidenceMismatch: <count>
InvalidTradeAction: <count>
Metadata TradeActionConfidenceScore: YES | NO | NOT_VERIFIED
Optional pytest: NOT_RUN
Repair rerun: YES

Verdict: PASS | FAIL | BLOCKED
Action: KEEP | STOP
```

If PASS/KEEP is reached, this rollout is complete and the agent must STOP. Do not add extra validation merely for confidence.

---

## 1. Scope

This runbook makes **historical initial load mandatory**.

Execution path for a fresh rollout is:

```text
sync main
→ full SmartMoney historical initload
→ historical public-contract validation inside the same transaction
→ commit
→ export DB metadata
→ terminal verdict
```

For the current rollout, use **Section 0** because the initial run has already failed, the one repair has already been applied, and only the repaired rerun remains.

The initload recalculates/upserts historical SmartMoney factor/score data using:

```python
refresh_smart_money_score(from_last_day=None)
```

`TradeAction` and `TradeActionConfidenceScore` remain derived public-view fields; they are not persisted as duplicate strategy columns. Full initload is required here to guarantee that the underlying historical SmartMoney score/factor dataset is present and current before the public historical strategy contract is accepted.

`TradeActionConfidenceScore` keeps **full calculation precision** in the public view. Do not round the stored/read contract inside the view because rounding can violate the strict invariant:

```text
TradeActionConfidenceScore <= ConfidenceScore
```

UI/report consumers may round the value for display only.

---

## 2. What the initload script validates automatically

The canonical command is:

```powershell
python scripts\initload\init_reload_smart_money_score.py
```

The script performs, in order:

```text
1. ensure SmartMoney schema + recreate vw_Ticker_SmartMoney
2. full historical factor/score calculation
3. historical upsert
4. validate public historical row coverage
5. validate TradeActionConfidenceScore invariants
6. commit only when validation passes
7. export generated DB metadata
```

Historical validation requires:

```text
ScoreRows > 0
ViewRows = ScoreRows
ViewMinDate = ScoreMinDate
ViewMaxDate = ScoreMaxDate
InvalidRange = 0
AboveUpstreamConfidence = 0
NonPassConfidenceMismatch = 0
InvalidTradeAction = 0
```

Where:

```text
InvalidRange
    → TradeActionConfidenceScore is NULL or outside 0..100

AboveUpstreamConfidence
    → TradeActionConfidenceScore > ConfidenceScore

NonPassConfidenceMismatch
    → DataQualityStatus != PASS but TradeActionConfidenceScore != 0

InvalidTradeAction
    → TradeAction is NULL or not BUY/HOLD/SELL
```

Because validation runs before the UnitOfWork exits, a validation exception prevents the run from being treated as a successful historical deployment.

---

## 3. Fresh rollout — safe sync

Use this section only when there has not already been a failed initial run followed by an approved repair.

Run from repository root:

```powershell
git status --short
```

If unexpected local changes exist:

```text
Verdict: BLOCKED
Action: STOP
```

Do not reset/stash/discard user work automatically.

If clean:

```powershell
git fetch origin
git checkout main
git pull --ff-only origin main
git log -1 --oneline
```

---

## 4. Fresh rollout — mandatory full historical initload

Run:

```powershell
python scripts\initload\init_reload_smart_money_score.py
```

Do **not** replace this with:

```powershell
python scripts\run_smart_money.py --days 1
```

or another incremental checkpoint. This rollout requires historical data to be fully recalculated/upserted.

Expected successful output includes both:

```text
SmartMoney full historical summary: {...}
SmartMoney historical public-contract validation: {...}
```

and ends with:

```text
SmartMoney V1 full historical initload committed; TradeActionConfidenceScore historical contract validated; DB metadata exported.
```

### PASS

The command exits successfully and validation evidence shows:

```text
score_rows > 0
view_rows = score_rows
score_min_date = view_min_date
score_max_date = view_max_date
invalid_range = 0
above_upstream_confidence = 0
non_pass_confidence_mismatch = 0
invalid_trade_action = 0
```

### FAIL / BLOCKED

If the command raises an exception:

```text
Verdict: FAIL | BLOCKED
Action: STOP
```

Capture the exception and printed evidence. Do not retry unchanged and do not bypass the canonical initload with ad-hoc DuckDB writes.

---

## 5. One owner-approved repair budget

A failed run may be repaired **once** only when all of the following are true:

```text
1. root cause is identified from the failed evidence
2. owner explicitly accepts the repair direction
3. the repair changes the root cause, not the validation threshold
4. focused CI/test protects the repaired case
5. the full historical initload is rerun exactly once after pulling the repaired commit
```

For the confirmed precision-cap defect found on historical data:

```text
Root cause:
ROUND(LEAST(...), 2) or ROUND(ConfidenceScore, 2)
can round upward and make TradeActionConfidenceScore > ConfidenceScore.

Accepted repair:
remove view-level rounding and preserve full calculation precision.

Regression protection:
use non-pre-rounded ConfidenceScore values such as 86.135 / 97.135 in strategy tests.
```

Once the repair has been applied, execution moves to **Section 0**. Do not repeat the fresh-rollout sections.

If the same contract fails again after the one repaired rerun:

```text
Verdict: FAIL
Action: STOP
```

No second repair loop is allowed in this runbook.

---

## 6. Metadata verification

The initload already exports metadata. Only verify that the generated reference contains the new public field:

```powershell
Select-String -Path docs\reference\DB_Metadata.md -Pattern "TradeActionConfidenceScore"
```

Required:

```text
TradeActionConfidenceScore present = YES
```

Do not hand-edit `docs/reference/DB_Metadata.md`.

---

## 7. Optional focused pytest

Do **not** run pytest by default when the pulled commit already has green SmartMoney CI and no local SmartMoney strategy code was modified after pull.

Only when CI is unavailable/not green or local code changed:

```powershell
python -m pytest tests\test_smart_money_strategy.py -q
```

Do not automatically expand to integration/full-suite validation for this rollout.

For the current repaired-rerun checkpoint, CI run #38 is already green and therefore:

```text
Optional pytest: NOT_RUN
```

unless local strategy/schema/test code is modified after pulling main.

---

## 8. Generic result format

For a fresh rollout return:

```text
SMART MONEY ACTION CONFIDENCE — HISTORICAL INITLOAD

HEAD: <sha>
Historical initload: PASS | FAIL | BLOCKED
Score rows: <count>
View rows: <count>
Historical range: <min date> -> <max date>
InvalidRange: <count>
AboveUpstreamConfidence: <count>
NonPassConfidenceMismatch: <count>
InvalidTradeAction: <count>
Metadata TradeActionConfidenceScore: YES | NO
Optional pytest: NOT_RUN | PASS | FAIL
Repair rerun: NO | YES

Verdict: PASS | FAIL | BLOCKED
Action: KEEP | STOP
```

PASS requires:

```text
historical initload PASS
ScoreRows > 0
ViewRows = ScoreRows
historical min/max dates match
all four violation counts = 0
metadata contains TradeActionConfidenceScore
```

After the terminal verdict, STOP.

---

## 9. Deliberately skipped extra validation

The historical initload script already owns the minimum deployment gate, so this runbook does not separately run:

```text
smart_money_v1_preflight.sql
tests/test_smart_money_integration.py
full pytest suite
run.py daily pipeline
OOS/backtest evaluation
```

Run those only when their own contracts change or separate evidence indicates a broader regression.
