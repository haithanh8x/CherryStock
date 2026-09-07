from datetime import date
from pathlib import Path

import pytest

from src.cherrystock.application.services.sync_write_pipeline import SyncWritePipelineService


class Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def make(self, name: str, *, raises: Exception | None = None, return_value=None):
        def _fn(**kwargs):
            self.calls.append((name, kwargs))
            if raises is not None:
                raise raises
            if return_value is not None:
                return return_value
            return {"status": "PASS"}

        return _fn


def _build_service(recorder: Recorder, *, validate_dated=None) -> SyncWritePipelineService:
    return SyncWritePipelineService(
        sql_dir=Path("sql"),
        sync_amibroker_eod=recorder.make("sync_amibroker_eod"),
        sync_amibroker_intraday=recorder.make("sync_amibroker_intraday"),
        sync_yahoo_eod=recorder.make("sync_yahoo_eod"),
        upsert_fa=recorder.make("upsert_fa"),
        upsert_tickers=recorder.make("upsert_tickers"),
        calc_index=recorder.make("calc_index"),
        calc_trend=recorder.make("calc_trend"),
        calc_indicators=recorder.make(
            "calc_indicators",
            return_value={"status": "PASS", "records_upserted": 12},
        ),
        calc_smart_money=recorder.make(
            "calc_smart_money",
            return_value={"status": "OK", "score_rows_upserted": 8},
        ),
        execute_sql=recorder.make("execute_sql"),
        validate_dated=validate_dated or recorder.make("validate_dated"),
        validate_reference=recorder.make("validate_reference"),
        resolve_yahoo_expected_date=lambda _connection: date(2026, 8, 21),
    )


def test_sync_write_pipeline_calls_steps_and_validation_in_order() -> None:
    recorder = Recorder()
    service = _build_service(recorder)

    connection = object()
    amibroker = object()
    ticker_repository = object()
    index_repository = object()
    trend_repository = object()
    indicator_repository = object()
    smart_money_repository = object()

    service.run(
        days_diff=9,
        amibroker=amibroker,
        connection=connection,
        ticker_repository=ticker_repository,
        index_repository=index_repository,
        trend_repository=trend_repository,
        indicator_repository=indicator_repository,
        smart_money_repository=smart_money_repository,
    )

    assert [name for name, _ in recorder.calls] == [
        "sync_amibroker_eod",
        "execute_sql",
        "validate_dated",
        "sync_amibroker_intraday",
        "validate_dated",
        "validate_dated",
        "validate_dated",
        "validate_dated",
        "sync_yahoo_eod",
        "validate_dated",
        "upsert_fa",
        "validate_reference",
        "upsert_tickers",
        "validate_reference",
        "calc_index",
        "validate_dated",
        "calc_trend",
        "validate_dated",
        "calc_indicators",
        "validate_dated",
        "execute_sql",
        "calc_smart_money",
        "validate_dated",
    ]

    assert recorder.calls[0][1] == {"from_last_day": 9, "connection": connection}
    assert recorder.calls[1][1] == {
        "con": connection,
        "sql_file_path": str(Path("sql") / "updateHoliday.sql"),
        "sql_description": "Refresh Trading Calendar",
    }
    assert recorder.calls[2][1]["pipeline_name"] == "AmiBroker EOD"
    assert recorder.calls[2][1]["table_name"] == '"CherryMon"."main"."raw_stock_eod"'

    assert recorder.calls[3][1] == {"from_last_day": 9, "connection": connection}
    intraday_validations = recorder.calls[4:8]
    assert [kwargs["pipeline_name"] for _, kwargs in intraday_validations] == [
        "AmiBroker Intraday Futures",
        "AmiBroker Intraday Index",
        "AmiBroker Intraday Stock",
        "AmiBroker Intraday Warrant",
    ]
    assert all(kwargs["key_cols"] == ["Ticker", "Date", "RawTime", "TickSeq"] for _, kwargs in intraday_validations)
    assert all(kwargs["max_row_change_pct"] == 1.0 for _, kwargs in intraday_validations)

    assert recorder.calls[8][1] == {"from_last_day": 9, "connection": connection}
    assert recorder.calls[9][1]["pipeline_name"] == "Yahoo Finance EOD"
    assert recorder.calls[9][1]["expected_date"] == date(2026, 8, 21)
    assert recorder.calls[9][1]["check_count_anomalies"] is False
    assert recorder.calls[9][1]["filters"] == {
        "Ticker": ["DX-Y.NYB", "BTC-USD", "VND=X", "GC=F"]
    }

    assert recorder.calls[10][1] == {"amibroker": amibroker, "connection": connection}
    assert recorder.calls[11][1]["pipeline_name"] == "Fundamental Analysis"
    assert recorder.calls[11][1]["key_cols"] == ["Ticker"]
    assert recorder.calls[11][1]["required_cols"] == ["Ticker", "Date"]
    assert recorder.calls[11][1]["date_col"] == "Date"

    assert recorder.calls[12][1] == {"connection": connection, "repository": ticker_repository}
    assert recorder.calls[13][1]["pipeline_name"] == "Ticker Master"
    assert recorder.calls[13][1]["key_cols"] == ["Ticker"]

    assert recorder.calls[14][1] == {"connection": connection, "repository": index_repository}
    assert recorder.calls[15][1]["filters"] == {"INDEX_NAME": "VNINDEX_NOT_VIN"}

    assert recorder.calls[16][1] == {
        "from_last_day": 9,
        "connection": connection,
        "repository": trend_repository,
    }
    assert recorder.calls[17][1]["pipeline_name"] == "Moving Average Trend"

    assert recorder.calls[18][1] == {
        "from_last_day": 9,
        "connection": connection,
        "repository": indicator_repository,
    }
    assert recorder.calls[19][1]["pipeline_name"] == "Technical Indicator Engine"
    assert recorder.calls[19][1]["key_cols"] == [
        "Ticker",
        "Date",
        "ConfigId",
        "ComponentCode",
    ]

    assert recorder.calls[20][1] == {
        "con": connection,
        "sql_file_path": str(Path("sql") / "smart_money_v1_schema.sql"),
        "sql_description": "Ensure SmartMoney V1 schema",
    }
    assert recorder.calls[21][1] == {
        "from_last_day": 9,
        "connection": connection,
        "repository": smart_money_repository,
    }
    assert recorder.calls[22][1]["pipeline_name"] == "SmartMoneyScore"
    assert recorder.calls[22][1]["key_cols"] == ["ModelId", "Ticker", "Date"]

