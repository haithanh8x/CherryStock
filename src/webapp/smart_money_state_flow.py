from __future__ import annotations

import re
from typing import Any

import pandas as pd


SMART_MONEY_STATE_FLOW: tuple[tuple[str, str], ...] = (
    ("ACCUMULATION", "Tích lũy đã đủ bằng chứng"),
    ("SUPPLY_LOCK", "Nguồn cung co lại trong nền tích lũy"),
    ("DEMAND_EXPANSION", "Cầu và thanh khoản mở rộng"),
    ("BREAKOUT", "Fresh flow xác nhận pha phá vỡ"),
    ("MARKUP", "Xu hướng tăng đang vận hành"),
    ("DISTRIBUTION", "Phân phối chiếm ưu thế"),
    ("SELLING_CLIMAX", "Áp lực bán cực điểm / exhaustion"),
    ("LIQUIDITY_DRYUP", "Thanh khoản co hẹp"),
    ("NEUTRAL", "Chưa có trạng thái trội"),
)

TRADE_ACTION_ORDER: tuple[str, ...] = ("BUY", "HOLD", "SELL")

_REQUIRED_COLUMNS = {
    "Ticker",
    "MarketState",
    "TradeAction",
    "TradeActionConfidenceScore",
    "Close",
    "MA200",
}


def market_state_anchor_id(state: str) -> str:
    """Return a stable in-page anchor id for a MarketState block."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(state).strip().lower()).strip("-")
    return f"smart-money-state-{slug or 'unknown'}"


def format_ticker_sequence(
    rows: list[dict[str, Any]],
    *,
    bold_top_n: int = 2,
) -> str:
    """Format confidence-ranked ticker rows as one comma-separated Markdown string."""
    tickers = [str(row.get("Ticker") or "").strip().upper() for row in rows]
    tickers = [ticker for ticker in tickers if ticker]
    if not tickers:
        return ""

    highlighted_count = min(max(int(bold_top_n), 0), len(tickers))
    if highlighted_count == 0:
        return ", ".join(tickers)

    highlighted = ", ".join(tickers[:highlighted_count])
    remainder = ", ".join(tickers[highlighted_count:])
    if remainder:
        return f"**{highlighted}**, {remainder}"
    return f"**{highlighted}**"


def build_smart_money_state_blocks(snapshot: pd.DataFrame) -> list[dict[str, Any]]:
    """Build UI-ready MarketState blocks split by price position versus MA200.

    Canonical states always appear in configured flow order. Future/unknown states
    are appended instead of being silently dropped. Within each state, ticker rows
    remain ranked by TradeActionConfidenceScore descending, then Ticker ascending.

    Price-position buckets use the latest snapshot Close and MA200:
    - above_ma200_rows: Close >= MA200
    - below_ma200_rows: Close < MA200
    - ma200_unavailable_rows: Close or MA200 is NULL/unusable

    The unavailable bucket preserves coverage without misclassifying a ticker into
    either requested MA200 column.
    """
    missing = _REQUIRED_COLUMNS.difference(snapshot.columns)
    if missing:
        raise ValueError(
            "SmartMoney snapshot missing required columns: " + ", ".join(sorted(missing))
        )

    frame = snapshot.copy()
    frame["Ticker"] = frame["Ticker"].astype(str).str.strip().str.upper()
    frame["MarketState"] = frame["MarketState"].astype(str).str.strip().str.upper()
    frame["TradeAction"] = frame["TradeAction"].astype(str).str.strip().str.upper()
    frame["TradeActionConfidenceScore"] = pd.to_numeric(
        frame["TradeActionConfidenceScore"], errors="coerce"
    )
    frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
    frame["MA200"] = pd.to_numeric(frame["MA200"], errors="coerce")

    frame = frame[
        frame["Ticker"].ne("")
        & frame["MarketState"].ne("")
        & frame["TradeActionConfidenceScore"].notna()
    ].copy()

    # Defensive one-row-per-ticker normalization for the latest cross-section.
    frame = (
        frame.sort_values(
            ["Ticker", "TradeActionConfidenceScore"],
            ascending=[True, False],
            kind="stable",
        )
        .drop_duplicates(subset=["Ticker"], keep="first")
        .reset_index(drop=True)
    )

    description_by_state = dict(SMART_MONEY_STATE_FLOW)
    canonical_states = [state for state, _ in SMART_MONEY_STATE_FLOW]
    observed_states = sorted(
        state
        for state in frame["MarketState"].unique().tolist()
        if state not in canonical_states
    )
    ordered_states = canonical_states + observed_states

    blocks: list[dict[str, Any]] = []
    for index, state in enumerate(ordered_states, start=1):
        state_rows = frame.loc[frame["MarketState"] == state].copy()
        state_rows = state_rows.sort_values(
            ["TradeActionConfidenceScore", "Ticker"],
            ascending=[False, True],
            kind="stable",
        )

        comparable = state_rows["Close"].notna() & state_rows["MA200"].notna()
        above_ma200 = state_rows.loc[
            comparable & (state_rows["Close"] >= state_rows["MA200"])
        ]
        below_ma200 = state_rows.loc[
            comparable & (state_rows["Close"] < state_rows["MA200"])
        ]
        ma200_unavailable = state_rows.loc[~comparable]

        rows = state_rows.to_dict("records")
        above_rows = above_ma200.to_dict("records")
        below_rows = below_ma200.to_dict("records")
        unavailable_rows = ma200_unavailable.to_dict("records")

        action_counts = {
            action: int((state_rows["TradeAction"] == action).sum())
            for action in TRADE_ACTION_ORDER
        }

        blocks.append(
            {
                "stage": index,
                "market_state": state,
                "anchor_id": market_state_anchor_id(state),
                "description": description_by_state.get(
                    state, "MarketState mới từ public SmartMoney contract"
                ),
                "total_tickers": int(state_rows["Ticker"].nunique()),
                "action_counts": action_counts,
                "rows": rows,
                # Retained for compatibility/diagnostics. UI renders MA200 buckets.
                "ticker_sequence": format_ticker_sequence(rows),
                "above_ma200_count": len(above_rows),
                "below_ma200_count": len(below_rows),
                "ma200_unavailable_count": len(unavailable_rows),
                "above_ma200_rows": above_rows,
                "below_ma200_rows": below_rows,
                "ma200_unavailable_rows": unavailable_rows,
                "above_ma200_ticker_sequence": format_ticker_sequence(above_rows),
                "below_ma200_ticker_sequence": format_ticker_sequence(below_rows),
                "ma200_unavailable_ticker_sequence": format_ticker_sequence(
                    unavailable_rows
                ),
            }
        )

    return blocks
