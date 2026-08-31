---
applyTo: "**/*.py,tests/**/*.py,tests/**/*.md,scripts/**/*.py"
---

# CherryStock Testing & Validation Instructions

This file owns repository-wide test, validation, execution-verification and completion rules.

## Core Principle

Every test task must converge to a finite result.

Default execution model:

~~~text
ONE target behavior
→ ONE focused change or test
→ ONE execution
→ ONE verdict
→ STOP or explicit handoff
~~~

Do not continue automatically into a new hypothesis, refactor, optimization or unrelated failure after the requested objective has been decided.

## Required Context

Before generating, changing or executing tests:

1. Read .github/copilot-instructions.md.
2. Read .github/agents/TestEngineer.agent.md for test-design or test-execution work.
3. Read matching domain instructions.
4. Read relevant architecture/spec/ADR docs from docs/00_HOME.md.
5. Inspect the production code under test.
6. Inspect the nearest existing tests and reuse project patterns.

Do not invent test conventions when repository examples already exist.

## Test Scope Contract

Before writing tests, define:

~~~text
Target: <single behavior/function/bug being validated>

In scope:
- ...

Out of scope:
- ...
~~~

The agent MUST NOT expand scope unless the user explicitly asks, or the current test cannot run because of a direct blocking dependency.

If blocked, report the blocker. Do not silently turn the task into a broader investigation.

## Anti-Loop Rules

### No hypothesis chaining

Do not do:

~~~text
H1 fails
→ automatically test H2
→ automatically test H3
→ refactor
→ benchmark
→ continue forever
~~~

Do:

~~~text
H1
→ test
→ PASS / FAIL / BLOCKED
→ STOP
~~~

A next hypothesis requires a new explicit task or a test plan that clearly allows continuation.

### No self-repeating analysis

If the same conclusion, command, error or proposed edit has already appeared once without new evidence, do not repeat it.

After two materially identical failures:
- stop retrying;
- capture the exact error;
- classify as BLOCKED or FAIL;
- report the next required input.

### Retry budget

Default maximum:
- command retry: 2 attempts;
- test rerun after a code fix: 2 attempts;
- alternate implementation attempts for the same defect: 2 attempts.

A retry is allowed only when something materially changed:
- code;
- environment;
- fixture/config;
- corrected command.

Never rerun the same failing command unchanged merely to see if it works.

### No speculative execution

Do not edit files just because they might help.

Every edit must map directly to:
- the stated target behavior; or
- a failing assertion/evidence from the current scope.

### Stop conditions

Stop immediately when any one is true:
- requested acceptance criteria pass;
- requested hypothesis is disproved;
- two equivalent attempts fail without new evidence;
- environment/dependency prevents further validation;
- continuing would require changing out-of-scope code;
- user-defined stop condition is reached.

## Minimum Test Cases

When applicable, validate:
- happy path;
- empty input;
- invalid/missing required input;
- boundary values;
- dependency/database/file/API failure;
- idempotency for write/upsert workflows;
- transaction behavior for multi-step writes;
- duplicate/null/key constraints for data pipelines.

Do not mechanically generate all categories. Only include cases relevant to the behavior being changed.

For a narrow bug fix, prefer a small regression test over a large generic matrix.

## Test Design Rules

Each test must have:
1. Purpose.
2. Preconditions/fixture.
3. Action.
4. Expected result.
5. Deterministic pass/fail assertion.

Prefer Arrange / Act / Assert.

Avoid:
- vague visual checks without criteria;
- tests with multiple unrelated purposes;
- unnecessary coupling to implementation details;
- sleep-based timing when deterministic synchronization exists;
- duplicated production business logic inside tests.

## Test Selection

Use this order:
1. Most focused existing test.
2. New/updated regression test for changed behavior.
3. Related module/package suite if practical.
4. Broader suite only when justified by impact.

Typical commands:

~~~powershell
python -m pytest tests/path/test_module.py -v
python -m pytest tests/path -v
~~~

Use the project's intended Python environment.

Do not run the full suite by default for a tiny isolated experiment unless impact requires it.

## Runtime / UI Performance Testing

For UI, browser, performance or interaction bugs, pytest alone is insufficient.

A runbook MUST specify:
- exact UI location;
- exact interaction;
- duration/repetition;
- before/after expectation;
- PASS criteria;
- FAIL criteria;
- regression checks;
- explicit STOP action.

For a single-hypothesis performance test:

~~~text
CHANGE
→ RUN
→ MANUAL TEST
→ VERDICT
→ KEEP or REVERT
→ STOP
~~~

Do not automatically continue to the next performance hypothesis.

## Failure Handling

If a test fails:
1. Capture exact failure.
2. Classify it as current-change, environment/fixture, unrelated pre-existing failure, or blocker.
3. Apply one focused correction when justified.
4. Rerun only the failed/focused test.
5. Respect retry budget.
6. Stop with FAIL/BLOCKED if no new evidence appears.

Do not broaden implementation to make unrelated failures pass.

## Standalone Execution

For changed callable workflows, provide a reproducible command.

Prefer an existing project entry point.

If none is suitable:

~~~powershell
python -c "from package.module import function_name; function_name()"
~~~

Create scripts/run_<function_name>.py only when a one-liner is impractical.

The script must import production code and must not duplicate business logic.

## Test Plan Markdown Rules

Files under tests ending in .md are execution runbooks, not open-ended research documents.

Every test runbook should contain:
1. Target.
2. Scope.
3. Exact files allowed to change.
4. Exact change.
5. Exact command.
6. Manual/automated test steps.
7. PASS criteria.
8. FAIL criteria.
9. Rollback/keep action.
10. STOP condition.
11. Required output format.

For small/local LLMs, strongly prefer imperative instructions and finite branches.

Recommended wording:

~~~text
Do X.
Run Y.
If PASS: keep and stop.
If FAIL: revert and stop.
Do not investigate another cause.
~~~

Avoid wording such as:
- continue investigating;
- try other possible causes;
- iterate until solved;
- analyze further;
- explore alternatives;

unless the user explicitly requested an open investigation.

## Execution Log Format

For narrow tests use:

~~~text
Test
----
Target:
Command:
Result: PASS / FAIL / BLOCKED

Evidence:
- ...

Action:
KEEP / REVERT / FIX ONCE / STOP
~~~

Do not add long speculative reasoning to execution logs.

## Completion Checklist

Before completion confirm:
- relevant instructions were read;
- target and scope were explicit;
- test maps to actual production behavior;
- focused test was executed where possible;
- no out-of-scope refactor was introduced;
- retry budget was respected;
- PASS/FAIL/BLOCKED is explicit;
- rollback/keep action is explicit;
- reproducible execution command is available;
- no unverified success claim was made;
- execution stopped when the requested objective was decided.
