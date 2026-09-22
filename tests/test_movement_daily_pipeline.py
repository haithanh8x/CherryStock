from __future__ import annotations

from datetime import date

import duckdb

from cherrystock.application.services.movement_daily_pipeline import (
    MovementDailyPipelineService,
)


class _Factory:
    def __init__(self, connection):
        self.connection = connection

    class _Reader:
        def __init__(self, connection):
            self.connection = connection

        def __enter__(self):
            return self.connection

        def __exit__(self, exc_type, exc_value, traceback):
            return None

    def reader(self):
        return self._Reader(self.connection)


class _FakeUow:
    def __init__(self, factory):
        self.connection = object()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None


def _plan_db():
    connection = duckdb.connect()
    connection.execute("ATTACH ':memory:' AS CherryMon")
    connection.execute("CREATE SCHEMA IF NOT EXISTS CherryMon.main")
    connection.execute(
        'CREATE TABLE CherryMon.main.vw_Ticker_Active (Ticker VARCHAR)'
    )
    connection.execute(
        '''
        CREATE TABLE CherryMon.main.vw_Ticker_OHLC_D (
            Ticker VARCHAR,
            Date DATE
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE CherryMon.main.vw_Ticker_ZigZag_Current (
            Ticker VARCHAR,
            ConfigCode VARCHAR,
            AsOfDate DATE
        )
        '''
    )
    return connection


def test_plan_selects_only_missing_or_stale_tickers() -> None:
    connection = _plan_db()
    try:
        connection.execute(
            "INSERT INTO CherryMon.main.vw_Ticker_Active VALUES ('AAA'), ('BBB'), ('CCC')"
        )
        connection.execute(
            """
            INSERT INTO CherryMon.main.vw_Ticker_OHLC_D VALUES
                ('AAA', DATE '2026-09-22'),
                ('BBB', DATE '2026-09-22'),
                ('CCC', DATE '2026-09-22')
            """
        )
        connection.execute(
            """
            INSERT INTO CherryMon.main.vw_Ticker_ZigZag_Current VALUES
                ('AAA', 'ZZ_D_5_MVP', DATE '2026-09-22'),
                ('BBB', 'ZZ_D_5_MVP', DATE '2026-09-21')
            """
        )

        service = MovementDailyPipelineService(connection_factory=_Factory(connection))
        plan = {row["Ticker"]: row for row in service.plan()}

        assert plan["AAA"]["PlanState"] == "UP_TO_DATE"
        assert plan["AAA"]["Selected"] is False
        assert plan["BBB"]["PlanState"] == "STALE"
        assert plan["BBB"]["Selected"] is True
        assert plan["CCC"]["PlanState"] == "MISSING_ZIGZAG"
        assert plan["CCC"]["Selected"] is True
    finally:
        connection.close()


def test_plan_force_selects_up_to_date_ticker() -> None:
    connection = _plan_db()
    try:
        connection.execute(
            "INSERT INTO CherryMon.main.vw_Ticker_Active VALUES ('AAA')"
        )
        connection.execute(
            "INSERT INTO CherryMon.main.vw_Ticker_OHLC_D VALUES ('AAA', DATE '2026-09-22')"
        )
        connection.execute(
            """
            INSERT INTO CherryMon.main.vw_Ticker_ZigZag_Current
            VALUES ('AAA', 'ZZ_D_5_MVP', DATE '2026-09-22')
            """
        )

        service = MovementDailyPipelineService(connection_factory=_Factory(connection))
        row = service.plan(force=True)[0]

        assert row["PlanState"] == "FORCED"
        assert row["Selected"] is True
    finally:
        connection.close()


def test_price_movement_refresh_rule_detects_only_lineage_change() -> None:
    current = {
        "zigzag_swing_count": 10,
        "zigzag_last_swing_seq": 10,
        "zigzag_last_confirmed_at": date(2026, 9, 20),
        "price_movement_swing_count": 10,
        "price_movement_last_swing_seq": 10,
        "price_movement_last_confirmed_at": date(2026, 9, 20),
        "profile_rows": 1,
        "profile_last_swing_seq": 10,
        "profile_as_of_confirmed_at": date(2026, 9, 20),
    }

    assert MovementDailyPipelineService._price_movement_needs_refresh(current) is False

    changed = dict(current)
    changed["zigzag_last_swing_seq"] = 11
    changed["zigzag_swing_count"] = 11
    assert MovementDailyPipelineService._price_movement_needs_refresh(changed) is True


