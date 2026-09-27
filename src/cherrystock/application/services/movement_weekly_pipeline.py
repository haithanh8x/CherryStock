from __future__ import annotations

from typing import Callable, Iterable

from Orchestrator.active_ticker_movement_initload import (
    initial_load_active_ticker_movement,
)


class MovementWeeklyPipelineService:
    """Weekly full-universe Movement refresh.

    This service intentionally reuses the validated REQ-0033 full-history
    ZigZag -> Price Movement orchestration instead of maintaining a second
    calculation algorithm.
    """

    def __init__(
        self,
        *,
        connection_factory,
        runner: Callable[..., dict[str, object]] = initial_load_active_ticker_movement,
    ) -> None:
        self._factory = connection_factory
        self._runner = runner

    def run(
        self,
        *,
        requested_tickers: Iterable[str] | None = None,
        limit: int | None = None,
        fail_fast: bool = False,
        progress_callback: Callable[[str, int, int, str, str], None] | None = None,
    ) -> dict[str, object]:
        return self._runner(
            factory=self._factory,
            requested_tickers=requested_tickers,
            limit=limit,
            fail_fast=fail_fast,
            progress_callback=progress_callback,
        )
