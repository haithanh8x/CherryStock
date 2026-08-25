import pytest

from src.calcEngine.calcIndicators import (
    IndicatorComponent,
    IndicatorConfig,
    validate_indicator_onboarding_contract,
)


def _config(config_id: int, timeframe: str, *, length: int = 14) -> IndicatorConfig:
    return IndicatorConfig(
        config_id=config_id,
        config_code=f"RSI{length}_{timeframe}",
        indicator_code="RSI",
        timeframe=timeframe,
        parameters={"length": length},
        warmup_bars=length,
    )


def _components() -> dict[str, list[IndicatorComponent]]:
    return {
        "RSI": [
            IndicatorComponent(
                indicator_code="RSI",
                component_code="VALUE",
                component_name="RSI Value",
                output_prefix=None,
                sort_order=1,
                is_primary=True,
            )
        ]
    }


def test_onboarding_requires_dwm_for_each_parameter_set() -> None:
    configs = [_config(1, "D"), _config(2, "W"), _config(3, "M")]

    validate_indicator_onboarding_contract(configs, _components())


def test_onboarding_rejects_missing_default_timeframe() -> None:
    configs = [_config(1, "D"), _config(2, "W")]

    with pytest.raises(ValueError, match="default timeframes"):
        validate_indicator_onboarding_contract(configs, _components())


def test_onboarding_checks_each_parameter_family_independently() -> None:
    configs = [
        _config(1, "D", length=14),
        _config(2, "W", length=14),
        _config(3, "M", length=14),
        _config(4, "D", length=21),
        _config(5, "W", length=21),
    ]

    with pytest.raises(ValueError, match='RSI Parameters={"length":21}'):
        validate_indicator_onboarding_contract(configs, _components())


def test_targeted_run_may_skip_dwm_completeness_only() -> None:
    configs = [_config(1, "D")]

    validate_indicator_onboarding_contract(
        configs,
        _components(),
        require_default_timeframes=False,
    )


def test_onboarding_always_requires_component_metadata() -> None:
    configs = [_config(1, "D"), _config(2, "W"), _config(3, "M")]

    with pytest.raises(ValueError, match="missing active rows"):
        validate_indicator_onboarding_contract(configs, {})
