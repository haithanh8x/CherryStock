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
                MA20_D DOUBLE,
                RSI14_D DOUBLE,
                MA20_W DOUBLE,
                RSI14_W DOUBLE,
                MA20_M DOUBLE,
                RSI14_M DOUBLE
            )
            """
        )
        connection.execute(
            """
            INSERT INTO ticker_indicator_source VALUES
                ('MWG', DATE '2026-08-28', 75.1, 55.2, 73.4, 58.1, 70.0, 60.0),
                ('MWG', DATE '2026-08-29', 75.4, 56.3, 73.6, 58.5, 70.2, 60.4),
                ('FPT', DATE '2026-08-29', 110.0, 52.0, 108.0, 54.0, 100.0, 57.0)
            """
        )
        connection.execute(
            """
            CREATE VIEW vw_Ticker_indicators AS
            SELECT
                Ticker,
                Date,
                MA20_D,
                RSI14_D,
                MA20_W,
                RSI14_W,
                MA20_M,
                RSI14_M
            FROM ticker_indicator_source
            """
        )

        connection.execute(
            """
            CREATE TABLE indicator_config_source (
                IndicatorCode VARCHAR NOT NULL,
                IndicatorName VARCHAR NOT NULL,
                ConfigCode VARCHAR NOT NULL,
                Timeframe VARCHAR NOT NULL,
                ComponentCode VARCHAR NOT NULL,
                Parameters JSON NOT NULL,
                IsEnabled BOOLEAN NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO indicator_config_source VALUES
                ('RSI', 'Relative Strength Index', 'RSI14_D', 'Daily', 'RSI', '{"length":14}', true),
                ('RSI', 'Relative Strength Index', 'RSI14_W', 'Weekly', 'RSI', '{"length":14}', true),
                ('RSI', 'Relative Strength Index', 'RSI14_M', 'Monthly', 'RSI', '{"length":14}', true)
            """
        )
        connection.execute(
            """
            CREATE VIEW vw_Indicator_config AS
            SELECT
                IndicatorCode,
                IndicatorName,
                ConfigCode,
                Timeframe,
                ComponentCode,
                Parameters,
                IsEnabled
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
