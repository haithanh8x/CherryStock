from __future__ import annotations

import pandas as pd

from webapp.smart_money_state_flow import (
    SMART_MONEY_STATE_FLOW,
    build_smart_money_state_blocks,
    format_ticker_sequence,
    market_state_anchor_id,
)


def test_state_blocks_follow_flow_and_split_tickers_by_ma200() -> None:
    snapshot = pd.DataFrame(
        [
            {
                "Ticker": "AAA",
                "MarketState": "ACCUMULATION",
                "TradeAction": "BUY",
                "TradeActionConfidenceScore": 81.25,
                "Close": 95.0,
                "MA200": 100.0,
            },
            {
                "Ticker": "BBB",
                "MarketState": "ACCUMULATION",
                "TradeAction": "BUY",
                "TradeActionConfidenceScore": 91.75,
                "Close": 110.0,
                "MA200": 100.0,
            },
            {
                "Ticker": "FFF",
                "MarketState": "ACCUMULATION",
                "TradeAction": "HOLD",
                "TradeActionConfidenceScore": 75.0,
                "Close": 100.0,
                "MA200": 100.0,
            },
            {
                "Ticker": "EEE",
                "MarketState": "ACCUMULATION",
                "TradeAction": "HOLD",
                "TradeActionConfidenceScore": 55.0,
                "Close": 90.0,
                "MA200": 100.0,
            },
            {
                "Ticker": "CCC",
                "MarketState": "DISTRIBUTION",
                "TradeAction": "SELL",
                "TradeActionConfidenceScore": 88.5,
                "Close": 101.0,
                "MA200": 99.0,
            },
            {
                "Ticker": "DDD",
                "MarketState": "NEUTRAL",
                "TradeAction": "HOLD",
                "TradeActionConfidenceScore": 72.0,
                "Close": 80.0,
                "MA200": 90.0,
            },
        ]
    )

    blocks = build_smart_money_state_blocks(snapshot)

    assert [block["market_state"] for block in blocks[: len(SMART_MONEY_STATE_FLOW)]] == [
        state for state, _ in SMART_MONEY_STATE_FLOW
    ]

    accumulation = next(block for block in blocks if block["market_state"] == "ACCUMULATION")
    assert accumulation["anchor_id"] == "smart-money-state-accumulation"
    assert accumulation["total_tickers"] == 4
    assert accumulation["action_counts"] == {"BUY": 2, "HOLD": 2, "SELL": 0}
    assert [row["Ticker"] for row in accumulation["rows"]] == [
        "BBB",
        "AAA",
        "FFF",
        "EEE",
    ]
    assert [row["Ticker"] for row in accumulation["above_ma200_rows"]] == ["BBB", "FFF"]
    assert [row["Ticker"] for row in accumulation["below_ma200_rows"]] == ["AAA", "EEE"]
    assert accumulation["above_ma200_count"] == 2
    assert accumulation["below_ma200_count"] == 2
    assert accumulation["ma200_unavailable_count"] == 0
    assert accumulation["above_ma200_ticker_sequence"] == "**BBB, FFF**"
    assert accumulation["below_ma200_ticker_sequence"] == "**AAA, EEE**"

    distribution = next(block for block in blocks if block["market_state"] == "DISTRIBUTION")
    assert distribution["above_ma200_ticker_sequence"] == "**CCC**"

    supply_lock = next(block for block in blocks if block["market_state"] == "SUPPLY_LOCK")
    assert supply_lock["total_tickers"] == 0
    assert supply_lock["above_ma200_rows"] == []
    assert supply_lock["below_ma200_rows"] == []


def test_state_blocks_keep_ma200_unavailable_tickers_without_misclassification() -> None:
    snapshot = pd.DataFrame(
        [
            {
                "Ticker": "NEW",
                "MarketState": "MARKUP",
                "TradeAction": "HOLD",
                "TradeActionConfidenceScore": 70.0,
                "Close": 25.0,
                "MA200": None,
            },
            {
                "Ticker": "OK",
                "MarketState": "MARKUP",
                "TradeAction": "HOLD",
                "TradeActionConfidenceScore": 60.0,
                "Close": 30.0,
                "MA200": 20.0,
            },
        ]
    )

    markup = next(
        block
        for block in build_smart_money_state_blocks(snapshot)
        if block["market_state"] == "MARKUP"
    )

    assert markup["total_tickers"] == 2
    assert markup["above_ma200_count"] == 1
    assert markup["below_ma200_count"] == 0
    assert markup["ma200_unavailable_count"] == 1
    assert markup["above_ma200_ticker_sequence"] == "**OK**"
    assert markup["ma200_unavailable_ticker_sequence"] == "**NEW**"


def test_unknown_state_is_appended_and_duplicate_ticker_keeps_strongest_row() -> None:
    snapshot = pd.DataFrame(
        [
            {
                "Ticker": "XYZ",
                "MarketState": "FUTURE_STATE",
                "TradeAction": "HOLD",
                "TradeActionConfidenceScore": 60.0,
                "Close": 90.0,
                "MA200": 100.0,
            },
            {
                "Ticker": "xyz",
                "MarketState": "FUTURE_STATE",
                "TradeAction": "BUY",
                "TradeActionConfidenceScore": 70.0,
                "Close": 105.0,
                "MA200": 100.0,
            },
        ]
    )

    blocks = build_smart_money_state_blocks(snapshot)
    future = blocks[-1]

    assert future["market_state"] == "FUTURE_STATE"
    assert future["anchor_id"] == "smart-money-state-future-state"
    assert future["total_tickers"] == 1
    assert future["action_counts"] == {"BUY": 1, "HOLD": 0, "SELL": 0}
    assert future["rows"][0]["Ticker"] == "XYZ"
    assert future["rows"][0]["TradeActionConfidenceScore"] == 70.0
    assert future["above_ma200_ticker_sequence"] == "**XYZ**"


def test_format_ticker_sequence_and_anchor_id_are_deterministic() -> None:
    rows = [
        {"Ticker": "MCH"},
        {"Ticker": "VC3"},
        {"Ticker": "CTR"},
        {"Ticker": "CTF"},
    ]

    assert format_ticker_sequence(rows) == "**MCH, VC3**, CTR, CTF"
    assert format_ticker_sequence(rows, bold_top_n=0) == "MCH, VC3, CTR, CTF"
    assert market_state_anchor_id("SELLING_CLIMAX") == "smart-money-state-selling-climax"
    assert market_state_anchor_id(" Future State ") == "smart-money-state-future-state"
