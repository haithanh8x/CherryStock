from __future__ import annotations

import duckdb

from Orchestrator import active_ticker_movement_initload as bulk


class _FakeUow:
    def __init__(self, factory) -> None:
        self.connection = object()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None


def test_load_active_tickers_normalizes_deduplicates_and_sorts() -> None:
    connection = duckdb.connect()
    try:
        connection.execute("ATTACH ':memory:' AS CherryMon")
        connection.execute("CREATE SCHEMA IF NOT EXISTS CherryMon.main")
        connection.execute(
            """
            CREATE TABLE CherryMon.main.vw_Ticker_Active (Ticker VARCHAR)
            """
        )
        connection.execute(
            """
            INSERT INTO CherryMon.main.vw_Ticker_Active
            VALUES ('mwg'), (' FPT '), ('MWG'), (NULL), ('')
            """
        )

        assert bulk.load_active_tickers(connection) == ["FPT", "MWG"]
    finally:
        connection.close()


def test_bulk_load_runs_zigzag_then_price_movement_and_clears_no_swing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(bulk, "_resolve_universe", lambda **_: ["AAA", "NEW"])
    monkeypatch.setattr(bulk, "DuckDBUnitOfWork", _FakeUow)
    monkeypatch.setattr(bulk, "_count_ohlc_rows", lambda factory, ticker: 100)

    zigzag_calls: list[str] = []
    price_calls: list[str] = []
    clear_calls: list[str] = []

    def _zigzag(*, connection, ticker):
        zigzag_calls.append(ticker)
        return {
            "source_rows": 100,
            "usable_rows": 100,
            "confirmed_pivots": 5 if ticker == "AAA" else 0,
            "current_status": "PROVISIONAL" if ticker == "AAA" else "TRANSITION",
        }

    monkeypatch.setattr(bulk, "refresh_zigzag_ticker", _zigzag)
    monkeypatch.setattr(
        bulk,
        "_count_zigzag_swings",
        lambda factory, ticker: 4 if ticker == "AAA" else 0,
    )

    def _price(*, connection, ticker, config_code):
        price_calls.append(ticker)
        return {
            "confirmed_movement_swings": 4,
            "profile_character": "MIXED",
        }

    def _clear(*, connection, ticker, config_code):
        clear_calls.append(ticker)
        return {"status": "CLEARED"}

    monkeypatch.setattr(bulk, "refresh_price_movement_ticker", _price)
    monkeypatch.setattr(bulk, "clear_price_movement_ticker", _clear)

    summary = bulk.initial_load_active_ticker_movement(factory=object())

    assert zigzag_calls == ["AAA", "NEW"]
    assert price_calls == ["AAA"]
    assert clear_calls == ["NEW"]
    assert summary["failure_count"] == 0
    assert summary["zigzag_ok"] == 2
    assert summary["price_movement_ok"] == 1
    assert summary["price_movement_skipped_no_confirmed_swing"] == 1

    by_ticker = {row["Ticker"]: row for row in summary["results"]}
    assert by_ticker["AAA"]["PriceMovementStatus"] == "OK"
    assert by_ticker["NEW"]["PriceMovementStatus"] == "SKIPPED_NO_CONFIRMED_SWING"


def test_bulk_load_isolates_zigzag_failure_and_continues(monkeypatch) -> None:
    monkeypatch.setattr(bulk, "_resolve_universe", lambda **_: ["BAD", "GOOD"])
    monkeypatch.setattr(bulk, "DuckDBUnitOfWork", _FakeUow)
    monkeypatch.setattr(bulk, "_count_ohlc_rows", lambda factory, ticker: 50)

    def _zigzag(*, connection, ticker):
        if ticker == "BAD":
            raise RuntimeError("synthetic failure")
        return {
            "source_rows": 50,
            "usable_rows": 50,
            "confirmed_pivots": 3,
            "current_status": "PROVISIONAL",
        }

    monkeypatch.setattr(bulk, "refresh_zigzag_ticker", _zigzag)
    monkeypatch.setattr(bulk, "_count_zigzag_swings", lambda factory, ticker: 2)
    monkeypatch.setattr(
        bulk,
        "refresh_price_movement_ticker",
        lambda **_: {
            "confirmed_movement_swings": 2,
            "profile_character": "MIXED",
        },
    )

    summary = bulk.initial_load_active_ticker_movement(factory=object())

    by_ticker = {row["Ticker"]: row for row in summary["results"]}
    assert by_ticker["BAD"]["ZigZagStatus"] == "FAILED"
    assert by_ticker["BAD"]["PriceMovementStatus"] == "SKIPPED_ZIGZAG_FAILED"
    assert by_ticker["GOOD"]["ZigZagStatus"] == "OK"
    assert by_ticker["GOOD"]["PriceMovementStatus"] == "OK"
    assert summary["failure_count"] == 1


def test_active_ticker_without_ohlc_is_a_hard_failure(monkeypatch) -> None:
    monkeypatch.setattr(bulk, "_resolve_universe", lambda **_: ["EMPTY"])
    monkeypatch.setattr(bulk, "_count_ohlc_rows", lambda factory, ticker: 0)

    summary = bulk.initial_load_active_ticker_movement(factory=object())

    row = summary["results"][0]
    assert row["ZigZagStatus"] == "FAILED_NO_OHLC"
    assert row["PriceMovementStatus"] == "SKIPPED_ZIGZAG_FAILED"
    assert summary["failure_count"] == 1
