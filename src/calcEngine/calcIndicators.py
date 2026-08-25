from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import pandas as pd

from Ults.DuckLib import DuckDBManager
from Ults.Timing import timeit
from calcEngine.indicatorRegistry import (
    build_indicator_input_kwargs,
    resolve_indicator_function,
)

DIM_INDICATOR_TABLE = '"CherryMon"."main"."dim_indicator"'
DIM_COMPONENT_TABLE = '"CherryMon"."main"."dim_indicator_component"'
DIM_CONFIG_TABLE = '"CherryMon"."main"."dim_indicator_config"'
SOURCE_TABLE = '"CherryMon"."main"."raw_stock_eod"'
TICKER_TABLE = '"CherryMon"."main"."raw_lstTicker"'
TARGET_TABLE = '"CherryMon"."main"."cal_indicator_values"'

SUPPORTED_TIMEFRAMES = {"D", "W", "M"}
RUNTIME_PARAMETER_NAMES = {"open", "open_", "high", "low", "close", "volume"}
VALUE_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


@dataclass(frozen=True)
class IndicatorDefinition:
    indicator_code: str
    indicator_name: str
    category: str
    engine: str
    function_name: str
    required_inputs: tuple[str, ...]
    parameter_schema: dict[str, Any] | None


@dataclass(frozen=True)
class IndicatorComponent:
    indicator_code: str
    component_code: str
    component_name: str
    output_prefix: str | None
    sort_order: int | None
    is_primary: bool


@dataclass(frozen=True)
class IndicatorConfig:
    config_id: int
    config_code: str
    indicator_code: str
    timeframe: str
    parameters: dict[str, Any]
    warmup_bars: int | None


