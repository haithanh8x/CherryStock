# IMP-REQ-0026 — SmartMoneyStrategy Runbook Validation Lessons

## Purpose

Historical implementation/validation note for the first local execution of:

`docs/runbook/SmartMoneyStrategy_V1.md`

on 2026-09-12.

This note is evidence/context only. It is **not** the canonical execution contract.

Canonical reusable rules now live in:

- `docs/development/Python_Execution_Conventions.md`
- `.github/instructions/python.instructions.md`
- `docs/runbook/SmartMoneyStrategy_V1.md`

## Final validation result

```text
Verdict: PASS
Action: KEEP
```

REQ-0026 / SmartMoneyStrategy was subsequently marked functionally validated.

---

## Issue 1 — pytest collection failed because import path was ambiguous

Observed:

```text
ModuleNotFoundError: No module named 'calcEngine'
```

The integration test used top-level imports while the local invocation did not reliably expose the `src` layout during collection.

Resolution incorporated into repository:

- `tests/test_smart_money_integration.py` uses the repository-root `src.*` test import convention;
- `[tool.pytest.ini_options]` in `pyproject.toml` now includes `pythonpath = ["src"]` so production top-level imports inside `src` modules resolve during pytest collection;
- the runbook now runs `--collect-only` checks before classifying integration behavior;
- collection/import error is classified as an import/execution-contract failure, not automatically as `REGRESSION`.

---

## Issue 2 — direct preflight script depended on external PYTHONPATH

Observed when running:

```powershell
python scripts\run_smart_money_preflight.py
```

Error:

```text
ModuleNotFoundError: No module named 'src'
```

Root cause:

A direct script under `scripts/` does not receive the same import path as `python -c` or a repository-root module.

Resolution incorporated into repository:

- `scripts/run_smart_money_preflight.py` now resolves `PROJECT_ROOT` and inserts it into `sys.path` before importing `src.*`;
- canonical runbooks must not require a developer-specific manual `PYTHONPATH` for repository-owned direct scripts;
- the reusable direct-script template is documented in `Python_Execution_Conventions.md`.

---

## Issue 3 — repeated diagnostics violated anti-loop behavior

Observed:

The local agent repeated equivalent `Select-String` / `sys.path` investigation after the error was already known.

Resolution incorporated into repository:

The Python convention and SmartMoneyStrategy runbook now require a finite diagnostic path:

```text
traceback
→ canonical convention
→ ONE known-good neighbor
→ ONE focused correction
→ ONE retest
→ STOP
```

No repeated equivalent grep/path probes without new evidence.

---

## Issue 4 — `python -c` and direct script execution were incorrectly treated as equivalent

Observed:

```powershell
python -c "from src.Ults import DuckLib; ..."
```

worked from repository root while:

```powershell
python scripts\run_smart_money_preflight.py
```

failed before the script bootstrap was fixed.

Resolution incorporated into repository:

The canonical Python execution document now explicitly distinguishes:

- pytest execution;
- repository-root entry points;
- `python -c` / stdin execution from repository root;
- direct `python scripts\x.py` execution.

Runbook authors must identify invocation mode before writing a command.

---

## Governance outcome

The original issue-export file under `tests/` was temporary handoff material. It was removed after reusable lessons were incorporated because repository policy reserves `tests/*.md` for finite test execution material, not postmortem knowledge.

This implementation note remains only to preserve historical rationale and traceability.
