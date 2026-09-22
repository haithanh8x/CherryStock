from __future__ import annotations

from time import perf_counter
from typing import Callable, Iterable

from calcEngine.priceMovement import (
    MVP_CONFIG_CODE as PRICE_MOVEMENT_CONFIG_CODE,
    clear_price_movement_ticker,
    refresh_price_movement_ticker,
)
from calcEngine.zigzag import refresh_zigzag_ticker
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork


ACTIVE_TICKER_VIEW = '"CherryMon"."main"."vw_Ticker_Active"'
ZIGZAG_CONFIG_CODE = "ZZ_D_5_MVP"


def load_active_tickers(connection) -> list[str]:
    """Load the canonical initial-load universe from vw_Ticker_Active."""

    try:
        rows = connection.execute(
            f"""
            SELECT DISTINCT UPPER(TRIM(CAST(Ticker AS VARCHAR))) AS Ticker
            FROM {ACTIVE_TICKER_VIEW}
            WHERE Ticker IS NOT NULL
              AND TRIM(CAST(Ticker AS VARCHAR)) <> ''
            ORDER BY Ticker
            """
        ).fetchall()
    except Exception as exc:
        raise RuntimeError(
            'Active ticker universe requires '
            '"CherryMon"."main"."vw_Ticker_Active" with a Ticker column.'
        ) from exc

    return [str(row[0]) for row in rows]


def _count_ohlc_rows(factory, ticker: str) -> int:
    with factory.reader() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
            WHERE Ticker = ?
            """,
            [ticker],
        ).fetchone()
    return int(row[0]) if row is not None else 0


def _count_zigzag_swings(factory, ticker: str) -> int:
    with factory.reader() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM "CherryMon"."main"."vw_Ticker_ZigZag_Swings"
            WHERE Ticker = ?
              AND ConfigCode = ?
            """,
            [ticker, ZIGZAG_CONFIG_CODE],
        ).fetchone()
    return int(row[0]) if row is not None else 0


def _resolve_universe(
    *,
    factory,
    requested_tickers: Iterable[str] | None,
    limit: int | None,
) -> list[str]:
    with factory.reader() as connection:
        active = load_active_tickers(connection)

    if requested_tickers:
        requested = {
            ticker.strip().upper()
            for ticker in requested_tickers
            if ticker and ticker.strip()
        }
        inactive = sorted(requested.difference(active))
        if inactive:
            raise ValueError(
                "Requested ticker(s) are not present in vw_Ticker_Active: "
                + ", ".join(inactive)
            )
        selected = [ticker for ticker in active if ticker in requested]
    else:
        selected = active

    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be >= 1.")
        selected = selected[:limit]

    return selected


def _new_result(ticker: str) -> dict[str, object]:
    return {
        "Ticker": ticker,
        "ZigZagStatus": "PENDING",
        "ZigZagSourceRows": None,
        "ZigZagUsableRows": None,
        "ZigZagConfirmedPivots": None,
        "ZigZagCurrentStatus": None,
        "ZigZagSwingCount": None,
        "PriceMovementStatus": "PENDING",
        "PriceMovementSwingCount": None,
        "MovementProfileCharacter": None,
        "ErrorStage": None,
        "ErrorMessage": None,
    }


def _progress(
    callback: Callable[[str, int, int, str, str], None] | None,
    *,
    stage: str,
    index: int,
    total: int,
    ticker: str,
    status: str,
) -> None:
    if callback is not None:
        callback(stage, index, total, ticker, status)


