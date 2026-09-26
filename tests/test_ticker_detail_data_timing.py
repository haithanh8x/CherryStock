from webapp import ticker_detail_data as data
from webapp.ticker_detail_trace import TickerTrace
from webapp.ticker_detail_contract import FIELDS


def test_partial_failure_is_timed_and_other_panels_survive(monkeypatch):
    class Cursor:
        description = [("Ticker",)]
        def execute(self, query, parameters):
            assert parameters == ["MWG"]
            if "vw_Ticker_Movement_Profile" in query:
                raise RuntimeError("fixture view unavailable")
            return self
        def fetchall(self):
            return [("MWG",)]
        def fetchone(self):
            return ("HOSE",)
    class Manager:
        def __init__(self, *, read_only):
            assert read_only
        def __enter__(self):
            return Cursor()
        def __exit__(self, *args):
            pass
    monkeypatch.setattr(data, "DuckDBManager", Manager)
    sentinel = object()
    monkeypatch.setattr(data, "build_level_ladder", lambda ticker: sentinel)
    trace = TickerTrace("MWG")
    result = data.load_ticker_details("mwg", trace)
    assert result["ladder"] is sentinel
    assert result["market"] == "HOSE"
    assert set(result["errors"]) == {"vw_Ticker_Movement_Profile"}
    assert set(result["sections"]) == set(FIELDS) - set(result["errors"])
    failed = [event for event in trace.events if event["status"] == "error"]
    assert [e["stage"] for e in failed] == ["vw_Ticker_Movement_Profile.execute"]
    assert any(e["stage"] == "rs.total" for e in trace.events)
    assert any(e["stage"] == "data.total" for e in trace.events)
