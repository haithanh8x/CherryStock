from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping, Sequence
from uuid import uuid4

import pandas as pd

from Ults.DataValidation import (
    DEFAULT_AUDIT_TABLE,
    DEFAULT_HISTORY_WINDOW,
    DEFAULT_MAX_NULL_RATE,
    DEFAULT_MAX_ROW_CHANGE_PCT,
    DEFAULT_MAX_SYMBOL_CHANGE_PCT,
    persist_data_quality_result,
    validate_data_quality,
)
from Ults.DuckLib import returnSQL


def _quote_identifier(identifier: str) -> str:
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("filter column must be a non-empty string")
    cleaned = identifier.strip().strip('"')
    if "\x00" in cleaned:
        raise ValueError(f"Invalid SQL identifier: {identifier!r}")
    return f'"{cleaned.replace(chr(34), chr(34) * 2)}"'


def _quote_relation(relation_name: str) -> str:
    if not isinstance(relation_name, str) or not relation_name.strip():
        raise ValueError("table_name must be a non-empty string")
    parts = [part.strip().strip('"') for part in relation_name.split(".")]
    if any(not part for part in parts):
        raise ValueError(f"Invalid table_name: {relation_name!r}")
    return ".".join(_quote_identifier(part) for part in parts)


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if pd.isna(value):
            return "NULL"
        return str(value)
    if isinstance(value, datetime):
        return f"TIMESTAMP '{value.isoformat(sep=' ')}'"
    if isinstance(value, date):
        return f"DATE '{value.isoformat()}'"
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def _build_filter_predicate(filters: Mapping[str, Any] | None) -> str | None:
    if filters is None:
        return None
    if not isinstance(filters, Mapping):
        raise TypeError("filters must be a mapping of column names to filter values")
    if not filters:
        raise ValueError("filters must not be empty when supplied")

    predicates: list[str] = []
    for column_name, filter_value in filters.items():
        quoted_column = _quote_identifier(column_name)
        if isinstance(filter_value, Sequence) and not isinstance(
            filter_value, (str, bytes, bytearray)
        ):
            values = list(filter_value)
            if not values:
                raise ValueError(f"Filter sequence for {column_name!r} must not be empty")
            non_null_values = [value for value in values if value is not None]
            clauses: list[str] = []
            if non_null_values:
                sql_values = ", ".join(_sql_literal(value) for value in non_null_values)
                clauses.append(f"{quoted_column} IN ({sql_values})")
            if len(non_null_values) != len(values):
                clauses.append(f"{quoted_column} IS NULL")
            predicates.append("(" + " OR ".join(clauses) + ")")
        elif filter_value is None:
            predicates.append(f"{quoted_column} IS NULL")
        else:
            predicates.append(f"{quoted_column} = {_sql_literal(filter_value)}")
    return " AND ".join(predicates)


def validate_and_persist_data_quality(
    connection: Any,
    table_name: str,
    pipeline_name: str,
    *,
    date_col: str = "Date",
    symbol_col: str = "Ticker",
    key_cols: Sequence[str] | None = None,
    required_cols: Sequence[str] | None = None,
    optional_null_rate_cols: Sequence[str] | None = None,
    max_optional_null_rate: float = 0.35,
    expected_date: date | datetime | str | None = None,
    check_count_anomalies: bool = True,
    max_row_change_pct: float = DEFAULT_MAX_ROW_CHANGE_PCT,
    max_symbol_change_pct: float = DEFAULT_MAX_SYMBOL_CHANGE_PCT,
    max_null_rate: float = DEFAULT_MAX_NULL_RATE,
    history_window: int = DEFAULT_HISTORY_WINDOW,
    filters: Mapping[str, Any] | None = None,
    audit_table: str = DEFAULT_AUDIT_TABLE,
    validation_id: str | None = None,
    checked_at: datetime | None = None,
    raise_on_fail: bool = True,
) -> dict[str, Any]:
    """Validate a dated dataset scope, persist its audit result, then apply failure policy."""
    if connection is None:
        raise ValueError(
            "connection is required; validate_and_persist_data_quality does not open DuckDB itself"
        )
    if not isinstance(raise_on_fail, bool):
        raise TypeError("raise_on_fail must be bool")

    filter_predicate = _build_filter_predicate(filters)
    validation_table = table_name
    temporary_view: str | None = None

    if filter_predicate is not None:
        temporary_view = f"_dq_scope_{uuid4().hex}"
        quoted_view = _quote_identifier(temporary_view)
        quoted_source = _quote_relation(table_name)
        connection.execute(
            f"CREATE TEMPORARY VIEW {quoted_view} AS "
            f"SELECT * FROM {quoted_source} WHERE {filter_predicate}"
        )
        validation_table = temporary_view

    try:
        validation_result = validate_data_quality(
            connection=connection,
            table_name=validation_table,
            date_col=date_col,
            symbol_col=symbol_col,
            key_cols=key_cols,
            required_cols=required_cols,
            optional_null_rate_cols=optional_null_rate_cols,
            max_optional_null_rate=max_optional_null_rate,
            expected_date=expected_date,
            check_count_anomalies=check_count_anomalies,
            max_row_change_pct=max_row_change_pct,
            max_symbol_change_pct=max_symbol_change_pct,
            max_null_rate=max_null_rate,
            history_window=history_window,
        )

        validation_result["table"] = table_name
        validation_result["metrics"]["filters"] = dict(filters) if filters is not None else None

        resolved_validation_id = persist_data_quality_result(
            connection=connection,
            validation_result=validation_result,
            pipeline_name=pipeline_name,
            audit_table=audit_table,
            validation_id=validation_id,
            checked_at=checked_at,
        )
        validation_result["validation_id"] = resolved_validation_id

        if raise_on_fail and validation_result["status"] == "FAIL":
            error_summary = " | ".join(validation_result["errors"]) or "Unknown validation error"
            raise RuntimeError(
                f"Data quality validation failed for {table_name!r}: {error_summary}"
            )
        return validation_result
    finally:
        if temporary_view is not None:
            connection.execute(f"DROP VIEW IF EXISTS {_quote_identifier(temporary_view)}")