def initial_load_active_ticker_movement(
    *,
    factory,
    requested_tickers: Iterable[str] | None = None,
    limit: int | None = None,
    fail_fast: bool = False,
    progress_callback: Callable[[str, int, int, str, str], None] | None = None,
) -> dict[str, object]:
    """Initial-load ZigZag then Price Movement for the active ticker universe.

    Transaction boundary is one ticker per stage. A Price Movement failure never
    rolls back a successfully committed ZigZag calculation for the same ticker.
    """

    tickers = _resolve_universe(
        factory=factory,
        requested_tickers=requested_tickers,
        limit=limit,
    )
    results = {ticker: _new_result(ticker) for ticker in tickers}
    started = perf_counter()
    total = len(tickers)

    # Stage 1: ZigZag for every active ticker with canonical daily OHLC.
    for index, ticker in enumerate(tickers, start=1):
        result = results[ticker]
        source_rows = _count_ohlc_rows(factory, ticker)
        result["ZigZagSourceRows"] = source_rows

        if source_rows <= 0:
            result["ZigZagStatus"] = "FAILED_NO_OHLC"
            result["PriceMovementStatus"] = "SKIPPED_ZIGZAG_FAILED"
            result["ErrorStage"] = "ZIGZAG"
            result["ErrorMessage"] = "No vw_Ticker_OHLC_D rows for active ticker."
            _progress(
                progress_callback,
                stage="ZIGZAG",
                index=index,
                total=total,
                ticker=ticker,
                status=str(result["ZigZagStatus"]),
            )
            if fail_fast:
                break
            continue

        try:
            with DuckDBUnitOfWork(factory) as uow:
                if uow.connection is None:
                    raise RuntimeError("UnitOfWork did not initialize a writer connection.")
                summary = refresh_zigzag_ticker(
                    connection=uow.connection,
                    ticker=ticker,
                )

            result["ZigZagStatus"] = "OK"
            result["ZigZagSourceRows"] = int(summary["source_rows"])
            result["ZigZagUsableRows"] = int(summary["usable_rows"])
            result["ZigZagConfirmedPivots"] = int(summary["confirmed_pivots"])
            result["ZigZagCurrentStatus"] = summary["current_status"]
        except Exception as exc:
            result["ZigZagStatus"] = "FAILED"
            result["PriceMovementStatus"] = "SKIPPED_ZIGZAG_FAILED"
            result["ErrorStage"] = "ZIGZAG"
            result["ErrorMessage"] = f"{type(exc).__name__}: {exc}"

        _progress(
            progress_callback,
            stage="ZIGZAG",
            index=index,
            total=total,
            ticker=ticker,
            status=str(result["ZigZagStatus"]),
        )
        if fail_fast and str(result["ZigZagStatus"]).startswith("FAILED"):
            break

    # Stage 2: Price Movement only after committed ZigZag stage.
    for index, ticker in enumerate(tickers, start=1):
        result = results[ticker]
        if result["ZigZagStatus"] != "OK":
            continue

        try:
            swing_count = _count_zigzag_swings(factory, ticker)
            result["ZigZagSwingCount"] = swing_count

            if swing_count <= 0:
                # Deterministically remove stale downstream rows from older runs.
                with DuckDBUnitOfWork(factory) as uow:
                    if uow.connection is None:
                        raise RuntimeError(
                            "UnitOfWork did not initialize a writer connection."
                        )
                    clear_price_movement_ticker(
                        connection=uow.connection,
                        ticker=ticker,
                        config_code=PRICE_MOVEMENT_CONFIG_CODE,
                    )
                result["PriceMovementStatus"] = "SKIPPED_NO_CONFIRMED_SWING"
                result["PriceMovementSwingCount"] = 0
            else:
                with DuckDBUnitOfWork(factory) as uow:
                    if uow.connection is None:
                        raise RuntimeError(
                            "UnitOfWork did not initialize a writer connection."
                        )
                    summary = refresh_price_movement_ticker(
                        connection=uow.connection,
                        ticker=ticker,
                        config_code=PRICE_MOVEMENT_CONFIG_CODE,
                    )

                result["PriceMovementStatus"] = "OK"
                result["PriceMovementSwingCount"] = int(
                    summary["confirmed_movement_swings"]
                )
                result["MovementProfileCharacter"] = summary["profile_character"]
        except Exception as exc:
            result["PriceMovementStatus"] = "FAILED"
            result["ErrorStage"] = "PRICE_MOVEMENT"
            result["ErrorMessage"] = f"{type(exc).__name__}: {exc}"

        _progress(
            progress_callback,
            stage="PRICE_MOVEMENT",
            index=index,
            total=total,
            ticker=ticker,
            status=str(result["PriceMovementStatus"]),
        )
        if fail_fast and result["PriceMovementStatus"] == "FAILED":
            break

    ordered_results = [results[ticker] for ticker in tickers]
    zigzag_ok = sum(row["ZigZagStatus"] == "OK" for row in ordered_results)
    zigzag_failed = sum(
        str(row["ZigZagStatus"]).startswith("FAILED") for row in ordered_results
    )
    price_ok = sum(row["PriceMovementStatus"] == "OK" for row in ordered_results)
    price_skipped_no_swing = sum(
        row["PriceMovementStatus"] == "SKIPPED_NO_CONFIRMED_SWING"
        for row in ordered_results
    )
    price_failed = sum(
        row["PriceMovementStatus"] == "FAILED" for row in ordered_results
    )

    return {
        "active_ticker_count": len(tickers),
        "zigzag_ok": zigzag_ok,
        "zigzag_failed": zigzag_failed,
        "price_movement_ok": price_ok,
        "price_movement_skipped_no_confirmed_swing": price_skipped_no_swing,
        "price_movement_failed": price_failed,
        "failure_count": zigzag_failed + price_failed,
        "elapsed_seconds": round(perf_counter() - started, 6),
        "results": ordered_results,
    }
