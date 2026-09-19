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
CONFIG_CODE = "ZZ_D_5_MVP"


def _load(connection):
    pivots = connection.execute(
        """
        SELECT *
        FROM "CherryMon"."main"."vw_Ticker_ZigZag_Pivots"
        WHERE Ticker = ? AND ConfigCode = ?
        ORDER BY PivotSeq
        """,
        [TICKER, CONFIG_CODE],
    ).df()
    swings = connection.execute(
        """
        SELECT *
        FROM "CherryMon"."main"."vw_Ticker_ZigZag_Swings"
        WHERE Ticker = ? AND ConfigCode = ?
        ORDER BY SwingSeq
        """,
        [TICKER, CONFIG_CODE],
    ).df()
    current = connection.execute(
        """
        SELECT *
        FROM "CherryMon"."main"."vw_Ticker_ZigZag_Current"
        WHERE Ticker = ? AND ConfigCode = ?
        """,
        [TICKER, CONFIG_CODE],
    ).df()
    source = connection.execute(
        """
        SELECT Date, High, Low, Close
        FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
        WHERE Ticker = ?
        ORDER BY Date
        """,
        [TICKER],
    ).df()

    for frame in (pivots, swings, current, source):
        for column in ("Date", "PivotDate", "ConfirmedAtDate", "StartDate", "EndDate", "AsOfDate"):
            if column in frame.columns:
                frame[column] = pd.to_datetime(frame[column])

    return pivots, swings, current, source


def validate() -> int:
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    failures: list[str] = []

    with factory.reader() as connection:
        pivots, swings, current, source = _load(connection)

    if pivots.empty:
        failures.append("no confirmed MWG pivots")
    else:
        if pivots.duplicated(subset=["ConfigId", "Ticker", "PivotSeq"]).any():
            failures.append("duplicate pivot primary keys")

        expected_seq = list(range(1, len(pivots) + 1))
        actual_seq = pivots["PivotSeq"].astype(int).tolist()
        if actual_seq != expected_seq:
            failures.append("PivotSeq is not contiguous from 1")

        types = pivots["PivotType"].astype(str).tolist()
        for i in range(1, len(types)):
            if types[i] == types[i - 1]:
                failures.append(f"pivot types do not alternate at seq {i + 1}")
                break

        if (pivots["PivotDate"] >= pivots["ConfirmedAtDate"]).any():
            failures.append("PivotDate must be strictly before ConfirmedAtDate")

        if pivots["PivotDate"].duplicated().any():
            failures.append("multiple confirmed pivots share the same PivotDate")

        confirmations = pivots["ConfirmedAtDate"].tolist()
        if any(confirmations[i] < confirmations[i - 1] for i in range(1, len(confirmations))):
            failures.append("ConfirmedAtDate decreases across PivotSeq")

        source_indexed = source.set_index("Date")
        for i, row in pivots.iterrows():
            pivot_date = row["PivotDate"]
            if pivot_date not in source_indexed.index:
                failures.append(f"pivot seq {int(row['PivotSeq'])} date missing in OHLC")
                continue

            source_row = source_indexed.loc[pivot_date]
            actual_source_price = (
                float(source_row["Low"])
                if row["PivotType"] == "LOW"
                else float(source_row["High"])
            )
            if not np.isclose(float(row["PivotPrice"]), actual_source_price, rtol=1e-9, atol=1e-9):
                failures.append(
                    f"pivot seq {int(row['PivotSeq'])} price does not match OHLC extreme on PivotDate"
                )

            if i == 0 or i == len(pivots) - 1:
                continue

            left_date = pivots.iloc[i - 1]["PivotDate"]
            right_date = pivots.iloc[i + 1]["PivotDate"]
            # Point-in-time contract: only knowledge at confirmation time is
            # valid. Bars after ConfirmedAtDate belong to the next leg and must
            # not influence the expected local extreme, so the window closes at
            # ConfirmedAtDate instead of the next pivot date.
            confirm_date = row["ConfirmedAtDate"]
            window_end = min(right_date, confirm_date)
            # Daily OHLC cannot establish intraday ordering on either neighboring
            # pivot bar. Local-extreme validation therefore uses only bars strictly
            # between adjacent PivotDates. The current pivot itself is inside this
            # interval because confirmed PivotDates must be strictly increasing.
            segment = source.loc[(source["Date"] > left_date) & (source["Date"] < window_end)]
            if segment.empty:
                failures.append(
                    f"empty strict local-extreme window at pivot seq {int(row['PivotSeq'])}"
                )
                continue

            if row["PivotType"] == "LOW":
                expected_price = float(segment["Low"].min())
            else:
                expected_price = float(segment["High"].max())

            if not np.isclose(float(row["PivotPrice"]), expected_price, rtol=1e-9, atol=1e-9):
                failures.append(
                    f"pivot seq {int(row['PivotSeq'])} is not the local {row['PivotType']} "
                    f"between adjacent pivots: stored={row['PivotPrice']} expected={expected_price}"
                )

    if len(current) != 1:
        failures.append(f"expected exactly one current-leg row, got {len(current)}")
    elif not pivots.empty:
        last_type = str(pivots.iloc[-1]["PivotType"])
        expected_direction = "UP" if last_type == "LOW" else "DOWN"
        actual_direction = current.iloc[0]["Direction"]
        if actual_direction != expected_direction:
            failures.append(
                f"current direction mismatch: last pivot={last_type}, direction={actual_direction}"
            )
        if current.iloc[0]["Status"] != "PROVISIONAL":
            failures.append("current row is not PROVISIONAL")

    print("=== ZigZag MWG MVP validation ===")
    print(f"confirmed_pivots: {len(pivots)}")
    print(f"derived_swings:   {len(swings)}")
    print(f"current_rows:     {len(current)}")
    print(f"structural_errors:{len(failures)}")

    review_start = pd.Timestamp("2026-07-01")
    review_end = pd.Timestamp("2026-09-30")
    pivot_window = pivots.loc[
        (pivots["PivotDate"] >= review_start) & (pivots["PivotDate"] <= review_end),
        ["PivotSeq", "PivotType", "PivotDate", "PivotPrice", "ConfirmedAtDate", "ConfirmationPrice"],
    ]
    swing_window = swings.loc[
        (swings["EndDate"] >= review_start) & (swings["StartDate"] <= review_end),
        [
            "SwingSeq",
            "Direction",
            "StartDate",
            "StartPrice",
            "EndDate",
            "EndPrice",
            "ConfirmedAtDate",
            "SwingPct",
        ],
    ]

    print("\n--- MWG pivots Jul-Sep 2026 ---")
    print(pivot_window.to_string(index=False) if not pivot_window.empty else "(none)")
    print("\n--- MWG swings Jul-Sep 2026 ---")
    print(swing_window.to_string(index=False) if not swing_window.empty else "(none)")
    print("\n--- Current leg ---")
    print(current.to_string(index=False) if not current.empty else "(none)")

    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nSTRUCTURAL VALIDATION: PASS")
    print("Visual MWG Jul-Sep 2026 review is still required before expanding scope.")
    return 0


if __name__ == "__main__":
    raise SystemExit(validate())
