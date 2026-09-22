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

from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402


def validate(*, evidence_dir: Path | None = None) -> int:
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    failures: list[str] = []

    with factory.reader() as connection:
        coverage = connection.execute(
            """
            WITH active AS (
                SELECT DISTINCT
                    UPPER(TRIM(CAST(Ticker AS VARCHAR))) AS Ticker
                FROM "CherryMon"."main"."vw_Ticker_Active"
                WHERE Ticker IS NOT NULL
                  AND TRIM(CAST(Ticker AS VARCHAR)) <> ''
            ),
            ohlc AS (
                SELECT Ticker, MAX(Date) AS LatestOHLCDate
                FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
                GROUP BY Ticker
            ),
            zz_current AS (
                SELECT Ticker, AsOfDate AS ZigZagAsOfDate
                FROM "CherryMon"."main"."vw_Ticker_ZigZag_Current"
                WHERE ConfigCode = 'ZZ_D_5_MVP'
            ),
            zz_swings AS (
                SELECT
                    Ticker,
                    COUNT(*) AS ZigZagSwingRows,
                    MAX(SwingSeq) AS ZigZagLastSwingSeq,
                    MAX(ConfirmedAtDate) AS ZigZagLastConfirmedAtDate
                FROM "CherryMon"."main"."vw_Ticker_ZigZag_Swings"
                WHERE ConfigCode = 'ZZ_D_5_MVP'
                GROUP BY Ticker
            ),
            pm AS (
                SELECT
                    Ticker,
                    COUNT(*) AS PriceMovementSwingRows,
                    MAX(SwingSeq) AS PriceMovementLastSwingSeq,
                    MAX(ConfirmedAtDate) AS PriceMovementLastConfirmedAtDate
                FROM "CherryMon"."main"."vw_Ticker_Price_Movement_Swings"
                WHERE PriceMovementConfigCode = 'PM_ZZ_D_V2'
                  AND ZigZagConfigCode = 'ZZ_D_5_MVP'
                GROUP BY Ticker
            ),
            profile AS (
                SELECT
                    Ticker,
                    COUNT(*) AS MovementProfileRows,
                    MAX(LastSwingSeq) AS ProfileLastSwingSeq,
                    MAX(AsOfConfirmedAtDate) AS ProfileAsOfConfirmedAtDate
                FROM "CherryMon"."main"."vw_Ticker_Movement_Profile"
                WHERE PriceMovementConfigCode = 'PM_ZZ_D_V2'
                  AND ZigZagConfigCode = 'ZZ_D_5_MVP'
                GROUP BY Ticker
            ),
            context AS (
                SELECT Ticker, COUNT(*) AS MovementContextRows
                FROM "CherryMon"."main"."vw_Ticker_Movement_Context"
                WHERE PriceMovementConfigCode = 'PM_ZZ_D_V2'
                  AND ZigZagConfigCode = 'ZZ_D_5_MVP'
                GROUP BY Ticker
            ),
            zz_identity AS (
                SELECT
                    Ticker,
                    SwingSeq,
                    Direction,
                    StartPivotSeq,
                    StartDate,
                    StartPrice,
                    EndPivotSeq,
                    EndDate,
                    EndPrice,
                    ConfirmedAtDate
                FROM "CherryMon"."main"."vw_Ticker_ZigZag_Swings"
                WHERE ConfigCode = 'ZZ_D_5_MVP'
            ),
            pm_identity AS (
                SELECT
                    Ticker,
                    SwingSeq,
                    Direction,
                    StartPivotSeq,
                    StartDate,
                    StartPrice,
                    EndPivotSeq,
                    EndDate,
                    EndPrice,
                    ConfirmedAtDate
                FROM "CherryMon"."main"."vw_Ticker_Price_Movement_Swings"
                WHERE PriceMovementConfigCode = 'PM_ZZ_D_V2'
                  AND ZigZagConfigCode = 'ZZ_D_5_MVP'
            ),
            identity_diff AS (
                SELECT * FROM (
                    SELECT * FROM zz_identity
                    EXCEPT
                    SELECT * FROM pm_identity
                )
                UNION ALL
                SELECT * FROM (
                    SELECT * FROM pm_identity
                    EXCEPT
                    SELECT * FROM zz_identity
                )
            ),
            identity_mismatch AS (
                SELECT Ticker, COUNT(*) AS IdentityMismatchRows
                FROM identity_diff
                GROUP BY Ticker
            )
            SELECT
                a.Ticker,
                o.LatestOHLCDate,
                z.ZigZagAsOfDate,
                COALESCE(zz.ZigZagSwingRows, 0) AS ZigZagSwingRows,
                zz.ZigZagLastSwingSeq,
                zz.ZigZagLastConfirmedAtDate,
                COALESCE(pm.PriceMovementSwingRows, 0) AS PriceMovementSwingRows,
                pm.PriceMovementLastSwingSeq,
                pm.PriceMovementLastConfirmedAtDate,
                COALESCE(p.MovementProfileRows, 0) AS MovementProfileRows,
                p.ProfileLastSwingSeq,
                p.ProfileAsOfConfirmedAtDate,
                COALESCE(c.MovementContextRows, 0) AS MovementContextRows,
                COALESCE(i.IdentityMismatchRows, 0) AS IdentityMismatchRows
            FROM active AS a
            LEFT JOIN ohlc AS o ON o.Ticker = a.Ticker
            LEFT JOIN zz_current AS z ON z.Ticker = a.Ticker
            LEFT JOIN zz_swings AS zz ON zz.Ticker = a.Ticker
            LEFT JOIN pm ON pm.Ticker = a.Ticker
            LEFT JOIN profile AS p ON p.Ticker = a.Ticker
            LEFT JOIN context AS c ON c.Ticker = a.Ticker
            LEFT JOIN identity_mismatch AS i ON i.Ticker = a.Ticker
            ORDER BY a.Ticker
            """
        ).df()

    if coverage.empty:
        failures.append("vw_Ticker_Active returned no rows")

    no_ohlc = coverage["LatestOHLCDate"].isna()
    if no_ohlc.any():
        failures.append(f"active ticker(s) without OHLC: {int(no_ohlc.sum())}")

    missing_current = coverage["ZigZagAsOfDate"].isna()
    if missing_current.any():
        failures.append(
            f"active ticker(s) without ZigZag current state: {int(missing_current.sum())}"
        )

    stale = (
        coverage["LatestOHLCDate"].notna()
        & coverage["ZigZagAsOfDate"].notna()
        & (coverage["LatestOHLCDate"] > coverage["ZigZagAsOfDate"])
    )
    if stale.any():
        failures.append(f"stale ZigZag ticker(s): {int(stale.sum())}")

    source_rewind = (
        coverage["LatestOHLCDate"].notna()
        & coverage["ZigZagAsOfDate"].notna()
        & (coverage["LatestOHLCDate"] < coverage["ZigZagAsOfDate"])
    )
    if source_rewind.any():
        failures.append(f"source rewind ticker(s): {int(source_rewind.sum())}")

    parity = (
        coverage["PriceMovementSwingRows"] != coverage["ZigZagSwingRows"]
    )
    if parity.any():
        failures.append(
            f"ZigZag/Price Movement swing mismatch ticker(s): {int(parity.sum())}"
        )

    geometry_mismatch = coverage["IdentityMismatchRows"] > 0
    if geometry_mismatch.any():
        failures.append(
            f"confirmed swing geometry mismatch ticker(s): {int(geometry_mismatch.sum())}"
        )

    profile_bad = (coverage["ZigZagSwingRows"] > 0) & (
        coverage["MovementProfileRows"] != 1
    )
    if profile_bad.any():
        failures.append(
            f"ticker(s) with swing but invalid profile count: {int(profile_bad.sum())}"
        )

    profile_stale = (coverage["ZigZagSwingRows"] > 0) & (
        (coverage["ProfileLastSwingSeq"] != coverage["ZigZagLastSwingSeq"])
        | (
            coverage["ProfileAsOfConfirmedAtDate"]
            != coverage["ZigZagLastConfirmedAtDate"]
        )
    )
    if profile_stale.any():
        failures.append(
            f"stale Movement Profile ticker(s): {int(profile_stale.sum())}"
        )

    context_bad = (coverage["MovementProfileRows"] == 1) & (
        coverage["MovementContextRows"] != 1
    )
    if context_bad.any():
        failures.append(
            f"MovementContext coverage mismatch ticker(s): {int(context_bad.sum())}"
        )

    summary = {
        "active_ticker_count": int(len(coverage)),
        "latest_ohlc_covered": int(coverage["LatestOHLCDate"].notna().sum()),
        "zigzag_current_covered": int(coverage["ZigZagAsOfDate"].notna().sum()),
        "stale_zigzag_count": int(stale.sum()),
        "source_rewind_count": int(source_rewind.sum()),
        "swing_parity_mismatch_count": int(parity.sum()),
        "swing_geometry_mismatch_count": int(geometry_mismatch.sum()),
        "profile_stale_count": int(profile_stale.sum()),
        "movement_context_covered": int((coverage["MovementContextRows"] == 1).sum()),
        "validation_failures": len(failures),
    }

    print("=== Daily Movement Validation ===")
    for key, value in summary.items():
        print(f"{key}: {value}")

    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f"- {failure}")

    if evidence_dir is not None:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        coverage.to_csv(
            evidence_dir / "Daily_Movement_Validation_Coverage.csv",
            index=False,
        )
        (evidence_dir / "Daily_Movement_Validation_Summary.json").write_text(
            json.dumps(summary, indent=2, default=str),
            encoding="utf-8",
        )

    if failures:
        return 1

    print("\nDAILY MOVEMENT VALIDATION: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    return validate(evidence_dir=args.evidence_dir)


if __name__ == "__main__":
    raise SystemExit(main())