YAHOO_OHLC_WARNING_TICKERS: tuple[str, ...] = ("VND=X",)


def validate_and_persist_yahoo_eod_quality(
    connection: Any,
    table_name: str,
    pipeline_name: str,
    *,
    scope_tickers: Sequence[str],
    expected_date: date | datetime | str | None = None,
    ohlc_warning_tickers: Sequence[str] = YAHOO_OHLC_WARNING_TICKERS,
    date_col: str = "Date",
    symbol_col: str = "Ticker",
    key_cols: Sequence[str] = ("Ticker", "Date"),
    required_cols: Sequence[str] = ("Ticker", "Date", "Open", "High", "Low", "Close"),
    audit_table: str = DEFAULT_AUDIT_TABLE,
    validation_id: str | None = None,
    checked_at: datetime | None = None,
    raise_on_fail: bool = True,
) -> dict[str, Any]:
    """Validate Yahoo EOD with a source-specific OHLC warning policy for VND=X.

    The generic DataValidation contract remains unchanged. This wrapper validates the
    complete Yahoo scope once, then downgrades only current-date OHLC envelope
    violations attributable exclusively to configured warning tickers. All other
    validation failures remain blocking.
    """
    if connection is None:
        raise ValueError("connection is required")
    if not isinstance(raise_on_fail, bool):
        raise TypeError("raise_on_fail must be bool")

    resolved_scope = [str(value).strip() for value in scope_tickers if str(value).strip()]
    if not resolved_scope:
        raise ValueError("scope_tickers must not be empty")
    resolved_scope = list(dict.fromkeys(resolved_scope))

    resolved_warning = [
        str(value).strip() for value in ohlc_warning_tickers if str(value).strip()
    ]
    resolved_warning = list(dict.fromkeys(resolved_warning))
    unknown_warning = sorted(set(resolved_warning).difference(resolved_scope))
    if unknown_warning:
        raise ValueError(
            "ohlc_warning_tickers must be a subset of scope_tickers: "
            + ", ".join(unknown_warning)
        )

    filter_predicate = _build_filter_predicate({symbol_col: resolved_scope})
    temporary_view = f"_dq_yahoo_scope_{uuid4().hex}"
    quoted_view = _quote_identifier(temporary_view)
    quoted_source = _quote_relation(table_name)
    connection.execute(
        f"CREATE TEMPORARY VIEW {quoted_view} AS "
        f"SELECT * FROM {quoted_source} WHERE {filter_predicate}"
    )

    try:
        validation_result = validate_data_quality(
            connection=connection,
            table_name=temporary_view,
            date_col=date_col,
            symbol_col=symbol_col,
            key_cols=key_cols,
            required_cols=required_cols,
            expected_date=expected_date,
            check_count_anomalies=False,
        )
        validation_result["table"] = table_name
        metrics = validation_result["metrics"]
        metrics["filters"] = {symbol_col: resolved_scope}
        metrics["ohlc_policy"] = "YAHOO_SOURCE_SPECIFIC_V1"
        metrics["ohlc_warning_tickers"] = resolved_warning
        metrics["invalid_ohlc_warning_count"] = 0
        metrics["invalid_ohlc_blocking_count"] = int(
            metrics.get("invalid_ohlc_count") or 0
        )
        metrics["invalid_ohlc_warning_symbols"] = []
        metrics["invalid_ohlc_blocking_symbols"] = []
        metrics["invalid_ohlc_by_symbol"] = {}

        invalid_ohlc_total = int(metrics.get("invalid_ohlc_count") or 0)
        if invalid_ohlc_total > 0:
            current_date = metrics.get("max_date")
            if not current_date:
                validation_result["errors"].append(
                    "Yahoo OHLC policy cannot reconcile invalid rows without max_date."
                )
            else:
                quoted_date = _quote_identifier(date_col)
                quoted_symbol = _quote_identifier(symbol_col)
                open_col = _quote_identifier("Open")
                high_col = _quote_identifier("High")
                low_col = _quote_identifier("Low")
                close_col = _quote_identifier("Close")
                breakdown = returnSQL(
                    connection,
                    f"""
                    SELECT
                        CAST({quoted_symbol} AS VARCHAR) AS symbol,
                        COUNT(*) AS invalid_count
                    FROM {quoted_view}
                    WHERE TRY_CAST({quoted_date} AS DATE) = DATE '{current_date}'
                      AND (
                          TRY_CAST({high_col} AS DOUBLE) < TRY_CAST({low_col} AS DOUBLE)
                          OR TRY_CAST({high_col} AS DOUBLE) < TRY_CAST({open_col} AS DOUBLE)
                          OR TRY_CAST({high_col} AS DOUBLE) < TRY_CAST({close_col} AS DOUBLE)
                          OR TRY_CAST({low_col} AS DOUBLE) > TRY_CAST({open_col} AS DOUBLE)
                          OR TRY_CAST({low_col} AS DOUBLE) > TRY_CAST({close_col} AS DOUBLE)
                      )
                    GROUP BY CAST({quoted_symbol} AS VARCHAR)
                    ORDER BY symbol
                    """,
                )
                by_symbol = {
                    str(row.symbol): int(row.invalid_count)
                    for row in breakdown.itertuples(index=False)
                }
                reconciled_total = sum(by_symbol.values())
                metrics["invalid_ohlc_by_symbol"] = by_symbol

                warning_symbols = sorted(
                    symbol
                    for symbol, count in by_symbol.items()
                    if count > 0 and symbol in resolved_warning
                )
                blocking_symbols = sorted(
                    symbol
                    for symbol, count in by_symbol.items()
                    if count > 0 and symbol not in resolved_warning
                )
                warning_count = sum(by_symbol[symbol] for symbol in warning_symbols)
                blocking_count = sum(by_symbol[symbol] for symbol in blocking_symbols)

                metrics["invalid_ohlc_warning_count"] = warning_count
                metrics["invalid_ohlc_blocking_count"] = blocking_count
                metrics["invalid_ohlc_warning_symbols"] = warning_symbols
                metrics["invalid_ohlc_blocking_symbols"] = blocking_symbols

                # Replace only the generic OHLC error. Every other generic DQ error
                # remains untouched and therefore blocking.
                validation_result["errors"] = [
                    error
                    for error in validation_result["errors"]
                    if not str(error).startswith("invalid_ohlc_count=")
                ]

                if reconciled_total != invalid_ohlc_total:
                    validation_result["errors"].append(
                        "Yahoo OHLC policy reconciliation mismatch: "
                        f"generic={invalid_ohlc_total}, by_symbol={reconciled_total}."
                    )

                if warning_count > 0:
                    validation_result["warnings"].append(
                        "Yahoo source-specific OHLC envelope warning accepted without "
                        "mutating raw values: "
                        f"symbols={warning_symbols}, count={warning_count}, "
                        f"date={current_date}."
                    )

                if blocking_count > 0:
                    validation_result["errors"].append(
                        "Yahoo OHLC envelope violation remains blocking: "
                        f"symbols={blocking_symbols}, count={blocking_count}, "
                        f"date={current_date}."
                    )

        validation_result["status"] = (
            "FAIL"
            if validation_result["errors"]
            else "WARNING"
            if validation_result["warnings"]
            else "PASS"
        )

        resolved_validation_id = persist_data_quality_result(
            connection=connection,
            validation_result=validation_result,
            pipeline_name=pipeline_name,
            audit_table=audit_table,
            validation_id=validation_id,
            checked_at=checked_at,
        )
        validation_result["validation_id"] = resolved_validation_id

        if raise_on_fail and validation_result["status"] == "FAIL":
            error_summary = " | ".join(validation_result["errors"]) or "Unknown validation error"
            raise RuntimeError(
                f"Data quality validation failed for {table_name!r}: {error_summary}"
            )

        return validation_result
    finally:
        connection.execute(f"DROP VIEW IF EXISTS {quoted_view}")

