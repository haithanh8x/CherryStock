from datetime import date

import duckdb
import pytest

from src.Ults.DataQualityOrchestration import validate_and_persist_data_quality


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
            symbol_count_current BIGINT,
            duplicate_count BIGINT,
            metrics JSON,
            errors JSON,
            warnings JSON
        )
        """
    )


def _create_index_table(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        CREATE TABLE cal_Indexes (
            INDEX_NAME VARCHAR,
            Date DATE,
            Close DOUBLE
        )
        """
    )
    connection.executemany(
        "INSERT INTO cal_Indexes VALUES (?, ?, ?)",
        [
            ("VNINDEX_NOT_VIN", date(2026, 8, 20), 1000.0),
            ("VNINDEX_NOT_VIN", date(2026, 8, 21), 1001.0),
            ("OTHER_INDEX", date(2026, 8, 21), -1.0),
        ],
    )


def test_helper_filters_shared_table_and_persists_before_return() -> None:
    connection = duckdb.connect(":memory:")
    _create_audit_table(connection)
    _create_index_table(connection)

    result = validate_and_persist_data_quality(
        connection=connection,
        table_name="cal_Indexes",
        pipeline_name="Composite Index",
        date_col="Date",
        symbol_col="INDEX_NAME",
        key_cols=["INDEX_NAME", "Date"],
        required_cols=["INDEX_NAME", "Date", "Close"],
        expected_date=date(2026, 8, 21),
        history_window=2,
        filters={"INDEX_NAME": "VNINDEX_NOT_VIN"},
        audit_table="data_quality_audit",
        raise_on_fail=False,
    )

    assert result["table"] == "cal_Indexes"
    assert result["metrics"]["filters"] == {"INDEX_NAME": "VNINDEX_NOT_VIN"}
    assert result["metrics"]["row_count_current"] == 1
    assert result["metrics"]["invalid_numeric_count"] == 0
    assert connection.execute("SELECT COUNT(*) FROM data_quality_audit").fetchone()[0] == 1


def test_helper_persists_fail_before_raising() -> None:
    connection = duckdb.connect(":memory:")
    _create_audit_table(connection)
    _create_index_table(connection)

    with pytest.raises(RuntimeError, match="Data quality validation failed"):
        validate_and_persist_data_quality(
            connection=connection,
            table_name="cal_Indexes",
            pipeline_name="Composite Index",
            date_col="Date",
            symbol_col="INDEX_NAME",
            key_cols=["INDEX_NAME", "Date"],
            required_cols=["INDEX_NAME", "Date", "Close"],
            expected_date=date(2026, 8, 22),
            history_window=2,
            filters={"INDEX_NAME": "VNINDEX_NOT_VIN"},
            audit_table="data_quality_audit",
            raise_on_fail=True,
        )

    status = connection.execute("SELECT status FROM data_quality_audit").fetchone()[0]
    assert status == "FAIL"


def test_helper_filter_sequence_limits_scope() -> None:
    connection = duckdb.connect(":memory:")
    _create_audit_table(connection)
    _create_index_table(connection)

    result = validate_and_persist_data_quality(
        connection=connection,
        table_name="cal_Indexes",
        pipeline_name="Composite Index",
        date_col="Date",
        symbol_col="INDEX_NAME",
        key_cols=["INDEX_NAME", "Date"],
        required_cols=["INDEX_NAME", "Date", "Close"],
        expected_date=date(2026, 8, 21),
        history_window=2,
        filters={"INDEX_NAME": ["VNINDEX_NOT_VIN"]},
        audit_table="data_quality_audit",
        raise_on_fail=False,
    )

    assert result["metrics"]["symbol_count_current"] == 1


def test_helper_rejects_empty_filters() -> None:
    connection = duckdb.connect(":memory:")

    with pytest.raises(ValueError, match="filters must not be empty"):
        validate_and_persist_data_quality(
            connection=connection,
            table_name="cal_Indexes",
            pipeline_name="Composite Index",
            filters={},
        )
