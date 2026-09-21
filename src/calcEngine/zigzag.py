from __future__ import annotations

from time import perf_counter

import pandas as pd

from cherrystock.domain.analytics.zigzag.engine import calculate_zigzag
from cherrystock.infrastructure.database.repositories.zigzag_repository import ZigZagRepository


MVP_TICKER = "MWG"
OHLC_VIEW = '"CherryMon"."main"."vw_Ticker_OHLC_D"'


def load_ticker_source(connection, ticker: str) -> pd.DataFrame:
    resolved_ticker = ticker.strip().upper()
    if not resolved_ticker:
        raise ValueError("ticker must not be empty.")

    frame = connection.execute(
        f"""
        SELECT
            Ticker,
            Date,
            High,
            Low,
            Close
        FROM {OHLC_VIEW}
        WHERE Ticker = ?
        ORDER BY Date
        """,
        [resolved_ticker],
    ).df()
    if not frame.empty:
        frame["Date"] = pd.to_datetime(frame["Date"])
    return frame


def load_mwg_source(connection) -> pd.DataFrame:
    return load_ticker_source(connection, MVP_TICKER)


def refresh_zigzag_ticker(
    *,
    connection,
    ticker: str,
    repository: ZigZagRepository | None = None,
) -> dict[str, object]:
    """Full deterministic rebuild of the active ZigZag config for one ticker."""

    resolved_ticker = ticker.strip().upper()
    if not resolved_ticker:
        raise ValueError("ticker must not be empty.")

    resolved_repository = repository or ZigZagRepository(connection)
    config = resolved_repository.load_mvp_config()
    source = load_ticker_source(connection, resolved_ticker)
    if source.empty:
        raise RuntimeError(f"ZigZag source returned no rows for {resolved_ticker}.")

    started = perf_counter()
    pivots, current, diagnostics = calculate_zigzag(
        source,
        ticker=resolved_ticker,
        config=config,
    )
    calc_seconds = perf_counter() - started

    persisted = resolved_repository.replace_ticker(
        config_id=config.config_id,
        ticker=resolved_ticker,
        pivots=pivots,
        current=current,
    )

    return {
        "status": "OK",
        "scope": "TICKER_FULL_REBUILD",
        "ticker": resolved_ticker,
        "config_id": config.config_id,
        "config_code": config.config_code,
        "deviation_pct": config.deviation_pct,
        "source_rows": diagnostics.source_rows,
        "usable_rows": diagnostics.usable_rows,
        "invalid_rows_dropped": diagnostics.invalid_rows_dropped,
        "confirmed_pivots": len(pivots),
        "current_status": current.status if current is not None else None,
        "current_direction": current.direction if current is not None else None,
        "as_of_date": current.as_of_date if current is not None else None,
        "calculation_seconds": round(calc_seconds, 6),
        **persisted,
    }


def refresh_zigzag_mwg(
    *,
    connection,
    repository: ZigZagRepository | None = None,
) -> dict[str, object]:
    """Backward-compatible MWG entry point used by the validated MVP runbook."""

    summary = refresh_zigzag_ticker(
        connection=connection,
        ticker=MVP_TICKER,
        repository=repository,
    )
    summary["scope"] = "MWG_MVP_ONLY"
    return summary
