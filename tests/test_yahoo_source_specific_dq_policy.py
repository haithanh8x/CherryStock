from __future__ import annotations

from datetime import date

import duckdb
import pytest

from src.Ults.DataQualityOrchestration import (
    validate_and_persist_yahoo_eod_quality,
)


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


def _create_yahoo_table(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        CREATE TABLE raw_other_eod (
            Ticker VARCHAR,
            Date DATE,
            Open DOUBLE,
            High DOUBLE,
            Low DOUBLE,
            Close DOUBLE
        )
        """
    )


def _scope() -> list[str]:
    return ["DX-Y.NYB", "BTC-USD", "VND=X", "GC=F"]


def test_vndx_ohlc_anomaly_becomes_warning_and_preserves_raw_values() -> None:
    connection = duckdb.connect(":memory:")
    try:
        _create_audit_table(connection)
        _create_yahoo_table(connection)
        connection.executemany(
            "INSERT INTO raw_other_eod VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("DX-Y.NYB", date(2026, 9, 22), 100.0, 101.0, 99.0, 100.0),
                ("BTC-USD", date(2026, 9, 22), 60000.0, 61000.0, 59000.0, 60500.0),
                ("VND=X", date(2026, 9, 22), 25979.0, 25999.0, 25970.0, 26010.0),
                ("GC=F", date(2026, 9, 22), 3600.0, 3610.0, 3590.0, 3605.0),
            ],
        )

        result = validate_and_persist_yahoo_eod_quality(
            connection=connection,
            table_name="raw_other_eod",
            pipeline_name="Yahoo Finance EOD",
            scope_tickers=_scope(),
            expected_date=date(2026, 9, 22),
            audit_table="data_quality_audit",
            raise_on_fail=True,
        )

        assert result["status"] == "WARNING"
        assert result["metrics"]["invalid_ohlc_count"] == 1
        assert result["metrics"]["invalid_ohlc_warning_count"] == 1
        assert result["metrics"]["invalid_ohlc_blocking_count"] == 0
        assert result["metrics"]["invalid_ohlc_warning_symbols"] == ["VND=X"]
        assert result["metrics"]["invalid_ohlc_blocking_symbols"] == []
        assert not result["errors"]
        assert any("source-specific OHLC envelope warning" in item for item in result["warnings"])

        stored = connection.execute(
            """
            SELECT Open, High, Low, Close
            FROM raw_other_eod
            WHERE Ticker = 'VND=X' AND Date = DATE '2026-09-22'
            """
        ).fetchone()
        assert stored == (25979.0, 25999.0, 25970.0, 26010.0)

        audit = connection.execute(
            "SELECT status, metrics, errors, warnings FROM data_quality_audit"
        ).fetchone()
        assert audit[0] == "WARNING"
        assert '"invalid_ohlc_warning_count": 1' in audit[1]
        assert audit[2] == "[]"
        assert "VND=X" in audit[3]
    finally:
        connection.close()


def test_non_vndx_ohlc_anomaly_remains_blocking() -> None:
    connection = duckdb.connect(":memory:")
    try:
        _create_audit_table(connection)
        _create_yahoo_table(connection)
        connection.executemany(
            "INSERT INTO raw_other_eod VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("VND=X", date(2026, 9, 22), 25979.0, 25999.0, 25970.0, 26010.0),
                ("GC=F", date(2026, 9, 22), 3600.0, 3601.0, 3590.0, 3610.0),
            ],
        )

        with pytest.raises(RuntimeError, match="remains blocking"):
            validate_and_persist_yahoo_eod_quality(
                connection=connection,
                table_name="raw_other_eod",
                pipeline_name="Yahoo Finance EOD",
                scope_tickers=_scope(),
                expected_date=date(2026, 9, 22),
                audit_table="data_quality_audit",
                raise_on_fail=True,
            )

        audit = connection.execute(
            "SELECT status, metrics, errors, warnings FROM data_quality_audit"
        ).fetchone()
        assert audit[0] == "FAIL"
        assert '"invalid_ohlc_warning_count": 1' in audit[1]
        assert '"invalid_ohlc_blocking_count": 1' in audit[1]
        assert "GC=F" in audit[2]
        assert "VND=X" in audit[3]
    finally:
        connection.close()


def test_vndx_duplicate_still_blocks_even_when_ohlc_is_warning_only() -> None:
    connection = duckdb.connect(":memory:")
    try:
        _create_audit_table(connection)
        _create_yahoo_table(connection)
        connection.executemany(
            "INSERT INTO raw_other_eod VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("VND=X", date(2026, 9, 22), 25979.0, 25999.0, 25970.0, 26010.0),
                ("VND=X", date(2026, 9, 22), 25979.0, 25999.0, 25970.0, 26010.0),
                ("BTC-USD", date(2026, 9, 22), 60000.0, 61000.0, 59000.0, 60500.0),
            ],
        )

        with pytest.raises(RuntimeError, match="duplicate"):
            validate_and_persist_yahoo_eod_quality(
                connection=connection,
                table_name="raw_other_eod",
                pipeline_name="Yahoo Finance EOD",
                scope_tickers=_scope(),
                expected_date=date(2026, 9, 22),
                audit_table="data_quality_audit",
                raise_on_fail=True,
            )

        audit = connection.execute(
            "SELECT status, metrics, errors, warnings FROM data_quality_audit"
        ).fetchone()
        assert audit[0] == "FAIL"
        assert '"duplicate_count": 1' in audit[1]
        assert "duplicate rows" in audit[2]
        assert "VND=X" in audit[3]
    finally:
        connection.close()


def test_warning_tickers_must_be_inside_scope() -> None:
    connection = duckdb.connect(":memory:")
    try:
        _create_audit_table(connection)
        _create_yahoo_table(connection)

        with pytest.raises(ValueError, match="subset"):
            validate_and_persist_yahoo_eod_quality(
                connection=connection,
                table_name="raw_other_eod",
                pipeline_name="Yahoo Finance EOD",
                scope_tickers=["VND=X"],
                ohlc_warning_tickers=["GC=F"],
                expected_date=date(2026, 9, 22),
                audit_table="data_quality_audit",
            )
    finally:
        connection.close()
