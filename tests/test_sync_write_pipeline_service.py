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
        sync_yahoo_eod=recorder.make("sync_yahoo_eod"),
        upsert_fa=recorder.make("upsert_fa"),
        upsert_tickers=recorder.make("upsert_tickers"),
        calc_index=recorder.make("calc_index"),
        calc_trend=recorder.make("calc_trend"),
        calc_indicators=recorder.make(
            "calc_indicators",
            return_value={"status": "PASS", "records_upserted": 12},
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

    service.run(
        days_diff=9,
        amibroker=amibroker,
        connection=connection,
        ticker_repository=ticker_repository,
        index_repository=index_repository,
        trend_repository=trend_repository,
        indicator_repository=indicator_repository,
    )

    assert [name for name, _ in recorder.calls] == [
        "sync_amibroker_eod",
        "validate_dated",
        "sync_yahoo_eod",
        "validate_dated",
        "upsert_fa",
        "validate_dated",
        "upsert_tickers",
        "validate_reference",
        "execute_sql",
        "calc_index",
        "validate_dated",
        "calc_trend",
        "validate_dated",
        "calc_indicators",
        "validate_dated",
    ]

    assert recorder.calls[0][1] == {"from_last_day": 9, "connection": connection}
    assert recorder.calls[1][1]["pipeline_name"] == "AmiBroker EOD"
    assert recorder.calls[1][1]["table_name"] == '"CherryMon"."main"."raw_stock_eod"'

    assert recorder.calls[2][1] == {"from_last_day": 9, "connection": connection}
    assert recorder.calls[3][1]["pipeline_name"] == "Yahoo Finance EOD"
    assert recorder.calls[3][1]["expected_date"] == date(2026, 8, 21)
    assert recorder.calls[3][1]["filters"] == {
        "Ticker": ["DX-Y.NYB", "BTC-USD", "VND=X", "GC=F"]
    }

    assert recorder.calls[4][1] == {"amibroker": amibroker, "connection": connection}
    assert recorder.calls[5][1]["pipeline_name"] == "Fundamental Analysis"
    assert recorder.calls[5][1]["key_cols"] == ["Ticker"]

    assert recorder.calls[6][1] == {"connection": connection, "repository": ticker_repository}
    assert recorder.calls[7][1]["pipeline_name"] == "Ticker Master"
    assert recorder.calls[7][1]["key_cols"] == ["Ticker"]

    assert recorder.calls[8][1] == {
        "con": connection,
        "sql_file_path": str(Path("sql") / "updateHoliday.sql"),
    }
    assert recorder.calls[9][1] == {"connection": connection, "repository": index_repository}
    assert recorder.calls[10][1]["filters"] == {"INDEX_NAME": "VNINDEX_NOT_VIN"}

    assert recorder.calls[11][1] == {
        "from_last_day": 9,
        "connection": connection,
        "repository": trend_repository,
    }
    assert recorder.calls[12][1]["pipeline_name"] == "Moving Average Trend"

    assert recorder.calls[13][1] == {
        "from_last_day": 9,
        "connection": connection,
        "repository": indicator_repository,
    }
    assert recorder.calls[14][1]["pipeline_name"] == "Technical Indicator Engine"
    assert recorder.calls[14][1]["key_cols"] == [
        "Ticker",
        "Date",
        "ConfigId",
        "ComponentCode",
    ]


def test_indicator_validation_is_skipped_when_engine_has_no_rows() -> None:
    recorder = Recorder()
    service = SyncWritePipelineService(
        sql_dir=Path("sql"),
        sync_amibroker_eod=recorder.make("sync_amibroker_eod"),
        sync_yahoo_eod=recorder.make("sync_yahoo_eod"),
        upsert_fa=recorder.make("upsert_fa"),
        upsert_tickers=recorder.make("upsert_tickers"),
        calc_index=recorder.make("calc_index"),
        calc_trend=recorder.make("calc_trend"),
        calc_indicators=recorder.make(
            "calc_indicators",
            return_value={"status": "SKIPPED", "records_upserted": 0},
        ),
        execute_sql=recorder.make("execute_sql"),
        validate_dated=recorder.make("validate_dated"),
        validate_reference=recorder.make("validate_reference"),
        resolve_yahoo_expected_date=lambda _connection: date(2026, 8, 21),
    )

    service.run(days_diff=1, amibroker=object(), connection=object())

    assert [name for name, _ in recorder.calls][-1] == "calc_indicators"
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
        "validate_dated",
    ]
