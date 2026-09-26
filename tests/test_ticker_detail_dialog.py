"""NiceGUI component checks; real DB/browser checks remain in the runbook."""
from __future__ import annotations

import asyncio
import json
import re

from webapp import ticker_detail_dialog as detail
from webapp.ticker_detail_contract import FIELDS


def test_widget_locks_symbol_and_retains_tradingview_attribution():
    document = detail.widget_document("mwg", "HSX")
    config = json.loads(re.search(r"async>(.*?)</script>", document).group(1))
    assert config["symbol"] == "HOSE:MWG"
    assert config["allow_symbol_change"] is False
    assert "embed-widget-advanced-chart.js" in document
    assert "tradingview-widget-copyright" in document


def test_popup_fields_and_close_cleanup(monkeypatch):
    async def immediate(function, *args):
        return function(*args)
    monkeypatch.setattr(detail.run, "io_bound", immediate)
    monkeypatch.setattr(detail, "load_ticker_details", lambda ticker: {
        "ticker": ticker, "market": "HOSE", "ladder": None, "errors": {},
        "sections": {view: [dict.fromkeys(fields)] for view, fields in FIELDS.items()},
    })
    popup = detail.TickerDetailDialog()
    try:
        asyncio.run(popup.show("MWG"))
        descendants = list(popup.body.descendants())
        frames = [element for element in descendants if element.tag == "iframe"]
        assert len(frames) == 1
        assert "HOSE:MWG" in frames[0]._props["srcdoc"]
        labels = [element for element in descendants if element.tag == "q-tooltip"]
        assert len(labels) >= 178  # each of the 89 field labels and values has a hint
        popup._closed()
        assert not list(popup.body.descendants())
    finally:
        popup.dialog.delete()


def test_late_result_cannot_replace_new_ticker(monkeypatch):
    pending = {}
    async def delayed(_function, ticker):
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
        frames = [e for e in popup.body.descendants() if e.tag == "iframe"]
        assert len(frames) == 1
        assert "HOSE:FPT" in frames[0]._props["srcdoc"]
        assert popup.title.text.startswith("FPT")
    try:
        asyncio.run(scenario())
    finally:
        popup.dialog.delete()
