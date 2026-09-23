from __future__ import annotations

from cherrystock.application.services.movement_weekly_pipeline import (
    MovementWeeklyPipelineService,
)


def test_weekly_service_delegates_to_validated_full_universe_runner() -> None:
    calls: list[dict[str, object]] = []

    def runner(**kwargs):
        calls.append(kwargs)
        return {
            "active_ticker_count": 349,
            "zigzag_ok": 349,
            "price_movement_ok": 349,
            "failure_count": 0,
            "elapsed_seconds": 3600.0,
            "results": [],
        }

    callback = lambda *args: None
    service = MovementWeeklyPipelineService(
        connection_factory="factory",
        runner=runner,
    )

    result = service.run(
        requested_tickers=["MWG"],
        limit=1,
        fail_fast=True,
        progress_callback=callback,
    )

    assert result["failure_count"] == 0
    assert calls == [
        {
            "factory": "factory",
            "requested_tickers": ["MWG"],
            "limit": 1,
            "fail_fast": True,
            "progress_callback": callback,
        }
    ]
