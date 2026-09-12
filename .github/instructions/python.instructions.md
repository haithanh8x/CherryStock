---
applyTo: "**/*.py,tests/**/*.py,scripts/**/*.py,docs/runbook/**/*.md,docs/development/**/*.md"
---

# CherryStock Python Execution Instructions

For any task that creates or changes Python tests, runnable scripts, repository-root commands or runbook commands, MUST follow:

`docs/development/Python_Execution_Conventions.md`

Do not invent a new import/bootstrap pattern when the repository already defines one.

Before generating a Python command or file:

1. Identify its invocation mode: pytest, repository-root entry point, `python -c`, or direct `python scripts\\x.py` execution.
2. Inspect one known-good neighboring file for the same invocation mode.
3. Ensure the documented command runs from repository root without undocumented developer-specific `PYTHONPATH` setup.
4. For directly executed scripts, make the script own any required repository-path bootstrap.
5. For pytest work, distinguish collection/import failure from behavioral test failure before declaring regression.
6. Use a finite import-error diagnostic and respect the repository anti-loop retry budget.

Technical examples and the preferred script template live only in the canonical development document above.
