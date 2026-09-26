from __future__ import annotations

import pytest

from webapp.tradingview_links import tradingview_chart_url


@pytest.mark.parametrize(
    ("ticker", "market", "expected"),
    [
        ("MWG", "HOSE", "HOSE%3AMWG"),
        (" mwg ", " hsx ", "HOSE%3AMWG"),
        ("SHS", "HNX", "HNX%3ASHS"),
        ("ACV", "UPCOM", "UPCOM%3AACV"),
    ],
)
def test_vietnam_chart_destination(ticker, market, expected):
    assert tradingview_chart_url(ticker, market) == (
        "https://vn.tradingview.com/chart/?symbol=" + expected
    )


@pytest.mark.parametrize(
    ("ticker", "market"),
    [
        ("ACV", None),
        ("ACV", "NYSE"),
        ("ACV", ""),
        ("", "HOSE"),
        (None, "HOSE"),
        ("<script>", "HOSE"),
        ("MWG&symbol=NYSE:ACV", "HOSE"),
    ],
)
def test_unresolved_input_never_opens_a_guessed_or_injected_symbol(ticker, market):
    assert tradingview_chart_url(ticker, market) is None
