"""Bounded per-request timing; opt-in JSONL, no database values or SQL logging."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from threading import Lock
from time import perf_counter
from uuid import uuid4

LOGGER = logging.getLogger(__name__)
_WRITE_LOCK = Lock()
TRACE_PATH = Path(__file__).resolve().parents[2] / "docs/reference/data/smart_money/ticker_detail_popup/timing.jsonl"


class TickerTrace:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.request_id = uuid4().hex
        self.started = perf_counter()
        self.events: list[dict] = []
        self.enabled = os.getenv("CHERRYSTOCK_TICKER_TRACE", "") == "1"

    def record(self, stage: str, duration_ms: float, status: str = "ok", **metadata):
        event = {
            "utc": datetime.now(timezone.utc).isoformat(),
            "request_id": self.request_id, "ticker": self.ticker,
            "stage": stage, "duration_ms": round(duration_ms, 3),
            "elapsed_ms": round((perf_counter() - self.started) * 1000, 3),
            "status": status, **metadata,
        }
        self.events.append(event)
        if self.enabled:
            line = json.dumps(event, ensure_ascii=False)
            LOGGER.info("ticker_timing %s", line)
            try:
                with _WRITE_LOCK:
                    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
                    with TRACE_PATH.open("a", encoding="utf-8") as stream:
                        stream.write(line + "\n")
            except OSError:
                LOGGER.exception("Cannot write ticker timing evidence")
        return event

    @contextmanager
    def span(self, stage: str, **metadata):
        start = perf_counter()
        status = "ok"
        try:
            yield
        except BaseException:
            status = "error"
            raise
        finally:
            self.record(stage, (perf_counter() - start) * 1000, status, **metadata)
