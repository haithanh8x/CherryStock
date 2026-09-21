from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Orchestrator.active_ticker_movement_initload import (  # noqa: E402
    PRICE_MOVEMENT_CONFIG_CODE,
    ZIGZAG_CONFIG_CODE,
    load_active_tickers,
)
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402


def _counts(connection, sql: str, params: list[object] | None = None) -> pd.DataFrame:
    frame = connection.execute(sql, params or []).df()
    if frame.empty:
        return pd.DataFrame(columns=["Ticker", "RowCount"])
    frame["Ticker"] = frame["Ticker"].astype(str).str.strip().str.upper()
    frame["RowCount"] = frame["RowCount"].astype(int)
    return frame


def validate(*, evidence_dir: Path | None = None) -> int:
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    failures: list[str] = []

    with factory.reader() as connection:
        active = load_active_tickers(connection)
        active_frame = pd.DataFrame({"Ticker": active})

        ohlc = _counts(
            connection,
            """
            SELECT Ticker, COUNT(*) AS RowCount
            FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
            GROUP BY Ticker
            """,
        )
        current = _counts(
            connection,
            """
            SELECT Ticker, COUNT(*) AS RowCount
            FROM "CherryMon"."main"."vw_Ticker_ZigZag_Current"
            WHERE ConfigCode = ?
            GROUP BY Ticker
            """,
            [ZIGZAG_CONFIG_CODE],
        )
        pivots = _counts(
            connection,
            """
            SELECT Ticker, COUNT(*) AS RowCount
            FROM "CherryMon"."main"."vw_Ticker_ZigZag_Pivots"
            WHERE ConfigCode = ?
            GROUP BY Ticker
            """,
            [ZIGZAG_CONFIG_CODE],
        )
        zz_swings = _counts(
            connection,
            """
            SELECT Ticker, COUNT(*) AS RowCount
            FROM "CherryMon"."main"."vw_Ticker_ZigZag_Swings"
            WHERE ConfigCode = ?
            GROUP BY Ticker
            """,
            [ZIGZAG_CONFIG_CODE],
        )
        pm_swings = _counts(
            connection,
            """
            SELECT Ticker, COUNT(*) AS RowCount
            FROM "CherryMon"."main"."vw_Ticker_Price_Movement_Swings"
            WHERE PriceMovementConfigCode = ?
              AND ZigZagConfigCode = ?
            GROUP BY Ticker
            """,
            [PRICE_MOVEMENT_CONFIG_CODE, ZIGZAG_CONFIG_CODE],
        )
        profiles = _counts(
            connection,
            """
            SELECT Ticker, COUNT(*) AS RowCount
            FROM "CherryMon"."main"."vw_Ticker_Movement_Profile"
            WHERE PriceMovementConfigCode = ?
              AND ZigZagConfigCode = ?
            GROUP BY Ticker
            """,
            [PRICE_MOVEMENT_CONFIG_CODE, ZIGZAG_CONFIG_CODE],
        )

    if not active:
        failures.append("vw_Ticker_Active returned no tickers")

    coverage = active_frame.copy()
    for frame, column in (
        (ohlc, "OHLCRows"),
        (current, "ZigZagCurrentRows"),
        (pivots, "ZigZagPivotRows"),
        (zz_swings, "ZigZagSwingRows"),
        (pm_swings, "PriceMovementSwingRows"),
        (profiles, "MovementProfileRows"),
    ):
        renamed = frame.rename(columns={"RowCount": column})
        coverage = coverage.merge(renamed, on="Ticker", how="left")
        coverage[column] = coverage[column].fillna(0).astype(int)

    coverage["ValidationStatus"] = "PASS"
    coverage["ValidationReason"] = ""

    no_ohlc = coverage["OHLCRows"] <= 0
    if no_ohlc.any():
        tickers = coverage.loc[no_ohlc, "Ticker"].tolist()
        failures.append(
            f"active tickers without OHLC: {len(tickers)} ({', '.join(tickers[:20])})"
        )
        coverage.loc[no_ohlc, "ValidationStatus"] = "FAIL"
        coverage.loc[no_ohlc, "ValidationReason"] = "NO_OHLC"

    missing_current = (coverage["OHLCRows"] > 0) & (
        coverage["ZigZagCurrentRows"] != 1
    )
    if missing_current.any():
        tickers = coverage.loc[missing_current, "Ticker"].tolist()
        failures.append(
            "active OHLC tickers without exactly one ZigZag current row: "
            f"{len(tickers)} ({', '.join(tickers[:20])})"
        )
        coverage.loc[missing_current, "ValidationStatus"] = "FAIL"
        coverage.loc[missing_current, "ValidationReason"] = (
            coverage.loc[missing_current, "ValidationReason"]
            .astype(str)
            .str.cat(pd.Series(["ZIGZAG_CURRENT_COUNT"] * missing_current.sum(),
                              index=coverage.index[missing_current]), sep=";")
            .str.strip(";")
        )

    parity_bad = (coverage["ZigZagSwingRows"] > 0) & (
        coverage["PriceMovementSwingRows"] != coverage["ZigZagSwingRows"]
    )
    if parity_bad.any():
        tickers = coverage.loc[parity_bad, "Ticker"].tolist()
        failures.append(
            "ZigZag/Price Movement swing-count mismatch: "
            f"{len(tickers)} ({', '.join(tickers[:20])})"
        )
        coverage.loc[parity_bad, "ValidationStatus"] = "FAIL"
        coverage.loc[parity_bad, "ValidationReason"] = (
            coverage.loc[parity_bad, "ValidationReason"]
            .astype(str)
            .str.cat(pd.Series(["SWING_COUNT_MISMATCH"] * parity_bad.sum(),
                              index=coverage.index[parity_bad]), sep=";")
            .str.strip(";")
        )

    profile_bad = (coverage["ZigZagSwingRows"] > 0) & (
        coverage["MovementProfileRows"] != 1
    )
    if profile_bad.any():
        tickers = coverage.loc[profile_bad, "Ticker"].tolist()
        failures.append(
            "eligible tickers without exactly one movement profile: "
            f"{len(tickers)} ({', '.join(tickers[:20])})"
        )
        coverage.loc[profile_bad, "ValidationStatus"] = "FAIL"
        coverage.loc[profile_bad, "ValidationReason"] = (
            coverage.loc[profile_bad, "ValidationReason"]
            .astype(str)
            .str.cat(pd.Series(["PROFILE_COUNT_MISMATCH"] * profile_bad.sum(),
                              index=coverage.index[profile_bad]), sep=";")
            .str.strip(";")
        )

    stale_downstream = (coverage["ZigZagSwingRows"] == 0) & (
        (coverage["PriceMovementSwingRows"] != 0)
        | (coverage["MovementProfileRows"] != 0)
    )
    if stale_downstream.any():
        tickers = coverage.loc[stale_downstream, "Ticker"].tolist()
        failures.append(
            "tickers without ZigZag swings retain stale Price Movement rows: "
            f"{len(tickers)} ({', '.join(tickers[:20])})"
        )
        coverage.loc[stale_downstream, "ValidationStatus"] = "FAIL"
        coverage.loc[stale_downstream, "ValidationReason"] = (
            coverage.loc[stale_downstream, "ValidationReason"]
            .astype(str)
            .str.cat(pd.Series(["STALE_DOWNSTREAM"] * stale_downstream.sum(),
                              index=coverage.index[stale_downstream]), sep=";")
            .str.strip(";")
        )

    run_text = (PROJECT_ROOT / "run.py").read_text(encoding="utf-8")
    run_py_unchanged = (
        "active_ticker_movement_initload" not in run_text
        and "init_reload_zigzag_price_movement_active" not in run_text
    )
    if not run_py_unchanged:
        failures.append("run.py unexpectedly contains REQ-0033 active movement integration")

    summary = {
        "active_ticker_count": int(len(coverage)),
        "active_with_ohlc": int((coverage["OHLCRows"] > 0).sum()),
        "zigzag_current_covered": int((coverage["ZigZagCurrentRows"] == 1).sum()),
        "zigzag_with_confirmed_swing": int((coverage["ZigZagSwingRows"] > 0).sum()),
        "price_movement_profile_covered": int(
            (coverage["MovementProfileRows"] == 1).sum()
        ),
        "run_py_unchanged": bool(run_py_unchanged),
        "validation_failures": int(len(failures)),
    }

    print("=== Active Ticker Movement Validation ===")
    for key, value in summary.items():
        print(f"{key}: {value}")

    failed_rows = coverage.loc[coverage["ValidationStatus"] == "FAIL"]
    if not failed_rows.empty:
        print("\n--- Failed ticker coverage (first 50) ---")
        print(failed_rows.head(50).to_string(index=False))

    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f"- {failure}")

    if evidence_dir is not None:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        coverage.to_csv(
            evidence_dir / "Active_Ticker_Movement_Validation_Coverage.csv",
            index=False,
        )
        (evidence_dir / "Active_Ticker_Movement_Validation_Summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
        print(f"evidence_dir: {evidence_dir}")

    if failures:
        return 1

    print("\nACTIVE TICKER MOVEMENT VALIDATION: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help="Optional directory for coverage CSV + validation JSON.",
    )
    args = parser.parse_args()
    return validate(evidence_dir=args.evidence_dir)


if __name__ == "__main__":
    raise SystemExit(main())
