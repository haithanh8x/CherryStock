---
applyTo: "**/*.py,tests/**/*.py,scripts/**/*.py"
---

# Testing and Validation Instructions

This file owns test, execution-verification and completion rules.

## Required validation mindset
Do not claim implementation success based only on code review. Run the most relevant available test or real execution.

## Minimum cases
When applicable, validate:
- happy path;
- empty input;
- invalid/missing required input;
- boundary values;
- dependency/database/file/API failure;
- idempotency for write/upsert workflows;
- transaction behavior for multi-step writes;
- duplicate/null/key constraints for data pipelines.

## Test selection
1. Run the most focused existing test first.
2. Add/update focused tests when behavior changes.
3. If focused tests pass, run the related module/package suite when practical.
4. Run lint/type-check if repository configuration exists and the changed area is covered.

Typical commands:

```powershell
python -m pytest tests/path/test_module.py -v
python -m pytest tests/path -v
```

Use the project's virtual environment/interpreter when required.

## Failure handling
If a test fails:
- identify whether the failure is caused by the change, stale fixture/environment or an existing unrelated problem;
- fix change-related failures;
- rerun the failing test;
- do not stop after the first failure without analysis.

If execution cannot be performed, report the exact limitation and do not state that the change is verified.

## Standalone execution
For changed callable workflows, provide a reproducible command. Prefer an existing project entry point. If none is suitable, use:

```powershell
python -c "from package.module import function_name; function_name()"
```

or create a focused `scripts/run_<function_name>.py` wrapper only when dependencies/config make a one-liner impractical.

The script must import production code, not duplicate business logic.

## Completion checklist
Before completion confirm:
- relevant instructions were read;
- architecture/conventions were followed;
- error handling is explicit;
- no unnecessary duplication/hard-coded environment configuration was introduced;
- tests were actually executed where possible;
- idempotency was tested when applicable;
- a reproducible execution command is available.