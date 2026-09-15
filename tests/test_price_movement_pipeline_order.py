from __future__ import annotations

from datetime import date
from pathlib import Path

from src.cherrystock.application.services.sync_write_pipeline import SyncWritePipelineService


class Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def make(self, name: str, *, return_value=None):
        def _fn(**kwargs):
            self.calls.append((name, kwargs))
            if return_value is not None:
                return return_value
            return {"status": "PASS"}

        return _fn


def test_price_movement_runs_after_indicators_and_before_smart_money() -> None:
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
            return_value={"status": "PASS", "records_upserted": 12},
        ),
        calc_price_movement=recorder.make(
            "calc_price_movement",
            return_value={
                "status": "OK",
                "swing_rows_upserted": 2,
                "daily_rows_upserted": 8,
            },
        ),
        calc_smart_money=recorder.make(
            "calc_smart_money",
            return_value={"status": "OK", "score_rows_upserted": 8},
        ),
        execute_sql=recorder.make("execute_sql"),
        validate_dated=recorder.make("validate_dated"),
        validate_reference=recorder.make("validate_reference"),
        resolve_yahoo_expected_date=lambda _connection: date(2026, 8, 21),
    )

    summary = service.run(
        days_diff=3,
        amibroker=object(),
        connection=object(),
        ticker_repository=object(),
        index_repository=object(),
        trend_repository=object(),
        indicator_repository=object(),
        price_movement_repository=object(),
        smart_money_repository=object(),
    )

    names = [name for name, _ in recorder.calls]
    assert names.index("calc_indicators") < names.index("calc_price_movement")
    assert names.index("calc_price_movement") < names.index("calc_smart_money")

    movement_call = next(kwargs for name, kwargs in recorder.calls if name == "calc_price_movement")
    assert movement_call["from_last_day"] == 3
    assert movement_call["repository"] is not None

    movement_validation = next(
        kwargs
        for name, kwargs in recorder.calls
        if name == "validate_dated" and kwargs.get("pipeline_name") == "Price Movement Character"
    )
    assert movement_validation["table_name"] == '"CherryMon"."main"."cal_price_movement_daily"'
    assert movement_validation["key_cols"] == ["ConfigId", "Ticker", "Date"]
    assert movement_validation["check_count_anomalies"] is False

    movement_schema_call = next(
        kwargs
        for name, kwargs in recorder.calls
        if name == "execute_sql"
        and kwargs.get("sql_description") == "Ensure Price Movement Character V1 schema"
    )
    assert movement_schema_call["sql_file_path"] == str(
        Path("sql") / "price_movement_character_v1_schema.sql"
    )
    assert summary["price_movement"]["status"] == "OK"
