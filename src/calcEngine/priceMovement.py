from __future__ import annotations

from time import perf_counter

from cherrystock.domain.analytics.price_movement.engine import calculate_price_movement
from cherrystock.infrastructure.database.repositories.price_movement_repository import (
    PriceMovementRepository,
)


MVP_TICKER = "MWG"
MVP_CONFIG_CODE = "PM_ZZ_D_V2"


def refresh_price_movement_ticker(
    *,
    connection,
    ticker: str,
    config_code: str = MVP_CONFIG_CODE,
    repository: PriceMovementRepository | None = None,
) -> dict[str, object]:
    resolved_ticker = ticker.strip().upper()
    if not resolved_ticker:
        raise ValueError("ticker must not be empty.")

    resolved_repository = repository or PriceMovementRepository(connection)
    config = resolved_repository.load_config(config_code)

    zigzag_swings = resolved_repository.load_zigzag_swings(
        ticker=resolved_ticker,
        zigzag_config_code=config.zigzag_config_code,
    )
    if zigzag_swings.empty:
        raise RuntimeError(
            f"No confirmed ZigZag swings for {resolved_ticker} "
            f"config={config.zigzag_config_code}."
        )

    ohlc = resolved_repository.load_ohlc(ticker=resolved_ticker)
    if ohlc.empty:
        raise RuntimeError(f"No daily OHLC source for {resolved_ticker}.")

    started = perf_counter()
    swings, profile = calculate_price_movement(
        zigzag_swings,
        ohlc,
        config=config,
    )
    calculation_seconds = perf_counter() - started

    persisted = resolved_repository.replace_ticker(
        price_movement_config_id=config.config_id,
        ticker=resolved_ticker,
        swings=swings,
        profile=profile,
    )

    zigzag_config_id = int(zigzag_swings.iloc[0]["ConfigId"])
    return {
        "status": "OK",
        "ticker": resolved_ticker,
        "price_movement_config_id": config.config_id,
        "price_movement_config_code": config.config_code,
        "zigzag_config_id": zigzag_config_id,
        "zigzag_config_code": config.zigzag_config_code,
        "source_ohlc_rows": len(ohlc),
        "source_zigzag_swings": len(zigzag_swings),
        "confirmed_movement_swings": len(swings),
        "profile_character": (
            profile.movement_character if profile is not None else None
        ),
        "profile_as_of": (
            profile.as_of_confirmed_at_date if profile is not None else None
        ),
        "calculation_seconds": round(calculation_seconds, 6),
        **persisted,
    }


def clear_price_movement_ticker(
    *,
    connection,
    ticker: str,
    config_code: str = MVP_CONFIG_CODE,
    repository: PriceMovementRepository | None = None,
) -> dict[str, object]:
    """Remove stale Price Movement rows when upstream has no confirmed ZigZag swing."""

    resolved_ticker = ticker.strip().upper()
    if not resolved_ticker:
        raise ValueError("ticker must not be empty.")

    resolved_repository = repository or PriceMovementRepository(connection)
    config = resolved_repository.load_config(config_code)
    persisted = resolved_repository.replace_ticker(
        price_movement_config_id=config.config_id,
        ticker=resolved_ticker,
        swings=[],
        profile=None,
    )
    return {
        "status": "CLEARED",
        "ticker": resolved_ticker,
        "price_movement_config_id": config.config_id,
        "price_movement_config_code": config.config_code,
        "zigzag_config_code": config.zigzag_config_code,
        **persisted,
    }


def refresh_price_movement_mwg(
    *,
    connection,
    repository: PriceMovementRepository | None = None,
) -> dict[str, object]:
    return refresh_price_movement_ticker(
        connection=connection,
        ticker=MVP_TICKER,
        config_code=MVP_CONFIG_CODE,
        repository=repository,
    )
