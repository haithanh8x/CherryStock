from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pandas.testing as pdt

from calcEngine.smartMoneyScore import refresh_smart_money_score
from cherrystock.infrastructure.database.repositories.smart_money_repository import (
    SmartMoneyRepository,
)


TICKERS = ("AAA", "BBB", "CCC", "DDD", "EEE", "FFF")


def _register_table(connection, name: str, frame: pd.DataFrame) -> None:
    temp_name = "_fixture_frame"
    connection.register(temp_name, frame)
    try:
        connection.execute(
            f'CREATE TABLE "CherryMon"."main"."{name}" AS SELECT * FROM {temp_name}'
        )
    finally:
        connection.unregister(temp_name)


def _build_fixture() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2026-01-02", periods=120)
    market_rows: list[dict[str, object]] = []
    indicator_rows: list[dict[str, object]] = []

    for ticker_index, ticker in enumerate(TICKERS):
        previous_close: float | None = None
        obv = 0.0
        ad = 0.0
        closes: list[float] = []
        ticker_market_rows: list[dict[str, object]] = []

        for index, current_date in enumerate(dates):
            base = 10.0 + ticker_index * 4.0
            trend = 0.035 * index * (1.0 + ticker_index * 0.04)
            cycle = np.sin(index / (5.0 + ticker_index)) * (0.30 + ticker_index * 0.02)
            close = base + trend + cycle
            open_price = close * (1.0 - 0.004 * np.cos(index / 3.0))
            high = max(open_price, close) * 1.018
            low = min(open_price, close) * 0.982
            volume = int(150_000 + ticker_index * 25_000 + (index % 13) * 9_000)
            typical = (high + low + close) / 3.0
            trading_value = int(round(typical * volume * 1000.0))

            ticker_market_rows.append(
                {
                    "Ticker": ticker,
                    "Date": current_date.date(),
                    "Open": open_price,
                    "High": high,
                    "Low": low,
                    "Close": close,
                    "Volume": volume,
                    "TradingValue": trading_value,
                    "TradingValue_Source": "EOD_TYPICAL_PRICE_PROXY",
                    "TradingValue_IsProxy": True,
                }
            )
            closes.append(close)

            if previous_close is not None:
                if close > previous_close:
                    obv += volume
                elif close < previous_close:
                    obv -= volume
            clv = ((close - low) - (high - close)) / (high - low)
            ad += clv * volume
            previous_close = close

            indicator_rows.extend(
                [
                    {
                        "Ticker": ticker,
                        "Date": current_date.date(),
                        "ConfigId": 40,
                        "ComponentCode": "VALUE",
                        "Value": obv,
                    },
                    {
                        "Ticker": ticker,
                        "Date": current_date.date(),
                        "ConfigId": 43,
                        "ComponentCode": "VALUE",
                        "Value": ad,
                    },
                ]
            )

        ticker_frame = pd.DataFrame(ticker_market_rows)
        ticker_frame["MA20"] = ticker_frame["Close"].rolling(20, min_periods=20).mean()
        ticker_frame["MA50"] = ticker_frame["Close"].rolling(50, min_periods=50).mean()
        for row_index, row in ticker_frame.iterrows():
            if pd.notna(row["MA20"]):
                indicator_rows.append(
                    {
                        "Ticker": ticker,
                        "Date": row["Date"],
                        "ConfigId": 20,
                        "ComponentCode": "VALUE",
                        "Value": float(row["MA20"]),
                    }
                )
            if pd.notna(row["MA50"]):
                indicator_rows.append(
                    {
                        "Ticker": ticker,
                        "Date": row["Date"],
                        "ConfigId": 50,
                        "ComponentCode": "VALUE",
                        "Value": float(row["MA50"]),
                    }
                )
        market_rows.extend(ticker_market_rows)

    market = pd.DataFrame(market_rows)
    benchmark = pd.DataFrame(
        {
            "Ticker": ["VNINDEX"] * len(dates),
            "Date": [value.date() for value in dates],
            "Close": [
                1000.0 + 1.2 * index + 5.0 * np.sin(index / 8.0)
                for index in range(len(dates))
            ],
        }
    )
    tickers = pd.DataFrame({"Ticker": list(TICKERS), "Status": ["Y"] * len(TICKERS)})
    indicators = pd.DataFrame(indicator_rows)
    return market, benchmark, tickers, indicators


