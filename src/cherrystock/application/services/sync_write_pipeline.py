from __future__ import annotations

from pathlib import Path
from typing import Callable

from CrawlStock.readAmi import syncAmibroker_EOD, upsert_lstTicker
from CrawlStock.upsertFA import upsert_stock_fa
from CrawlStock.readYahooFinance import YAHOO_OTHER_TICKERS, syncYahooFinance_EOD
from Ults.DataQualityOrchestration import (
    validate_and_persist_data_quality,
    validate_and_persist_reference_quality,
)
from Ults.DuckLib import executeDuckSQL, returnSQL
from Ults.lstPara import DUCKDB_SQL_PATH
from calcEngine import calc_fv_Trend
from calcEngine.calcIndexes import calculate_VNINDEX_NOT_VIN


class SyncWritePipelineService:
    """Application service that orchestrates write-side sync, validation, and audit steps."""

    def __init__(
        self,
        sql_dir: Path = DUCKDB_SQL_PATH,
        sync_amibroker_eod: Callable[..., None] = syncAmibroker_EOD,
        sync_yahoo_eod: Callable[..., None] = syncYahooFinance_EOD,
        upsert_fa: Callable[..., None] = upsert_stock_fa,
        upsert_tickers: Callable[..., None] = upsert_lstTicker,
        calc_index: Callable[..., None] = calculate_VNINDEX_NOT_VIN,
        calc_trend: Callable[..., None] = calc_fv_Trend.cal_Moving_Average,
        execute_sql: Callable[..., None] = executeDuckSQL,
        validate_dated: Callable[..., dict] = validate_and_persist_data_quality,
        validate_reference: Callable[..., dict] = validate_and_persist_reference_quality,
    ) -> None:
        self._sql_dir = sql_dir
        self._sync_amibroker_eod = sync_amibroker_eod
        self._sync_yahoo_eod = sync_yahoo_eod
        self._upsert_fa = upsert_fa
        self._upsert_tickers = upsert_tickers
        self._calc_index = calc_index
        self._calc_trend = calc_trend
        self._execute_sql = execute_sql
        self._validate_dated = validate_dated
        self._validate_reference = validate_reference

    @staticmethod
    def _latest_yahoo_date(connection):
        ticker_values = ", ".join(
            "'" + ticker.replace("'", "''") + "'" for ticker in YAHOO_OTHER_TICKERS
        )
        latest_frame = returnSQL(
            connection,
            f"""
            SELECT MAX(Date) AS max_date
            FROM "CherryMon"."main"."raw_other_eod"
            WHERE Ticker IN ({ticker_values})
            """,
        )
        if latest_frame is None or latest_frame.empty or latest_frame["max_date"].isna().all():
            raise RuntimeError("Yahoo EOD validation cannot resolve the latest source date.")
        return latest_frame["max_date"].iloc[0]

    def run(
        self,
        *,
        days_diff: int,
        amibroker,
        connection,
        ticker_repository=None,
        index_repository=None,
        trend_repository=None,
    ) -> None:
        self._sync_amibroker_eod(from_last_day=days_diff, connection=connection)
        self._validate_dated(
            connection=connection,
            table_name='"CherryMon"."main"."raw_stock_eod"',
            pipeline_name="AmiBroker EOD",
            date_col="Date",
            symbol_col="Ticker",
            key_cols=["Ticker", "Date"],
            required_cols=["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"],
            raise_on_fail=True,
        )

        self._sync_yahoo_eod(from_last_day=days_diff, connection=connection)
        yahoo_expected_date = self._latest_yahoo_date(connection)
        self._validate_dated(
            connection=connection,
            table_name='"CherryMon"."main"."raw_other_eod"',
            pipeline_name="Yahoo Finance EOD",
            date_col="Date",
            symbol_col="Ticker",
            key_cols=["Ticker", "Date"],
            required_cols=["Ticker", "Date", "Open", "High", "Low", "Close"],
            expected_date=yahoo_expected_date,
            filters={"Ticker": list(YAHOO_OTHER_TICKERS)},
            raise_on_fail=True,
        )

        self._upsert_fa(amibroker=amibroker, connection=connection)
        self._validate_dated(
            connection=connection,
            table_name='"CherryMon"."main"."raw_stock_fa"',
            pipeline_name="Fundamental Analysis",
            date_col="Date",
            symbol_col="Ticker",
            key_cols=["Ticker"],
            required_cols=["Ticker", "Date"],
            raise_on_fail=True,
        )

        self._upsert_tickers(connection=connection, repository=ticker_repository)
        self._validate_reference(
            connection=connection,
            table_name='"CherryMon"."main"."raw_lstTicker"',
            pipeline_name="Ticker Master",
            key_cols=["Ticker"],
            required_cols=["Ticker", "status"],
            raise_on_fail=True,
        )

        self._execute_sql(con=connection, sql_file_path=str(self._sql_dir / "updateHoliday.sql"))

        self._calc_index(connection=connection, repository=index_repository)
        self._validate_dated(
            connection=connection,
            table_name='"CherryMon"."main"."cal_Indexes"',
            pipeline_name="Composite Index",
            date_col="Date",
            symbol_col="INDEX_NAME",
            key_cols=["INDEX_NAME", "Date"],
            required_cols=["INDEX_NAME", "Date", "Close"],
            filters={"INDEX_NAME": "VNINDEX_NOT_VIN"},
            raise_on_fail=True,
        )

        self._calc_trend(
            from_last_day=days_diff,
            connection=connection,
            repository=trend_repository,
        )
        self._validate_dated(
            connection=connection,
            table_name='"CherryMon"."main"."cal_Trends"',
            pipeline_name="Moving Average Trend",
            date_col="Date",
            symbol_col="Ticker",
            key_cols=["Ticker", "Date"],
            required_cols=["Ticker", "Date", "Close"],
            raise_on_fail=True,
        )
