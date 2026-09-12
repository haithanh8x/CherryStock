from __future__ import annotations

import pandas as pd

from webapp.smart_money_state_flow import (
    SMART_MONEY_STATE_FLOW,
    build_smart_money_state_blocks,
    format_ticker_sequence,
)


def test_state_blocks_follow_flow_and_rank_one_flat_ticker_sequence() -> None:
    snapshot = pd.DataFrame(
        [
            {
                "Ticker": "AAA",
                "MarketState": "ACCUMULATION",
                "TradeAction": "BUY",
                "TradeActionConfidenceScore": 81.25,
                "SmartMoneyScore": 78.0,
                "ConfidenceScore": 84.0,
            },
            {
                "Ticker": "BBB",
                "MarketState": "ACCUMULATION",
                "TradeAction": "BUY",
                "TradeActionConfidenceScore": 91.75,
                "SmartMoneyScore": 86.0,
                "ConfidenceScore": 94.0,
            },
            {
                "Ticker": "FFF",
                "MarketState": "ACCUMULATION",
                "TradeAction": "HOLD",
                "TradeActionConfidenceScore": 75.0,
                "SmartMoneyScore": 70.0,
                "ConfidenceScore": 76.0,
            },
            {
                "Ticker": "EEE",
                "MarketState": "ACCUMULATION",
                "TradeAction": "HOLD",
                "TradeActionConfidenceScore": 55.0,
                "SmartMoneyScore": 65.0,
                "ConfidenceScore": 58.0,
            },
            {
                "Ticker": "CCC",
                "MarketState": "DISTRIBUTION",
                "TradeAction": "SELL",
                "TradeActionConfidenceScore": 88.5,
                "SmartMoneyScore": 35.0,
                "ConfidenceScore": 90.0,
            },
            {
                "Ticker": "DDD",
                "MarketState": "NEUTRAL",
                "TradeAction": "HOLD",
                "TradeActionConfidenceScore": 72.0,
                "SmartMoneyScore": 51.0,
                "ConfidenceScore": 72.0,
            },
        ]
    )

    blocks = build_smart_money_state_blocks(snapshot)

    assert [block["market_state"] for block in blocks[: len(SMART_MONEY_STATE_FLOW)]] == [
        state for state, _ in SMART_MONEY_STATE_FLOW
    ]

    accumulation = next(block for block in blocks if block["market_state"] == "ACCUMULATION")
    assert accumulation["total_tickers"] == 4
    assert accumulation["action_counts"] == {"BUY": 2, "HOLD": 2, "SELL": 0}
    assert [row["Ticker"] for row in accumulation["rows"]] == [
        "BBB",
        "AAA",
        "FFF",
        "EEE",
    ]
    assert accumulation["ticker_sequence"] == "**BBB, AAA**, FFF, EEE"
    assert "action_rows" not in accumulation

    distribution = next(block for block in blocks if block["market_state"] == "DISTRIBUTION")
    assert distribution["total_tickers"] == 1
    assert distribution["action_counts"] == {"BUY": 0, "HOLD": 0, "SELL": 1}
    assert distribution["ticker_sequence"] == "**CCC**"

    supply_lock = next(block for block in blocks if block["market_state"] == "SUPPLY_LOCK")
    assert supply_lock["total_tickers"] == 0
    assert supply_lock["rows"] == []
    assert supply_lock["ticker_sequence"] == ""


def test_state_blocks_append_unknown_state_and_deduplicate_ticker() -> None:
    snapshot = pd.DataFrame(
        [
            {
                "Ticker": "XYZ",
                "MarketState": "FUTURE_STATE",
                "TradeAction": "HOLD",
                "TradeActionConfidenceScore": 60.0,
            },
            {
                "Ticker": "xyz",
                "MarketState": "FUTURE_STATE",
                "TradeAction": "BUY",
                "TradeActionConfidenceScore": 70.0,
            },
        ]
    )

    blocks = build_smart_money_state_blocks(snapshot)
    future = blocks[-1]

    assert future["market_state"] == "FUTURE_STATE"
    assert future["total_tickers"] == 1
    assert future["action_counts"] == {"BUY": 1, "HOLD": 0, "SELL": 0}
    assert future["rows"][0]["Ticker"] == "XYZ"
    assert future["rows"][0]["TradeActionConfidenceScore"] == 70.0
    assert future["ticker_sequence"] == "**XYZ**"


def test_format_ticker_sequence_bolds_top_two_and_uses_comma_separator() -> None:
    rows = [
        {"Ticker": "MCH"},
        {"Ticker": "VC3"},
        {"Ticker": "CTR"},
        {"Ticker": "CTF"},
    ]

    assert format_ticker_sequence(rows) == "**MCH, VC3**, CTR, CTF"
    assert format_ticker_sequence(rows, bold_top_n=0) == "MCH, VC3, CTR, CTF"
