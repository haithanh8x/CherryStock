from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402


TICKER = "MWG"
PM_CONFIG_CODE = "PM_ZZ_D_V2"


def _load(connection):
    config = connection.execute(
        """
        SELECT
            ConfigId,
            ZigZagConfigCode,
            ProfileLookbackSwings,
            MinimumProfileSwings
        FROM "CherryMon"."main"."dim_price_movement_config"
        WHERE ConfigCode = ?
          AND IsEnabled = TRUE
        LIMIT 1
        """,
        [PM_CONFIG_CODE],
    ).fetchone()
    if config is None:
        raise RuntimeError(f"Price Movement config {PM_CONFIG_CODE} not found.")

    zigzag_config_code = str(config[1])
    zigzag = connection.execute(
        """
        SELECT
            ConfigId,
            ConfigCode,
            Ticker,
            SwingSeq,
            Direction,
            StartPivotSeq,
            StartDate,
            StartPrice,
            EndPivotSeq,
            EndDate,
            EndPrice,
            ConfirmedAtDate,
            SwingPct
        FROM "CherryMon"."main"."vw_Ticker_ZigZag_Swings"
        WHERE Ticker = ?
          AND ConfigCode = ?
        ORDER BY SwingSeq
        """,
        [TICKER, zigzag_config_code],
    ).df()

    movement = connection.execute(
        """
        SELECT
            PriceMovementConfigId,
            ZigZagConfigId,
            ZigZagConfigCode,
            Ticker,
            SwingSeq,
            Direction,
            StartPivotSeq,
            StartDate,
            StartPrice,
            EndPivotSeq,
            EndDate,
            EndPrice,
            ConfirmedAtDate,
            SwingPct,
            TradingBars,
            CalendarDays,
            VelocityPctPerBar,
            AvgATRPct,
            ATRNormalizedMove,
            PathEfficiency,
            DirectionalPersistenceRate
        FROM "CherryMon"."main"."vw_Ticker_Price_Movement_Swings"
        WHERE Ticker = ?
          AND PriceMovementConfigCode = ?
        ORDER BY SwingSeq
        """,
        [TICKER, PM_CONFIG_CODE],
    ).df()

    profile = connection.execute(
        """
        SELECT
            *
        FROM "CherryMon"."main"."vw_Ticker_Movement_Profile"
        WHERE Ticker = ?
          AND PriceMovementConfigCode = ?
        """,
        [TICKER, PM_CONFIG_CODE],
    ).df()

    ohlc = connection.execute(
        """
        SELECT Date, High, Low, Close
        FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
        WHERE Ticker = ?
        ORDER BY Date
        """,
        [TICKER],
    ).df()

    for frame in (zigzag, movement, profile, ohlc):
        for column in (
            "Date",
            "StartDate",
            "EndDate",
            "ConfirmedAtDate",
            "AsOfConfirmedAtDate",
        ):
            if column in frame.columns:
                frame[column] = pd.to_datetime(frame[column])

    return config, zigzag, movement, profile, ohlc


