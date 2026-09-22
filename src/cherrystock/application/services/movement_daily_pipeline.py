from __future__ import annotations

from datetime import date
from time import perf_counter
from typing import Callable, Iterable

from calcEngine.priceMovement import (
    MVP_CONFIG_CODE as PRICE_MOVEMENT_CONFIG_CODE,
    clear_price_movement_ticker,
    refresh_price_movement_ticker,
)
from calcEngine.zigzag import refresh_zigzag_ticker
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork


ZIGZAG_CONFIG_CODE = "ZZ_D_5_MVP"


def _normalize_tickers(values: Iterable[str] | None) -> set[str] | None:
    if values is None:
        return None
    normalized = {
        value.strip().upper()
        for value in values
        if value is not None and value.strip()
    }
    return normalized or None


class MovementDailyPipelineService:
    """Daily ticker-level incremental refresh for ZigZag and Price Movement.

    Incremental selection is date-based at ticker level. Each selected ticker is
    rebuilt deterministically from full daily OHLC so daily output remains exactly
    compatible with the validated initial-load path.
    """

    def __init__(
        self,
        *,
        connection_factory,
        refresh_zigzag: Callable[..., dict[str, object]] = refresh_zigzag_ticker,
        refresh_price_movement: Callable[..., dict[str, object]] = refresh_price_movement_ticker,
        clear_price_movement: Callable[..., dict[str, object]] = clear_price_movement_ticker,
        unit_of_work_cls= DuckDBUnitOfWork,
    ) -> None:
        self._factory = connection_factory
        self._refresh_zigzag = refresh_zigzag
        self._refresh_price_movement = refresh_price_movement
        self._clear_price_movement = clear_price_movement
        self._unit_of_work_cls = unit_of_work_cls

    def plan(
        self,
        *,
        requested_tickers: Iterable[str] | None = None,
        force: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, object]]:
        requested = _normalize_tickers(requested_tickers)

        with self._factory.reader() as connection:
            rows = connection.execute(
                """
                WITH active AS (
                    SELECT DISTINCT
                        UPPER(TRIM(CAST(Ticker AS VARCHAR))) AS Ticker
                    FROM "CherryMon"."main"."vw_Ticker_Active"
                    WHERE Ticker IS NOT NULL
                      AND TRIM(CAST(Ticker AS VARCHAR)) <> ''
                ),
                latest_ohlc AS (
                    SELECT
                        Ticker,
                        MAX(Date) AS LatestOHLCDate,
                        COUNT(*) AS OHLCRows
                    FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
                    GROUP BY Ticker
                ),
                current_zigzag AS (
                    SELECT
                        Ticker,
                        AsOfDate AS ZigZagAsOfDate
                    FROM "CherryMon"."main"."vw_Ticker_ZigZag_Current"
                    WHERE ConfigCode = ?
                )
                SELECT
                    a.Ticker,
                    o.LatestOHLCDate,
                    COALESCE(o.OHLCRows, 0) AS OHLCRows,
                    z.ZigZagAsOfDate
                FROM active AS a
                LEFT JOIN latest_ohlc AS o
                    ON o.Ticker = a.Ticker
                LEFT JOIN current_zigzag AS z
                    ON z.Ticker = a.Ticker
                ORDER BY a.Ticker
                """,
                [ZIGZAG_CONFIG_CODE],
            ).fetchall()

        available = {str(row[0]) for row in rows}
        if requested is not None:
            inactive = sorted(requested.difference(available))
            if inactive:
                raise ValueError(
                    "Requested ticker(s) are not present in vw_Ticker_Active: "
                    + ", ".join(inactive)
                )

        planned: list[dict[str, object]] = []
        for ticker_raw, latest_ohlc, ohlc_rows, zigzag_as_of in rows:
            ticker = str(ticker_raw)
            if requested is not None and ticker not in requested:
                continue

            if latest_ohlc is None or int(ohlc_rows) <= 0:
                state = "NO_OHLC"
                selected = False
            elif zigzag_as_of is not None and latest_ohlc < zigzag_as_of:
                state = "SOURCE_REWIND"
                selected = False
            elif force:
                state = "FORCED"
                selected = True
            elif zigzag_as_of is None:
                state = "MISSING_ZIGZAG"
                selected = True
            elif latest_ohlc > zigzag_as_of:
                state = "STALE"
                selected = True
            else:
                state = "UP_TO_DATE"
                selected = False

            planned.append(
                {
                    "Ticker": ticker,
                    "LatestOHLCDate": latest_ohlc,
                    "OHLCRows": int(ohlc_rows),
                    "ZigZagAsOfDate": zigzag_as_of,
                    "PlanState": state,
                    "Selected": selected,
                }
            )

        if limit is not None:
            if limit < 1:
                raise ValueError("limit must be >= 1.")
            selected_count = 0
            limited: list[dict[str, object]] = []
            for row in planned:
                if bool(row["Selected"]):
                    if selected_count >= limit:
                        row = dict(row)
                        row["Selected"] = False
                        row["PlanState"] = "LIMITED_OUT"
                    else:
                        selected_count += 1
                limited.append(row)
            planned = limited

        return planned

    def _load_price_movement_state(self, ticker: str) -> dict[str, object]:
        with self._factory.reader() as connection:
            row = connection.execute(
                """
                WITH zz AS (
                    SELECT
                        COUNT(*) AS SwingCount,
                        MAX(SwingSeq) AS LastSwingSeq,
                        MAX(ConfirmedAtDate) AS LastConfirmedAtDate
                    FROM "CherryMon"."main"."vw_Ticker_ZigZag_Swings"
                    WHERE Ticker = ?
                      AND ConfigCode = ?
                ),
                pm AS (
                    SELECT
                        COUNT(*) AS SwingCount,
                        MAX(SwingSeq) AS LastSwingSeq,
                        MAX(ConfirmedAtDate) AS LastConfirmedAtDate
                    FROM "CherryMon"."main"."vw_Ticker_Price_Movement_Swings"
                    WHERE Ticker = ?
                      AND PriceMovementConfigCode = ?
                      AND ZigZagConfigCode = ?
                ),
                profile AS (
                    SELECT
                        COUNT(*) AS ProfileRows,
                        MAX(LastSwingSeq) AS LastSwingSeq,
                        MAX(AsOfConfirmedAtDate) AS AsOfConfirmedAtDate
                    FROM "CherryMon"."main"."vw_Ticker_Movement_Profile"
                    WHERE Ticker = ?
                      AND PriceMovementConfigCode = ?
                      AND ZigZagConfigCode = ?
                )
                SELECT
                    zz.SwingCount,
                    zz.LastSwingSeq,
                    zz.LastConfirmedAtDate,
                    pm.SwingCount,
                    pm.LastSwingSeq,
                    pm.LastConfirmedAtDate,
                    profile.ProfileRows,
                    profile.LastSwingSeq,
                    profile.AsOfConfirmedAtDate
                FROM zz, pm, profile
                """,
                [
                    ticker,
                    ZIGZAG_CONFIG_CODE,
                    ticker,
                    PRICE_MOVEMENT_CONFIG_CODE,
                    ZIGZAG_CONFIG_CODE,
                    ticker,
                    PRICE_MOVEMENT_CONFIG_CODE,
                    ZIGZAG_CONFIG_CODE,
                ],
            ).fetchone()

        if row is None:
            raise RuntimeError(f"Unable to resolve Price Movement state for {ticker}.")

        return {
            "zigzag_swing_count": int(row[0] or 0),
            "zigzag_last_swing_seq": row[1],
            "zigzag_last_confirmed_at": row[2],
            "price_movement_swing_count": int(row[3] or 0),
            "price_movement_last_swing_seq": row[4],
            "price_movement_last_confirmed_at": row[5],
            "profile_rows": int(row[6] or 0),
            "profile_last_swing_seq": row[7],
            "profile_as_of_confirmed_at": row[8],
        }

    @staticmethod
    def _price_movement_needs_refresh(state: dict[str, object]) -> bool:
        if int(state["zigzag_swing_count"]) <= 0:
            return False
        return (
            int(state["price_movement_swing_count"]) != int(state["zigzag_swing_count"])
            or state["price_movement_last_swing_seq"] != state["zigzag_last_swing_seq"]
            or state["price_movement_last_confirmed_at"] != state["zigzag_last_confirmed_at"]
            or int(state["profile_rows"]) != 1
            or state["profile_last_swing_seq"] != state["zigzag_last_swing_seq"]
            or state["profile_as_of_confirmed_at"] != state["zigzag_last_confirmed_at"]
        )

    def run(
        self,
        *,
        requested_tickers: Iterable[str] | None = None,
        force: bool = False,
        limit: int | None = None,
        progress_callback: Callable[[int, int, str, str], None] | None = None,
    ) -> dict[str, object]:
        started = perf_counter()
        plan = self.plan(
            requested_tickers=requested_tickers,
            force=force,
            limit=limit,
        )

        results: list[dict[str, object]] = []
        hard_preflight = [
            row for row in plan if row["PlanState"] in {"NO_OHLC", "SOURCE_REWIND"}
        ]

        for row in hard_preflight:
            results.append(
                {
                    **row,
                    "ZigZagStatus": "FAILED_PRECHECK",
                    "PriceMovementStatus": "SKIPPED_ZIGZAG_FAILED",
                    "ErrorStage": "PRECHECK",
                    "ErrorMessage": (
                        "Active ticker has no OHLC."
                        if row["PlanState"] == "NO_OHLC"
                        else "Latest OHLC date is behind persisted ZigZag AsOfDate."
                    ),
                }
            )

        selected = [row for row in plan if bool(row["Selected"])]
        total = len(selected)

        for index, row in enumerate(selected, start=1):
            ticker = str(row["Ticker"])
            result = {
                **row,
                "ZigZagStatus": "PENDING",
                "PriceMovementStatus": "PENDING",
                "ZigZagConfirmedPivots": None,
                "ZigZagCurrentStatus": None,
                "PriceMovementSwingCount": None,
                "MovementProfileCharacter": None,
                "ErrorStage": None,
                "ErrorMessage": None,
            }

            try:
                with self._unit_of_work_cls(self._factory) as uow:
                    if uow.connection is None:
                        raise RuntimeError(
                            "UnitOfWork did not initialize a writer connection."
                        )
                    zigzag_summary = self._refresh_zigzag(
                        connection=uow.connection,
                        ticker=ticker,
                    )

                result["ZigZagStatus"] = "OK"
                result["ZigZagConfirmedPivots"] = int(
                    zigzag_summary["confirmed_pivots"]
                )
                result["ZigZagCurrentStatus"] = zigzag_summary["current_status"]
            except Exception as exc:
                result["ZigZagStatus"] = "FAILED"
                result["PriceMovementStatus"] = "SKIPPED_ZIGZAG_FAILED"
                result["ErrorStage"] = "ZIGZAG"
                result["ErrorMessage"] = f"{type(exc).__name__}: {exc}"
                results.append(result)
                if progress_callback is not None:
                    progress_callback(index, total, ticker, "FAILED_ZIGZAG")
                continue

            try:
                state = self._load_price_movement_state(ticker)
                zigzag_swing_count = int(state["zigzag_swing_count"])

                if zigzag_swing_count <= 0:
                    if (
                        int(state["price_movement_swing_count"]) > 0
                        or int(state["profile_rows"]) > 0
                    ):
                        with self._unit_of_work_cls(self._factory) as uow:
                            if uow.connection is None:
                                raise RuntimeError(
                                    "UnitOfWork did not initialize a writer connection."
                                )
                            self._clear_price_movement(
                                connection=uow.connection,
                                ticker=ticker,
                                config_code=PRICE_MOVEMENT_CONFIG_CODE,
                            )
                        result["PriceMovementStatus"] = "CLEARED_NO_CONFIRMED_SWING"
                    else:
                        result["PriceMovementStatus"] = "SKIPPED_NO_CONFIRMED_SWING"
                    result["PriceMovementSwingCount"] = 0
                elif self._price_movement_needs_refresh(state):
                    with self._unit_of_work_cls(self._factory) as uow:
                        if uow.connection is None:
                            raise RuntimeError(
                                "UnitOfWork did not initialize a writer connection."
                            )
                        pm_summary = self._refresh_price_movement(
                            connection=uow.connection,
                            ticker=ticker,
                            config_code=PRICE_MOVEMENT_CONFIG_CODE,
                        )
                    result["PriceMovementStatus"] = "REFRESHED"
                    result["PriceMovementSwingCount"] = int(
                        pm_summary["confirmed_movement_swings"]
                    )
                    result["MovementProfileCharacter"] = pm_summary[
                        "profile_character"
                    ]
                else:
                    result["PriceMovementStatus"] = "UP_TO_DATE"
                    result["PriceMovementSwingCount"] = zigzag_swing_count
            except Exception as exc:
                result["PriceMovementStatus"] = "FAILED"
                result["ErrorStage"] = "PRICE_MOVEMENT"
                result["ErrorMessage"] = f"{type(exc).__name__}: {exc}"

            results.append(result)
            if progress_callback is not None:
                progress_callback(
                    index,
                    total,
                    ticker,
                    (
                        "OK"
                        if result["PriceMovementStatus"] != "FAILED"
                        else "FAILED_PRICE_MOVEMENT"
                    ),
                )

        up_to_date_count = sum(row["PlanState"] == "UP_TO_DATE" for row in plan)
        limited_out_count = sum(row["PlanState"] == "LIMITED_OUT" for row in plan)
        zigzag_refreshed = sum(row.get("ZigZagStatus") == "OK" for row in results)
        zigzag_failed = sum(
            str(row.get("ZigZagStatus", "")).startswith("FAILED") for row in results
        )
        pm_refreshed = sum(
            row.get("PriceMovementStatus") == "REFRESHED" for row in results
        )
        pm_up_to_date = sum(
            row.get("PriceMovementStatus") == "UP_TO_DATE" for row in results
        )
        pm_no_swing = sum(
            row.get("PriceMovementStatus")
            in {"SKIPPED_NO_CONFIRMED_SWING", "CLEARED_NO_CONFIRMED_SWING"}
            for row in results
        )
        pm_failed = sum(
            row.get("PriceMovementStatus") == "FAILED" for row in results
        )

        return {
            "active_ticker_count": len(plan),
            "selected_ticker_count": len(selected),
            "up_to_date_ticker_count": up_to_date_count,
            "limited_out_ticker_count": limited_out_count,
            "preflight_failure_count": len(hard_preflight),
            "zigzag_refreshed": zigzag_refreshed,
            "zigzag_failed": zigzag_failed,
            "price_movement_refreshed": pm_refreshed,
            "price_movement_up_to_date": pm_up_to_date,
            "price_movement_no_confirmed_swing": pm_no_swing,
            "price_movement_failed": pm_failed,
            "failure_count": zigzag_failed + pm_failed,
            "elapsed_seconds": round(perf_counter() - started, 6),
            "results": results,
            "plan": plan,
        }