def test_indicator_validation_is_skipped_when_engine_has_no_rows() -> None:
    recorder = Recorder()
    service = SyncWritePipelineService(
        sql_dir=Path("sql"),
        sync_amibroker_eod=recorder.make("sync_amibroker_eod"),
        sync_amibroker_intraday=recorder.make("sync_amibroker_intraday"),
        sync_yahoo_eod=recorder.make("sync_yahoo_eod"),
        upsert_fa=recorder.make("upsert_fa"),
        upsert_tickers=recorder.make("upsert_tickers"),
        calc_index=recorder.make("calc_index"),
        calc_trend=recorder.make("calc_trend"),
        calc_indicators=recorder.make(
            "calc_indicators",
            return_value={"status": "SKIPPED", "records_upserted": 0},
        ),
        calc_smart_money=recorder.make(
            "calc_smart_money",
            return_value={"status": "OK", "score_rows_upserted": 0},
        ),
        execute_sql=recorder.make("execute_sql"),
        validate_dated=recorder.make("validate_dated"),
        validate_reference=recorder.make("validate_reference"),
        resolve_yahoo_expected_date=lambda _connection: date(2026, 8, 21),
    )

    service.run(days_diff=1, amibroker=object(), connection=object())

    assert [name for name, _ in recorder.calls][-1] == "calc_smart_money"
    assert sum(
        1
        for name, kwargs in recorder.calls
        if name == "validate_dated" and kwargs.get("pipeline_name") == "Technical Indicator Engine"
    ) == 0


def test_validation_failure_blocks_downstream_steps() -> None:
    recorder = Recorder()
    validation_error = RuntimeError("Data quality validation failed")
    service = _build_service(
        recorder,
        validate_dated=recorder.make("validate_dated", raises=validation_error),
    )

    with pytest.raises(RuntimeError, match="Data quality validation failed"):
        service.run(
            days_diff=3,
            amibroker=object(),
            connection=object(),
        )

    assert [name for name, _ in recorder.calls] == [
        "sync_amibroker_eod",
        "execute_sql",
        "validate_dated",
    ]
