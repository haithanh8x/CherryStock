from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd

from cherrystock.config.settings import settings
from cherrystock.domain.analytics.price_movement.runtime import (
    calculate_ticker_movement_fast,
)
from cherrystock.domain.analytics.price_movement.source_quality import (
    inspect_price_source_quality,
)
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory
from cherrystock.infrastructure.database.repositories.price_movement_repository import (
    PriceMovementRepository,
)
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork


MARKET_DATA_VIEW = '"CherryMon"."main"."vw_Ticker_OHLC_D"'
INDICATOR_VALUE_VIEW = '"CherryMon"."main"."vw_Ticker_indicators"'
INDICATOR_CONFIG_VIEW = '"CherryMon"."main"."vw_Indicator_config"'
TICKER_TABLE = '"CherryMon"."main"."raw_lstTicker"'


def _normalize_tickers(tickers: Iterable[str] | None) -> list[str]:
    return sorted(
        {str(value).strip().upper() for value in (tickers or []) if str(value).strip()}
    )


def load_active_tickers(connection, tickers: Iterable[str] | None = None) -> list[str]:
    requested = _normalize_tickers(tickers)
    params: list[object] = []
    extra = ""
    if requested:
        placeholders = ", ".join("?" for _ in requested)
        extra = f" AND Ticker IN ({placeholders})"
        params.extend(requested)
    rows = connection.execute(
        f"""
        SELECT Ticker
        FROM {TICKER_TABLE}
        WHERE Status = 'Y'
          {extra}
        ORDER BY Ticker
        """,
        params,
    ).fetchall()
    return [str(row[0]) for row in rows]


