"""Evaluate and optionally audit the R/S V2.4 Source Promotion Gate.

Dry-run:
    python scripts/promote_rs_v2_4_source.py --effectiveness-run RSEFF_MA50_D_H20

Audit an already-approved decision:
    python scripts/promote_rs_v2_4_source.py \
        --effectiveness-run RSEFF_MA50_D_H20 --apply

Even --apply never changes Indicator Engine metadata or R/S runtime configuration.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from calcEngine.rsSourceEffectiveness import (  # noqa: E402
    SourceEffectivenessRecord,
    SourcePromotionPolicy,
    evaluate_source_promotion,
)
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="R/S V2.4 Source Promotion Gate")
    parser.add_argument("--effectiveness-run", required=True)
    parser.add_argument("--policy-json", default="{}")
    parser.add_argument("--decision-id", default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--notes", default=None)
    return parser.parse_args()


def _load_run(connection, run_id: str) -> dict:
    row = connection.execute(
        """
        SELECT
            "EffectivenessRunId", "SourceKey", "SourceFamily", "SourceRole",
            "HorizonBars", "Status"
        FROM "CherryMon"."main"."cal_rs_source_effectiveness_run"
        WHERE "EffectivenessRunId" = ?;
        """,
        [run_id],
    ).fetchone()
    if row is None:
        raise ValueError(f"source-effectiveness run not found: {run_id}")
    result = {
        "run_id": str(row[0]),
        "source_key": str(row[1]),
        "source_family": str(row[2]),
        "source_role": str(row[3]),
        "horizon_bars": int(row[4]),
        "status": str(row[5]),
    }
    if result["status"] != "COMPLETED":
        raise ValueError("source-effectiveness run must be COMPLETED")
    return result


def _load_records(connection, run_id: str) -> list[SourceEffectivenessRecord]:
    rows = connection.execute(
        """
        SELECT
            "Ticker", "ScopeType", "SourceKey", "SourceFamily", "SourceRole",
            "HorizonBars", "AttributionMode", "MarginalMetric",
            "LineageEventCount", "ValidationEventCount", "TestEventCount", "TouchRate",
            "HoldRateGivenTouch", "BreakRateGivenTouch", "RetestRateGivenBreak",
            "DirectionalEdgePct", "ValidationQuality", "TestQuality",
            "ValidationMarginalLift", "TestMarginalLift", "TemporalStability",
            "RegimeStability", "ComplexityDelta", "EffectivenessScore",
            "Recommendation", "EvidenceJson"
        FROM "CherryMon"."main"."cal_rs_source_effectiveness"
        WHERE "EffectivenessRunId" = ?
        ORDER BY "Ticker";
        """,
        [run_id],
    ).fetchall()

    result: list[SourceEffectivenessRecord] = []
    for row in rows:
        result.append(
            SourceEffectivenessRecord(
                ticker=str(row[0]),
                scope_type=str(row[1]),
                source_key=str(row[2]),
                source_family=str(row[3]),
                source_role=str(row[4]),
                horizon_bars=int(row[5]),
                attribution_mode=str(row[6]),
                marginal_metric=str(row[7]),
                lineage_event_count=int(row[8] or 0),
                validation_event_count=int(row[9] or 0),
                test_event_count=int(row[10] or 0),
                touch_rate=float(row[11]) if row[11] is not None else None,
                hold_rate_given_touch=float(row[12]) if row[12] is not None else None,
                break_rate_given_touch=float(row[13]) if row[13] is not None else None,
                retest_rate_given_break=float(row[14]) if row[14] is not None else None,
                directional_edge_pct=float(row[15]) if row[15] is not None else None,
                validation_quality=float(row[16] or 0.0),
                test_quality=float(row[17] or 0.0),
                validation_marginal_lift=float(row[18] or 0.0),
                test_marginal_lift=float(row[19] or 0.0),
                temporal_stability=float(row[20] or 0.0),
                regime_stability=float(row[21]) if row[21] is not None else None,
                complexity_delta=float(row[22] or 0.0),
                effectiveness_score=float(row[23] or 0.0),
                recommendation=str(row[24]),
                evidence=json.loads(row[25] or "{}"),
            )
        )
    if not result:
        raise ValueError(f"no effectiveness rows found for run: {run_id}")
    return result


def main() -> None:
    args = _parse_args()
    policy_payload = json.loads(args.policy_json)
    if not isinstance(policy_payload, dict):
        raise ValueError("--policy-json must decode to an object")
    policy = SourcePromotionPolicy(**policy_payload)

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with factory.reader() as connection:
        run = _load_run(connection, args.effectiveness_run)
        records = _load_records(connection, args.effectiveness_run)
        decision = evaluate_source_promotion(records, policy=policy)

    payload = asdict(decision)
    payload["effectiveness_run_id"] = args.effectiveness_run
    payload["apply_requested"] = bool(args.apply)
    payload["runtime_mutation"] = False
    print(json.dumps(payload, indent=2, sort_keys=True))

    if not args.apply:
        return

    decision_id = args.decision_id or f"RSSRC_{uuid.uuid4().hex[:16].upper()}"
    with DuckDBUnitOfWork(factory) as uow:
        if uow.rs_evaluations is None:
            raise RuntimeError("UnitOfWork did not initialize R/S evaluation repository")
        uow.rs_evaluations.record_source_promotion_decision(
            decision_id=decision_id,
            effectiveness_run_id=args.effectiveness_run,
            source_key=decision.source_key,
            source_family=decision.source_family,
            source_role=decision.source_role,
            horizon_bars=decision.horizon_bars,
            outcome=decision.outcome,
            ticker_count=decision.ticker_count,
            positive_ticker_count=decision.positive_ticker_count,
            positive_ticker_ratio=decision.positive_ticker_ratio,
            avg_effectiveness_score=decision.avg_effectiveness_score,
            avg_validation_lift=decision.avg_validation_lift,
            avg_test_lift=decision.avg_test_lift,
            avg_temporal_stability=decision.avg_temporal_stability,
            avg_regime_stability=decision.avg_regime_stability,
            max_complexity_delta=decision.max_complexity_delta,
            reasons=decision.reasons,
            policy=asdict(policy),
            applied=True,
            notes=args.notes,
        )

    print(
        f"Recorded source-promotion audit: {decision_id} "
        f"outcome={decision.outcome}; runtime unchanged."
    )


if __name__ == "__main__":
    main()
