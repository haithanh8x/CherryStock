from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DAILY = PROJECT_ROOT / "run.py"
WEEKLY = PROJECT_ROOT / "runWeekly.py"


def test_daily_runner_does_not_invoke_movement() -> None:
    text = DAILY.read_text(encoding="utf-8")

    assert "MovementDailyPipelineService" not in text
    assert "_run_movement_steps" not in text
    assert "movement_pipeline.run" not in text


def test_weekly_runner_owns_full_universe_movement() -> None:
    text = WEEKLY.read_text(encoding="utf-8")

    assert "MovementWeeklyPipelineService" in text
    assert "_run_movement_weekly" in text
    assert "movement_pipeline.run" in text


def test_weekly_movement_is_not_nested_inside_daily_uow() -> None:
    tree = ast.parse(DAILY.read_text(encoding="utf-8"))
    main_fn = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )

    assert any(isinstance(node, ast.With) for node in main_fn.body)
    assert not any(
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and getattr(node.value.func, "id", None) == "_run_movement_steps"
        for node in main_fn.body
    )
