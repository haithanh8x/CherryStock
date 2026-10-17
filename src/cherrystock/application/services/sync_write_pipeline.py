from __future__ import annotations

from pathlib import Path
from typing import Callable

from CrawlStock.readAmi import syncAmibroker_EOD, syncAmibroker_Intraday, upsert_lstTicker
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
from calcEngine.calcIndicators import refresh_technical_indicators
from calcEngine.smartMoneyScore import refresh_smart_money_score


class SyncWritePipelineService:
    """Application service that orchestrates write-side sync, validation, and audit steps."""

    def __init__(
        self,
        sql_dir: Path = DUCKDB_SQL_PATH,
        sync_amibroker_eod: Callable[..., None] = syncAmibroker_EOD,
        sync_amibroker_intraday: Callable[..., None] = syncAmibroker_Intraday,
        sync_yahoo_eod: Callable[..., None] = syncYahooFinance_EOD,
        upsert_fa: Callable[..., None] = upsert_stock_fa,
        upsert_tickers: Callable[..., None] = upsert_lstTicker,
        calc_index: Callable[..., None] = calculate_VNINDEX_NOT_VIN,
        calc_trend: Callable[..., None] = calc_fv_Trend.cal_Moving_Average,
        calc_indicators: Callable[..., dict] = refresh_technical_indicators,
        calc_smart_money: Callable[..., dict] = refresh_smart_money_score,
        execute_sql: Callable[..., None] = executeDuckSQL,
        validate_dated: Callable[..., dict] = validate_and_persist_data_quality,
        validate_reference: Callable[..., dict] = validate_and_persist_reference_quality,
        resolve_yahoo_expected_date: Callable[[object], object] | None = None,
    ) -> None:
        self._sql_dir = sql_dir
        self._sync_amibroker_eod = sync_amibroker_eod
        self._sync_amibroker_intraday = sync_amibroker_intraday
        self._sync_yahoo_eod = sync_yahoo_eod
        self._upsert_fa = upsert_fa
        self._upsert_tickers = upsert_tickers
        self._calc_index = calc_index
        self._calc_trend = calc_trend
        self._calc_indicators = calc_indicators
        self._calc_smart_money = calc_smart_money
        self._execute_sql = execute_sql
        self._validate_dated = validate_dated
        self._validate_reference = validate_reference
        self._resolve_yahoo_expected_date = resolve_yahoo_expected_date or self._latest_yahoo_date

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
        indicator_repository=None,
        smart_money_repository=None,
    ) -> dict[str, object]:
        self._sync_amibroker_eod(from_last_day=days_diff, connection=connection)
        self._execute_sql(
            con=connection,
            sql_file_path=str(self._sql_dir / "updateHoliday.sql"),
            sql_description="Refresh Trading Calendar",
        )
        self._validate_dated(
            connection=connection,
            table_name='"CherryMon"."main"."raw_stock_eod"',
            pipeline_name="AmiBroker EOD",
            date_col="Date",
            symbol_col="Ticker",
            key_cols=["Ticker", "Date"],
            required_cols=["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"],
            small_count_anomaly_warn_pct=0.005,
            raise_on_fail=True,
        )

        self._sync_amibroker_intraday(
            from_last_day=days_diff,
            connection=connection,
        )
        for table_name, pipeline_name in (
            ('"CherryMon"."main"."raw_futures_intraday"', "AmiBroker Intraday Futures"),
            ('"CherryMon"."main"."raw_index_intraday"', "AmiBroker Intraday Index"),
            ('"CherryMon"."main"."raw_stock_intraday"', "AmiBroker Intraday Stock"),
            ('"CherryMon"."main"."raw_warrant_intraday"', "AmiBroker Intraday Warrant"),
        ):
            self._validate_dated(
                connection=connection,
                table_name=table_name,
                pipeline_name=pipeline_name,
                date_col="Date",
                symbol_col="Ticker",
                key_cols=["Ticker", "Date", "RawTime", "TickSeq"],
                required_cols=[
                    "Ticker",
                    "Date",
                    "DateTime",
                    "RawTime",
                    "TickSeq",
                    "Close",
                    "Volume",
                ],
                max_row_change_pct=1.0,
                max_symbol_change_pct=0.25,
                raise_on_fail=True,
            )

        self._sync_yahoo_eod(from_last_day=days_diff, connection=connection)
        yahoo_expected_date = self._resolve_yahoo_expected_date(connection)
        self._validate_dated(
            connection=connection,
            table_name='"CherryMon"."main"."raw_other_eod"',
            pipeline_name="Yahoo Finance EOD",
            date_col="Date",
            symbol_col="Ticker",
            key_cols=["Ticker", "Date"],
            required_cols=["Ticker", "Date", "Open", "High", "Low", "Close"],
            expected_date=yahoo_expected_date,
            check_count_anomalies=False,
            filters={"Ticker": list(YAHOO_OTHER_TICKERS)},
            raise_on_fail=True,
        )

        self._upsert_fa(amibroker=amibroker, connection=connection)
        self._validate_reference(
            connection=connection,
            table_name='"CherryMon"."main"."raw_stock_fa"',
            pipeline_name="Fundamental Analysis",
            key_cols=["Ticker"],
            required_cols=["Ticker", "Date"],
            date_col="Date",
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


        return {"status": "sync_and_data_quality_completed"}
