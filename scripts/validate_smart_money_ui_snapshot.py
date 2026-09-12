from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Ults.DuckLib import DuckDBManager  # noqa: E402
from webapp.smart_money_state_flow import (  # noqa: E402
    SMART_MONEY_STATE_FLOW,
    TRADE_ACTION_ORDER,
    build_smart_money_state_blocks,
)


VIEW = '"CherryMon"."main"."vw_Ticker_SmartMoney"'
MODEL_CODE = "SMART_MONEY_V1"


def main() -> int:
    sql = f"""
        WITH latest AS (
            SELECT MAX(Date) AS Date
            FROM {VIEW}
            WHERE ModelCode = ?
        )
        SELECT
            v.Ticker,
            v.Date,
            v.MarketState,
            v.TradeAction,
            v.TradeActionConfidenceScore,
            v.SmartMoneyScore,
            v.ConfidenceScore,
            v.DataQualityStatus
        FROM {VIEW} AS v
        INNER JOIN latest AS d ON d.Date = v.Date
        WHERE v.ModelCode = ?
        ORDER BY v.MarketState, v.TradeActionConfidenceScore DESC, v.Ticker
    """

    with DuckDBManager(read_only=True) as connection:
        snapshot = connection.execute(sql, [MODEL_CODE, MODEL_CODE]).df()

    if snapshot.empty:
        raise RuntimeError("Latest SMART_MONEY_V1 snapshot is empty.")

    dates = snapshot["Date"].dropna().unique().tolist()
    if len(dates) != 1:
        raise RuntimeError(f"Expected exactly one latest snapshot date, got {dates!r}")

    blocks = build_smart_money_state_blocks(snapshot)
    expected_states = [state for state, _ in SMART_MONEY_STATE_FLOW]
    actual_prefix = [block["market_state"] for block in blocks[: len(expected_states)]]
    if actual_prefix != expected_states:
        raise RuntimeError(
            f"MarketState flow mismatch: expected={expected_states}, actual={actual_prefix}"
        )

    snapshot_tickers = int(snapshot["Ticker"].astype(str).str.upper().nunique())
    block_tickers = sum(int(block["total_tickers"]) for block in blocks)
    if block_tickers != snapshot_tickers:
        raise RuntimeError(
            f"Ticker coverage mismatch: snapshot={snapshot_tickers}, blocks={block_tickers}"
        )

    for block in blocks:
        total = int(block["total_tickers"])
        action_total = sum(
            int(block["action_counts"].get(action, 0))
            for action in TRADE_ACTION_ORDER
        )
        if action_total != total:
            raise RuntimeError(
                f"TradeAction summary mismatch for {block['market_state']}: "
                f"total={total}, action_total={action_total}"
            )

        rows = list(block["rows"])
        if len(rows) != total:
            raise RuntimeError(
                f"MarketState row coverage mismatch for {block['market_state']}: "
                f"rows={len(rows)}, total={total}"
            )

        confidences = [
            float(row["TradeActionConfidenceScore"])
            for row in rows
        ]
        if confidences != sorted(confidences, reverse=True):
            raise RuntimeError(
                f"Ticker confidence ranking is not descending for {block['market_state']}"
            )

        expected_tickers = [str(row["Ticker"]).upper() for row in rows]
        sequence = str(block.get("ticker_sequence") or "")
        normalized_sequence = sequence.replace("**", "")
        actual_tickers = normalized_sequence.split(", ") if normalized_sequence else []
        if actual_tickers != expected_tickers:
            raise RuntimeError(
                f"Ticker sequence mismatch for {block['market_state']}: "
                f"expected={expected_tickers}, actual={actual_tickers}"
            )

        if len(expected_tickers) >= 2:
            expected_prefix = f"**{expected_tickers[0]}, {expected_tickers[1]}**"
            if not sequence.startswith(expected_prefix):
                raise RuntimeError(
                    f"Top-two ticker emphasis mismatch for {block['market_state']}"
                )
        elif len(expected_tickers) == 1 and sequence != f"**{expected_tickers[0]}**":
            raise RuntimeError(
                f"Single ticker emphasis mismatch for {block['market_state']}"
            )

    print("SMART MONEY UI SNAPSHOT — PASS")
    print(f"Date: {dates[0]}")
    print(f"Tickers: {snapshot_tickers}")
    for block in blocks:
        counts = block["action_counts"]
        actions = " ".join(
            f"{action}={counts.get(action, 0)}"
            for action in TRADE_ACTION_ORDER
            if int(counts.get(action, 0)) > 0
        ) or "NO_TICKER"
        print(
            f"{block['stage']:02d}. {block['market_state']}: "
            f"total={block['total_tickers']} {actions}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
