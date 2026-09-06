from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from calcEngine.smartMoneyEvaluation import (  # noqa: E402
    build_forward_labels,
    evaluate_smart_money_labels,
)
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate SmartMoneyScore V1 on chronological TRAIN/VALIDATION/TEST splits."
    )
    parser.add_argument(
        "--horizons",
        nargs="+",
        type=int,
        default=[5, 10, 20],
    )
    parser.add_argument(
        "--output-dir",
        default=str(settings.data_dir / "evaluation" / "smart_money_v1"),
    )
    args = parser.parse_args()
    horizons = tuple(sorted({int(value) for value in args.horizons}))
    if not horizons or any(value <= 0 for value in horizons):
        raise ValueError("All horizons must be positive.")

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with factory.reader() as connection:
        scores = connection.execute(
            """
            SELECT
                Ticker,
                Date,
                ModelCode,
                ModelVersion,
                SmartMoneyScore,
                ConfidenceScore,
                MarketState,
                FactorCoverage,
                DataQualityStatus
            FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
            ORDER BY Ticker, Date
            """
        ).df()
        if scores.empty:
            raise RuntimeError("No SmartMoney rows. Run full historical initload first.")

        stock = connection.execute(
            """
            SELECT
                Ticker,
                Date,
                Close
            FROM "CherryMon"."main"."raw_stock_eod"
            ORDER BY Ticker, Date
            """
        ).df()
        benchmark = connection.execute(
            """
            SELECT
                Date,
                Close
            FROM "CherryMon"."main"."raw_index_eod"
            WHERE Ticker = 'VNINDEX'
            ORDER BY Date
            """
        ).df()

    labels = build_forward_labels(
        scores,
        stock,
        benchmark,
        horizons=horizons,
    )
    metrics, monotonicity = evaluate_smart_money_labels(
        labels,
        horizons=horizons,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "metrics.csv"
    monotonicity_path = output_dir / "monotonicity.csv"
    summary_path = output_dir / "summary.json"

    metrics.to_csv(metrics_path, index=False)
    monotonicity.to_csv(monotonicity_path, index=False)

    test_metrics = metrics.loc[metrics["Split"].eq("TEST")] if not metrics.empty else metrics
    summary = {
        "rows_scored": int(len(scores)),
        "date_start": str(scores["Date"].min()),
        "date_end": str(scores["Date"].max()),
        "horizons": list(horizons),
        "metric_rows": int(len(metrics)),
        "test_metric_rows": int(len(test_metrics)),
        "outputs": {
            "metrics": str(metrics_path),
            "monotonicity": str(monotonicity_path),
        },
        "note": (
            "Evaluation evidence is research/calibration output only. "
            "It does not mutate production SmartMoney weights or enable auto-run."
        ),
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("SmartMoney V1 evaluation complete.")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if not monotonicity.empty:
        print("\nTEST monotonicity:")
        print(monotonicity.loc[monotonicity["Split"].eq("TEST")].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
