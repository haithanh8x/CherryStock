from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_PY = PROJECT_ROOT / "run.py"


def test_run_py_invokes_movement_after_core_unit_of_work() -> None:
    tree = ast.parse(RUN_PY.read_text(encoding="utf-8"))
    main_fn = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )

    core_uow = next(
        node
        for node in main_fn.body
        if isinstance(node, ast.With)
        and any(
            isinstance(item.context_expr, ast.Call)
            and getattr(item.context_expr.func, "id", None) == "DuckDBUnitOfWork"
            for item in node.items
        )
    )

    movement_statement = next(
        node
        for node in main_fn.body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and getattr(node.value.func, "id", None) == "_run_movement_steps"
    )

    assert movement_statement.lineno > core_uow.end_lineno


def test_run_py_checks_movement_failures_before_metadata_export() -> None:
    text = RUN_PY.read_text(encoding="utf-8")
    main_text = text[text.index("def main():") :]

    assert main_text.index("_run_movement_steps(") < main_text.index(
        "DuckLib.exportDuckDB_metadata()"
    )
