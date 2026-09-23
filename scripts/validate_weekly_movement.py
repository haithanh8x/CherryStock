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
            )
            SELECT
                a.Ticker,
                c.ContextAsOfDate,
                c.LatestOHLCDate,
                c.MovementAgeTradingDays,
                c.MovementFreshnessStatus,
                c.ContextStatus,
                c.TrendRegime,
                c.TrendQuality
            FROM active AS a
            LEFT JOIN "CherryMon"."main"."vw_Ticker_Movement_Context" AS c
              ON c.Ticker = a.Ticker
             AND c.PriceMovementConfigCode = 'PM_ZZ_D_V2'
             AND c.ZigZagConfigCode = 'ZZ_D_5_MVP'
            ORDER BY a.Ticker
            """
        ).df()

    if coverage.empty:
        failures.append("vw_Ticker_Active returned no rows")

    missing_context = coverage["ContextAsOfDate"].isna()
    if missing_context.any():
        failures.append(
            f"active ticker(s) without MovementContext: {int(missing_context.sum())}"
        )

    stale = coverage["MovementFreshnessStatus"] == "STALE"
    if stale.any():
        failures.append(
            f"stale weekly Movement ticker(s): {int(stale.sum())}"
        )

    unknown = coverage["MovementFreshnessStatus"].isin(["UNKNOWN", None])
    if unknown.any():
        failures.append(
            f"unknown Movement freshness ticker(s): {int(unknown.sum())}"
        )

    over_age = coverage["MovementAgeTradingDays"].fillna(9999) > 5
    if over_age.any():
        failures.append(
            f"Movement age exceeds weekly SLA (>5 trading days): {int(over_age.sum())}"
        )

    summary = {
        "active_ticker_count": int(len(coverage)),
        "movement_context_covered": int(coverage["ContextAsOfDate"].notna().sum()),
        "fresh_count": int((coverage["MovementFreshnessStatus"] == "FRESH").sum()),
        "aging_count": int((coverage["MovementFreshnessStatus"] == "AGING").sum()),
        "stale_count": int(stale.sum()),
        "max_movement_age_trading_days": (
            None
            if coverage["MovementAgeTradingDays"].dropna().empty
            else int(coverage["MovementAgeTradingDays"].max())
        ),
        "validation_failures": len(failures),
    }

    print("=== Weekly Movement Validation ===")
    for key, value in summary.items():
        print(f"{key}: {value}")

    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f"- {failure}")

    if evidence_dir is not None:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        coverage.to_csv(
            evidence_dir / "Weekly_Movement_Validation_Coverage.csv",
            index=False,
        )
        (evidence_dir / "Weekly_Movement_Validation_Summary.json").write_text(
            json.dumps(summary, indent=2, default=str),
            encoding="utf-8",
        )

    if failures:
        return 1

    print("\nWEEKLY MOVEMENT VALIDATION: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    return validate(evidence_dir=args.evidence_dir)


if __name__ == "__main__":
    raise SystemExit(main())
