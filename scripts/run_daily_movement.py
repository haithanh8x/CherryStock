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

from cherrystock.application.services.movement_daily_pipeline import (  # noqa: E402
    MovementDailyPipelineService,
)
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402


def _progress(index: int, total: int, ticker: str, status: str) -> None:
    print(f"[movement {index}/{total}] {ticker}: {status}")


def _export(summary: dict[str, object], evidence_dir: Path) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summary["plan"]).to_csv(
        evidence_dir / "Daily_Movement_Plan.csv",
        index=False,
    )
    pd.DataFrame(summary["results"]).to_csv(
        evidence_dir / "Daily_Movement_Result.csv",
        index=False,
    )
    aggregate = {k: v for k, v in summary.items() if k not in {"plan", "results"}}
    (evidence_dir / "Daily_Movement_Summary.json").write_text(
        json.dumps(aggregate, indent=2, default=str),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run manual/on-demand ticker-level ZigZag + Price Movement refresh."
    )
    parser.add_argument(
        "--ticker",
        action="append",
        dest="tickers",
        help="Optional active ticker. Repeat for multiple tickers.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process at most N selected stale/forced tickers.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force selected active tickers even when ZigZag date matches latest OHLC.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the selection plan without writing movement data.",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help="Optional docs/reference/data/... output directory.",
    )
    args = parser.parse_args()

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    service = MovementDailyPipelineService(connection_factory=factory)

    if args.dry_run:
        plan = service.plan(
            requested_tickers=args.tickers,
            force=args.force,
            limit=args.limit,
        )
        frame = pd.DataFrame(plan)
        print(frame.to_string(index=False))
        selected = int(frame["Selected"].sum()) if not frame.empty else 0
        failures = (
            int(frame["PlanState"].isin(["NO_OHLC", "SOURCE_REWIND"]).sum())
            if not frame.empty
            else 0
        )
        print(f"selected_ticker_count: {selected}")
        print(f"preflight_failure_count: {failures}")
        return 1 if failures else 0

    summary = service.run(
        requested_tickers=args.tickers,
        force=args.force,
        limit=args.limit,
        progress_callback=_progress,
    )

    print("\n=== Manual / On-Demand Movement Refresh ===")
    for key, value in summary.items():
        if key not in {"plan", "results"}:
            print(f"{key}: {value}")

    if args.evidence_dir is not None:
        _export(summary, args.evidence_dir)
        print(f"evidence_dir: {args.evidence_dir}")

    return 1 if int(summary["failure_count"]) > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
