from datetime import date, timedelta
import importlib.util
from pathlib import Path
import sys

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "Orchestrator"
    / "rs_v2_4_full_evaluation.py"
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


class _ActiveTickerConnection:
    def __init__(self):
        self.sql = ""
        self.params = None

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params
        return _Rows(
            [
                ("FPT", 700, date(2023, 7, 4), date(2026, 8, 28)),
                ("MWG", 710, date(2023, 7, 4), date(2026, 8, 28)),
            ]
        )


class _IndicatorConfigConnection:
    def execute(self, sql, params=None):
        assert '"vw_Indicator_config"' in sql
        return _Rows(
            [
                ("MA20_D", "MA", "D", "VALUE", '{"length":20}', "PRICE_LEVEL"),
                ("MA250_D", "MA", "D", "VALUE", '{"length":250}', "PRICE_LEVEL"),
                ("BB20_2_D", "BB", "D", "LOWER", '{"length":20}', "PRICE_LEVEL"),
                ("ATR14_D", "ATR", "D", "VALUE", '{"length":14}', "VOLATILITY_DISTANCE"),
                ("ATR14_W", "ATR", "W", "VALUE", '{"length":14}', "VOLATILITY_DISTANCE"),
                ("RSI14_D", "RSI", "D", "VALUE", '{"length":14}', "OSCILLATOR"),
                ("RSI14_W", "RSI", "W", "VALUE", '{"length":14}', "OSCILLATOR"),
            ]
        )


def test_resolve_tickers_filters_raw_lstTicker_status_y() -> None:
    connection = _ActiveTickerConnection()
    window = module.EvaluationWindow(
        start_date=date(2023, 7, 4),
        evaluation_end=date(2026, 7, 3),
        latest_data_date=date(2026, 8, 28),
        freshness_cutoff=date(2026, 8, 21),
    )

    tickers = module._resolve_tickers(
        connection,
        window,
        explicit_tickers=(),
        min_history_bars=500,
        max_tickers=None,
    )

    assert tickers == ("FPT", "MWG")
    assert '"raw_lstTicker"' in connection.sql
    assert 'ticker."status" = \'Y\'' in connection.sql
    assert 'ticker."Ticker" = eod."Ticker"' in connection.sql
    assert connection.params == [
        window.start_date,
        window.latest_data_date,
        500,
        window.freshness_cutoff,
    ]


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


def test_indicator_catalog_matches_current_runtime_provider_contracts() -> None:
    specs = module._indicator_source_specs(_IndicatorConfigConnection())
    by_key = {item.source_key: item for item in specs}

    assert "MA20_D" in by_key
    assert "MA250_D" not in by_key
    assert "BB20_2_D:LOWER" in by_key
    assert "ATR14_D" in by_key
    assert "ATR14_W" not in by_key
    assert "RSI14_D" in by_key
    assert "RSI14_W" in by_key
    assert by_key["ATR14_D"].source_role == "CONTEXT"
    assert by_key["RSI14_W"].source_role == "CONFIRMATION"


def test_default_run_prefix_changes_when_universe_changes() -> None:
    first = module._build_run_prefix(
        None,
        "202609",
        date(2026, 7, 1),
        ("FPT", "MWG"),
        5,
    )
    second = module._build_run_prefix(
        None,
        "202609",
        date(2026, 7, 1),
        ("HPG", "MWG"),
        5,
    )

    assert first != second
    assert "_S5_U" in first


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
        "ticker_count": 3,
        "snapshot_count": 30,
        "status": "COMPLETED",
        "include_keys": (),
        "exclude_keys": ("MA20_D",),
        "event_tickers": ("FPT", "HPG", "MWG"),
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
            ("FPT", "HPG", "MWG"),
            30,
        )
