"""NiceGUI component checks; real DB/browser checks remain in the runbook."""
from __future__ import annotations

import asyncio

from webapp import ticker_detail_dialog as detail
from webapp.ticker_detail_contract import FIELDS


def test_widget_locks_symbol_and_retains_tradingview_attribution():
    from webapp.tradingview_widget import widget_config
    config = widget_config("mwg", "HSX")
    assert config["symbol"] == "HOSE:MWG"
    assert config["allow_symbol_change"] is False


def test_popup_fields_and_close_cleanup(monkeypatch):
    async def immediate(function, *args):
        return function(*args)
    monkeypatch.setattr(detail.run, "io_bound", immediate)
    monkeypatch.setattr(detail, "load_ticker_details", lambda ticker, trace: {
        "ticker": ticker, "market": "HOSE", "ladder": None, "errors": {},
        "sections": {view: [dict.fromkeys(fields)] for view, fields in FIELDS.items()},
    })
    popup = detail.TickerDetailDialog()
    try:
        asyncio.run(popup.show("MWG"))
        descendants = list(popup.body.descendants())
        frames = [element for element in descendants if "data-tv-symbol" in element._props]
        assert len(frames) == 1
        assert frames[0]._props["data-tv-symbol"] == "HOSE:MWG"
        labels = [element for element in descendants if element.tag == "q-tooltip"]
        assert len(labels) >= 178  # each of the 89 field labels and values has a hint
        popup._closed()
        assert not list(popup.body.descendants())
    finally:
        popup.dialog.delete()


def test_late_result_cannot_replace_new_ticker(monkeypatch):
    pending = {}
    async def delayed(_function, ticker, trace):
        future = asyncio.get_running_loop().create_future()
        pending[ticker] = future
        return await future
    monkeypatch.setattr(detail.run, "io_bound", delayed)
    popup = detail.TickerDetailDialog()
    def payload(ticker):
        return {"ticker": ticker, "market": "HOSE", "ladder": None,
                "errors": {}, "sections": {}}
    async def scenario():
        first = asyncio.create_task(popup.show("MWG"))
        await asyncio.sleep(0)  # let the first request reach its controlled future
        second = asyncio.create_task(popup.show("FPT"))
        await asyncio.sleep(0)
        pending["FPT"].set_result(payload("FPT"))
        await second
        pending["MWG"].set_result(payload("MWG"))
        await first
        frames = [e for e in popup.body.descendants() if "data-tv-symbol" in e._props]
        assert len(frames) == 1
        assert frames[0]._props["data-tv-symbol"] == "HOSE:FPT"
        assert popup.title.text.startswith("FPT")
    try:
        asyncio.run(scenario())
    finally:
        popup.dialog.delete()


def test_tooltip_escapes_text_and_separates_example():
    rendered = detail.tooltip_html("<ticker>", "Diễn giải <b>. Ví dụ: 10 > 5")
    assert "&lt;ticker&gt;" in rendered
    assert "&lt;b&gt;" in rendered
    assert "<b>Ví dụ:</b>" in rendered
    assert "10 &gt; 5" in rendered


def test_empty_ladder_does_not_require_tooltip_options(monkeypatch):
    monkeypatch.setattr(detail, "build_level_ladder_chart_options", lambda ladder: {"series": []})
    assert detail._ladder_options(object())["series"] == []
