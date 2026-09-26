import csv
from scripts import profile_ticker_detail as profile


def test_cli_writes_bounded_timings_and_hotspots(monkeypatch, tmp_path):
    def load(ticker, trace):
        with trace.span("fixture.query"):
            pass
        return {"errors": {}}
    monkeypatch.setattr(profile, "load_ticker_details", load)
    monkeypatch.setattr(profile, "OUTPUT", tmp_path)
    monkeypatch.setattr(profile, "PROJECT_ROOT", tmp_path.parent)
    monkeypatch.setattr(profile.sys, "argv", ["profile", "--tickers", "MWG", "--repeat", "2", "--profile"])
    assert profile.main() == 0
    with (tmp_path / "stages_profiled.csv").open(encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    assert {row["sample"] for row in rows} == {"1", "2"}
    assert len({row["request_id"] for row in rows}) == 2
    assert (tmp_path / "python_hotspots.csv").exists()
    assert (tmp_path / "summary_profiled.csv").exists()


def test_cli_partial_data_returns_nonzero(monkeypatch, tmp_path):
    monkeypatch.setattr(profile, "load_ticker_details", lambda ticker, trace: {"errors": {"view": "fixture"}})
    monkeypatch.setattr(profile, "OUTPUT", tmp_path)
    monkeypatch.setattr(profile, "PROJECT_ROOT", tmp_path.parent)
    monkeypatch.setattr(profile.sys, "argv", ["profile", "--tickers", "MWG", "--repeat", "1"])
    assert profile.main() == 1
    assert (tmp_path / "stages_baseline.csv").exists()
