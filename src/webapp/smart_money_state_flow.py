from __future__ import annotations

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
}


def build_smart_money_state_blocks(snapshot: pd.DataFrame) -> list[dict[str, Any]]:
    """Build UI-ready MarketState blocks from one SmartMoney snapshot.

    Canonical states always appear in the configured flow order. Any future/unknown
    MarketState found in the public view is appended rather than silently dropped.
    Within each state and each TradeAction subgroup, tickers are sorted by
    TradeActionConfidenceScore descending, then Ticker ascending for deterministic
    ties.
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

    frame = frame[
        frame["Ticker"].ne("")
        & frame["MarketState"].ne("")
        & frame["TradeActionConfidenceScore"].notna()
    ].copy()

    # Public SmartMoney V1 should already be one row per ticker/date/model. This
    # defensive de-duplication keeps UI ticker counts stable if the input contains
    # duplicate rows, retaining the strongest action-confidence evidence.
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
        state for state in frame["MarketState"].unique().tolist() if state not in canonical_states
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

        action_rows = {
            action: state_rows.loc[state_rows["TradeAction"] == action].to_dict("records")
            for action in TRADE_ACTION_ORDER
        }
        action_counts = {
            action: len(action_rows[action])
            for action in TRADE_ACTION_ORDER
        }
        blocks.append(
            {
                "stage": index,
                "market_state": state,
                "description": description_by_state.get(
                    state, "MarketState mới từ public SmartMoney contract"
                ),
                "total_tickers": int(state_rows["Ticker"].nunique()),
                "action_counts": action_counts,
                "action_rows": action_rows,
                "rows": state_rows.to_dict("records"),
            }
        )

    return blocks
