from __future__ import annotations

import re
from collections.abc import Callable

import pandas as pd
import pandas_ta_classic as ta

SUPPORTED_ENGINES = {"PANDAS_TA", "PANDAS_TA_CLASSIC"}

SOURCE_ARGUMENT_MAP = {
    "Open": "open_",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
}

_FUNCTION_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Build the registry once from public callables exposed by pandas-ta-classic.
# Runtime config can only resolve functions that actually exist in this registry.
FUNCTION_REGISTRY: dict[str, Callable[..., object]] = {
    name: value
    for name, value in vars(ta).items()
    if not name.startswith("_") and callable(value)
}


def resolve_indicator_function(engine: str, function_name: str) -> Callable[..., object]:
    """Resolve a configured indicator function from the approved engine registry."""
    normalized_engine = str(engine).strip().upper()
    if normalized_engine not in SUPPORTED_ENGINES:
        raise ValueError(
            f"Unsupported indicator engine={engine!r}. "
            f"Supported engines: {sorted(SUPPORTED_ENGINES)}"
        )

    normalized_name = str(function_name).strip()
    if not normalized_name or _FUNCTION_NAME_PATTERN.fullmatch(normalized_name) is None:
        raise ValueError(f"Invalid indicator FunctionName={function_name!r}.")

    function = FUNCTION_REGISTRY.get(normalized_name)
    if function is None:
        raise ValueError(
            f"Indicator function {normalized_name!r} is not available in pandas-ta-classic."
        )
    return function


def build_indicator_input_kwargs(
    frame: pd.DataFrame,
    required_inputs: tuple[str, ...],
) -> dict[str, pd.Series]:
    """Map CherryStock OHLCV column names to pandas-ta-classic function arguments."""
    kwargs: dict[str, pd.Series] = {}
    for source_column in required_inputs:
        argument_name = SOURCE_ARGUMENT_MAP.get(source_column)
        if argument_name is None:
            raise ValueError(
                f"Unsupported RequiredInputs field={source_column!r}. "
                f"Supported fields: {sorted(SOURCE_ARGUMENT_MAP)}"
            )
        if source_column not in frame.columns:
            raise ValueError(
                f"Source frame is missing required indicator input column {source_column!r}."
            )
        kwargs[argument_name] = frame[source_column]
    return kwargs
