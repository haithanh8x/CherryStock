from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Orchestrator.active_ticker_movement_initload import (  # noqa: E402
    initial_load_active_ticker_movement,
)
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


ZIGZAG_SCHEMA_SQL = PROJECT_ROOT / "src" / "DuckDB" / "sql" / "zigzag_mvp_schema.sql"
PRICE_MOVEMENT_SCHEMA_SQL = (
    PROJECT_ROOT / "src" / "DuckDB" / "sql" / "price_movement_v2_schema.sql"
)


def _apply_schema(factory: DuckDBConnectionFactory) -> None:
    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None:
            raise RuntimeError("UnitOfWork did not initialize a writer connection.")
        uow.connection.execute(ZIGZAG_SCHEMA_SQL.read_text(encoding="utf-8"))
        uow.connection.execute(PRICE_MOVEMENT_SCHEMA_SQL.read_text(encoding="utf-8"))


def _progress(stage: str, index: int, total: int, ticker: str, status: str) -> None:
    print(f"[{stage} {index}/{total}] {ticker}: {status}")


def _export_evidence(summary: dict[str, object], evidence_dir: Path) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summary["results"]).to_csv(
        evidence_dir / "Active_Ticker_Movement_Initload_Detail.csv",
        index=False,
    )

    aggregate = {
        key: value
        for key, value in summary.items()
        if key != "results"
    }
    (evidence_dir / "Active_Ticker_Movement_Initload_Summary.json").write_text(
        json.dumps(aggregate, indent=2, default=str),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Initial-load ZigZag then Price Movement for "
            'CherryMon.main.vw_Ticker_Active.'
        )
    )
    parser.add_argument(
        "--ticker",
        action="append",
        dest="tickers",
        help="Optional active ticker canary. Repeat for multiple tickers.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional deterministic first-N active ticker canary.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop the current stage after the first failure.",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help="Optional directory for detail CSV + aggregate JSON evidence.",
    )
    args = parser.parse_args()

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    _apply_schema(factory)

    summary = initial_load_active_ticker_movement(
        factory=factory,
        requested_tickers=args.tickers,
        limit=args.limit,
        fail_fast=args.fail_fast,
        progress_callback=_progress,
    )

    print("\n=== Active Ticker ZigZag + Price Movement Initial Load ===")
    for key, value in summary.items():
        if key != "results":
            print(f"{key}: {value}")

    failures = [
        row
        for row in summary["results"]
        if str(row["ZigZagStatus"]).startswith("FAILED")
        or row["PriceMovementStatus"] == "FAILED"
    ]
    if failures:
        print("\n--- Failures ---")
        print(pd.DataFrame(failures).to_string(index=False))

    if args.evidence_dir is not None:
        _export_evidence(summary, args.evidence_dir)
        print(f"evidence_dir: {args.evidence_dir}")

    return 1 if int(summary["failure_count"]) > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
