from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Price Movement Character public contracts.")
    parser.add_argument("ticker", help="ticker to inspect, e.g. MWG")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    ticker = args.ticker.strip().upper()
    limit = max(1, int(args.limit))

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with factory.reader() as connection:
        daily = connection.execute(
            """
            SELECT
                Ticker, Date, Direction, SwingStatus,
                CurrentSwingPct, DurationBars,
                MagnitudeScore, VelocityScore, PersistenceScore,
                MovementCharacter, HistoricalSameDirSwingCount,
                ThresholdPct, ThresholdSource, QualityStatus
            FROM "CherryMon"."main"."vw_Ticker_Movement_D"
            WHERE Ticker = ?
            ORDER BY Date DESC
            LIMIT ?
            """,
            [ticker, limit],
        ).df()
        swings = connection.execute(
            """
            SELECT
                Ticker, Direction, SwingSeq,
                PivotStartDate, PivotEndDate, ConfirmedAtDate,
                SwingPct, DurationBars, VelocityPctPerBar,
                ATRNormMagnitude, PersistenceScore,
                ThresholdPct, ThresholdSource, QualityStatus
            FROM "CherryMon"."main"."vw_Ticker_Movement_Swings"
            WHERE Ticker = ?
            ORDER BY SwingSeq DESC
            LIMIT ?
            """,
            [ticker, limit],
        ).df()
        profile = connection.execute(
            """
            SELECT
                Ticker, Direction, SwingCount,
                MagnitudeMedian, MagnitudeP75, MagnitudeP90,
                DurationBarsMedian, DurationBarsP75,
                VelocityMedian, VelocityP75,
                ATRNormMagnitudeMedian, PersistenceMedian,
                LatestConfirmedAtDate
            FROM "CherryMon"."main"."vw_Ticker_Movement_Profile"
            WHERE Ticker = ?
            ORDER BY Direction
            """,
            [ticker],
        ).df()
        future_leak = connection.execute(
            """
            SELECT COUNT(*)
            FROM "CherryMon"."main"."cal_price_movement_daily" AS d
            INNER JOIN "CherryMon"."main"."cal_price_movement_swing" AS s
                ON s.ConfigId = d.ConfigId
               AND s.Ticker = d.Ticker
               AND s.Direction = d.Direction
               AND s.ConfirmedAtDate > d.Date
               AND s.PivotEndDate <= d.Date
            WHERE d.Ticker = ?
            """,
            [ticker],
        ).fetchone()[0]

    print(f"\n=== {ticker} latest daily movement ===")
    print(daily.to_string(index=False))
    print(f"\n=== {ticker} latest confirmed swings ===")
    print(swings.to_string(index=False))
    print(f"\n=== {ticker} movement profile ===")
    print(profile.to_string(index=False))
    print(f"\nNo-look-ahead diagnostic rows (must be 0): {int(future_leak or 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
