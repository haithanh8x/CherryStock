from datetime import datetime
import json

import duckdb
import pytest

from src.Ults.DataValidation import persist_data_quality_result


def _create_audit_table(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        CREATE TABLE data_quality_audit (
            validation_id VARCHAR,
            checked_at TIMESTAMP,
            pipeline_name VARCHAR,
            table_name VARCHAR,
            expected_date DATE,
            max_date DATE,
            status VARCHAR,
            row_count_current BIGINT,
            row_count_previous BIGINT,
            row_count_change_pct DOUBLE,
            symbol_count_current BIGINT,
            symbol_count_previous BIGINT,
            symbol_count_change_pct DOUBLE,
            missing_symbol_count BIGINT,
            new_symbol_count BIGINT,
            duplicate_count BIGINT,
            row_count_zscore DOUBLE,
            symbol_count_zscore DOUBLE,
            metrics JSON,
            errors JSON,
            warnings JSON
        )
        """
    )


def _validation_result(status: str = "PASS") -> dict:
    return {
        "status": status,
        "table": "raw_stock_eod",
        "metrics": {
            "expected_date": "2026-08-21",
            "max_date": "2026-08-21",
            "row_count_current": 1600,
            "row_count_previous": 1598,
            "row_count_change_pct": 2 / 1598,
            "symbol_count_current": 1580,
            "symbol_count_previous": 1579,
            "symbol_count_change_pct": 1 / 1579,
            "missing_symbol_count": 1,
            "missing_symbols": ["AAA"],
            "new_symbol_count": 2,
            "new_symbols": ["BBB", "CCC"],
            "duplicate_count": 0,
            "row_count_zscore": 0.4,
            "symbol_count_zscore": 0.2,
            "null_rate": {"Ticker": 0.0},
        },
        "errors": [],
        "warnings": ["sample warning"] if status == "WARNING" else [],
    }


def test_persist_data_quality_result_writes_audit_row() -> None:
    connection = duckdb.connect(":memory:")
    _create_audit_table(connection)

    validation_id = persist_data_quality_result(
        connection=connection,
        validation_result=_validation_result(),
        pipeline_name="EOD",
        audit_table="data_quality_audit",
        validation_id="validation-001",
        checked_at=datetime(2026, 8, 21, 18, 30),
    )

    row = connection.execute(
        """
        SELECT validation_id, pipeline_name, table_name, status,
               row_count_current, symbol_count_current, metrics, errors, warnings
        FROM data_quality_audit
        """
    ).fetchone()

    assert validation_id == "validation-001"
    assert row[:6] == (
        "validation-001",
        "EOD",
        "raw_stock_eod",
        "PASS",
        1600,
        1580,
    )
    assert json.loads(row[6])["missing_symbols"] == ["AAA"]
    assert json.loads(row[7]) == []
    assert json.loads(row[8]) == []


def test_persist_data_quality_result_is_idempotent_for_same_validation_id() -> None:
    connection = duckdb.connect(":memory:")
    _create_audit_table(connection)
    validation_result = _validation_result("WARNING")

    first_id = persist_data_quality_result(
        connection=connection,
        validation_result=validation_result,
        pipeline_name="EOD",
        audit_table="data_quality_audit",
        validation_id="same-event",
    )
    second_id = persist_data_quality_result(
        connection=connection,
        validation_result=validation_result,
        pipeline_name="EOD",
        audit_table="data_quality_audit",
        validation_id="same-event",
    )

    assert first_id == second_id == "same-event"
    assert connection.execute("SELECT COUNT(*) FROM data_quality_audit").fetchone()[0] == 1


def test_persist_data_quality_result_keeps_working_with_only_core_audit_columns() -> None:
    connection = duckdb.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE minimal_audit (
            validation_id VARCHAR,
            checked_at TIMESTAMP,
            pipeline_name VARCHAR,
            table_name VARCHAR,
            status VARCHAR,
            metrics JSON,
            errors JSON,
            warnings JSON
        )
        """
    )

    persist_data_quality_result(
        connection=connection,
        validation_result=_validation_result(),
        pipeline_name="FA",
        audit_table="minimal_audit",
        validation_id="minimal-001",
    )

    assert connection.execute("SELECT COUNT(*) FROM minimal_audit").fetchone()[0] == 1


def test_persist_data_quality_result_rejects_invalid_payload() -> None:
    connection = duckdb.connect(":memory:")
    _create_audit_table(connection)

    with pytest.raises(ValueError, match="missing required keys"):
        persist_data_quality_result(
            connection=connection,
            validation_result={"status": "PASS"},
            pipeline_name="EOD",
            audit_table="data_quality_audit",
        )


def test_persist_data_quality_result_fails_for_invalid_audit_schema() -> None:
    connection = duckdb.connect(":memory:")
    connection.execute("CREATE TABLE broken_audit (validation_id VARCHAR, status VARCHAR)")

    with pytest.raises(RuntimeError, match="missing required columns"):
        persist_data_quality_result(
            connection=connection,
            validation_result=_validation_result(),
            pipeline_name="EOD",
            audit_table="broken_audit",
        )