def load_price_movement_source(
    connection,
    *,
    tickers: Iterable[str],
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    normalized = _normalize_tickers(tickers)
    if not normalized:
        return pd.DataFrame(
            columns=["Ticker", "Date", "Open", "High", "Low", "Close", "ATR"]
        )

    placeholders = ", ".join("?" for _ in normalized)
    params: list[object] = list(normalized)
    date_filters: list[str] = []
    if start_date is not None:
        date_filters.append("AND e.Date >= ?")
        params.append(start_date)
    if end_date is not None:
        date_filters.append("AND e.Date <= ?")
        params.append(end_date)

    frame = connection.execute(
        f"""
        WITH atr_config AS (
            SELECT ConfigId, ComponentCode
            FROM (
                SELECT
                    ConfigId,
                    ComponentCode,
                    ROW_NUMBER() OVER (
                        ORDER BY
                            CASE WHEN ConfigCode = 'ATR14_D' THEN 0 ELSE 1 END,
                            ConfigId DESC
                    ) AS rn
                FROM {INDICATOR_CONFIG_VIEW}
                WHERE IndicatorCode = 'ATR'
                  AND Timeframe = 'D'
                  AND ComponentCode = 'VALUE'
                  AND ConfigIsEnabled = TRUE
                  AND IndicatorIsActive = TRUE
                  AND ComponentIsActive = TRUE
            ) AS ranked
            WHERE rn = 1
        ),
        atr_values AS (
            SELECT
                v.Ticker,
                v.Date,
                v.Value AS ATR
            FROM {INDICATOR_VALUE_VIEW} AS v
            INNER JOIN atr_config AS cfg
                ON cfg.ConfigId = v.ConfigId
               AND cfg.ComponentCode = v.ComponentCode
        )
        SELECT
            e.Ticker,
            e.Date,
            e.Open,
            e.High,
            e.Low,
            e.Close,
            a.ATR
        FROM {MARKET_DATA_VIEW} AS e
        LEFT JOIN atr_values AS a
            ON a.Ticker = e.Ticker
           AND a.Date = e.Date
        WHERE e.Ticker IN ({placeholders})
          {' '.join(date_filters)}
        ORDER BY e.Ticker, e.Date
        """,
        params,
    ).df()
    if not frame.empty:
        frame["Date"] = pd.to_datetime(frame["Date"])
    return frame


def _refresh_with_connection(
    *,
    connection,
    repository: PriceMovementRepository,
    from_last_day: int | None,
    tickers: Iterable[str] | None,
    end_date: date | None,
    mode: str,
) -> dict[str, object]:
    normalized_mode = mode.strip().lower()
    if normalized_mode not in {"incremental", "full"}:
        raise ValueError("mode must be 'incremental' or 'full'.")

    active_tickers = load_active_tickers(connection, tickers)
    if not active_tickers:
        return {
            "status": "SKIPPED",
            "reason": "no_active_tickers",
            "swing_rows_upserted": 0,
            "daily_rows_upserted": 0,
            "tickers_processed": 0,
        }

    config = repository.load_enabled_config(as_of_date=end_date or date.today())
    full_requested = normalized_mode == "full" or from_last_day is None

    prior_map = repository.load_confirmed_swings(
        config_id=config.config_id,
        tickers=active_tickers,
    )
    latest_dates = (
        {}
        if full_requested
        else repository.load_latest_daily_dates(
            config_id=config.config_id,
            tickers=active_tickers,
        )
    )
    seed_map = (
        {}
        if full_requested
        else repository.load_latest_daily_states(
            config_id=config.config_id,
            tickers=active_tickers,
        )
    )

    if full_requested:
        rebuild_tickers = set(active_tickers)
        incremental_tickers: set[str] = set()
        source_start = None
    else:
        rebuild_tickers = {
            ticker
            for ticker in active_tickers
            if ticker not in latest_dates or ticker not in seed_map
        }
        incremental_tickers = set(active_tickers) - rebuild_tickers
        source_start = None
        if not rebuild_tickers and incremental_tickers:
            source_start = min(
                seed_map[ticker].current_swing_start_date
                for ticker in incremental_tickers
            )

    source = load_price_movement_source(
        connection,
        tickers=active_tickers,
        start_date=source_start,
        end_date=end_date,
    )
    if source.empty:
        return {
            "status": "SKIPPED",
            "reason": "no_source_rows",
            "config_id": config.config_id,
            "swing_rows_upserted": 0,
            "daily_rows_upserted": 0,
            "tickers_processed": 0,
        }

    incremental_swing_records: list[dict[str, object]] = []
    incremental_daily_records: list[dict[str, object]] = []
    rebuild_swing_records: list[dict[str, object]] = []
    rebuild_daily_records: list[dict[str, object]] = []
    processed = 0

    source_rows = 0
    invalid_ohlc_rows = 0
    invalid_calculation_rows = 0
    open_only_invalid_rows = 0
    degraded_tickers = 0
    tickers_without_usable_price_rows = 0

    for ticker in active_tickers:
        ticker_frame = source.loc[source["Ticker"] == ticker].copy()
        if ticker_frame.empty:
            continue

        source_quality = inspect_price_source_quality(ticker_frame)
        source_rows += source_quality.source_rows
        invalid_ohlc_rows += source_quality.invalid_ohlc_rows
        invalid_calculation_rows += source_quality.invalid_calculation_rows
        open_only_invalid_rows += source_quality.open_only_invalid_rows
        if source_quality.degraded:
            degraded_tickers += 1
        if source_quality.usable_rows == 0:
            tickers_without_usable_price_rows += 1

        if ticker in rebuild_tickers:
            events, daily = calculate_ticker_movement_fast(
                ticker_frame,
                ticker=ticker,
                config=config,
                prior_swings=[],
                seed_state=None,
            )
            rebuild_swing_records.extend(event.to_record() for event in events)
            rebuild_daily_records.extend(daily)
        else:
            seed = seed_map[ticker]
            events, daily = calculate_ticker_movement_fast(
                ticker_frame,
                ticker=ticker,
                config=config,
                prior_swings=prior_map.get(ticker, []),
                seed_state=seed,
            )
            incremental_swing_records.extend(event.to_record() for event in events)
            incremental_daily_records.extend(daily)
        processed += 1

    swing_count = 0
    daily_count = 0
    if rebuild_tickers:
        rebuild_swing_df = pd.DataFrame(rebuild_swing_records)
        rebuild_daily_df = pd.DataFrame(rebuild_daily_records)
        s_count, d_count = repository.replace_checkpoint(
            config_id=config.config_id,
            tickers=sorted(rebuild_tickers),
            swing_rows=rebuild_swing_df,
            daily_rows=rebuild_daily_df,
            full_replace=True,
        )
        swing_count += s_count
        daily_count += d_count

    if incremental_tickers:
        incremental_swing_df = pd.DataFrame(incremental_swing_records)
        incremental_daily_df = pd.DataFrame(incremental_daily_records)
        s_count, d_count = repository.replace_checkpoint(
            config_id=config.config_id,
            tickers=sorted(incremental_tickers),
            swing_rows=incremental_swing_df,
            daily_rows=incremental_daily_df,
            full_replace=False,
        )
        swing_count += s_count
        daily_count += d_count

    return {
        "status": "OK",
        "config_id": config.config_id,
        "model_code": config.model_code,
        "model_version": config.model_version,
        "mode": "full" if full_requested else "incremental",
        "tickers_processed": processed,
        "tickers_rebuilt": len(rebuild_tickers),
        "tickers_incremental": len(incremental_tickers),
        "swing_rows_upserted": int(swing_count),
        "daily_rows_upserted": int(daily_count),
        "source_quality_status": "PARTIAL" if degraded_tickers else "OK",
        "source_rows": int(source_rows),
        "invalid_ohlc_rows": int(invalid_ohlc_rows),
        "invalid_calculation_rows_dropped": int(invalid_calculation_rows),
        "open_only_invalid_rows_retained": int(open_only_invalid_rows),
        "degraded_tickers": int(degraded_tickers),
        "tickers_without_usable_price_rows": int(tickers_without_usable_price_rows),
    }


def refresh_price_movement_character(
    from_last_day: int | None = None,
    *,
    tickers: Iterable[str] | None = None,
    end_date: date | None = None,
    mode: str = "incremental",
    connection=None,
    repository: PriceMovementRepository | None = None,
) -> dict[str, object]:
    """Refresh Price Movement Character.

    `from_last_day=None` or `mode="full"` performs a deterministic full rebuild
    for the requested active tickers. Incremental mode resumes from the latest
    persisted point-in-time state and appends only newly knowable dates/events.
    """
    if connection is not None:
        resolved_repository = repository or PriceMovementRepository(connection)
        return _refresh_with_connection(
            connection=connection,
            repository=resolved_repository,
            from_last_day=from_last_day,
            tickers=tickers,
            end_date=end_date,
            mode=mode,
        )

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None or uow.price_movement is None:
            raise RuntimeError("UnitOfWork did not initialize Price Movement dependencies.")
        return _refresh_with_connection(
            connection=uow.connection,
            repository=uow.price_movement,
            from_last_day=from_last_day,
            tickers=tickers,
            end_date=end_date,
            mode=mode,
        )
