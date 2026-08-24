from __future__ import annotations

from datetime import date, datetime
from typing import Any, Sequence

import pandas as pd

from Ults.DuckLib import returnSQL

DEFAULT_MAX_ROW_CHANGE_PCT = 0.10
DEFAULT_MAX_SYMBOL_CHANGE_PCT = 0.05
DEFAULT_MAX_NULL_RATE = 0.01
DEFAULT_HISTORY_WINDOW = 20
DEFAULT_AUDIT_TABLE = '"CherryMon"."main"."sys_data_quality_audit"'
_ZSCORE_WARNING = 2.0
_ZSCORE_FAIL = 3.0
_SAMPLE_SIZE = 20


def _quote_identifier(identifier: str) -> str:
    cleaned = identifier.strip().strip('"')
    if not cleaned or "\x00" in cleaned:
        raise ValueError(f"Invalid SQL identifier: {identifier!r}")
    return f'"{cleaned.replace(chr(34), chr(34) * 2)}"'


def _quote_relation(relation_name: str) -> str:
    if not isinstance(relation_name, str) or not relation_name.strip():
        raise ValueError("table_name must be a non-empty string")
    parts = [part.strip() for part in relation_name.split(".")]
    if any(not part for part in parts):
        raise ValueError(f"Invalid table_name: {relation_name!r}")
    return ".".join(_quote_identifier(part) for part in parts)


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _query_frame(connection: Any, sql: str, context: str) -> pd.DataFrame:
    frame = returnSQL(connection, sql)
    if frame is None:
        raise RuntimeError(f"DuckDB query failed while {context}.")
    return frame


