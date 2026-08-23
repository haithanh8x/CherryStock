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
    expected_date: date | datetime | str | None = None,
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
    """Validate a dataset scope, persist its audit result, then apply the failure policy.

    ``filters`` supports safe equality/IN/IS NULL predicates for validating one logical dataset
    inside a shared physical table, for example ``{"INDEX_NAME": "VNINDEX_NOT_VIN"}``.
    The helper creates a short-lived temporary view only when filters are supplied, validates that
    view with the existing read-only validator, rewrites the result back to the source table name,
    persists the audit event, and always removes the temporary view before returning or raising.

    Persistence happens before ``raise_on_fail`` is evaluated so failed validations are still
    recorded in ``data_quality_audit``.
    """
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
            expected_date=expected_date,
            max_row_change_pct=max_row_change_pct,
            max_symbol_change_pct=max_symbol_change_pct,
            max_null_rate=max_null_rate,
            history_window=history_window,
        )

        validation_result["table"] = table_name
        validation_result["metrics"]["filters"] = (
            dict(filters) if filters is not None else None
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
        if temporary_view is not None:
            connection.execute(f"DROP VIEW IF EXISTS {_quote_identifier(temporary_view)}")
