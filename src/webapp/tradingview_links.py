"""Vietnamese TradingView destinations; no network calls or default exchange guesses."""
from __future__ import annotations

import re
from urllib.parse import urlencode

VIETNAM_EXCHANGES = {"HOSE": "HOSE", "HSX": "HOSE", "HNX": "HNX", "UPCOM": "UPCOM"}


def tradingview_chart_url(ticker: object, market: object) -> str | None:
    """Return an exchange-qualified chart URL, or None for unresolved input."""
    symbol = str(ticker).strip().upper() if ticker is not None else ""
    exchange = VIETNAM_EXCHANGES.get(str(market).strip().upper())
    if not exchange or not re.fullmatch(r"[A-Z0-9]{1,20}", symbol):
        return None
    return "https://vn.tradingview.com/chart/?" + urlencode(
        {"symbol": f"{exchange}:{symbol}"}
    )