def validate() -> int:
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    failures: list[str] = []

    with factory.reader() as connection:
        config, zigzag, movement, profile, ohlc = _load(connection)

    if zigzag.empty:
        failures.append("no upstream confirmed ZigZag swings")
    if movement.empty:
        failures.append("no Price Movement swings")

    if len(zigzag) != len(movement):
        failures.append(
            f"row count mismatch: zigzag={len(zigzag)} movement={len(movement)}"
        )

    if not movement.empty:
        if movement.duplicated(
            subset=["PriceMovementConfigId", "ZigZagConfigId", "Ticker", "SwingSeq"]
        ).any():
            failures.append("duplicate Price Movement swing identity")

        if not (movement["EndDate"] < movement["ConfirmedAtDate"]).all():
            failures.append("EndDate must be strictly before ConfirmedAtDate")

        if (movement["TradingBars"] < 1).any():
            failures.append("TradingBars contains value < 1")

        if (
            (movement["PathEfficiency"] < 0)
            | (movement["PathEfficiency"] > 1)
        ).any():
            failures.append("PathEfficiency outside [0,1]")

        if (
            (movement["DirectionalPersistenceRate"] < 0)
            | (movement["DirectionalPersistenceRate"] > 1)
        ).any():
            failures.append("DirectionalPersistenceRate outside [0,1]")

        formula = movement["EndPrice"] / movement["StartPrice"] - 1.0
        if not np.allclose(
            movement["SwingPct"].astype(float),
            formula.astype(float),
            rtol=1e-9,
            atol=1e-9,
        ):
            failures.append("SwingPct formula mismatch")

        velocity = movement["SwingPct"] / movement["TradingBars"]
        if not np.allclose(
            movement["VelocityPctPerBar"].astype(float),
            velocity.astype(float),
            rtol=1e-9,
            atol=1e-9,
        ):
            failures.append("VelocityPctPerBar formula mismatch")

        up_bad = movement.loc[
            (movement["Direction"] == "UP") & (movement["SwingPct"] <= 0)
        ]
        down_bad = movement.loc[
            (movement["Direction"] == "DOWN") & (movement["SwingPct"] >= 0)
        ]
        if not up_bad.empty or not down_bad.empty:
            failures.append("direction/sign mismatch")

        ohlc_dates = pd.to_datetime(ohlc["Date"])
        for row in movement.itertuples(index=False):
            expected_bars = int(
                (
                    (ohlc_dates >= row.StartDate)
                    & (ohlc_dates <= row.EndDate)
                ).sum()
                - 1
            )
            if int(row.TradingBars) != expected_bars:
                failures.append(
                    f"TradingBars mismatch at SwingSeq={int(row.SwingSeq)}: "
                    f"stored={int(row.TradingBars)} expected={expected_bars}"
                )
                break

    if not zigzag.empty and not movement.empty:
        merged = zigzag.merge(
            movement,
            on=["Ticker", "SwingSeq"],
            how="outer",
            suffixes=("_zz", "_pm"),
            indicator=True,
        )
        if (merged["_merge"] != "both").any():
            failures.append("ZigZag/Price Movement identity set mismatch")
        else:
            exact_columns = (
                "Direction",
                "StartPivotSeq",
                "EndPivotSeq",
                "StartDate",
                "EndDate",
                "ConfirmedAtDate",
            )
            for column in exact_columns:
                left = merged[f"{column}_zz"]
                right = merged[f"{column}_pm"]
                if not left.equals(right):
                    failures.append(f"upstream identity mismatch: {column}")
                    break

            for column in ("StartPrice", "EndPrice", "SwingPct"):
                if not np.allclose(
                    merged[f"{column}_zz"].astype(float),
                    merged[f"{column}_pm"].astype(float),
                    rtol=1e-9,
                    atol=1e-9,
                ):
                    failures.append(f"upstream numeric mismatch: {column}")
                    break

    if len(profile) != 1:
        failures.append(f"expected one movement profile row, got {len(profile)}")
    elif not movement.empty:
        p = profile.iloc[0]
        lookback = int(config[2])
        recent = movement.tail(lookback)
        last = recent.iloc[-1]
        if int(p["ConfirmedSwingCount"]) != len(recent):
            failures.append("profile ConfirmedSwingCount mismatch")
        if int(p["LastSwingSeq"]) != int(last["SwingSeq"]):
            failures.append("profile LastSwingSeq mismatch")
        if p["LastSwingDirection"] != last["Direction"]:
            failures.append("profile LastSwingDirection mismatch")
        if not np.isclose(
            float(p["LastSwingPct"]),
            float(last["SwingPct"]),
            rtol=1e-9,
            atol=1e-9,
        ):
            failures.append("profile LastSwingPct mismatch")
        if pd.Timestamp(p["AsOfConfirmedAtDate"]) != pd.Timestamp(
            recent["ConfirmedAtDate"].max()
        ):
            failures.append("profile AsOfConfirmedAtDate mismatch")

        allowed = {
            "INSUFFICIENT_HISTORY",
            "TRENDING_UP",
            "TRENDING_DOWN",
            "RANGE_BOUND",
            "MIXED",
        }
        if str(p["MovementCharacter"]) not in allowed:
            failures.append("unsupported MovementCharacter")

    run_text = (PROJECT_ROOT / "run.py").read_text(encoding="utf-8")
    if "priceMovement" in run_text or "price_movement" in run_text:
        failures.append("run.py unexpectedly contains Price Movement integration")

    print("=== Price Movement V2 MWG validation ===")
    print(f"zigzag_swings:        {len(zigzag)}")
    print(f"movement_swings:      {len(movement)}")
    print(f"profile_rows:         {len(profile)}")
    print(f"structural_errors:    {len(failures)}")

    review_start = pd.Timestamp("2026-07-01")
    review_end = pd.Timestamp("2026-09-30")
    review = movement.loc[
        (movement["EndDate"] >= review_start)
        & (movement["StartDate"] <= review_end),
        [
            "SwingSeq",
            "Direction",
            "StartDate",
            "StartPrice",
            "EndDate",
            "EndPrice",
            "ConfirmedAtDate",
            "SwingPct",
            "TradingBars",
            "VelocityPctPerBar",
            "ATRNormalizedMove",
            "PathEfficiency",
            "DirectionalPersistenceRate",
        ],
    ]

    print("\n--- MWG movement swings Jul-Sep 2026 ---")
    print(review.to_string(index=False) if not review.empty else "(none)")
    print("\n--- MWG movement profile ---")
    print(profile.to_string(index=False) if not profile.empty else "(none)")

    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nSTRUCTURAL VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(validate())
