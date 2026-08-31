from __future__ import annotations

import pytest

from src.Ults.DuckLib import DuckDBManager
from src.cherrystock.infrastructure.database.connection import DuckDBConnectionFactory


@pytest.fixture()
def mcp_test_db(tmp_path, monkeypatch):
    """Create a deterministic CherryStock-like DuckDB for MCP tests."""

    monkeypatch.delenv("DUCKDB_ENV", raising=False)
    monkeypatch.delenv("LOCAL_DB_PATH", raising=False)

    db_path = tmp_path / "CherryMon-test.duckdb"
    factory = DuckDBConnectionFactory(db_path=db_path, duckdb_env="local")

    with factory.writer() as connection:
        connection.execute(
            """
            CREATE TABLE ticker_indicator_source (
                Ticker VARCHAR NOT NULL,
                Date DATE NOT NULL,
                ConfigId BIGINT NOT NULL,
                ComponentCode VARCHAR NOT NULL,
                Value DOUBLE
            )
            """
        )
        connection.execute(
            """
            INSERT INTO ticker_indicator_source VALUES
                ('MWG', DATE '2026-08-28', 1, 'VALUE', 55.2),
                ('MWG', DATE '2026-08-29', 1, 'VALUE', 56.3),
                ('MWG', DATE '2026-08-22', 2, 'VALUE', 57.5),
                ('MWG', DATE '2026-08-29', 2, 'VALUE', 58.5),
                ('MWG', DATE '2026-08-28', 4, 'VALUE', 75.1),
                ('MWG', DATE '2026-08-29', 4, 'VALUE', 75.4),
                ('FPT', DATE '2026-08-29', 1, 'VALUE', 52.0)
            """
        )
        connection.execute(
            """
            CREATE VIEW vw_Ticker_indicators AS
            SELECT
                Ticker,
                Date,
                ConfigId,
                ComponentCode,
                Value
            FROM ticker_indicator_source
            """
        )

        connection.execute(
            """
            CREATE TABLE indicator_config_source (
                ConfigId BIGINT NOT NULL,
                ConfigCode VARCHAR NOT NULL,
                IndicatorCode VARCHAR NOT NULL,
                Timeframe VARCHAR NOT NULL,
                Parameters JSON NOT NULL,
                ConfigIsEnabled BOOLEAN NOT NULL,
                IndicatorIsActive BOOLEAN NOT NULL,
                ComponentCode VARCHAR NOT NULL,
                ComponentIsActive BOOLEAN
            )
            """
        )
        connection.execute(
            """
            INSERT INTO indicator_config_source VALUES
                (1, 'RSI14_D', 'RSI', 'Daily', '{"length":14}', true, true, 'VALUE', true),
                (2, 'RSI14_W', 'RSI', 'Weekly', '{"length":14}', true, true, 'VALUE', true),
                (3, 'RSI14_M', 'RSI', 'Monthly', '{"length":14}', true, true, 'VALUE', true),
                (4, 'MA20_D', 'MA', 'Daily', '{"length":20}', true, true, 'VALUE', true)
            """
        )
        connection.execute(
            """
            CREATE VIEW vw_Indicator_config AS
            SELECT
                ConfigId,
                ConfigCode,
                IndicatorCode,
                Timeframe,
                Parameters,
                ConfigIsEnabled,
                IndicatorIsActive,
                ComponentCode,
                ComponentIsActive
            FROM indicator_config_source
            """
        )

    previous_factory = DuckDBManager._factory
    DuckDBManager._factory = factory
    try:
        yield db_path
    finally:
        DuckDBManager.close_connection()
        DuckDBManager._factory = previous_factory