def _normalize_date(value: date | datetime | str | pd.Timestamp, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError as exc:
            raise ValueError(f"{field_name} must use ISO format YYYY-MM-DD") from exc
    raise TypeError(f"{field_name} must be date, datetime, pandas.Timestamp, or YYYY-MM-DD string")


def _validate_threshold(name: str, value: float) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be numeric") from exc
    if not 0 <= numeric_value <= 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return numeric_value


def _normalize_column_sequence(
    values: Sequence[str] | None,
    default_values: Sequence[str],
    field_name: str,
) -> list[str]:
    if values is None:
        return list(default_values)
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{field_name} must be a sequence of column names, not a string")
    normalized = list(values)
    if not normalized:
        raise ValueError(f"{field_name} must contain at least one column")
    if any(not isinstance(value, str) or not value.strip() for value in normalized):
        raise TypeError(f"{field_name} must contain only non-empty strings")
    return normalized


def _get_table_schema(connection: Any, table_name: str) -> pd.DataFrame:
    raw_parts = [part.strip().strip('"') for part in table_name.split(".")]
    table = raw_parts[-1]
    filters = [f"lower(table_name) = lower({_sql_literal(table)})"]
    if len(raw_parts) >= 2:
        schema = raw_parts[-2]
        filters.append(f"lower(table_schema) = lower({_sql_literal(schema)})")
    else:
        filters.append("table_schema = current_schema()")
    if len(raw_parts) >= 3:
        catalog = raw_parts[-3]
        filters.append(f"lower(table_catalog) = lower({_sql_literal(catalog)})")

    sql = f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE {' AND '.join(filters)}
        ORDER BY ordinal_position
    """
    return _query_frame(connection, sql, f"reading schema for {table_name}")


def _resolve_column(requested_name: str, column_lookup: dict[str, str], field_name: str) -> str:
    if not isinstance(requested_name, str) or not requested_name.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    actual_name = column_lookup.get(requested_name.strip().lower())
    if actual_name is None:
        raise KeyError(requested_name)
    return actual_name


def _resolve_expected_date(connection: Any, expected_date: date | datetime | str | None) -> date:
    if expected_date is not None:
        return _normalize_date(expected_date, "expected_date")

    as_of_date = date.today()
    sql = f"""
        SELECT MAX(CAST(FullDate AS DATE)) AS expected_date
        FROM "CherryMon"."main"."dimCalendar"
        WHERE IsHoliday = 'N'
          AND CAST(FullDate AS DATE) <= DATE '{as_of_date.isoformat()}'
    """
    frame = _query_frame(connection, sql, "resolving latest trading date from dimCalendar")
    resolved = frame["expected_date"].iloc[0] if not frame.empty else None
    if pd.isna(resolved):
        raise RuntimeError(
            "Unable to resolve expected trading date from CherryMon.main.dimCalendar."
        )
    return _normalize_date(resolved, "expected_date")


def _change_severity(
    metric_name: str,
    change_pct: float | None,
    threshold: float,
    errors: list[str],
    warnings: list[str],
) -> None:
    if change_pct is None or abs(change_pct) <= threshold:
        return
    message = (
        f"{metric_name} changed {change_pct:+.2%}, exceeding threshold {threshold:.2%}."
    )
    if abs(change_pct) > threshold * 2:
        errors.append(message)
    else:
        warnings.append(message)


def _zscore_severity(
    metric_name: str,
    zscore: float | None,
    errors: list[str],
    warnings: list[str],
) -> None:
    if zscore is None:
        return
    absolute_zscore = abs(zscore)
    message = f"{metric_name} historical z-score is {zscore:+.2f}."
    if absolute_zscore >= _ZSCORE_FAIL:
        errors.append(message)
    elif absolute_zscore >= _ZSCORE_WARNING:
        warnings.append(message)


def _calculate_history_metrics(
    current_value: int,
    history_values: pd.Series,
) -> tuple[float | None, float | None, float | None]:
    if len(history_values) < 2:
        return None, None, None
    numeric_history = pd.to_numeric(history_values, errors="coerce").dropna()
    if len(numeric_history) < 2:
        return None, None, None
    mean_value = float(numeric_history.mean())
    std_value = float(numeric_history.std(ddof=0))
    if std_value == 0:
        zscore = 0.0 if float(current_value) == mean_value else None
    else:
        zscore = (float(current_value) - mean_value) / std_value
    return mean_value, std_value, zscore


def _base_result(table_name: str) -> dict[str, Any]:
    return {
        "status": "PASS",
        "table": table_name,
        "metrics": {
            "expected_date": None,
            "max_date": None,
            "date_lag": None,
            "row_count_current": None,
            "row_count_previous": None,
            "row_count_change_pct": None,
            "symbol_count_current": None,
            "symbol_count_previous": None,
            "symbol_count_change_pct": None,
            "missing_symbol_count": 0,
            "missing_symbols": [],
            "new_symbol_count": 0,
            "new_symbols": [],
            "duplicate_count": None,
            "null_rate": {},
            "historical_null_rate": {},
            "historical_row_mean": None,
            "historical_row_std": None,
            "row_count_zscore": None,
            "historical_symbol_mean": None,
            "historical_symbol_std": None,
            "symbol_count_zscore": None,
            "invalid_date_count": 0,
            "invalid_numeric_count": 0,
            "invalid_ohlc_count": 0,
            "negative_price_count": 0,
            "negative_volume_value_count": 0,
        },
        "errors": [],
        "warnings": [],
    }


def _finalize_result(validation_result: dict[str, Any]) -> dict[str, Any]:
    errors = validation_result["errors"]
    warnings = validation_result["warnings"]
    validation_result["status"] = "FAIL" if errors else "WARNING" if warnings else "PASS"
    return validation_result


def _log_validation_summary(validation_result: dict[str, Any]) -> None:
    metrics = validation_result["metrics"]
    print(
        "[DataValidation] "
        f"table={validation_result['table']} | status={validation_result['status']} | "
        f"expected_date={metrics['expected_date']} | max_date={metrics['max_date']} | "
        f"rows={metrics['row_count_current']} | symbols={metrics['symbol_count_current']} | "
        f"duplicates={metrics['duplicate_count']} | missing_symbols={metrics['missing_symbol_count']}"
    )
    if validation_result["errors"]:
        print(f"[DataValidation][ERROR] {' | '.join(validation_result['errors'])}")
    if validation_result["warnings"]:
        print(f"[DataValidation][WARNING] {' | '.join(validation_result['warnings'])}")


def validate_data_quality(
    connection: Any,
    table_name: str,
    date_col: str = "Date",
    symbol_col: str = "Ticker",
    key_cols: Sequence[str] | None = None,
    required_cols: Sequence[str] | None = None,
    expected_date: date | datetime | str | None = None,
    max_row_change_pct: float = DEFAULT_MAX_ROW_CHANGE_PCT,
    max_symbol_change_pct: float = DEFAULT_MAX_SYMBOL_CHANGE_PCT,
    max_null_rate: float = DEFAULT_MAX_NULL_RATE,
    history_window: int = DEFAULT_HISTORY_WINDOW,
) -> dict[str, Any]:
    """Validate freshness, completeness, integrity, and anomalies for a DuckDB table.

    The supplied connection is reused and never closed or mutated by this function. Data-quality
    failures are returned as ``PASS``/``WARNING``/``FAIL``. Invalid function configuration raises
    ``TypeError``/``ValueError`` while database query failures raise ``RuntimeError``.
    """
    if connection is None:
        raise ValueError("connection is required; validate_data_quality does not open DuckDB itself")
    quoted_table = _quote_relation(table_name)
    max_row_change_pct = _validate_threshold("max_row_change_pct", max_row_change_pct)
    max_symbol_change_pct = _validate_threshold(
        "max_symbol_change_pct", max_symbol_change_pct
    )
    max_null_rate = _validate_threshold("max_null_rate", max_null_rate)
    if not isinstance(history_window, int) or isinstance(history_window, bool) or history_window < 2:
        raise ValueError("history_window must be an integer >= 2")

    validation_result = _base_result(table_name)
    metrics: dict[str, Any] = validation_result["metrics"]
    errors: list[str] = validation_result["errors"]
    warnings: list[str] = validation_result["warnings"]

    schema_frame = _get_table_schema(connection, table_name)
    if schema_frame.empty:
        errors.append(f"Table {table_name!r} does not exist or has no readable schema.")
        finalized = _finalize_result(validation_result)
        _log_validation_summary(finalized)
        return finalized

    column_lookup = {
        str(column_name).lower(): str(column_name)
        for column_name in schema_frame["column_name"].tolist()
    }
    try:
        actual_date_col = _resolve_column(date_col, column_lookup, "date_col")
        actual_symbol_col = _resolve_column(symbol_col, column_lookup, "symbol_col")
    except KeyError as exc:
        errors.append(f"Required validation column is missing: {exc.args[0]!r}.")
        finalized = _finalize_result(validation_result)
        _log_validation_summary(finalized)
        return finalized

    requested_required_cols = _normalize_column_sequence(
        required_cols, [date_col, symbol_col], "required_cols"
    )
    requested_key_cols = _normalize_column_sequence(
        key_cols, [symbol_col, date_col], "key_cols"
    )

    resolved_required_cols: list[str] = []
    resolved_key_cols: list[str] = []
    missing_configured_columns: list[str] = []
    for requested_name in requested_required_cols:
        try:
            resolved_required_cols.append(
                _resolve_column(requested_name, column_lookup, "required_cols")
            )
        except KeyError:
            missing_configured_columns.append(str(requested_name))
    for requested_name in requested_key_cols:
        try:
            resolved_key_cols.append(_resolve_column(requested_name, column_lookup, "key_cols"))
        except KeyError:
            missing_configured_columns.append(str(requested_name))

    if missing_configured_columns:
        missing_columns = sorted(set(missing_configured_columns))
        errors.append(f"Configured validation columns are missing: {missing_columns}.")
        finalized = _finalize_result(validation_result)
        _log_validation_summary(finalized)
        return finalized

    try:
        resolved_expected_date = _resolve_expected_date(connection, expected_date)
    except RuntimeError as exc:
        errors.append(str(exc))
        finalized = _finalize_result(validation_result)
        _log_validation_summary(finalized)
        return finalized
    metrics["expected_date"] = resolved_expected_date.isoformat()

    quoted_date_col = _quote_identifier(actual_date_col)
    quoted_symbol_col = _quote_identifier(actual_symbol_col)

    invalid_date_sql = f"""
        SELECT COUNT(*) AS invalid_date_count
        FROM {quoted_table}
        WHERE {quoted_date_col} IS NOT NULL
          AND TRY_CAST({quoted_date_col} AS DATE) IS NULL
    """
    invalid_date_frame = _query_frame(connection, invalid_date_sql, "checking invalid dates")
    invalid_date_count = int(invalid_date_frame["invalid_date_count"].iloc[0])
    metrics["invalid_date_count"] = invalid_date_count
    if invalid_date_count > 0:
        errors.append(f"Found {invalid_date_count} rows with invalid {actual_date_col} values.")

    daily_sql = f"""
        WITH daily_counts AS (
            SELECT
                TRY_CAST({quoted_date_col} AS DATE) AS validation_date,
                COUNT(*) AS row_count,
                COUNT(DISTINCT {quoted_symbol_col}) AS symbol_count
            FROM {quoted_table}
            WHERE {quoted_date_col} IS NOT NULL
            GROUP BY TRY_CAST({quoted_date_col} AS DATE)
        )
        SELECT validation_date, row_count, symbol_count
        FROM daily_counts
        WHERE validation_date IS NOT NULL
        ORDER BY validation_date DESC
        LIMIT {history_window + 1}
    """
    daily_frame = _query_frame(connection, daily_sql, "calculating daily validation metrics")
    if daily_frame.empty:
        errors.append(f"Table {table_name!r} has no valid dated rows.")
        finalized = _finalize_result(validation_result)
        _log_validation_summary(finalized)
        return finalized

    current_date = _normalize_date(daily_frame["validation_date"].iloc[0], "max_date")
    current_row_count = int(daily_frame["row_count"].iloc[0])
    current_symbol_count = int(daily_frame["symbol_count"].iloc[0])
    metrics["max_date"] = current_date.isoformat()
    metrics["date_lag"] = (resolved_expected_date - current_date).days
    metrics["row_count_current"] = current_row_count
    metrics["symbol_count_current"] = current_symbol_count

    if current_date < resolved_expected_date:
        errors.append(
            f"Data is stale: max_date={current_date.isoformat()}, "
            f"expected_date={resolved_expected_date.isoformat()}."
        )
    elif current_date > resolved_expected_date:
        errors.append(
            f"Data date is ahead of expected trading date: max_date={current_date.isoformat()}, "
            f"expected_date={resolved_expected_date.isoformat()}."
        )

    previous_date: date | None = None
    previous_row_count: int | None = None
    previous_symbol_count: int | None = None
    if len(daily_frame) >= 2:
        previous_date = _normalize_date(daily_frame["validation_date"].iloc[1], "previous_date")
        previous_row_count = int(daily_frame["row_count"].iloc[1])
        previous_symbol_count = int(daily_frame["symbol_count"].iloc[1])
        metrics["row_count_previous"] = previous_row_count
        metrics["symbol_count_previous"] = previous_symbol_count

        if previous_row_count > 0:
            row_change_pct = (current_row_count - previous_row_count) / previous_row_count
            metrics["row_count_change_pct"] = row_change_pct
            _change_severity(
                "Row count", row_change_pct, max_row_change_pct, errors, warnings
            )
        else:
            warnings.append("Previous row count is zero; row-count change is unavailable.")

        if previous_symbol_count > 0:
            symbol_change_pct = (
                current_symbol_count - previous_symbol_count
            ) / previous_symbol_count
            metrics["symbol_count_change_pct"] = symbol_change_pct
            _change_severity(
                "Symbol count",
                symbol_change_pct,
                max_symbol_change_pct,
                errors,
                warnings,
            )
        else:
            warnings.append("Previous symbol count is zero; symbol-count change is unavailable.")
    else:
        warnings.append("Only one valid data date is available; previous-date comparisons are unavailable.")

    history_frame = daily_frame.iloc[1 : history_window + 1]
    if len(history_frame) < history_window:
        warnings.append(
            f"Historical baseline has {len(history_frame)} periods; requested {history_window}."
        )
    historical_row_mean, historical_row_std, row_count_zscore = _calculate_history_metrics(
        current_row_count,
        history_frame["row_count"],
    )
    historical_symbol_mean, historical_symbol_std, symbol_count_zscore = (
        _calculate_history_metrics(current_symbol_count, history_frame["symbol_count"])
    )
    metrics["historical_row_mean"] = historical_row_mean
    metrics["historical_row_std"] = historical_row_std
    metrics["row_count_zscore"] = row_count_zscore
    metrics["historical_symbol_mean"] = historical_symbol_mean
    metrics["historical_symbol_std"] = historical_symbol_std
    metrics["symbol_count_zscore"] = symbol_count_zscore
    if historical_row_std == 0 and historical_row_mean is not None and current_row_count != historical_row_mean:
        errors.append(
            "Row count differs from a zero-variance historical baseline: "
            f"current={current_row_count}, baseline={historical_row_mean:.2f}."
        )
    else:
        _zscore_severity("Row count", row_count_zscore, errors, warnings)
    if (
        historical_symbol_std == 0
        and historical_symbol_mean is not None
        and current_symbol_count != historical_symbol_mean
    ):
        errors.append(
            "Symbol count differs from a zero-variance historical baseline: "
            f"current={current_symbol_count}, baseline={historical_symbol_mean:.2f}."
        )
    else:
        _zscore_severity("Symbol count", symbol_count_zscore, errors, warnings)

    current_date_literal = current_date.isoformat()
    if previous_date is not None:
        previous_date_literal = previous_date.isoformat()
        symbol_delta_sql = f"""
            WITH current_symbols AS (
                SELECT DISTINCT CAST({quoted_symbol_col} AS VARCHAR) AS symbol
                FROM {quoted_table}
                WHERE TRY_CAST({quoted_date_col} AS DATE) = DATE '{current_date_literal}'
                  AND {quoted_symbol_col} IS NOT NULL
            ),
            previous_symbols AS (
                SELECT DISTINCT CAST({quoted_symbol_col} AS VARCHAR) AS symbol
                FROM {quoted_table}
                WHERE TRY_CAST({quoted_date_col} AS DATE) = DATE '{previous_date_literal}'
                  AND {quoted_symbol_col} IS NOT NULL
            )
            SELECT 'missing' AS change_type, symbol
            FROM previous_symbols
            WHERE symbol NOT IN (SELECT symbol FROM current_symbols)
            UNION ALL
            SELECT 'new' AS change_type, symbol
            FROM current_symbols
            WHERE symbol NOT IN (SELECT symbol FROM previous_symbols)
            ORDER BY change_type, symbol
        """
        symbol_delta_frame = _query_frame(
            connection, symbol_delta_sql, "comparing current and previous symbols"
        )
        missing_symbols = symbol_delta_frame.loc[
            symbol_delta_frame["change_type"] == "missing", "symbol"
        ].astype(str).tolist()
        new_symbols = symbol_delta_frame.loc[
            symbol_delta_frame["change_type"] == "new", "symbol"
        ].astype(str).tolist()
        metrics["missing_symbol_count"] = len(missing_symbols)
        metrics["missing_symbols"] = missing_symbols
        metrics["new_symbol_count"] = len(new_symbols)
        metrics["new_symbols"] = new_symbols

        if previous_symbol_count:
            missing_symbol_rate = len(missing_symbols) / previous_symbol_count
            _change_severity(
                "Missing-symbol rate",
                -missing_symbol_rate,
                max_symbol_change_pct,
                errors,
                warnings,
            )

    quoted_keys = ", ".join(_quote_identifier(column) for column in resolved_key_cols)
    duplicate_scope = (
        f"WHERE TRY_CAST({quoted_date_col} AS DATE) = DATE '{current_date_literal}'"
        if actual_date_col in resolved_key_cols
        else ""
    )
    duplicate_sql = f"""
        SELECT COALESCE(SUM(duplicate_rows), 0) AS duplicate_count
        FROM (
            SELECT COUNT(*) - 1 AS duplicate_rows
            FROM {quoted_table}
            {duplicate_scope}
            GROUP BY {quoted_keys}
            HAVING COUNT(*) > 1
        ) AS duplicate_groups
    """
    duplicate_frame = _query_frame(connection, duplicate_sql, "checking duplicate keys")
    duplicate_count = int(duplicate_frame["duplicate_count"].iloc[0])
    metrics["duplicate_count"] = duplicate_count
    if duplicate_count > 0:
        errors.append(
            f"Found {duplicate_count} duplicate rows beyond unique key {resolved_key_cols}."
        )

    null_expressions = [
        f"SUM(CASE WHEN {_quote_identifier(column)} IS NULL THEN 1 ELSE 0 END) "
        f"AS {_quote_identifier(f'null_{index}') }"
        for index, column in enumerate(resolved_required_cols)
    ]
    null_sql = f"""
        SELECT COUNT(*) AS total_rows, {', '.join(null_expressions)}
        FROM {quoted_table}
        WHERE TRY_CAST({quoted_date_col} AS DATE) = DATE '{current_date_literal}'
    """
    null_frame = _query_frame(connection, null_sql, "checking required-column NULL rates")
    total_rows = int(null_frame["total_rows"].iloc[0])
    for index, column in enumerate(resolved_required_cols):
        null_count = int(null_frame[f"null_{index}"].iloc[0])
        null_rate = null_count / total_rows if total_rows else 0.0
        metrics["null_rate"][column] = null_rate
        if null_rate > max_null_rate:
            errors.append(
                f"{column} NULL rate is {null_rate:.2%}, exceeding {max_null_rate:.2%}."
            )

    if not history_frame.empty and resolved_required_cols:
        historical_null_parts = [
            f"AVG(null_count_{index} * 1.0 / NULLIF(total_rows, 0)) "
            f"AS {_quote_identifier(f'null_rate_{index}') }"
            for index in range(len(resolved_required_cols))
        ]
        per_day_null_parts = [
            f"SUM(CASE WHEN {_quote_identifier(column)} IS NULL THEN 1 ELSE 0 END) "
            f"AS {_quote_identifier(f'null_count_{index}') }"
            for index, column in enumerate(resolved_required_cols)
        ]
        historical_null_sql = f"""
            WITH historical_daily AS (
                SELECT
                    TRY_CAST({quoted_date_col} AS DATE) AS validation_date,
                    COUNT(*) AS total_rows,
                    {', '.join(per_day_null_parts)}
                FROM {quoted_table}
                WHERE TRY_CAST({quoted_date_col} AS DATE) < DATE '{current_date_literal}'
                GROUP BY TRY_CAST({quoted_date_col} AS DATE)
                ORDER BY validation_date DESC
                LIMIT {history_window}
            )
            SELECT {', '.join(historical_null_parts)}
            FROM historical_daily
        """
        historical_null_frame = _query_frame(
            connection, historical_null_sql, "calculating historical NULL-rate baseline"
        )
        for index, column in enumerate(resolved_required_cols):
            baseline_value = historical_null_frame[f"null_rate_{index}"].iloc[0]
            if pd.isna(baseline_value):
                continue
            historical_null_rate = float(baseline_value)
            metrics["historical_null_rate"][column] = historical_null_rate
            current_null_rate = float(metrics["null_rate"][column])
            meaningful_increase = max(0.01, historical_null_rate)
            if (
                current_null_rate <= max_null_rate
                and current_null_rate > historical_null_rate + meaningful_increase
            ):
                warnings.append(
                    f"{column} NULL rate rose to {current_null_rate:.2%} from historical "
                    f"{historical_null_rate:.2%}."
                )

    lower_columns = {column.lower(): column for column in column_lookup.values()}
    price_columns = [
        lower_columns[name]
        for name in ("open", "high", "low", "close")
        if name in lower_columns
    ]
    volume_value_columns = [
        lower_columns[name] for name in ("volume", "value") if name in lower_columns
    ]
    numeric_columns = price_columns + volume_value_columns
    if numeric_columns:
        invalid_numeric_conditions = [
            f"({_quote_identifier(column)} IS NOT NULL AND "
            f"TRY_CAST({_quote_identifier(column)} AS DOUBLE) IS NULL)"
            for column in numeric_columns
        ]
        negative_price_conditions = [
            f"COALESCE(TRY_CAST({_quote_identifier(column)} AS DOUBLE) < 0, FALSE)"
            for column in price_columns
        ]
        negative_volume_value_conditions = [
            f"COALESCE(TRY_CAST({_quote_identifier(column)} AS DOUBLE) < 0, FALSE)"
            for column in volume_value_columns
        ]
        validity_selects = [
            "SUM(CASE WHEN "
            + " OR ".join(invalid_numeric_conditions)
            + " THEN 1 ELSE 0 END) AS invalid_numeric_count"
        ]
        if negative_price_conditions:
            validity_selects.append(
                "SUM(CASE WHEN "
                + " OR ".join(negative_price_conditions)
                + " THEN 1 ELSE 0 END) AS negative_price_count"
            )
        if negative_volume_value_conditions:
            validity_selects.append(
                "SUM(CASE WHEN "
                + " OR ".join(negative_volume_value_conditions)
                + " THEN 1 ELSE 0 END) AS negative_volume_value_count"
            )
        if all(name in lower_columns for name in ("open", "high", "low", "close")):
            open_col = _quote_identifier(lower_columns["open"])
            high_col = _quote_identifier(lower_columns["high"])
            low_col = _quote_identifier(lower_columns["low"])
            close_col = _quote_identifier(lower_columns["close"])
            validity_selects.append(
                "SUM(CASE WHEN "
                f"TRY_CAST({high_col} AS DOUBLE) < TRY_CAST({low_col} AS DOUBLE) OR "
                f"TRY_CAST({high_col} AS DOUBLE) < TRY_CAST({open_col} AS DOUBLE) OR "
                f"TRY_CAST({high_col} AS DOUBLE) < TRY_CAST({close_col} AS DOUBLE) OR "
                f"TRY_CAST({low_col} AS DOUBLE) > TRY_CAST({open_col} AS DOUBLE) OR "
                f"TRY_CAST({low_col} AS DOUBLE) > TRY_CAST({close_col} AS DOUBLE) "
                "THEN 1 ELSE 0 END) AS invalid_ohlc_count"
            )

        validity_sql = f"""
            SELECT {', '.join(validity_selects)}
            FROM {quoted_table}
            WHERE TRY_CAST({quoted_date_col} AS DATE) = DATE '{current_date_literal}'
        """
        validity_frame = _query_frame(connection, validity_sql, "checking numeric and OHLC validity")
        for metric_name in (
            "invalid_numeric_count",
            "negative_price_count",
            "negative_volume_value_count",
            "invalid_ohlc_count",
        ):
            if metric_name in validity_frame.columns:
                value = validity_frame[metric_name].iloc[0]
                count = 0 if pd.isna(value) else int(value)
                metrics[metric_name] = count
                if count > 0:
                    errors.append(f"{metric_name}={count} on {current_date_literal}.")

    finalized = _finalize_result(validation_result)
    _log_validation_summary(finalized)
    return finalized


def _to_json_compatible(value: Any) -> Any:
    """Normalize validation payload values so DuckDB JSON receives valid JSON."""
    import math

    if value is None:
        return None
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _to_json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_json_compatible(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "item"):
        try:
            return _to_json_compatible(value.item())
        except (TypeError, ValueError):
            pass
    return value


def _validate_audit_payload(validation_result: dict[str, Any]) -> None:
    if not isinstance(validation_result, dict):
        raise TypeError("validation_result must be a dict returned by validate_data_quality")

    required_keys = {"status", "table", "metrics", "errors", "warnings"}
    missing_keys = sorted(required_keys.difference(validation_result))
    if missing_keys:
        raise ValueError(f"validation_result is missing required keys: {missing_keys}")

    if validation_result["status"] not in {"PASS", "WARNING", "FAIL"}:
        raise ValueError("validation_result.status must be PASS, WARNING, or FAIL")
    if not isinstance(validation_result["table"], str) or not validation_result["table"].strip():
        raise ValueError("validation_result.table must be a non-empty string")
    if not isinstance(validation_result["metrics"], dict):
        raise TypeError("validation_result.metrics must be a dict")
    if not isinstance(validation_result["errors"], list):
        raise TypeError("validation_result.errors must be a list")
    if not isinstance(validation_result["warnings"], list):
        raise TypeError("validation_result.warnings must be a list")


def persist_data_quality_result(
    connection: Any,
    validation_result: dict[str, Any],
    pipeline_name: str,
    audit_table: str = DEFAULT_AUDIT_TABLE,
    validation_id: str | None = None,
    checked_at: datetime | None = None,
) -> str:
    """Persist one validation event into the configured DuckDB audit table.

    The caller owns the supplied connection and transaction. This function does not open, close,
    commit, or rollback the connection. Core validation remains read-only; only this persistence
    helper writes audit history. Supplying the same ``validation_id`` more than once is idempotent.

    The audit table must contain these core columns: ``validation_id``, ``checked_at``,
    ``pipeline_name``, ``table_name``, ``status``, ``metrics``, ``errors``, and ``warnings``.
    Known metric columns are persisted when present in the audit schema; detailed payloads are
    always preserved in the JSON columns.
    """
    import json
    import uuid

    if connection is None:
        raise ValueError("connection is required; persist_data_quality_result does not open DuckDB itself")
    if not isinstance(pipeline_name, str) or not pipeline_name.strip():
        raise ValueError("pipeline_name must be a non-empty string")
    if checked_at is not None and not isinstance(checked_at, datetime):
        raise TypeError("checked_at must be datetime or None")

    _validate_audit_payload(validation_result)

    audit_schema = _get_table_schema(connection, audit_table)
    if audit_schema.empty:
        raise RuntimeError(f"Audit table {audit_table!r} does not exist or has no readable schema.")

    audit_columns = {
        str(column_name).lower(): (str(column_name), str(data_type).upper())
        for column_name, data_type in audit_schema[["column_name", "data_type"]].itertuples(
            index=False, name=None
        )
    }
    required_audit_columns = {
        "validation_id",
        "checked_at",
        "pipeline_name",
        "table_name",
        "status",
        "metrics",
        "errors",
        "warnings",
    }
    missing_audit_columns = sorted(required_audit_columns.difference(audit_columns))
    if missing_audit_columns:
        raise RuntimeError(
            f"Audit table {audit_table!r} is missing required columns: {missing_audit_columns}."
        )

    resolved_validation_id = validation_id.strip() if isinstance(validation_id, str) else None
    if validation_id is not None and not resolved_validation_id:
        raise ValueError("validation_id must be a non-empty string when supplied")
    resolved_validation_id = resolved_validation_id or str(uuid.uuid4())
    resolved_checked_at = checked_at or datetime.now().astimezone()

    metrics = validation_result["metrics"]
    audit_values: dict[str, Any] = {
        "validation_id": resolved_validation_id,
        "checked_at": resolved_checked_at,
        "pipeline_name": pipeline_name.strip(),
        "table_name": validation_result["table"],
        "expected_date": metrics.get("expected_date"),
        "max_date": metrics.get("max_date"),
        "status": validation_result["status"],
        "row_count_current": metrics.get("row_count_current"),
        "row_count_previous": metrics.get("row_count_previous"),
        "row_count_change_pct": metrics.get("row_count_change_pct"),
        "symbol_count_current": metrics.get("symbol_count_current"),
        "symbol_count_previous": metrics.get("symbol_count_previous"),
        "symbol_count_change_pct": metrics.get("symbol_count_change_pct"),
        "missing_symbol_count": metrics.get("missing_symbol_count"),
        "new_symbol_count": metrics.get("new_symbol_count"),
        "duplicate_count": metrics.get("duplicate_count"),
        "row_count_zscore": metrics.get("row_count_zscore"),
        "symbol_count_zscore": metrics.get("symbol_count_zscore"),
        "metrics": json.dumps(
            _to_json_compatible(metrics), ensure_ascii=False, sort_keys=True, allow_nan=False
        ),
        "errors": json.dumps(
            _to_json_compatible(validation_result["errors"]),
            ensure_ascii=False,
            allow_nan=False,
        ),
        "warnings": json.dumps(
            _to_json_compatible(validation_result["warnings"]),
            ensure_ascii=False,
            allow_nan=False,
        ),
    }

    insert_column_names: list[str] = []
    insert_values: list[Any] = []
    value_expressions: list[str] = []
    for logical_name, value in audit_values.items():
        schema_entry = audit_columns.get(logical_name)
        if schema_entry is None:
            continue
        actual_name, data_type = schema_entry
        insert_column_names.append(actual_name)
        insert_values.append(value)
        if data_type == "JSON":
            value_expressions.append("CAST(? AS JSON)")
        elif data_type == "DATE":
            value_expressions.append("CAST(? AS DATE)")
        elif data_type.startswith("TIMESTAMP"):
            value_expressions.append("CAST(? AS TIMESTAMP)")
        else:
            value_expressions.append("?")

    quoted_audit_table = _quote_relation(audit_table)
    quoted_insert_columns = ", ".join(
        _quote_identifier(column_name) for column_name in insert_column_names
    )
    validation_id_column = _quote_identifier(audit_columns["validation_id"][0])
    insert_sql = f"""
        INSERT INTO {quoted_audit_table} ({quoted_insert_columns})
        SELECT {', '.join(value_expressions)}
        WHERE NOT EXISTS (
            SELECT 1
            FROM {quoted_audit_table}
            WHERE {validation_id_column} = ?
        )
    """

    try:
        # DuckLib.returnSQL is intentionally SELECT-only. Audit persistence requires a
        # parameterized write on the caller-owned writer connection.
        connection.execute(insert_sql, [*insert_values, resolved_validation_id])
    except Exception as exc:
        raise RuntimeError(
            f"Failed to persist data-quality audit for table {validation_result['table']!r} "
            f"into {audit_table!r}: {exc}"
        ) from exc

    print(
        "[DataValidation][AUDIT] "
        f"validation_id={resolved_validation_id} | pipeline={pipeline_name.strip()} | "
        f"table={validation_result['table']} | status={validation_result['status']}"
    )
    return resolved_validation_id
