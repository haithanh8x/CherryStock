from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from calcEngine.zigzag import load_ticker_source  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.domain.analytics.zigzag.research import (  # noqa: E402
    chronological_split,
    compare_static_variants,
)
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.repositories.zigzag_repository import ZigZagRepository  # noqa: E402
from cherrystock.infrastructure.database.repositories.zigzag_research_repository import (  # noqa: E402
    ZigZagResearchRepository,
)
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


DEFAULT_TICKERS = "MWG,FPT,HPG,MBB,VCB,VNM,DIG,CEO,NVL,SSI"
SCHEMA_SQL = PROJECT_ROOT / "src" / "DuckDB" / "sql" / "zigzag_research_schema.sql"


def _tickers(value: str) -> list[str]:
    return list(dict.fromkeys(item.strip().upper() for item in value.split(",") if item.strip()))


def main() -> int:
    parser = argparse.ArgumentParser(description="ZigZag V1.2 multi-ticker static-deviation pilot.")
    parser.add_argument("--tickers", default=DEFAULT_TICKERS)
    parser.add_argument("--calibration-version", default="V1.1")
    parser.add_argument("--pilot-version", default="V1.2")
    args = parser.parse_args()

    tickers = _tickers(args.tickers)
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    output_rows: list[dict[str, object]] = []

    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None:
            raise RuntimeError("UnitOfWork did not initialize a writer connection.")

        uow.connection.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        base_config = ZigZagRepository(uow.connection).load_mvp_config()
        research_repo = ZigZagResearchRepository(uow.connection)
        recommendations = research_repo.load_recommendations(
            calibration_version=args.calibration_version,
            tickers=tickers,
        )

        missing = [ticker for ticker in tickers if ticker not in recommendations]
        if missing:
            raise RuntimeError(
                "Missing V1.1 recommendation for: "
                + ", ".join(missing)
                + ". Run calibrate_zigzag_deviation.py first."
            )

        for ticker in tickers:
            source = load_ticker_source(uow.connection, ticker)
            test_frame = chronological_split(source)["TEST"]
            row = compare_static_variants(
                test_frame,
                ticker=ticker,
                base_config=base_config,
                calibrated_deviation_pct=recommendations[ticker],
                baseline_deviation_pct=0.05,
            )
            research_repo.replace_pilot(
                pilot_version=args.pilot_version,
                calibration_version=args.calibration_version,
                row=row,
            )
            row = {
                "PilotVersion": args.pilot_version,
                "CalibrationVersion": args.calibration_version,
                **row,
            }
            output_rows.append(row)
            print(
                f"{ticker}: 5% vs {recommendations[ticker]:.2%} -> {row['Decision']}"
            )

    output_dir = settings.project_root / "docs" / "reference" / "data" / "zigzag" / "pilot"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"ZigZag_MultiTicker_Pilot_{args.pilot_version}.csv"
    pd.DataFrame(output_rows).to_csv(output_path, index=False, encoding="utf-8")

    print(f"Pilot rows: {len(output_rows)}")
    print(f"Evidence: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
