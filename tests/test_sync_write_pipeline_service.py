from pathlib import Path

from src.cherrystock.application.services.sync_write_pipeline import SyncWritePipelineService


class Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def make(self, name: str):
        def _fn(**kwargs):
            self.calls.append((name, kwargs))

        return _fn


def test_sync_write_pipeline_calls_steps_in_order() -> None:
    recorder = Recorder()

    service = SyncWritePipelineService(
        sql_dir=Path("sql"),
        sync_amibroker_eod=recorder.make("sync_amibroker_eod"),
        sync_yahoo_eod=recorder.make("sync_yahoo_eod"),
        upsert_fa=recorder.make("upsert_fa"),
        upsert_tickers=recorder.make("upsert_tickers"),
        calc_index=recorder.make("calc_index"),
        calc_trend=recorder.make("calc_trend"),
        execute_sql=recorder.make("execute_sql"),
    )

    connection = object()
    amibroker = object()
    ticker_repository = object()
    index_repository = object()
    trend_repository = object()

    service.run(
        days_diff=9,
        amibroker=amibroker,
        connection=connection,
        ticker_repository=ticker_repository,
        index_repository=index_repository,
        trend_repository=trend_repository,
    )

    assert [name for name, _ in recorder.calls] == [
        "sync_amibroker_eod",
        "sync_yahoo_eod",
        "upsert_fa",
        "upsert_tickers",
        "execute_sql",
        "calc_index",
        "calc_trend",
    ]

    assert recorder.calls[0][1] == {"from_last_day": 9, "connection": connection}
    assert recorder.calls[1][1] == {"from_last_day": 9, "connection": connection}
    assert recorder.calls[2][1] == {"amibroker": amibroker, "connection": connection}
    assert recorder.calls[3][1] == {"connection": connection, "repository": ticker_repository}
    assert recorder.calls[4][1] == {
        "con": connection,
        "sql_file_path": str(Path("sql") / "updateHoliday.sql"),
    }
    assert recorder.calls[5][1] == {"connection": connection, "repository": index_repository}
    assert recorder.calls[6][1] == {
        "from_last_day": 9,
        "connection": connection,
        "repository": trend_repository,
    }
