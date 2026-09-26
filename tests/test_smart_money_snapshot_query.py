from __future__ import annotations

import duckdb

from webapp.smart_money_snapshot_query import (
    MODEL_CODE,
    latest_smart_money_snapshot_sql,
)


def test_latest_snapshot_query_reads_close_and_ma200_from_canonical_views(tmp_path) -> None:
    database_path = (tmp_path / "CherryMon-query-test.duckdb").as_posix().replace("'", "''")
    connection = duckdb.connect()
    connection.execute(f"ATTACH '{database_path}' AS CherryMon")

    connection.execute(
        """
        CREATE TABLE CherryMon.main.raw_stock_fa (
            Ticker VARCHAR, Date DATE, Market VARCHAR
        )
        """
    )
    connection.execute(
        """
        INSERT INTO CherryMon.main.raw_stock_fa VALUES
        ('AAA', DATE '2026-09-01', 'HNX'),
        ('AAA', DATE '2026-09-12', 'HOSE')
        """
    )
    connection.execute(
        """
        CREATE TABLE CherryMon.main.vw_Ticker_SmartMoney (
            Ticker VARCHAR,
            Date DATE,
            ModelCode VARCHAR,
            ModelVersion VARCHAR,
            SmartMoneyScore DOUBLE,
            ConfidenceScore DOUBLE,
            MarketState VARCHAR,
            DataQualityStatus VARCHAR,
            TradeAction VARCHAR,
            TradeActionConfidenceScore DOUBLE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE CherryMon.main.vw_Ticker_OHLC_D (
            Ticker VARCHAR,
            Date DATE,
            Close DOUBLE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE CherryMon.main.vw_Ticker_indicators (
            Ticker VARCHAR,
            Date DATE,
            ConfigId INTEGER,
            ComponentCode VARCHAR,
            Value DOUBLE,
            IndicatorCode VARCHAR,
            Timeframe VARCHAR,
            WarmupBars INTEGER
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE CherryMon.main.vw_Indicator_config (
            ConfigId INTEGER,
            ConfigCode VARCHAR,
            ComponentCode VARCHAR,
            ConfigIsEnabled BOOLEAN,
            IndicatorIsActive BOOLEAN,
            ComponentIsActive BOOLEAN
        )
        """
    )

    connection.execute(
        """
        INSERT INTO CherryMon.main.vw_Ticker_SmartMoney VALUES
        ('AAA', DATE '2026-09-12', 'SMART_MONEY_V1', '1.0', 80, 90,
         'MARKUP', 'PASS', 'HOLD', 75)
        """
    )
    connection.execute(
        """
        INSERT INTO CherryMon.main.vw_Ticker_OHLC_D VALUES
        ('AAA', DATE '2026-09-12', 110)
        """
    )
    connection.execute(
        """
        INSERT INTO CherryMon.main.vw_Indicator_config VALUES
        (7, 'MA200_D', 'VALUE', TRUE, TRUE, TRUE),
        (6, 'MA50_D', 'VALUE', TRUE, TRUE, TRUE)
        """
    )
    connection.execute(
        """
        INSERT INTO CherryMon.main.vw_Ticker_indicators VALUES
        ('AAA', DATE '2026-09-12', 7, 'VALUE', 100, 'MA', 'D', 200),
        ('AAA', DATE '2026-09-12', 6, 'VALUE', 105, 'MA', 'D', 50)
        """
    )

    result = connection.execute(
        latest_smart_money_snapshot_sql(),
        [MODEL_CODE, MODEL_CODE],
    ).df()
    assert result.loc[0, "Market"] == "HOSE"

    # Missing listing metadata must not remove a SmartMoney ticker.
    connection.execute("DELETE FROM CherryMon.main.raw_stock_fa")
    missing_market = connection.execute(
        latest_smart_money_snapshot_sql(), [MODEL_CODE, MODEL_CODE]
    ).df()
    assert missing_market.shape[0] == 1
    assert missing_market.loc[0, "Market"] is None
    connection.close()

    assert result.shape[0] == 1
    assert result.loc[0, "Ticker"] == "AAA"
    assert result.loc[0, "Close"] == 110.0
    assert result.loc[0, "MA200"] == 100.0
