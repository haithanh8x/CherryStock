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
from cherrystock.domain.analytics.zigzag.engine import calculate_zigzag  # noqa: E402
from cherrystock.domain.analytics.zigzag.regime import (  # noqa: E402
    RegimeDeviationResolver,
    RegimePolicyConfig,
    build_regime_context,
    regime_counts,
)
from cherrystock.domain.analytics.zigzag.research import calculate_swing_metrics  # noqa: E402
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


def _pivot_evidence(source, pivots, resolver):
    rows = []
    previous = None
    for pivot in pivots:
        if previous is None:
            selected_at = None
            regime_used = "BOOTSTRAP"
        else:
            selected_at = previous.confirmed_at_date
            regime_used = resolver.regime_on_date(previous.confirmed_at_date)
        rows.append(
            {
                "Ticker": pivot.ticker,
                "PivotSeq": pivot.pivot_seq,
                "PivotType": pivot.pivot_type,
                "PivotDate": pivot.pivot_date,
                "PivotPrice": pivot.pivot_price,
                "ConfirmedAtDate": pivot.confirmed_at_date,
                "ConfirmationPrice": pivot.confirmation_price,
                "DeviationPctUsed": pivot.deviation_pct,
                "DeviationSelectedAtDate": selected_at,
                "RegimeUsed": regime_used,
            }
        )
        previous = pivot
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="ZigZag V2 regime-aware swing-locked evaluation.")
    parser.add_argument("--tickers", default=DEFAULT_TICKERS)
    parser.add_argument("--calibration-version", default="V1.1")
    parser.add_argument("--regime-version", default="V2.0")
    args = parser.parse_args()

    tickers = _tickers(args.tickers)
    policy = RegimePolicyConfig()
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    summary_rows: list[dict[str, object]] = []
    pivot_rows: list[dict[str, object]] = []

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
                "Missing calibrated base deviation for: "
                + ", ".join(missing)
                + ". Run V1.1 first."
            )

        from dataclasses import replace

        for ticker in tickers:
            source = load_ticker_source(uow.connection, ticker)
            base_deviation = recommendations[ticker]
            ticker_config = replace(
                base_config,
                deviation_pct=base_deviation,
                config_code=f"ZZ_D_REGIME_{ticker}",
                model_version=args.regime_version,
            )

            static_pivots, _, _ = calculate_zigzag(
                source,
                ticker=ticker,
                config=ticker_config,
            )
            context = build_regime_context(source, policy=policy)
            resolver = RegimeDeviationResolver(context, policy=policy)
            regime_pivots, _, _ = calculate_zigzag(
                source,
                ticker=ticker,
                config=ticker_config,
                deviation_resolver=resolver,
            )

            static_metrics = calculate_swing_metrics(
                source,
                static_pivots,
                deviation_pct=base_deviation,
            )
            regime_metrics = calculate_swing_metrics(
                source,
                regime_pivots,
                deviation_pct=base_deviation,
            )
            counts = regime_counts(context)

            row = {
                "Ticker": ticker,
                "BaseDeviationPct": base_deviation,
                "StaticSwingCount": static_metrics.swing_count,
                "RegimeSwingCount": regime_metrics.swing_count,
                "StaticShortSwingRate": static_metrics.short_swing_rate,
                "RegimeShortSwingRate": regime_metrics.short_swing_rate,
                "StaticMedianSwingBars": static_metrics.median_swing_bars,
                "RegimeMedianSwingBars": regime_metrics.median_swing_bars,
                "StaticMedianAbsSwingPct": static_metrics.median_abs_swing_pct,
                "RegimeMedianAbsSwingPct": regime_metrics.median_abs_swing_pct,
                "StaticStructuralValid": static_metrics.structural_valid,
                "RegimeStructuralValid": regime_metrics.structural_valid,
                "StaticScore": static_metrics.calibration_score,
                "RegimeScore": regime_metrics.calibration_score,
                "LowVolBars": counts["LOW_VOL"],
                "NormalBars": counts["NORMAL"],
                "HighVolBars": counts["HIGH_VOL"],
            }
            research_repo.replace_regime(
                regime_version=args.regime_version,
                calibration_version=args.calibration_version,
                row=row,
            )
            summary_rows.append(
                {
                    "RegimeVersion": args.regime_version,
                    "CalibrationVersion": args.calibration_version,
                    **row,
                }
            )
            for evidence in _pivot_evidence(source, regime_pivots, resolver):
                pivot_rows.append(
                    {
                        "RegimeVersion": args.regime_version,
                        "CalibrationVersion": args.calibration_version,
                        **evidence,
                    }
                )
            print(
                f"{ticker}: base={base_deviation:.2%} "
                f"static_swings={static_metrics.swing_count} "
                f"regime_swings={regime_metrics.swing_count}"
            )

    output_dir = settings.project_root / "docs" / "reference" / "data" / "zigzag" / "regime"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / f"ZigZag_Regime_Summary_{args.regime_version}.csv"
    pivots_path = output_dir / f"ZigZag_Regime_Pivots_{args.regime_version}.csv"
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False, encoding="utf-8")
    pd.DataFrame(pivot_rows).to_csv(pivots_path, index=False, encoding="utf-8")

    print(f"Summary evidence: {summary_path}")
    print(f"Pivot evidence: {pivots_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