def _decode_json_object(value: Any, *, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        if parsed is None:
            return {}
        if not isinstance(parsed, dict):
            raise TypeError(f"{field_name} must decode to a JSON object.")
        return parsed
    raise TypeError(f"{field_name} must be a dict or JSON object string, got {type(value).__name__}.")


def _decode_json_array(value: Any, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        raise ValueError(f"{field_name} cannot be NULL.")
    parsed = json.loads(value) if isinstance(value, str) else value
    if not isinstance(parsed, (list, tuple)):
        raise TypeError(f"{field_name} must decode to a JSON array.")
    normalized = tuple(str(item).strip() for item in parsed if str(item).strip())
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty.")
    return normalized


def get_enabled_indicator_configs(
    connection,
    *,
    config_ids: list[int] | None = None,
    timeframes: list[str] | None = None,
) -> list[IndicatorConfig]:
    """Load enabled executable indicator configs without querying inside calculation loops."""
    where_clauses = ["IsEnabled = TRUE"]
    params: list[object] = []

    if config_ids:
        placeholders = ", ".join("?" for _ in config_ids)
        where_clauses.append(f"ConfigId IN ({placeholders})")
        params.extend(int(config_id) for config_id in config_ids)

    if timeframes:
        normalized_timeframes = [str(value).strip().upper() for value in timeframes]
        invalid = sorted(set(normalized_timeframes) - SUPPORTED_TIMEFRAMES)
        if invalid:
            raise ValueError(f"Unsupported timeframes: {invalid}")
        placeholders = ", ".join("?" for _ in normalized_timeframes)
        where_clauses.append(f"upper(Timeframe) IN ({placeholders})")
        params.extend(normalized_timeframes)

    config_df = connection.sql(
        f"""
        SELECT
            ConfigId,
            ConfigCode,
            IndicatorCode,
            Timeframe,
            Parameters,
            WarmupBars
        FROM {DIM_CONFIG_TABLE}
        WHERE {' AND '.join(where_clauses)}
        ORDER BY Timeframe, ConfigId
        """,
        params=params,
    ).df()

    configs: list[IndicatorConfig] = []
    for row in config_df.itertuples(index=False):
        configs.append(
            IndicatorConfig(
                config_id=int(row.ConfigId),
                config_code=str(row.ConfigCode),
                indicator_code=str(row.IndicatorCode).strip().upper(),
                timeframe=str(row.Timeframe).strip().upper(),
                parameters=_decode_json_object(row.Parameters, field_name="Parameters"),
                warmup_bars=int(row.WarmupBars) if pd.notna(row.WarmupBars) else None,
            )
        )
    return configs


def get_indicator_definitions(
    connection,
    indicator_codes: list[str],
) -> dict[str, IndicatorDefinition]:
    """Load active indicator definitions for one batch."""
    normalized_codes = sorted({str(code).strip().upper() for code in indicator_codes})
    if not normalized_codes:
        return {}

    placeholders = ", ".join("?" for _ in normalized_codes)
    definition_df = connection.sql(
        f"""
        SELECT
            IndicatorCode,
            IndicatorName,
            Category,
            Engine,
            FunctionName,
            RequiredInputs,
            ParameterSchema
        FROM {DIM_INDICATOR_TABLE}
        WHERE IsActive = TRUE
          AND IndicatorCode IN ({placeholders})
        ORDER BY IndicatorCode
        """,
        params=normalized_codes,
    ).df()

    definitions: dict[str, IndicatorDefinition] = {}
    for row in definition_df.itertuples(index=False):
        code = str(row.IndicatorCode).strip().upper()
        schema = None
        if row.ParameterSchema is not None and not (
            isinstance(row.ParameterSchema, float) and pd.isna(row.ParameterSchema)
        ):
            parsed_schema = _decode_json_object(row.ParameterSchema, field_name="ParameterSchema")
            schema = parsed_schema or None
        definitions[code] = IndicatorDefinition(
            indicator_code=code,
            indicator_name=str(row.IndicatorName),
            category=str(row.Category),
            engine=str(row.Engine),
            function_name=str(row.FunctionName),
            required_inputs=_decode_json_array(row.RequiredInputs, field_name="RequiredInputs"),
            parameter_schema=schema,
        )

    missing = sorted(set(normalized_codes) - set(definitions))
    if missing:
        raise ValueError(f"Missing active dim_indicator definitions for: {missing}")
    return definitions


def get_indicator_components(
    connection,
    indicator_codes: list[str],
) -> dict[str, list[IndicatorComponent]]:
    """Load active component/output mappings for configured indicators."""
    normalized_codes = sorted({str(code).strip().upper() for code in indicator_codes})
    if not normalized_codes:
        return {}

    placeholders = ", ".join("?" for _ in normalized_codes)
    component_df = connection.sql(
        f"""
        SELECT
            IndicatorCode,
            ComponentCode,
            ComponentName,
            OutputPrefix,
            SortOrder,
            IsPrimary
        FROM {DIM_COMPONENT_TABLE}
        WHERE IsActive = TRUE
          AND IndicatorCode IN ({placeholders})
        ORDER BY IndicatorCode, SortOrder, ComponentCode
        """,
        params=normalized_codes,
    ).df()

    components: dict[str, list[IndicatorComponent]] = {}
    for row in component_df.itertuples(index=False):
        code = str(row.IndicatorCode).strip().upper()
        components.setdefault(code, []).append(
            IndicatorComponent(
                indicator_code=code,
                component_code=str(row.ComponentCode).strip().upper(),
                component_name=str(row.ComponentName),
                output_prefix=(
                    str(row.OutputPrefix).strip()
                    if row.OutputPrefix is not None and pd.notna(row.OutputPrefix)
                    else None
                ),
                sort_order=int(row.SortOrder) if pd.notna(row.SortOrder) else None,
                is_primary=bool(row.IsPrimary),
            )
        )
    return components


def validate_indicator_config(
    config: IndicatorConfig,
    definition: IndicatorDefinition,
) -> None:
    """Validate one executable config before any indicator values are written."""
    if config.indicator_code != definition.indicator_code:
        raise ValueError(
            f"Config {config.config_code} indicator mismatch: "
            f"{config.indicator_code} != {definition.indicator_code}"
        )
    if config.timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError(
            f"Config {config.config_code} has unsupported Timeframe={config.timeframe!r}."
        )
    if config.warmup_bars is not None and config.warmup_bars < 0:
        raise ValueError(f"Config {config.config_code} WarmupBars cannot be negative.")

    reserved = sorted(set(config.parameters) & RUNTIME_PARAMETER_NAMES)
    if reserved:
        raise ValueError(
            f"Config {config.config_code} cannot override runtime OHLCV parameters: {reserved}"
        )

    schema = definition.parameter_schema or {}
    for parameter_name, raw_spec in schema.items():
        if not isinstance(raw_spec, dict):
            raise TypeError(
                f"ParameterSchema[{parameter_name!r}] for {definition.indicator_code} must be an object."
            )
        is_required = bool(raw_spec.get("required", False))
        if is_required and parameter_name not in config.parameters:
            raise ValueError(
                f"Config {config.config_code} is missing required parameter {parameter_name!r}."
            )
        if parameter_name not in config.parameters:
            continue

        value = config.parameters[parameter_name]
        expected_type = str(raw_spec.get("type", "")).lower()
        if expected_type == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
            raise TypeError(
                f"Config {config.config_code} parameter {parameter_name!r} must be integer."
            )
        if expected_type == "number" and (
            isinstance(value, bool) or not isinstance(value, (int, float))
        ):
            raise TypeError(
                f"Config {config.config_code} parameter {parameter_name!r} must be numeric."
            )
        if expected_type == "boolean" and not isinstance(value, bool):
            raise TypeError(
                f"Config {config.config_code} parameter {parameter_name!r} must be boolean."
            )

        minimum = raw_spec.get("min")
        maximum = raw_spec.get("max")
        if minimum is not None and value < minimum:
            raise ValueError(
                f"Config {config.config_code} parameter {parameter_name!r} must be >= {minimum}."
            )
        if maximum is not None and value > maximum:
            raise ValueError(
                f"Config {config.config_code} parameter {parameter_name!r} must be <= {maximum}."
            )
        allowed_values = raw_spec.get("enum")
        if allowed_values is not None and value not in allowed_values:
            raise ValueError(
                f"Config {config.config_code} parameter {parameter_name!r} "
                f"must be one of {allowed_values}."
            )

    if definition.indicator_code == "MACD":
        fast = config.parameters.get("fast")
        slow = config.parameters.get("slow")
        if fast is not None and slow is not None and fast >= slow:
            raise ValueError(f"Config {config.config_code} requires fast < slow.")


def _effective_warmup_bars(config: IndicatorConfig) -> int:
    configured = int(config.warmup_bars or 0)
    numeric_parameters = [
        int(value)
        for value in config.parameters.values()
        if isinstance(value, int) and not isinstance(value, bool) and value > 0
    ]
    inferred = max(numeric_parameters, default=1)
    if "slow" in config.parameters and "signal" in config.parameters:
        slow = config.parameters.get("slow")
        signal = config.parameters.get("signal")
        if isinstance(slow, int) and isinstance(signal, int):
            inferred = max(inferred, slow + signal)
    return max(configured, inferred, 1)


def _source_date_bounds(connection, tickers: list[str] | None = None) -> tuple[date, date] | None:
    params: list[object] = []
    ticker_filter = ""
    if tickers:
        placeholders = ", ".join("?" for _ in tickers)
        ticker_filter = f" AND eod.Ticker IN ({placeholders})"
        params.extend(tickers)

    bounds_df = connection.sql(
        f"""
        SELECT
            MIN(eod.Date) AS min_date,
            MAX(eod.Date) AS max_date
        FROM {SOURCE_TABLE} AS eod
        INNER JOIN {TICKER_TABLE} AS ticker
            ON ticker.Ticker = eod.Ticker
        WHERE ticker.status = 'Y'
        {ticker_filter}
        """,
        params=params,
    ).df()
    if bounds_df.empty or pd.isna(bounds_df.loc[0, "max_date"]):
        return None
    return (
        pd.Timestamp(bounds_df.loc[0, "min_date"]).date(),
        pd.Timestamp(bounds_df.loc[0, "max_date"]).date(),
    )


def _resolve_checkpoint_start_date(
    *,
    source_min_date: date,
    source_max_date: date,
    from_last_day: int | None,
) -> date:
    if from_last_day is None:
        return source_min_date
    if from_last_day < 0:
        raise ValueError("from_last_day cannot be negative.")
    return source_max_date - timedelta(days=int(from_last_day))


def _resolve_warmup_source_start_date(
    connection,
    *,
    checkpoint_start: date,
    source_min_date: date,
    source_max_date: date,
    configs: list[IndicatorConfig],
    full_refresh: bool,
) -> date:
    if full_refresh:
        return source_min_date

    trading_dates = connection.sql(
        f"""
        SELECT DISTINCT Date
        FROM {SOURCE_TABLE}
        WHERE Date <= ?
        ORDER BY Date
        """,
        params=[source_max_date],
    ).df()
    if trading_dates.empty:
        return source_min_date

    trading_dates["Date"] = pd.to_datetime(trading_dates["Date"])
    checkpoint_ts = pd.Timestamp(checkpoint_start)
    warmup_by_timeframe: dict[str, int] = {}
    for config in configs:
        warmup_by_timeframe[config.timeframe] = max(
            warmup_by_timeframe.get(config.timeframe, 0),
            _effective_warmup_bars(config),
        )

    candidates: list[pd.Timestamp] = [checkpoint_ts]
    date_series = trading_dates["Date"]

    daily_warmup = warmup_by_timeframe.get("D")
    if daily_warmup:
        eligible = date_series.loc[date_series <= checkpoint_ts].reset_index(drop=True)
        if not eligible.empty:
            position = max(0, len(eligible) - daily_warmup - 1)
            candidates.append(eligible.iloc[position])

    weekly_warmup = warmup_by_timeframe.get("W")
    if weekly_warmup:
        period_frame = trading_dates.copy()
        period_frame["Period"] = period_frame["Date"].dt.to_period("W-FRI")
        target_period = checkpoint_ts.to_period("W-FRI")
        periods = (
            period_frame.loc[period_frame["Period"] <= target_period, "Period"]
            .drop_duplicates()
            .sort_values()
            .reset_index(drop=True)
        )
        if not periods.empty:
            selected = periods.iloc[max(0, len(periods) - weekly_warmup - 1) :]
            earliest_period = selected.iloc[0]
            first_date = period_frame.loc[period_frame["Period"] == earliest_period, "Date"].min()
            candidates.append(first_date)

    monthly_warmup = warmup_by_timeframe.get("M")
    if monthly_warmup:
        period_frame = trading_dates.copy()
        period_frame["Period"] = period_frame["Date"].dt.to_period("M")
        target_period = checkpoint_ts.to_period("M")
        periods = (
            period_frame.loc[period_frame["Period"] <= target_period, "Period"]
            .drop_duplicates()
            .sort_values()
            .reset_index(drop=True)
        )
        if not periods.empty:
            selected = periods.iloc[max(0, len(periods) - monthly_warmup - 1) :]
            earliest_period = selected.iloc[0]
            first_date = period_frame.loc[period_frame["Period"] == earliest_period, "Date"].min()
            candidates.append(first_date)

    return max(source_min_date, min(candidate.date() for candidate in candidates))


def load_indicator_source_data(
    connection,
    *,
    source_start_date: date,
    source_end_date: date,
    required_inputs: tuple[str, ...],
    tickers: list[str] | None = None,
) -> pd.DataFrame:
    """Load active-ticker OHLCV inputs once for a whole indicator batch."""
    unsupported = sorted(set(required_inputs) - set(VALUE_COLUMNS))
    if unsupported:
        raise ValueError(f"Unsupported indicator source columns: {unsupported}")

    value_columns = [column for column in VALUE_COLUMNS if column in required_inputs]
    select_columns = ["eod.Ticker", "eod.Date"] + [f'eod."{column}"' for column in value_columns]
    params: list[object] = [source_start_date, source_end_date]
    ticker_filter = ""
    if tickers:
        placeholders = ", ".join("?" for _ in tickers)
        ticker_filter = f" AND eod.Ticker IN ({placeholders})"
        params.extend(tickers)

    source_df = connection.sql(
        f"""
        SELECT
            {', '.join(select_columns)}
        FROM {SOURCE_TABLE} AS eod
        INNER JOIN {TICKER_TABLE} AS ticker
            ON ticker.Ticker = eod.Ticker
        WHERE ticker.status = 'Y'
          AND eod.Date >= ?
          AND eod.Date <= ?
          {ticker_filter}
        ORDER BY eod.Ticker, eod.Date
        """,
        params=params,
    ).df()
    if source_df.empty:
        return source_df

    source_df["Date"] = pd.to_datetime(source_df["Date"])
    return source_df.sort_values(["Ticker", "Date"]).reset_index(drop=True)


def resample_indicator_timeframe(source_df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample Daily EOD data to D/W/M using the last actual trading date as Date."""
    normalized = str(timeframe).strip().upper()
    if normalized not in SUPPORTED_TIMEFRAMES:
        raise ValueError(f"Unsupported timeframe={timeframe!r}.")
    if source_df.empty or normalized == "D":
        return source_df.copy()

    frame = source_df.copy().sort_values(["Ticker", "Date"])
    period_frequency = "W-FRI" if normalized == "W" else "M"
    frame["_Period"] = frame["Date"].dt.to_period(period_frequency)

    aggregation: dict[str, str] = {"Date": "max"}
    if "Open" in frame.columns:
        aggregation["Open"] = "first"
    if "High" in frame.columns:
        aggregation["High"] = "max"
    if "Low" in frame.columns:
        aggregation["Low"] = "min"
    if "Close" in frame.columns:
        aggregation["Close"] = "last"
    if "Volume" in frame.columns:
        aggregation["Volume"] = "sum"

    return (
        frame.groupby(["Ticker", "_Period"], as_index=False, sort=True)
        .agg(aggregation)
        .drop(columns=["_Period"])
        .sort_values(["Ticker", "Date"])
        .reset_index(drop=True)
    )


def _coerce_indicator_output(raw_output: object, source_index: pd.DatetimeIndex) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    raw_items = raw_output if isinstance(raw_output, (tuple, list)) else (raw_output,)
    for item in raw_items:
        if item is None:
            continue
        if isinstance(item, pd.Series):
            frames.append(item.to_frame())
        elif isinstance(item, pd.DataFrame):
            frames.append(item.copy())
        else:
            raise TypeError(
                f"Indicator library returned unsupported output type {type(item).__name__}."
            )

    if not frames:
        return pd.DataFrame(index=source_index)

    normalized_frames: list[pd.DataFrame] = []
    for frame in frames:
        if not isinstance(frame.index, pd.DatetimeIndex):
            if len(frame) != len(source_index):
                raise ValueError(
                    "Indicator output has a non-datetime index and cannot be aligned to source dates."
                )
            frame = frame.copy()
            frame.index = source_index
        else:
            frame = frame.copy()
            frame.index = pd.to_datetime(frame.index)
        normalized_frames.append(frame)

    output = pd.concat(normalized_frames, axis=1)
    output = output.loc[:, ~output.columns.astype(str).duplicated(keep="first")]
    return output.sort_index()


def normalize_indicator_output(
    *,
    ticker: str,
    config: IndicatorConfig,
    raw_output: object,
    source_index: pd.DatetimeIndex,
    components: list[IndicatorComponent],
) -> pd.DataFrame:
    """Normalize Series/DataFrame/tuple library outputs to CherryStock long-format components."""
    raw_frame = _coerce_indicator_output(raw_output, source_index)
    if raw_frame.empty or len(raw_frame.columns) == 0:
        return pd.DataFrame(columns=["Ticker", "Date", "ConfigId", "ComponentCode", "Value"])

    rows: list[pd.DataFrame] = []
    active_components = sorted(
        components,
        key=lambda component: len(component.output_prefix or ""),
        reverse=True,
    )

    if not active_components:
        if len(raw_frame.columns) != 1:
            raise ValueError(
                f"Config {config.config_code} returned {len(raw_frame.columns)} outputs but "
                "dim_indicator_component has no mapping."
            )
        raw_column = raw_frame.columns[0]
        value_frame = pd.DataFrame(
            {
                "Ticker": ticker,
                "Date": raw_frame.index,
                "ConfigId": config.config_id,
                "ComponentCode": "VALUE",
                "Value": pd.to_numeric(raw_frame[raw_column], errors="coerce"),
            }
        )
        return value_frame.dropna(subset=["Value"])

    for raw_column in raw_frame.columns:
        raw_name = str(raw_column)
        matching = [
            component
            for component in active_components
            if component.output_prefix
            and raw_name.upper().startswith(component.output_prefix.upper())
        ]
        if not matching and len(active_components) == 1 and not active_components[0].output_prefix:
            matching = [active_components[0]]
        if not matching:
            continue

        component = matching[0]
        rows.append(
            pd.DataFrame(
                {
                    "Ticker": ticker,
                    "Date": raw_frame.index,
                    "ConfigId": config.config_id,
                    "ComponentCode": component.component_code,
                    "Value": pd.to_numeric(raw_frame[raw_column], errors="coerce"),
                }
            )
        )

    if not rows:
        available_columns = [str(column) for column in raw_frame.columns]
        raise ValueError(
            f"Config {config.config_code} output columns {available_columns} do not match "
            "dim_indicator_component.OutputPrefix metadata."
        )

    normalized = pd.concat(rows, ignore_index=True).dropna(subset=["Value"])
    return normalized.drop_duplicates(
        subset=["Ticker", "Date", "ConfigId", "ComponentCode"], keep="last"
    )


def calculate_indicator_from_config(
    source_ticker_df: pd.DataFrame,
    config: IndicatorConfig,
    definition: IndicatorDefinition,
    components: list[IndicatorComponent],
) -> pd.DataFrame:
    """Calculate one configured indicator for one ticker using pandas-ta-classic."""
    validate_indicator_config(config, definition)
    ticker = str(source_ticker_df["Ticker"].iloc[0])
    frame = source_ticker_df.sort_values("Date").set_index("Date")
    frame.index = pd.DatetimeIndex(frame.index)

    input_kwargs = build_indicator_input_kwargs(frame, definition.required_inputs)
    function = resolve_indicator_function(definition.engine, definition.function_name)
    try:
        raw_output = function(**input_kwargs, **config.parameters)
    except Exception as exc:
        raise RuntimeError(
            f"Indicator calculation failed for ticker={ticker}, config={config.config_code}, "
            f"function={definition.function_name}: {exc}"
        ) from exc

    return normalize_indicator_output(
        ticker=ticker,
        config=config,
        raw_output=raw_output,
        source_index=frame.index,
        components=components,
    )


def _period_checkpoint_start(checkpoint_start: date, timeframe: str) -> date:
    checkpoint_ts = pd.Timestamp(checkpoint_start)
    if timeframe == "W":
        return (checkpoint_ts - pd.Timedelta(days=checkpoint_ts.weekday())).date()
    if timeframe == "M":
        return checkpoint_ts.replace(day=1).date()
    return checkpoint_start


def calculate_indicator_batch(
    source_df: pd.DataFrame,
    *,
    configs: list[IndicatorConfig],
    definitions: dict[str, IndicatorDefinition],
    components: dict[str, list[IndicatorComponent]],
    checkpoint_start: date,
    source_end_date: date,
) -> pd.DataFrame:
    """Calculate all configs without issuing database calls inside calculation loops."""
    if source_df.empty:
        return pd.DataFrame(columns=["Ticker", "Date", "ConfigId", "ComponentCode", "Value"])

    calculated_frames: list[pd.DataFrame] = []
    for timeframe in sorted({config.timeframe for config in configs}):
        timeframe_configs = [config for config in configs if config.timeframe == timeframe]
        timeframe_df = resample_indicator_timeframe(source_df, timeframe)
        persist_start = pd.Timestamp(_period_checkpoint_start(checkpoint_start, timeframe))
        persist_end = pd.Timestamp(source_end_date)

        for _, ticker_df in timeframe_df.groupby("Ticker", sort=False):
            for config in timeframe_configs:
                definition = definitions[config.indicator_code]
                missing_columns = sorted(set(definition.required_inputs) - set(ticker_df.columns))
                if missing_columns:
                    raise ValueError(
                        f"Config {config.config_code} source is missing columns {missing_columns}."
                    )
                indicator_values = calculate_indicator_from_config(
                    ticker_df,
                    config,
                    definition,
                    components.get(config.indicator_code, []),
                )
                if indicator_values.empty:
                    continue
                indicator_values["Date"] = pd.to_datetime(indicator_values["Date"])
                indicator_values = indicator_values.loc[
                    indicator_values["Date"].between(persist_start, persist_end)
                ]
                if not indicator_values.empty:
                    calculated_frames.append(indicator_values)

    if not calculated_frames:
        return pd.DataFrame(columns=["Ticker", "Date", "ConfigId", "ComponentCode", "Value"])

    result = pd.concat(calculated_frames, ignore_index=True)
    result["Date"] = pd.to_datetime(result["Date"]).dt.date
    return result.drop_duplicates(
        subset=["Ticker", "Date", "ConfigId", "ComponentCode"], keep="last"
    )


def _build_cleanup_dataframe(
    source_df: pd.DataFrame,
    configs: list[IndicatorConfig],
    checkpoint_start: date,
) -> pd.DataFrame:
    tickers = sorted(source_df["Ticker"].dropna().astype(str).unique())
    rows = [
        {
            "Ticker": ticker,
            "ConfigId": config.config_id,
            "StartDate": _period_checkpoint_start(checkpoint_start, config.timeframe),
        }
        for ticker in tickers
        for config in configs
    ]
    return pd.DataFrame(rows, columns=["Ticker", "ConfigId", "StartDate"])


@timeit
def refresh_technical_indicators(
    *,
    from_last_day: int | None = None,
    tickers: list[str] | None = None,
    config_ids: list[int] | None = None,
    timeframes: list[str] | None = None,
    connection=None,
    repository=None,
) -> dict[str, object]:
    """Refresh enabled technical indicators using the CherryStock main checkpoint.

    ``from_last_day`` is the same checkpoint value supplied by ``run.py`` to the
    write pipeline. The engine expands the read window backwards using
    ``WarmupBars`` but only replaces values inside the requested checkpoint.
    Weekly/monthly cleanup starts at the containing period so provisional values
    from an earlier trading day in the same week/month cannot remain stale.
    """
    con = connection or DuckDBManager.get_connection(read_only=False)
    owns_connection = connection is None
    owns_transaction = owns_connection

    if repository is None:
        from cherrystock.infrastructure.database.repositories.indicator_repository import (
            IndicatorRepository,
        )

        repository = IndicatorRepository(con)

    if owns_transaction:
        con.execute("BEGIN")

    try:
        repository.ensure_storage()
        configs = get_enabled_indicator_configs(
            con,
            config_ids=config_ids,
            timeframes=timeframes,
        )
        if not configs:
            summary = {
                "status": "SKIPPED",
                "reason": "No enabled indicator configs",
                "records_upserted": 0,
                "configs_processed": 0,
                "tickers_processed": 0,
            }
            if owns_transaction:
                con.execute("COMMIT")
            print("Technical Indicator Engine skipped: no enabled configs.")
            return summary

        definitions = get_indicator_definitions(
            con,
            [config.indicator_code for config in configs],
        )
        component_map = get_indicator_components(
            con,
            [config.indicator_code for config in configs],
        )
        for config in configs:
            validate_indicator_config(config, definitions[config.indicator_code])

        source_bounds = _source_date_bounds(con, tickers=tickers)
        if source_bounds is None:
            summary = {
                "status": "SKIPPED",
                "reason": "No active raw_stock_eod source data",
                "records_upserted": 0,
                "configs_processed": len(configs),
                "tickers_processed": 0,
            }
            if owns_transaction:
                con.execute("COMMIT")
            print("Technical Indicator Engine skipped: no active source data.")
            return summary

        source_min_date, source_max_date = source_bounds
        checkpoint_start = _resolve_checkpoint_start_date(
            source_min_date=source_min_date,
            source_max_date=source_max_date,
            from_last_day=from_last_day,
        )
        source_start_date = _resolve_warmup_source_start_date(
            con,
            checkpoint_start=checkpoint_start,
            source_min_date=source_min_date,
            source_max_date=source_max_date,
            configs=configs,
            full_refresh=from_last_day is None,
        )

        required_inputs = tuple(
            sorted(
                {
                    source_column
                    for definition in definitions.values()
                    for source_column in definition.required_inputs
                }
            )
        )
        source_df = load_indicator_source_data(
            con,
            source_start_date=source_start_date,
            source_end_date=source_max_date,
            required_inputs=required_inputs,
            tickers=tickers,
        )
        if source_df.empty:
            raise RuntimeError(
                "Technical Indicator Engine resolved source date bounds but loaded no source rows."
            )

        indicator_values = calculate_indicator_batch(
            source_df,
            configs=configs,
            definitions=definitions,
            components=component_map,
            checkpoint_start=checkpoint_start,
            source_end_date=source_max_date,
        )
        cleanup_df = _build_cleanup_dataframe(source_df, configs, checkpoint_start)
        records_upserted = repository.replace_indicator_checkpoint(
            dataframe=indicator_values,
            cleanup_dataframe=cleanup_df,
            table_name=TARGET_TABLE,
        )

        summary = {
            "status": "PASS" if records_upserted > 0 else "WARNING",
            "checkpoint_start": checkpoint_start.isoformat(),
            "source_start": source_start_date.isoformat(),
            "source_max_date": source_max_date.isoformat(),
            "records_upserted": records_upserted,
            "configs_processed": len(configs),
            "tickers_processed": int(source_df["Ticker"].nunique()),
        }
        if owns_transaction:
            con.execute("COMMIT")
        print(
            "Technical Indicator Engine: "
            f"status={summary['status']} | configs={summary['configs_processed']} | "
            f"tickers={summary['tickers_processed']} | records={records_upserted} | "
            f"checkpoint={summary['checkpoint_start']} | warmup_start={summary['source_start']}"
        )
        return summary
    except Exception:
        if owns_transaction:
            con.execute("ROLLBACK")
        raise
    finally:
        if owns_connection:
            DuckDBManager.close_connection(con)
