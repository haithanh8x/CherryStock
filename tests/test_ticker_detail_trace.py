from webapp.ticker_detail_trace import TickerTrace
import pytest


def test_trace_records_error_and_reraises(monkeypatch):
    monkeypatch.delenv("CHERRYSTOCK_TICKER_TRACE", raising=False)
    trace = TickerTrace("MWG")
    with pytest.raises(ValueError):
        with trace.span("query"):
            raise ValueError("fixture")
    event = trace.events[0]
    assert event["ticker"] == "MWG"
    assert event["request_id"] == trace.request_id
    assert event["status"] == "error"
    assert event["duration_ms"] >= 0
    assert "fixture" not in str(event)


def test_trace_file_is_opt_in(monkeypatch, tmp_path):
    from webapp import ticker_detail_trace as module
    target = tmp_path / "timing.jsonl"
    monkeypatch.setattr(module, "TRACE_PATH", target)
    monkeypatch.delenv("CHERRYSTOCK_TICKER_TRACE", raising=False)
    TickerTrace("MWG").record("query", 1)
    assert not target.exists()
    monkeypatch.setenv("CHERRYSTOCK_TICKER_TRACE", "1")
    TickerTrace("MWG").record("query", 2)
    assert '"duration_ms": 2' in target.read_text(encoding="utf-8")
