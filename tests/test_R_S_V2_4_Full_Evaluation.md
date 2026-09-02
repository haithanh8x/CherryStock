# R/S V2.4 Monthly Full Evaluation — Local Cross-check

## Target

Validate one objective:

> scripts/run_rs_v2_4_full_evaluation.py correctly orchestrates a bounded monthly Source Effectiveness run by reusing existing V2.3/V2.4 child runners, preserving dry-run promotion and resumable evidence contracts.

## Scope

In scope:

- CLI/import contract;
- automatic safe evaluation window;
- deterministic run IDs;
- source/family selection;
- one-source H20 smoke;
- resume behavior;
- public effectiveness output.

Out of scope:

- changing R/S scoring formulas;
- changing Source Effectiveness formulas;
- changing Promotion Gate thresholds;
- automatic production source integration;
- full market monthly execution during this validation.

## Production Files

~~~text
scripts/run_rs_v2_4_full_evaluation.py
src/Orchestrator/rs_v2_4_full_evaluation.py
scripts/run_rs_v2_3_evaluation.py
scripts/run_rs_v2_4_source_effectiveness.py
scripts/promote_rs_v2_4_source.py
~~~

## Automated Test File

~~~text
tests/test_rs_v2_4_full_evaluation.py
~~~

## Allowed Fix Scope

Only:

~~~text
scripts/run_rs_v2_4_full_evaluation.py
src/Orchestrator/rs_v2_4_full_evaluation.py
tests/test_rs_v2_4_full_evaluation.py
docs/runbook/RS_V2_4_Monthly_Full_Evaluation.md
docs/architecture/RS_Source_Effectiveness.md
~~~

Do not change V2.4 scoring/effectiveness/promotion business logic.

## Sequence 1 — Sync

~~~powershell
git fetch origin
git switch feature/rs-v2-4-full-evaluation
git pull origin feature/rs-v2-4-full-evaluation
~~~

PASS when branch is current and working tree is clean before local validation.

## Sequence 2 — CLI Compile / Unit Tests

~~~powershell
python -m py_compile scripts/run_rs_v2_4_full_evaluation.py src/Orchestrator/rs_v2_4_full_evaluation.py
python -m pytest tests/test_rs_v2_4_full_evaluation.py -v
~~~

PASS when compile succeeds and all focused unit tests pass.

## Sequence 3 — Child Runner Presence

~~~powershell
Test-Path .\scripts\run_rs_v2_3_evaluation.py
Test-Path .\scripts\run_rs_v2_4_source_effectiveness.py
Test-Path .\scripts\promote_rs_v2_4_source.py
~~~

PASS when all three return True.

## Sequence 4 — Plan-only

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py --plan-only
~~~

PASS when output contains:

~~~text
monthly_full_evaluation_plan
run_prefix
start
evaluation_end
latest_data_date
future_outcome_bars_reserved = 40
ticker_count > 0
horizons = 5,10,20,40
promotion_mode = dry-run
plan_only = true
~~~

Also verify:

~~~text
evaluation_end < latest_data_date
~~~

No baseline/effectiveness child run should execute in plan-only mode.

## Sequence 5 — Focused One-source Smoke

Use a unique smoke prefix:

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py --tickers MWG,FPT,HPG --horizons 20 --only-source-keys MA50_D --scopes SOURCE_CONFIG --promotion-mode dry-run --run-prefix RSV24FULL_SMOKE_20260902
~~~

PASS when terminal output contains:

~~~text
monthly_full_evaluation_status = COMPLETED
ticker_count = 3
source_count = 1
horizons = [20]
promotion_mode = dry-run
public_view = "CherryMon"."main"."vw_RS_Source_Effectiveness"
~~~

A Source Promotion outcome of RESEARCH/TICKER_SELECTIVE/REJECTED is allowed. It is evidence, not an orchestration failure.

## Sequence 6 — Persistence Check

~~~powershell
python -c "from src.Ults.DuckLib import DuckDBManager; m=DuckDBManager(read_only=True); c=m.get_connection(); print(c.sql(\"SELECT \\\"Ticker\\\",\\\"SourceKey\\\",\\\"HorizonBars\\\",\\\"Recommendation\\\",\\\"EffectivenessRunId\\\" FROM \\\"CherryMon\\\".\\\"main\\\".\\\"vw_RS_Source_Effectiveness\\\" WHERE \\\"SourceKey\\\"='MA50_D' AND \\\"HorizonBars\\\"=20 ORDER BY \\\"Ticker\\\"\").df()); m.close_connection()"
~~~

PASS when MWG/FPT/HPG rows are readable for MA50_D H20 after the smoke.

## Sequence 7 — Resume

Run the exact same smoke command again:

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py --tickers MWG,FPT,HPG --horizons 20 --only-source-keys MA50_D --scopes SOURCE_CONFIG --promotion-mode dry-run --run-prefix RSV24FULL_SMOKE_20260902
~~~

PASS when completed evaluation/effectiveness child runs are reported as REUSE rather than recalculated.

Promotion dry-run may execute again because it is read-only and non-persistent.

## Sequence 8 — Resume Collision Guard

Run the same prefix with a different horizon:

~~~powershell
python scripts/run_rs_v2_4_full_evaluation.py --tickers MWG,FPT,HPG --horizons 10 --only-source-keys MA50_D --scopes SOURCE_CONFIG --promotion-mode dry-run --run-prefix RSV24FULL_SMOKE_20260902
~~~

This creates different H10 child IDs and is allowed.

Then do not manually rename or reuse a H20 child run ID for incompatible data. The unit test covers the metadata collision guard.

## Sequence 9 — Runtime Regression

~~~powershell
python scripts/run_rs_v2_3_golden.py
~~~

PASS when existing golden regression remains PASS.

The monthly orchestrator must not alter default R/S runtime behavior.

## Final Verdict

Return exactly one:

~~~text
PASS
FAIL
BLOCKED
REGRESSION
~~~

Action:

~~~text
KEEP
REVERT
FIX ONCE
STOP
~~~

Expected successful release-validation output:

~~~text
Final Verdict: PASS
Action: KEEP
~~~

## Stop Condition

If Sequences 2–7 pass and golden regression passes:

~~~text
PASS
KEEP
STOP
~~~

If one failure is directly caused by the new orchestrator, allow one focused fix and one focused rerun.

Do not refactor R/S V2.4 business logic during this test.
