"""Read-only DuckDB service used by CherryStock MCP tools."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator

_SRC_ROOT = Path(__file__).resolve().parents[1]
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from Ults.DuckLib import DuckDBManager


MAIN_SCHEMA = "main"
INDICATOR_VALUES_VIEW = "vw_Ticker_indicators"
INDICATOR_CONFIG_VIEW = "vw_Indicator_config"

_TIMEFRAMES = {
    "daily": "Daily",
    "weekly": "Weekly",
    "monthly": "Monthly",
}

_VALUE_VIEW_REQUIRED_COLUMNS = (
    "Ticker",
    "Date",
    "ConfigId",
    "ComponentCode",
    "Value",
)

_CONFIG_VIEW_REQUIRED_COLUMNS = (
    "ConfigId",
    "ConfigCode",
    "IndicatorCode",
    "Timeframe",
    "Parameters",
    "ConfigIsEnabled",
    "IndicatorIsActive",
    "ComponentCode",
    "ComponentIsActive",
)


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


def _rows_as_dicts(
    cursor: Any,
    rows: list[tuple[Any, ...]] | None = None,
) -> list[dict[str, Any]]:
    description = cursor.description or []
    columns = [item[0] for item in description]
    source_rows = rows if rows is not None else cursor.fetchall()
    return [
        {
            column: _json_safe(value)
            for column, value in zip(columns, row, strict=True)
        }
        for row in source_rows
    ]


def _normalize_timeframe(timeframe: str) -> str:
    normalized = (timeframe or "").strip().lower()
    canonical = _TIMEFRAMES.get(normalized)
    if canonical is None:
        raise ValueError("timeframe must be one of: Daily, Weekly, Monthly.")
    return canonical


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

    def _require_columns(
        self,
        connection: Any,
        relation_name: str,
        required_columns: tuple[str, ...],
    ) -> tuple[str, dict[str, str]]:
        actual_name = self._resolve_relation(connection, relation_name)
        available = self._columns(connection, actual_name)
        by_lower = {column.lower(): column for column in available}

        missing = [
            column
            for column in required_columns
            if column.lower() not in by_lower
        ]
        if missing:
            raise ValueError(
                f"main.{actual_name} is missing required columns: {missing}. "
                f"Available={available}"
            )

        resolved = {
            column: by_lower[column.lower()]
            for column in required_columns
        }
        return actual_name, resolved

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

    def _indicator_query_context(
        self,
        connection: Any,
    ) -> tuple[str, str, dict[str, str], dict[str, str]]:
        value_view, value_columns = self._require_columns(
            connection,
            INDICATOR_VALUES_VIEW,
            _VALUE_VIEW_REQUIRED_COLUMNS,
        )
        config_view, config_columns = self._require_columns(
            connection,
            INDICATOR_CONFIG_VIEW,
            _CONFIG_VIEW_REQUIRED_COLUMNS,
        )
        return value_view, config_view, value_columns, config_columns

    def _indicator_select_list(
        self,
        value_columns: dict[str, str],
        config_columns: dict[str, str],
    ) -> str:
        return ", ".join(
            (
                f'val.{_quote_identifier(value_columns["Ticker"])} AS "Ticker"',
                f'val.{_quote_identifier(value_columns["Date"])} AS "Date"',
                f'cfg.{_quote_identifier(config_columns["ConfigId"])} AS "ConfigId"',
                f'cfg.{_quote_identifier(config_columns["ConfigCode"])} AS "ConfigCode"',
                f'cfg.{_quote_identifier(config_columns["IndicatorCode"])} AS "IndicatorCode"',
                f'cfg.{_quote_identifier(config_columns["Timeframe"])} AS "Timeframe"',
                f'cfg.{_quote_identifier(config_columns["ComponentCode"])} AS "ComponentCode"',
                f'val.{_quote_identifier(value_columns["Value"])} AS "Value"',
                f'cfg.{_quote_identifier(config_columns["Parameters"])} AS "Parameters"',
            )
        )

    def get_indicator_history(
        self,
        ticker: str,
        timeframe: str = "Daily",
        limit: int = 30,
    ) -> dict[str, Any]:
        """Return bounded long-form indicator history for one ticker/timeframe."""

        requested_ticker = (ticker or "").strip().upper()
        if not requested_ticker:
            raise ValueError("ticker must be provided.")
        canonical_timeframe = _normalize_timeframe(timeframe)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 200
        ):
            raise ValueError("limit must be an integer between 1 and 200.")

        with self.connection() as connection:
            (
                value_view,
                config_view,
                value_columns,
                config_columns,
            ) = self._indicator_query_context(connection)

            select_list = self._indicator_select_list(
                value_columns,
                config_columns,
            )
            cursor = connection.execute(
                f"""
                SELECT {select_list}
                FROM {_quote_identifier(MAIN_SCHEMA)}.{_quote_identifier(value_view)} val
                INNER JOIN {_quote_identifier(MAIN_SCHEMA)}.{_quote_identifier(config_view)} cfg
                    ON cfg.{_quote_identifier(config_columns["ConfigId"])}
                       = val.{_quote_identifier(value_columns["ConfigId"])}
                   AND cfg.{_quote_identifier(config_columns["ComponentCode"])}
                       = val.{_quote_identifier(value_columns["ComponentCode"])}
                WHERE val.{_quote_identifier(value_columns["Ticker"])} = ?
                  AND cfg.{_quote_identifier(config_columns["Timeframe"])} = ?
                  AND cfg.{_quote_identifier(config_columns["ConfigIsEnabled"])} = TRUE
                  AND cfg.{_quote_identifier(config_columns["IndicatorIsActive"])} = TRUE
                  AND COALESCE(
                        cfg.{_quote_identifier(config_columns["ComponentIsActive"])},
                        TRUE
                      ) = TRUE
                  AND val.{_quote_identifier(value_columns["Value"])} IS NOT NULL
                ORDER BY
                    val.{_quote_identifier(value_columns["Date"])} DESC,
                    cfg.{_quote_identifier(config_columns["IndicatorCode"])},
                    cfg.{_quote_identifier(config_columns["ConfigCode"])},
                    cfg.{_quote_identifier(config_columns["ComponentCode"])}
                LIMIT ?
                """,
                [requested_ticker, canonical_timeframe, limit],
            )
            rows = _rows_as_dicts(cursor)

        return {
            "ticker": requested_ticker,
            "timeframe": canonical_timeframe,
            "row_count": len(rows),
            "rows": rows,
        }

    def get_ticker_indicators(
        self,
        ticker: str,
        timeframe: str = "Daily",
    ) -> dict[str, Any]:
        """Return the latest value per active config/component for a ticker."""

        requested_ticker = (ticker or "").strip().upper()
        if not requested_ticker:
            raise ValueError("ticker must be provided.")
        canonical_timeframe = _normalize_timeframe(timeframe)

        with self.connection() as connection:
            (
                value_view,
                config_view,
                value_columns,
                config_columns,
            ) = self._indicator_query_context(connection)

            select_list = self._indicator_select_list(
                value_columns,
                config_columns,
            )
            cursor = connection.execute(
                f"""
                WITH ranked AS (
                    SELECT
                        {select_list},
                        ROW_NUMBER() OVER (
                            PARTITION BY
                                val.{_quote_identifier(value_columns["ConfigId"])},
                                val.{_quote_identifier(value_columns["ComponentCode"])}
                            ORDER BY
                                val.{_quote_identifier(value_columns["Date"])} DESC
                        ) AS "_mcp_rank"
                    FROM {_quote_identifier(MAIN_SCHEMA)}.{_quote_identifier(value_view)} val
                    INNER JOIN {_quote_identifier(MAIN_SCHEMA)}.{_quote_identifier(config_view)} cfg
                        ON cfg.{_quote_identifier(config_columns["ConfigId"])}
                           = val.{_quote_identifier(value_columns["ConfigId"])}
                       AND cfg.{_quote_identifier(config_columns["ComponentCode"])}
                           = val.{_quote_identifier(value_columns["ComponentCode"])}
                    WHERE val.{_quote_identifier(value_columns["Ticker"])} = ?
                      AND cfg.{_quote_identifier(config_columns["Timeframe"])} = ?
                      AND cfg.{_quote_identifier(config_columns["ConfigIsEnabled"])} = TRUE
                      AND cfg.{_quote_identifier(config_columns["IndicatorIsActive"])} = TRUE
                      AND COALESCE(
                            cfg.{_quote_identifier(config_columns["ComponentIsActive"])},
                            TRUE
                          ) = TRUE
                      AND val.{_quote_identifier(value_columns["Value"])} IS NOT NULL
                )
                SELECT
                    "Ticker",
                    "Date",
                    "ConfigId",
                    "ConfigCode",
                    "IndicatorCode",
                    "Timeframe",
                    "ComponentCode",
                    "Value",
                    "Parameters"
                FROM ranked
                WHERE "_mcp_rank" = 1
                ORDER BY
                    "IndicatorCode",
                    "ConfigCode",
                    "ComponentCode"
                """,
                [requested_ticker, canonical_timeframe],
            )
            rows = _rows_as_dicts(cursor)

        as_of_date = max(
            (row["Date"] for row in rows if row.get("Date") is not None),
            default=None,
        )
        return {
            "ticker": requested_ticker,
            "timeframe": canonical_timeframe,
            "as_of_date": as_of_date,
            "row_count": len(rows),
            "rows": rows,
        }

    def get_indicator_config(self, indicator: str) -> dict[str, Any]:
        """Return configuration rows from the indicator configuration SSOT."""

        indicator_code = (indicator or "").strip().upper()
        if not indicator_code:
            raise ValueError("indicator must be provided.")

        with self.connection() as connection:
            actual_view, columns = self._require_columns(
                connection,
                INDICATOR_CONFIG_VIEW,
                _CONFIG_VIEW_REQUIRED_COLUMNS,
            )
            select_list = ", ".join(
                _quote_identifier(columns[column])
                for column in _CONFIG_VIEW_REQUIRED_COLUMNS
            )

            cursor = connection.execute(
                f"""
                SELECT {select_list}
                FROM {_quote_identifier(MAIN_SCHEMA)}.{_quote_identifier(actual_view)}
                WHERE upper({_quote_identifier(columns["IndicatorCode"])}) = ?
                ORDER BY
                    {_quote_identifier(columns["Timeframe"])},
                    {_quote_identifier(columns["ConfigCode"])},
                    {_quote_identifier(columns["ComponentCode"])}
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
        """Return a read-only row-count statistic for a relation."""

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

    def execute_readonly_query(
        self,
        sql: str,
        max_rows: int,
    ) -> dict[str, Any]:
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