def test_no_selected_ticker_is_noop(monkeypatch) -> None:
    service = MovementDailyPipelineService(
        connection_factory=object(),
        unit_of_work_cls=_FakeUow,
    )
    monkeypatch.setattr(
        service,
        "plan",
        lambda **_: [
            {
                "Ticker": "AAA",
                "LatestOHLCDate": date(2026, 9, 22),
                "OHLCRows": 100,
                "ZigZagAsOfDate": date(2026, 9, 22),
                "PlanState": "UP_TO_DATE",
                "Selected": False,
            }
        ],
    )

    summary = service.run()

    assert summary["selected_ticker_count"] == 0
    assert summary["up_to_date_ticker_count"] == 1
    assert summary["failure_count"] == 0


def test_selected_ticker_refreshes_zigzag_but_skips_pm_when_lineage_unchanged(
    monkeypatch,
) -> None:
    zigzag_calls: list[str] = []
    pm_calls: list[str] = []

    service = MovementDailyPipelineService(
        connection_factory=object(),
        unit_of_work_cls=_FakeUow,
        refresh_zigzag=lambda **kwargs: (
            zigzag_calls.append(kwargs["ticker"])
            or {"confirmed_pivots": 11, "current_status": "PROVISIONAL"}
        ),
        refresh_price_movement=lambda **kwargs: pm_calls.append(kwargs["ticker"]) or {},
    )
    monkeypatch.setattr(
        service,
        "plan",
        lambda **_: [
            {
                "Ticker": "AAA",
                "LatestOHLCDate": date(2026, 9, 22),
                "OHLCRows": 100,
                "ZigZagAsOfDate": date(2026, 9, 21),
                "PlanState": "STALE",
                "Selected": True,
            }
        ],
    )
    monkeypatch.setattr(
        service,
        "_load_price_movement_state",
        lambda ticker: {
            "zigzag_swing_count": 10,
            "zigzag_last_swing_seq": 10,
            "zigzag_last_confirmed_at": date(2026, 9, 20),
            "price_movement_swing_count": 10,
            "price_movement_last_swing_seq": 10,
            "price_movement_last_confirmed_at": date(2026, 9, 20),
            "profile_rows": 1,
            "profile_last_swing_seq": 10,
            "profile_as_of_confirmed_at": date(2026, 9, 20),
        },
    )

    summary = service.run()

    assert zigzag_calls == ["AAA"]
    assert pm_calls == []
    assert summary["zigzag_refreshed"] == 1
    assert summary["price_movement_up_to_date"] == 1
    assert summary["failure_count"] == 0


def test_selected_ticker_refreshes_pm_when_new_confirmed_swing(monkeypatch) -> None:
    pm_calls: list[str] = []
    service = MovementDailyPipelineService(
        connection_factory=object(),
        unit_of_work_cls=_FakeUow,
        refresh_zigzag=lambda **_: {
            "confirmed_pivots": 12,
            "current_status": "PROVISIONAL",
        },
        refresh_price_movement=lambda **kwargs: (
            pm_calls.append(kwargs["ticker"])
            or {
                "confirmed_movement_swings": 11,
                "profile_character": "TRENDING_UP",
            }
        ),
    )
    monkeypatch.setattr(
        service,
        "plan",
        lambda **_: [
            {
                "Ticker": "AAA",
                "LatestOHLCDate": date(2026, 9, 22),
                "OHLCRows": 100,
                "ZigZagAsOfDate": date(2026, 9, 21),
                "PlanState": "STALE",
                "Selected": True,
            }
        ],
    )
    monkeypatch.setattr(
        service,
        "_load_price_movement_state",
        lambda ticker: {
            "zigzag_swing_count": 11,
            "zigzag_last_swing_seq": 11,
            "zigzag_last_confirmed_at": date(2026, 9, 22),
            "price_movement_swing_count": 10,
            "price_movement_last_swing_seq": 10,
            "price_movement_last_confirmed_at": date(2026, 9, 20),
            "profile_rows": 1,
            "profile_last_swing_seq": 10,
            "profile_as_of_confirmed_at": date(2026, 9, 20),
        },
    )

    summary = service.run()

    assert pm_calls == ["AAA"]
    assert summary["price_movement_refreshed"] == 1
    assert summary["failure_count"] == 0


def test_zigzag_failure_isolated_and_reported(monkeypatch) -> None:
    service = MovementDailyPipelineService(
        connection_factory=object(),
        unit_of_work_cls=_FakeUow,
        refresh_zigzag=lambda **_: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(
        service,
        "plan",
        lambda **_: [
            {
                "Ticker": "AAA",
                "LatestOHLCDate": date(2026, 9, 22),
                "OHLCRows": 100,
                "ZigZagAsOfDate": date(2026, 9, 21),
                "PlanState": "STALE",
                "Selected": True,
            }
        ],
    )

    summary = service.run()

    assert summary["zigzag_failed"] == 1
    assert summary["failure_count"] == 1
    assert summary["results"][0]["PriceMovementStatus"] == "SKIPPED_ZIGZAG_FAILED"
