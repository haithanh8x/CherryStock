"""Run the R/S V2.3 golden regression benchmark (read-only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from calcEngine.levelLadder import build_level_ladder  # noqa: E402
from calcEngine.rsEvaluation import validate_golden_ladder_invariants  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402


def main() -> None:
    fixture_path = PROJECT_ROOT / "tests" / "fixtures" / "rs_v2_3_golden_cases.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    model_version = str(payload["model_version"])

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    results = []
    failed = False
    with factory.reader() as connection:
        for case in payload["cases"]:
            from datetime import date

            requested_date = date.fromisoformat(case["as_of_date"])
            result = build_level_ladder(
                str(case["ticker"]),
                as_of_date=requested_date,
                model_version=model_version,
                connection=connection,
            )
            check = validate_golden_ladder_invariants(result)
            failed = failed or not check.passed
            results.append(
                {
                    "ticker": result.ticker,
                    "requested_as_of_date": requested_date.isoformat(),
                    "resolved_as_of_date": result.as_of_date.isoformat(),
                    "current_price": result.current_price,
                    "model_version": result.model_version,
                    "s1": (
                        result.nearest_support.price
                        if result.nearest_support is not None
                        else None
                    ),
                    "r1": (
                        result.nearest_resistance.price
                        if result.nearest_resistance is not None
                        else None
                    ),
                    "passed": check.passed,
                    "errors": list(check.errors),
                }
            )

    print(
        json.dumps(
            {
                "benchmark": payload["benchmark"],
                "model_version": model_version,
                "passed": not failed,
                "cases": results,
            },
            indent=2,
            sort_keys=True,
        )
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
