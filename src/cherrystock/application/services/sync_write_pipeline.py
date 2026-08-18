from __future__ import annotations

from pathlib import Path
from typing import Callable

from CrawlStock.readAmi import syncAmibroker_EOD, upsert_lstTicker
from CrawlStock.upsertFA import upsert_stock_fa
from CrawlStock.readYahooFinance import syncYahooFinance_EOD
from Ults.DuckLib import executeDuckSQL
from Ults.lstPara import DUCKDB_SQL_PATH
from calcEngine import calc_fv_Trend
from calcEngine.calcIndexes import calculate_VNINDEX_NOT_VIN


class SyncWritePipelineService:
    """Application service that orchestrates all write-side sync steps in one flow."""

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
    ) -> None:
        self._sql_dir = sql_dir
        self._sync_amibroker_eod = sync_amibroker_eod
        self._sync_yahoo_eod = sync_yahoo_eod
        self._upsert_fa = upsert_fa
        self._upsert_tickers = upsert_tickers
        self._calc_index = calc_index
        self._calc_trend = calc_trend
        self._execute_sql = execute_sql

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
        self._sync_yahoo_eod(from_last_day=days_diff, connection=connection)
        self._upsert_fa(amibroker=amibroker, connection=connection)
        self._upsert_tickers(connection=connection, repository=ticker_repository)
        self._execute_sql(con=connection, sql_file_path=str(self._sql_dir / "updateHoliday.sql"))
        self._calc_index(connection=connection, repository=index_repository)
        self._calc_trend(
            from_last_day=days_diff,
            connection=connection,
            repository=trend_repository,
        )
