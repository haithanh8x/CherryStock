from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Ults.DuckLib import DuckDBManager  # noqa: E402
from webapp.smart_money_snapshot_query import (  # noqa: E402
    MODEL_CODE,
    latest_smart_money_snapshot_sql,
)
from webapp.smart_money_state_flow import (  # noqa: E402
    SMART_MONEY_STATE_FLOW,
    TRADE_ACTION_ORDER,
    build_smart_money_state_blocks,
)


def _sequence_tickers(sequence: str) -> list[str]:
    normalized = sequence.replace("**", "")
    return normalized.split(", ") if normalized else []


def _validate_bucket_sequence(
    block: dict,
    *,
    rows_key: str,
    sequence_key: str,
    bucket_name: str,
) -> None:
    rows = list(block[rows_key])
    expected_tickers = [str(row["Ticker"]).upper() for row in rows]
    sequence = str(block.get(sequence_key) or "")
    actual_tickers = _sequence_tickers(sequence)
    if actual_tickers != expected_tickers:
        raise RuntimeError(
            f"{bucket_name} ticker sequence mismatch for {block['market_state']}: "
            f"expected={expected_tickers}, actual={actual_tickers}"
        )

    if len(expected_tickers) >= 2:
        expected_prefix = f"**{expected_tickers[0]}, {expected_tickers[1]}**"
        if not sequence.startswith(expected_prefix):
            raise RuntimeError(
                f"{bucket_name} top-two ticker emphasis mismatch for {block['market_state']}"
            )
    elif len(expected_tickers) == 1 and sequence != f"**{expected_tickers[0]}**":
        raise RuntimeError(
            f"{bucket_name} single ticker emphasis mismatch for {block['market_state']}"
        )


def main() -> int:
    with DuckDBManager(read_only=True) as connection:
        snapshot = connection.execute(
            latest_smart_money_snapshot_sql(),
            [MODEL_CODE, MODEL_CODE],
        ).df()

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

        confidences = [float(row["TradeActionConfidenceScore"]) for row in rows]
        if confidences != sorted(confidences, reverse=True):
            raise RuntimeError(
                f"Ticker confidence ranking is not descending for {block['market_state']}"
            )

        above = list(block["above_ma200_rows"])
        below = list(block["below_ma200_rows"])
        unavailable = list(block["ma200_unavailable_rows"])
        bucket_total = len(above) + len(below) + len(unavailable)
        if bucket_total != total:
            raise RuntimeError(
                f"MA200 bucket coverage mismatch for {block['market_state']}: "
                f"total={total}, bucket_total={bucket_total}"
            )

        for row in above:
            if (
                pd.isna(row["Close"])
                or pd.isna(row["MA200"])
                or float(row["Close"]) < float(row["MA200"])
            ):
                raise RuntimeError(
                    f">= MA200 classification mismatch for {block['market_state']}: "
                    f"{row['Ticker']}"
                )
        for row in below:
            if (
                pd.isna(row["Close"])
                or pd.isna(row["MA200"])
                or float(row["Close"]) >= float(row["MA200"])
            ):
                raise RuntimeError(
                    f"< MA200 classification mismatch for {block['market_state']}: "
                    f"{row['Ticker']}"
                )
        for row in unavailable:
            if not (pd.isna(row["Close"]) or pd.isna(row["MA200"])):
                raise RuntimeError(
                    f"MA200 N/A classification mismatch for {block['market_state']}: "
                    f"{row['Ticker']}"
                )

        _validate_bucket_sequence(
            block,
            rows_key="above_ma200_rows",
            sequence_key="above_ma200_ticker_sequence",
            bucket_name=">= MA200",
        )
        _validate_bucket_sequence(
            block,
            rows_key="below_ma200_rows",
            sequence_key="below_ma200_ticker_sequence",
            bucket_name="< MA200",
        )
        _validate_bucket_sequence(
            block,
            rows_key="ma200_unavailable_rows",
            sequence_key="ma200_unavailable_ticker_sequence",
            bucket_name="MA200 N/A",
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
            f"total={block['total_tickers']} "
            f">=MA200={block['above_ma200_count']} "
            f"<MA200={block['below_ma200_count']} "
            f"NA={block['ma200_unavailable_count']} "
            f"{actions}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
