# Python Execution & Import Conventions

## Purpose

Define one reproducible convention for CherryStock Python tests, repository-root commands and directly executed scripts.

This document exists because Python resolves imports differently for:

```text
python -m pytest ...
python -c "..."
python run.py
python scripts\some_script.py
```

Agents MUST NOT assume these invocation modes share the same `sys.path`.

Canonical rule:

> A documented command must run from the repository root without requiring an undocumented user-specific `PYTHONPATH`.

If a runnable repository script needs repository paths, the script owns that bootstrap explicitly.

---

## Repository layout

CherryStock uses a `src` layout:

```text
CherryStock/
├─ pyproject.toml
├─ run.py
├─ scripts/
├─ tests/
└─ src/
   ├─ cherrystock/
   ├─ calcEngine/
   ├─ Ults/
   └─ ...
```

`pyproject.toml` declares:

```toml
[tool.setuptools.packages.find]
where = ["src"]
```

Pytest also adds `src` to its Python path so production imports such as `cherrystock`, `calcEngine` and `Ults` resolve deterministically during test collection.

---

# 1. Tests

Run tests from repository root:

```powershell
python -m pytest tests\path\test_module.py -v
```

For new or modified test modules, prefer repository-root imports:

```python
from src.calcEngine.smartMoneyScore import refresh_smart_money_score
from src.cherrystock.infrastructure.database.repositories.smart_money_repository import (
    SmartMoneyRepository,
)
```

Do not depend on a developer having manually set `PYTHONPATH` before pytest starts.

Do not mix import styles casually inside one test file.

Before an integration test is treated as a behavioral regression, verify that pytest can collect it:

```powershell
python -m pytest tests\path\test_module.py --collect-only -q
```

A collection/import error is an execution/import-contract failure. It is not automatically a product regression.

---

# 2. Repository-root entry points

Commands executed from repository root, for example:

```powershell
python run.py
python runMonthly.py
python -c "from src.Ults import DuckLib; DuckLib.exportDuckDB_metadata()"
```

have the repository root available to Python.

Root entry points may therefore use the repository's established `src.*` imports.

Runbook commands using `python -c` MUST state that they are executed from repository root.

---

# 3. Direct scripts under `scripts/`

Important Python behavior:

```powershell
python scripts\some_script.py
```

sets `scripts/` as the script path context. The repository root is not guaranteed to be importable merely because the shell current directory is the repository root.

Therefore a directly executable script MUST NOT rely on an external/manual `PYTHONPATH` as an undocumented prerequisite.

## Preferred template for new scripts

For a script directly under `scripts/`:

```python
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.Ults.DuckLib import DuckDBManager  # noqa: E402
```

For a script one level deeper, such as `scripts/initload/x.py`, resolve the correct parent explicitly, for example:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[2]
```

Agents MUST calculate the parent from the actual file location. Do not copy `parents[1]` blindly.

## Existing legacy pattern

Some existing scripts add `PROJECT_ROOT / "src"` and then import top-level packages:

```python
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from calcEngine.some_module import some_function
```

This remains compatible for existing files. For new scripts, prefer the repository-root + `src.*` template above unless the neighboring script family clearly owns the legacy convention.

Do not mix both bootstrap styles in one new script without a concrete compatibility reason.

---

# 4. Runbook command rule

A runbook that says:

```powershell
python scripts\some_script.py
```

MUST ensure that `some_script.py` is directly executable from a clean repository-root shell.

Do not write a canonical runbook that silently assumes:

```powershell
$env:PYTHONPATH="C:\some\developer\path"
```

If a command only works after manual `PYTHONPATH` setup, fix the repository script/config or document an explicit environment contract owned by the project. Do not encode a user-specific absolute path.

---

# 5. Import/collection diagnostic — finite procedure

When Python reports:

```text
ModuleNotFoundError
ImportError
pytest collection error
```

use exactly this first diagnostic path:

```text
1. Read the first relevant traceback and identify the unresolved module.
2. Check this document and one known-good neighboring test/script.
3. Check the invocation mode: pytest/root entry point/direct scripts path.
4. Apply one focused import/bootstrap correction.
5. Rerun collection or the exact failing command once.
6. If the same failure remains without new evidence: STOP.
```

Do not repeatedly grep/search the same import or `sys.path` pattern after the convention is established.

---

# 6. Failure classification

Use these classifications:

| Failure | Classification |
|---|---|
| pytest cannot collect because repository module is unresolved | `FAIL` import/execution contract; allow focused fix |
| direct script cannot import repository code because it lacks bootstrap | `FAIL` script execution contract; fix script |
| required external interpreter/dependency is unavailable | `BLOCKED` environment/dependency |
| test collects and executes, then an existing behavior assertion breaks due to the current change | `REGRESSION` |
| test collects and executes, assertion for new behavior fails | `FAIL` |

Do not label every collection error as `REGRESSION`.

---

# 7. Generation checklist for agents

Before creating or updating a Python script, test or runbook:

```text
[ ] Identify invocation mode.
[ ] Use a neighboring working file as the import-pattern reference.
[ ] For tests, ensure pytest path configuration supports production imports.
[ ] For direct scripts, bootstrap repository path inside the script.
[ ] Do not require undocumented manual PYTHONPATH.
[ ] Add a compile/import/collection check appropriate to the invocation mode.
[ ] Make documented commands runnable from repository root.
[ ] Classify collection/import failures separately from behavioral regression.
[ ] Respect anti-loop retry limits.
```

---

## Related materials

- `docs/development/Development_Workflow.md`
- `.github/agents/GeneralCoding.agent.md`
- `.github/agents/TestEngineer.agent.md`
- `.github/instructions/testing.instructions.md`
- `docs/runbook/SmartMoneyStrategy_V1.md`
