"""Read-only DuckDB service used by CherryStock MCP tools."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import sys
from typing import Any, Iterator

_SRC_ROOT = Path(__file__).resolve().parents[1]
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from Ults.DuckLib import DuckDBManager


MAIN_SCHEMA = "main"
INDICATOR_VALUES_VIEW = "vw_Ticker_indicators"
INDICATOR_CONFIG_VIEW = "vw_Indicator_config"

_TIMEFRAME_SUFFIX = {
    "daily": "_D",
    "weekly": "_W",
    "monthly": "_M",
}


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _json_safe(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.hex()
    return value


def _rows_as_dicts(cursor: Any, rows: list[tuple[Any, ...]] | None = None) -> list[dict[str, Any]]:
    description = cursor.description or []
    columns = [item[0] for item in description]
    source_rows = rows if rows is not None else cursor.fetchall()
    return [
        {column: _json_safe(value) for column, value in zip(columns, row, strict=True)}
        for row in source_rows
    ]


def _resolve_column(columns: list[str], expected: str) -> str | None:
    expected_lower = expected.lower()
    return next((column for column in columns if column.lower() == expected_lower), None)


def _normalize_timeframe(timeframe: str) -> tuple[str, str]:
    normalized = (timeframe or "").strip().lower()
    suffix = _TIMEFRAME_SUFFIX.get(normalized)
    if suffix is None:
        raise ValueError(
            "timeframe must be one of: Daily, Weekly, Monthly."
        )
    return normalized.capitalize(), suffix


class DuckDBReadService:
    """Small read-side service built on CherryStock's centralized DB manager."""

    @contextmanager
    def connection(self) -> Iterator[Any]:
        """Open a short-lived read-only connection using project DB policy."""

        with DuckDBManager(read_only=True) as connection:
            yield connection

    def health_check(self) -> dict[str, Any]:
        """Verify that the configured CherryStock database is readable."""

        with self.connection() as connection:
            cursor = connection.execute(
                """
                SELECT
                    current_database() AS database_name,
                    current_schema() AS schema_name
                """
            )
            row = cursor.fetchone()

        return {
            "status": "ok",
            "database": _json_safe(row[0]) if row else None,
            "schema": _json_safe(row[1]) if row else None,
            "access": "read-only",
        }

    def list_relations(self) -> list[dict[str, Any]]:
        """List tables and views in the public CherryStock schema."""

        with self.connection() as connection:
            cursor = connection.execute(
                """
                SELECT
                    table_schema,
                    table_name,
                    table_type
                FROM information_schema.tables
                WHERE table_schema = ?
                ORDER BY table_name
                """,
                [MAIN_SCHEMA],
            )
            return _rows_as_dicts(cursor)

    def _resolve_relation(self, connection: Any, relation_name: str) -> str:
        requested = (relation_name or "").strip()
        if not requested:
            raise ValueError("relation_name must be provided.")

        row = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = ?
              AND lower(table_name) = lower(?)
            LIMIT 1
            """,
            [MAIN_SCHEMA, requested],
        ).fetchone()

        if row is None:
            raise ValueError(
                f"CherryStock relation main.{requested} was not found."
            )
        return str(row[0])

    def _columns(self, connection: Any, relation_name: str) -> list[str]:
        rows = connection.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = ?
              AND table_name = ?
            ORDER BY ordinal_position
            """,
            [MAIN_SCHEMA, relation_name],
        ).fetchall()
        return [str(row[0]) for row in rows]

    def describe_relation(self, relation_name: str) -> list[dict[str, Any]]:
        """Return column metadata for one table/view in main schema."""

        with self.connection() as connection:
            actual_name = self._resolve_relation(connection, relation_name)
            cursor = connection.execute(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    ordinal_position
                FROM information_schema.columns
                WHERE table_schema = ?
                  AND table_name = ?
                ORDER BY ordinal_position
                """,
                [MAIN_SCHEMA, actual_name],
            )
            return _rows_as_dicts(cursor)

    def _indicator_columns(
        self,
        connection: Any,
        *,
        timeframe: str,
    ) -> tuple[str, str, str, list[str]]:
        actual_view = self._resolve_relation(connection, INDICATOR_VALUES_VIEW)
        columns = self._columns(connection, actual_view)
        ticker_column = _resolve_column(columns, "Ticker")
        date_column = _resolve_column(columns, "Date")
        normalized_timeframe, suffix = _normalize_timeframe(timeframe)

        if ticker_column is None or date_column is None:
            raise ValueError(
                f"main.{actual_view} must expose Ticker and Date columns."
            )

        value_columns = [
            column
            for column in columns
            if column.upper().endswith(suffix)
            and column not in {ticker_column, date_column}
        ]
        if not value_columns:
            raise ValueError(
                f"main.{actual_view} has no {normalized_timeframe} indicator columns "
                f"using the {suffix} naming convention."
            )

        return actual_view, ticker_column, date_column, value_columns

    def get_indicator_history(
        self,
        ticker: str,
        timeframe: str = "Daily",
        limit: int = 30,
    ) -> dict[str, Any]:
        """Return bounded indicator history from the calculated-value SSOT."""

        requested_ticker = (ticker or "").strip().upper()
        if not requested_ticker:
            raise ValueError("ticker must be provided.")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise ValueError("limit must be an integer between 1 and 200.")

        with self.connection() as connection:
            (
                actual_view,
                ticker_column,
                date_column,
                value_columns,
            ) = self._indicator_columns(connection, timeframe=timeframe)
            normalized_timeframe, _ = _normalize_timeframe(timeframe)
            selected_columns = [ticker_column, date_column, *value_columns]
            select_list = ", ".join(_quote_identifier(column) for column in selected_columns)

            cursor = connection.execute(
                f"""
                SELECT {select_list}
                FROM {_quote_identifier(MAIN_SCHEMA)}.{_quote_identifier(actual_view)}
                WHERE {_quote_identifier(ticker_column)} = ?
                ORDER BY {_quote_identifier(date_column)} DESC
                LIMIT ?
                """,
                [requested_ticker, limit],
            )
            rows = _rows_as_dicts(cursor)

        return {
            "ticker": requested_ticker,
            "timeframe": normalized_timeframe,
            "row_count": len(rows),
            "rows": rows,
        }

    def get_ticker_indicators(
        self,
        ticker: str,
        timeframe: str = "Daily",
    ) -> dict[str, Any]:
        """Return the latest technical indicators for one ticker/timeframe."""

        result = self.get_indicator_history(
            ticker=ticker,
            timeframe=timeframe,
            limit=1,
        )
        result["latest"] = result["rows"][0] if result["rows"] else None
        return result

    def get_indicator_config(self, indicator: str) -> dict[str, Any]:
        """Return configuration rows from the indicator configuration SSOT."""

        indicator_code = (indicator or "").strip().upper()
        if not indicator_code:
            raise ValueError("indicator must be provided.")

        with self.connection() as connection:
            actual_view = self._resolve_relation(connection, INDICATOR_CONFIG_VIEW)
            columns = self._columns(connection, actual_view)
            indicator_column = _resolve_column(columns, "IndicatorCode")
            if indicator_column is None:
                raise ValueError(
                    f"main.{actual_view} must expose IndicatorCode."
                )

            select_list = ", ".join(_quote_identifier(column) for column in columns)
            order_columns = [
                column
                for expected in ("Timeframe", "ConfigCode", "ComponentCode")
                if (column := _resolve_column(columns, expected)) is not None
            ]
            order_clause = ""
            if order_columns:
                order_clause = " ORDER BY " + ", ".join(
                    _quote_identifier(column) for column in order_columns
                )

            cursor = connection.execute(
                f"""
                SELECT {select_list}
                FROM {_quote_identifier(MAIN_SCHEMA)}.{_quote_identifier(actual_view)}
                WHERE upper({_quote_identifier(indicator_column)}) = ?
                {order_clause}
                """,
                [indicator_code],
            )
            rows = _rows_as_dicts(cursor)

        return {
            "indicator": indicator_code,
            "row_count": len(rows),
            "rows": rows,
        }

    def table_stats(self, relation_name: str) -> dict[str, Any]:
        """Return a bounded, read-only row-count statistic for a relation."""

        with self.connection() as connection:
            actual_name = self._resolve_relation(connection, relation_name)
            row = connection.execute(
                f"""
                SELECT count(*) AS row_count
                FROM {_quote_identifier(MAIN_SCHEMA)}.{_quote_identifier(actual_name)}
                """
            ).fetchone()

        return {
            "schema": MAIN_SCHEMA,
            "relation": actual_name,
            "row_count": int(row[0]) if row else 0,
        }

    def execute_readonly_query(self, sql: str, max_rows: int) -> dict[str, Any]:
        """Execute already-validated SQL and return at most max_rows records."""

        with self.connection() as connection:
            cursor = connection.execute(sql)
            if cursor.description is None:
                raise ValueError("The SQL statement did not return a result set.")

            fetched = cursor.fetchmany(max_rows + 1)
            truncated = len(fetched) > max_rows
            visible_rows = fetched[:max_rows]
            rows = _rows_as_dicts(cursor, visible_rows)
            columns = [item[0] for item in cursor.description]

        return {
            "columns": columns,
            "row_count": len(rows),
            "truncated": truncated,
            "rows": rows,
        }