def validate_and_persist_reference_quality(
    connection: Any,
    table_name: str,
    pipeline_name: str,
    *,
    key_cols: Sequence[str],
    required_cols: Sequence[str],
    date_col: str | None = None,
    expected_date: date | datetime | str | None = None,
    max_null_rate: float = DEFAULT_MAX_NULL_RATE,
    audit_table: str = DEFAULT_AUDIT_TABLE,
    validation_id: str | None = None,
    checked_at: datetime | None = None,
    raise_on_fail: bool = True,
) -> dict[str, Any]:
    """Validate a reference/master table that has no daily time-series contract.

    Checks table existence, row count, duplicate business keys and NULL rates for required fields,
    persists the compatible audit payload, then optionally raises after persistence.
    """
    if connection is None:
        raise ValueError("connection is required")
    if not key_cols or not required_cols:
        raise ValueError("key_cols and required_cols must not be empty")
    if not 0 <= float(max_null_rate) <= 1:
        raise ValueError("max_null_rate must be between 0 and 1")

    quoted_table = _quote_relation(table_name)
    relation_parts = [part.strip().strip('"') for part in table_name.split(".")]
    schema_filters = [
        f"lower(table_name) = lower({_sql_literal(relation_parts[-1])})"
    ]
    if len(relation_parts) >= 2:
        schema_filters.append(
            f"lower(table_schema) = lower({_sql_literal(relation_parts[-2])})"
        )
    if len(relation_parts) >= 3:
        schema_filters.append(
            f"lower(table_catalog) = lower({_sql_literal(relation_parts[-3])})"
        )
    schema_sql = f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE {' AND '.join(schema_filters)}
        ORDER BY ordinal_position
    """
    schema_frame = returnSQL(connection, schema_sql)
    if schema_frame is None or schema_frame.empty:
        raise RuntimeError(f"Reference table {table_name!r} does not exist or has no readable schema")

    schema_columns = {str(column).lower(): str(column) for column in schema_frame.iloc[:, 0].tolist()}
    requested_columns = list(key_cols) + list(required_cols)
    if date_col is not None:
        requested_columns.append(date_col)
    missing_columns = [column for column in requested_columns if column.lower() not in schema_columns]

    metrics: dict[str, Any] = {
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
        "validation_mode": "reference",
    }
    errors: list[str] = []
    warnings: list[str] = []

    if missing_columns:
        errors.append(f"Configured reference columns are missing: {sorted(set(missing_columns))}.")
    else:
        row_frame = returnSQL(connection, f"SELECT COUNT(*) AS row_count FROM {quoted_table}")
        if row_frame is None or row_frame.empty:
            raise RuntimeError(f"Unable to count rows in reference table {table_name!r}")
        row_count = int(row_frame["row_count"].iloc[0])
        metrics["row_count_current"] = row_count
        if row_count == 0:
            errors.append(f"Reference table {table_name!r} is empty.")

        actual_keys = [schema_columns[column.lower()] for column in key_cols]
        grouped_keys = ", ".join(_quote_identifier(column) for column in actual_keys)
        duplicate_frame = returnSQL(
            connection,
            f"""
            SELECT COALESCE(SUM(duplicate_rows), 0) AS duplicate_count
            FROM (
                SELECT COUNT(*) - 1 AS duplicate_rows
                FROM {quoted_table}
                GROUP BY {grouped_keys}
                HAVING COUNT(*) > 1
            ) duplicate_groups
            """,
        )
        if duplicate_frame is None or duplicate_frame.empty:
            raise RuntimeError(f"Unable to check duplicate keys in {table_name!r}")
        duplicate_count = int(duplicate_frame["duplicate_count"].iloc[0])
        metrics["duplicate_count"] = duplicate_count
        if duplicate_count > 0:
            errors.append(f"Found {duplicate_count} duplicate rows for reference key {list(key_cols)}.")

        for requested_column in required_cols:
            actual_column = schema_columns[requested_column.lower()]
            null_frame = returnSQL(
                connection,
                f"""
                SELECT COUNT(*) AS total_rows,
                       SUM(CASE WHEN {_quote_identifier(actual_column)} IS NULL THEN 1 ELSE 0 END) AS null_count
                FROM {quoted_table}
                """,
            )
            if null_frame is None or null_frame.empty:
                raise RuntimeError(f"Unable to check NULL rate for {actual_column!r}")
            total_rows = int(null_frame["total_rows"].iloc[0])
            null_count = int(null_frame["null_count"].iloc[0] or 0)
            null_rate = null_count / total_rows if total_rows else 0.0
            metrics["null_rate"][actual_column] = null_rate
            if null_rate > max_null_rate:
                errors.append(
                    f"{actual_column} NULL rate is {null_rate:.2%}, exceeding {max_null_rate:.2%}."
                )

        if date_col is not None:
            actual_date_col = schema_columns[date_col.lower()]
            if expected_date is None:
                expected_frame = returnSQL(
                    connection,
                    """
                    SELECT MAX(CAST(FullDate AS DATE)) AS expected_date
                    FROM "CherryMon"."main"."dimCalendar"
                    WHERE IsHoliday = 'N'
                      AND CAST(FullDate AS DATE) <= CURRENT_DATE
                    """,
                )
                resolved_expected = (
                    None
                    if expected_frame is None or expected_frame.empty
                    else expected_frame["expected_date"].iloc[0]
                )
            else:
                resolved_expected = expected_date

            if resolved_expected is None or pd.isna(resolved_expected):
                errors.append("Unable to resolve expected trading date for snapshot freshness.")
            else:
                expected_day = pd.Timestamp(resolved_expected).date()
                freshness_frame = returnSQL(
                    connection,
                    f"""
                    SELECT
                        MAX(TRY_CAST({_quote_identifier(actual_date_col)} AS DATE)) AS max_date,
                        COUNT(*) FILTER (
                            WHERE TRY_CAST({_quote_identifier(actual_date_col)} AS DATE) = DATE '{expected_day.isoformat()}'
                        ) AS latest_date_rows
                    FROM {quoted_table}
                    """,
                )
                max_date_value = (
                    None
                    if freshness_frame is None or freshness_frame.empty
                    else freshness_frame["max_date"].iloc[0]
                )
                metrics["expected_date"] = expected_day.isoformat()
                if max_date_value is None or pd.isna(max_date_value):
                    errors.append(
                        f"Snapshot table {table_name!r} has no valid {actual_date_col} values."
                    )
                else:
                    max_day = pd.Timestamp(max_date_value).date()
                    metrics["max_date"] = max_day.isoformat()
                    metrics["date_lag"] = (expected_day - max_day).days
                    latest_rows = int(freshness_frame["latest_date_rows"].iloc[0] or 0)
                    metrics["latest_date_row_count"] = latest_rows
                    metrics["latest_date_coverage"] = (
                        latest_rows / row_count if row_count else 0.0
                    )
                    metrics["validation_mode"] = "snapshot"
                    if max_day < expected_day:
                        errors.append(
                            f"Snapshot is stale: max_date={max_day.isoformat()}, "
                            f"expected_date={expected_day.isoformat()}."
                        )
                    elif max_day > expected_day:
                        errors.append(
                            f"Snapshot date is ahead of expected trading date: "
                            f"max_date={max_day.isoformat()}, expected_date={expected_day.isoformat()}."
                        )

    status = "FAIL" if errors else "WARNING" if warnings else "PASS"
    validation_result = {
        "status": status,
        "table": table_name,
        "metrics": metrics,
        "errors": errors,
        "warnings": warnings,
    }

    resolved_validation_id = persist_data_quality_result(
        connection=connection,
        validation_result=validation_result,
        pipeline_name=pipeline_name,
        audit_table=audit_table,
        validation_id=validation_id,
        checked_at=checked_at,
    )
    validation_result["validation_id"] = resolved_validation_id

    print(
        "[DataValidation][REFERENCE] "
        f"table={table_name} | status={status} | rows={metrics['row_count_current']} | "
        f"duplicates={metrics['duplicate_count']} | max_date={metrics['max_date']}"
    )

    if raise_on_fail and status == "FAIL":
        raise RuntimeError(
            f"Reference data quality validation failed for {table_name!r}: {' | '.join(errors)}"
        )
    return validation_result
