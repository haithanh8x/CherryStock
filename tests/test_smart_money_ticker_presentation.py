from nicegui import ui
from webapp.smart_money_tab import _render_state_block, _action_color


def test_all_rows_are_bold_action_colored_without_ma200_or_commas():
    rows = [{"Ticker": ticker, "Market": "HOSE", "TradeAction": action}
            for ticker, action in [("MWG", "BUY"), ("FPT", "HOLD"), ("VCB", "SELL")]]
    async def show(_ticker):
        pass
    with ui.column() as root:
        _render_state_block({
            "market_state": "ACCUMULATION", "total_tickers": 3,
            "action_counts": {"BUY": 1, "HOLD": 1, "SELL": 1},
            "anchor_id": "smart-money-state-accumulation", "stage": 1,
            "description": "fixture", "rows": rows,
        }, show)
    try:
        elements = list(root.descendants())
        links = [e for e in elements if "cs-ticker-link" in e._classes]
        assert len(links) == 3
        for element, row in zip(links, rows):
            assert "font-bold" in element._classes
            assert element._style["--ticker-color"] == _action_color(row["TradeAction"])
            assert row["Ticker"] in element._props["href"]
        texts = [getattr(e, "text", "") for e in elements]
        assert "," not in texts
        assert not any("MA200" in text for text in texts)
    finally:
        root.delete()