def _create_fixture_database(connection, tmp_path: Path) -> None:
    attached_path = (tmp_path / "CherryMon-fixture.duckdb").as_posix().replace("'", "''")
    connection.execute(f"ATTACH '{attached_path}' AS CherryMon")

    market, benchmark, tickers, indicators = _build_fixture()
    _register_table(connection, "vw_Ticker_OHLC_D", market)
    _register_table(connection, "raw_index_eod", benchmark)
    _register_table(connection, "raw_lstTicker", tickers)
    _register_table(connection, "vw_Ticker_indicators", indicators)

    config = pd.DataFrame(
        [
            {
                "ConfigId": 20,
                "ComponentCode": "VALUE",
                "ConfigCode": "MA20_D",
                "ConfigIsEnabled": True,
                "IndicatorIsActive": True,
                "ComponentIsActive": True,
            },
            {
                "ConfigId": 50,
                "ComponentCode": "VALUE",
                "ConfigCode": "MA50_D",
                "ConfigIsEnabled": True,
                "IndicatorIsActive": True,
                "ComponentIsActive": True,
            },
            {
                "ConfigId": 40,
                "ComponentCode": "VALUE",
                "ConfigCode": "OBV_D",
                "ConfigIsEnabled": True,
                "IndicatorIsActive": True,
                "ComponentIsActive": True,
            },
            {
                "ConfigId": 43,
                "ComponentCode": "VALUE",
                "ConfigCode": "AD_D",
                "ConfigIsEnabled": True,
                "IndicatorIsActive": True,
                "ComponentIsActive": True,
            },
        ]
    )
    _register_table(connection, "vw_Indicator_config", config)

    schema_sql = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "DuckDB"
        / "sql"
        / "smart_money_v1_schema.sql"
    ).read_text(encoding="utf-8")
    connection.execute(schema_sql)
    connection.execute(schema_sql)

    model_count = connection.execute(
        'SELECT COUNT(*) FROM "CherryMon"."main"."dim_smart_money_model" WHERE ModelId = 1'
    ).fetchone()[0]
    factor_count = connection.execute(
        'SELECT COUNT(*) FROM "CherryMon"."main"."dim_smart_money_factor" WHERE IsEnabled = TRUE'
    ).fetchone()[0]
    assert int(model_count) == 1
    assert int(factor_count) == 10


def _recent_scores(connection, start_date) -> pd.DataFrame:
    return connection.execute(
        """
        SELECT
            ModelId,
            Ticker,
            Date,
            SmartMoneyScore,
            ConfidenceScore,
            MarketState,
            FactorCoverage,
            DataQualityStatus
        FROM "CherryMon"."main"."cal_smart_money_ticker_score"
        WHERE Date >= ?
        ORDER BY ModelId, Ticker, Date
        """,
        [start_date],
    ).df()


def _recent_factors(connection, start_date) -> pd.DataFrame:
    return connection.execute(
        """
        SELECT
            ModelId,
            Ticker,
            Date,
            FactorId,
            RawValue,
            NormalizedValue,
            DataQuality,
            SourceCode
        FROM "CherryMon"."main"."cal_smart_money_factor_values"
        WHERE Date >= ?
        ORDER BY ModelId, Ticker, Date, FactorId
        """,
        [start_date],
    ).df()


def test_full_refresh_public_view_and_incremental_convergence(tmp_path: Path) -> None:
    connection = duckdb.connect(":memory:")
    try:
        _create_fixture_database(connection, tmp_path)
        repository = SmartMoneyRepository(connection)

        full_summary = refresh_smart_money_score(
            from_last_day=None,
            connection=connection,
            repository=repository,
        )

        assert full_summary["status"] == "OK"
        assert int(full_summary["score_rows_upserted"]) > 0
        assert int(full_summary["factor_rows_upserted"]) > 0

        public_count = connection.execute(
            'SELECT COUNT(*) FROM "CherryMon"."main"."vw_Ticker_SmartMoney"'
        ).fetchone()[0]
        assert int(public_count) > 0

        preflight_sql = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "DuckDB"
            / "sql"
            / "smart_money_v1_preflight.sql"
        ).read_text(encoding="utf-8")
        connection.execute(preflight_sql)

        limit_rows = connection.execute(
            """
            SELECT
                COUNT(*) AS Rows,
                SUM(CASE WHEN v.NormalizedValue IS NOT NULL THEN 1 ELSE 0 END) AS NonNullValues,
                SUM(CASE WHEN v.DataQuality <> 'UNAVAILABLE' THEN 1 ELSE 0 END) AS NonUnavailable
            FROM "CherryMon"."main"."cal_smart_money_factor_values" AS v
            INNER JOIN "CherryMon"."main"."dim_smart_money_factor" AS f
                ON f.FactorId = v.FactorId
            WHERE f.FactorCode = 'LIMIT_UP'
            """
        ).fetchone()
        assert int(limit_rows[0]) > 0
        assert int(limit_rows[1] or 0) == 0
        assert int(limit_rows[2] or 0) == 0

        max_date = connection.execute(
            'SELECT MAX(Date) FROM "CherryMon"."main"."cal_smart_money_ticker_score"'
        ).fetchone()[0]
        start_date = (pd.Timestamp(max_date) - pd.Timedelta(days=20)).date()
        before_scores = _recent_scores(connection, start_date)
        before_factors = _recent_factors(connection, start_date)

        incremental_summary = refresh_smart_money_score(
            from_last_day=20,
            connection=connection,
            repository=repository,
        )
        assert incremental_summary["status"] == "OK"
        assert int(incremental_summary["score_rows_upserted"]) > 0

        after_scores = _recent_scores(connection, start_date)
        after_factors = _recent_factors(connection, start_date)

        pdt.assert_frame_equal(
            before_scores,
            after_scores,
            check_dtype=False,
            check_exact=False,
            rtol=1e-10,
            atol=1e-10,
        )
        pdt.assert_frame_equal(
            before_factors,
            after_factors,
            check_dtype=False,
            check_exact=False,
            rtol=1e-10,
            atol=1e-10,
        )
    finally:
        connection.close()
