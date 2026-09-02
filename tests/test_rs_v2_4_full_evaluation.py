from datetime import date, timedelta
import importlib.util
from pathlib import Path
import sys

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_rs_v2_4_full_evaluation.py"
)
SPEC = importlib.util.spec_from_file_location("rs_v24_full_eval", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _MarketDateConnection:
    def __init__(self, dates):
        self._dates = dates

    def execute(self, sql, params=None):
        assert 'SELECT DISTINCT "Date"' in sql
        return _Rows([(value,) for value in self._dates])


def test_parse_horizons_is_sorted_unique_and_positive() -> None:
    assert module._parse_horizons("20,5,20,40") == (5, 20, 40)

    with pytest.raises(ValueError):
        module._parse_horizons("20,0")


def test_default_window_reserves_largest_future_horizon() -> None:
    dates = [date(2026, 1, 1) + timedelta(days=index) for index in range(80)]
    connection = _MarketDateConnection(dates)

    window = module._resolve_window(
        connection,
        horizons=(5, 10, 20),
        explicit_start="2026-01-05",
        explicit_end=None,
        lookback_years=3,
        freshness_bars=5,
    )

    assert window.latest_data_date == dates[-1]
    assert window.evaluation_end == dates[-21]
    assert len([value for value in dates if value > window.evaluation_end]) == 20


def test_explicit_end_rejects_immature_future_outcomes() -> None:
    dates = [date(2026, 1, 1) + timedelta(days=index) for index in range(50)]
    connection = _MarketDateConnection(dates)

    with pytest.raises(ValueError, match="insufficient future trading bars"):
        module._resolve_window(
            connection,
            horizons=(40,),
            explicit_start="2026-01-01",
            explicit_end=dates[-10].isoformat(),
            lookback_years=3,
            freshness_bars=5,
        )


def test_ablation_model_version_is_order_independent_and_membership_sensitive() -> None:
    first = module._ablation_model_version(
        "SOURCE_FAMILY",
        "TREND_AVERAGE",
        ("MA20_D", "MA50_D"),
    )
    reordered = module._ablation_model_version(
        "SOURCE_FAMILY",
        "TREND_AVERAGE",
        ("MA50_D", "MA20_D"),
    )
    changed = module._ablation_model_version(
        "SOURCE_FAMILY",
        "TREND_AVERAGE",
        ("MA20_D", "MA50_D", "MA100_D"),
    )

    assert first == reordered
    assert first != changed


def test_family_ablation_keeps_full_family_membership_when_config_selection_is_narrow() -> None:
    full_catalog = (
        module.SourceSpec("MA20_D", "TREND_AVERAGE", "LEVEL"),
        module.SourceSpec("MA50_D", "TREND_AVERAGE", "LEVEL"),
        module.SourceSpec("RSI14_D", "MOMENTUM_CONFIRMATION", "CONFIRMATION"),
    )
    selected = (module.SourceSpec("MA50_D", "TREND_AVERAGE", "LEVEL"),)

    groups = module._family_groups(
        full_catalog,
        selected,
        skip_source_keys=(),
    )

    assert groups[("TREND_AVERAGE", "LEVEL")] == ("MA20_D", "MA50_D")
    assert ("MOMENTUM_CONFIRMATION", "CONFIRMATION") not in groups


def test_select_config_specs_requires_level_lineage_but_keeps_marginal_roles() -> None:
    catalog = (
        module.SourceSpec("MA20_D", "TREND_AVERAGE", "LEVEL"),
        module.SourceSpec("MA50_D", "TREND_AVERAGE", "LEVEL"),
        module.SourceSpec("ATR14_D", "VOLATILITY_CONTEXT", "CONTEXT"),
        module.SourceSpec("RSI14_D", "MOMENTUM_CONFIRMATION", "CONFIRMATION"),
    )

    selected = module._select_config_specs(
        catalog,
        lineage={"MA50_D"},
        only_source_keys=(),
        skip_source_keys=(),
    )

    assert {item.source_key for item in selected} == {
        "MA50_D",
        "ATR14_D",
        "RSI14_D",
    }


def test_promotion_default_is_non_applying_dry_run() -> None:
    command = module._promotion_command(
        "RSEFF_X",
        "{}",
        "dry-run",
        "DECISION_X",
        "monthly test",
    )
    assert command is not None
    assert "--apply" not in command
    assert "--decision-id" not in command

    audit_command = module._promotion_command(
        "RSEFF_X",
        "{}",
        "audit",
        "DECISION_X",
        "monthly test",
    )
    assert audit_command is not None
    assert "--apply" in audit_command
    assert "--decision-id" in audit_command


def test_resume_compatibility_blocks_reusing_different_ablation() -> None:
    state = {
        "dataset_start": date(2024, 1, 1),
        "dataset_end": date(2026, 6, 30),
        "horizon_bars": 20,
        "status": "COMPLETED",
        "include_keys": (),
        "exclude_keys": ("MA20_D",),
    }
    window = module.EvaluationWindow(
        start_date=date(2024, 1, 1),
        evaluation_end=date(2026, 6, 30),
        latest_data_date=date(2026, 8, 31),
        freshness_cutoff=date(2026, 8, 24),
    )

    with pytest.raises(ValueError, match="resume collision"):
        module._assert_evaluation_compatible(
            state,
            "RUN_X",
            window,
            20,
            ("MA50_D",),
        )
