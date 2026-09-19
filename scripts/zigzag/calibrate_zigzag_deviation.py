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
    DEFAULT_DEVIATION_GRID,
    calibrate_static_deviation,
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


def _deviations(value: str) -> tuple[float, ...]:
    values = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        number = float(item)
        if number >= 1:
            number /= 100.0
        if not 0 < number < 1:
            raise argparse.ArgumentTypeError("deviations must be percentages between 0 and 100.")
        values.append(number)
    if not values:
        raise argparse.ArgumentTypeError("deviation grid must not be empty.")
    return tuple(sorted(set(values)))


def main() -> int:
    parser = argparse.ArgumentParser(description="ZigZag V1.1 ticker deviation calibration.")
    parser.add_argument("--tickers", default=DEFAULT_TICKERS)
    parser.add_argument("--version", default="V1.1")
    parser.add_argument(
        "--deviations",
        type=_deviations,
        default=DEFAULT_DEVIATION_GRID,
        help="Comma-separated fractions or percentages, e.g. 2,3,4,5,6,7,8,10,12.",
    )
    args = parser.parse_args()

    tickers = _tickers(args.tickers)
    if not tickers:
        raise SystemExit("No tickers supplied.")

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    all_evaluations: list[dict[str, object]] = []
    recommendations: list[dict[str, object]] = []

    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None:
            raise RuntimeError("UnitOfWork did not initialize a writer connection.")

        uow.connection.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        base_config = ZigZagRepository(uow.connection).load_mvp_config()
        research_repo = ZigZagResearchRepository(uow.connection)

        for ticker in tickers:
            source = load_ticker_source(uow.connection, ticker)
            if len(source) < 30:
                print(f"SKIP {ticker}: only {len(source)} source rows.")
                continue

            evaluations, selection = calibrate_static_deviation(
                source,
                ticker=ticker,
                base_config=base_config,
                calibration_version=args.version,
                deviations=args.deviations,
            )
            research_repo.replace_calibration(
                calibration_version=args.version,
                ticker=ticker,
                evaluations=evaluations,
                selection=selection,
            )
            all_evaluations.extend(evaluations)
            recommendations.append(
                {
                    "CalibrationVersion": args.version,
                    "Ticker": ticker,
                    "Timeframe": "D",
                    "BaseDeviationPct": selection.selected_deviation_pct,
                    "SelectionMethod": selection.selection_method,
                    "TrainScore": selection.train_score,
                    "ValidationScore": selection.validation_score,
                    "TestScore": selection.test_score,
                }
            )
            print(
                f"{ticker}: deviation={selection.selected_deviation_pct:.2%} "
                f"method={selection.selection_method} "
                f"test_score={selection.test_score:.4f}"
            )

    output_dir = settings.project_root / "docs" / "reference" / "data" / "zigzag" / "calibration"
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_evaluations).to_csv(
        output_dir / f"ZigZag_Calibration_{args.version}.csv",
        index=False,
        encoding="utf-8",
    )
    pd.DataFrame(recommendations).to_csv(
        output_dir / f"ZigZag_Ticker_Config_{args.version}.csv",
        index=False,
        encoding="utf-8",
    )

    print(f"Calibration rows: {len(all_evaluations)}")
    print(f"Recommendations: {len(recommendations)}")
    print(f"Evidence: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
