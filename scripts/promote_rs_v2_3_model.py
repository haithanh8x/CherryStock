"""Evaluate and optionally apply the R/S V2.3 incremental Promotion Gate.

Example dry-run:
    python scripts/promote_rs_v2_3_model.py \
        --baseline-run RSV23_BASELINE \
        --challenger-run RSV23_CHALLENGER

Apply only when the gate returns promote=true:
    python scripts/promote_rs_v2_3_model.py ... --apply
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

from calcEngine.rsEvaluation import (  # noqa: E402
    EvaluationMetrics,
    PromotionPolicy,
    RSModelSpec,
    promotion_gate,
)
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="R/S V2.3 Promotion Gate")
    parser.add_argument("--baseline-run", required=True)
    parser.add_argument("--challenger-run", required=True)
    parser.add_argument("--policy-json", default="{}")
    parser.add_argument("--decision-id", default=None)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def _load_run(connection, run_id: str) -> dict:
    row = connection.execute(
        """
        SELECT
            "EvaluationRunId", "ModelVersion", "DatasetStart", "DatasetEnd",
            "HorizonBars", "Status"
        FROM "CherryMon"."main"."cal_rs_evaluation_run"
        WHERE "EvaluationRunId" = ?;
        """,
        [run_id],
    ).fetchone()
    if row is None:
        raise ValueError(f"evaluation run not found: {run_id}")
    return {
        "run_id": row[0],
        "model_version": row[1],
        "dataset_start": row[2],
        "dataset_end": row[3],
        "horizon_bars": int(row[4]),
        "status": row[5],
    }


def _load_model(connection, model_version: str) -> RSModelSpec:
    row = connection.execute(
        """
        SELECT "ParentVersion", "ConfigJson", "Notes"
        FROM "CherryMon"."main"."dim_rs_model_version"
        WHERE "ModelVersion" = ?;
        """,
        [model_version],
    ).fetchone()
    if row is None:
        raise ValueError(f"model version not found: {model_version}")
    payload = json.loads(row[1])
    if not isinstance(payload, dict):
        raise ValueError(f"invalid model ConfigJson: {model_version}")
    payload.setdefault("model_version", model_version)
    payload.setdefault("enabled_sources", ())
    payload.setdefault("strength_config", {})
    payload.setdefault("volume_profile_config", {})
    payload.setdefault("structural_config", {})
    payload.setdefault("parent_version", row[0])
    payload.setdefault("notes", row[2])
    payload["enabled_sources"] = tuple(payload["enabled_sources"])
    return RSModelSpec(**payload)


def _load_scope_metrics(
    connection,
    run_id: str,
    scope_type: str,
    scope_key: str,
) -> EvaluationMetrics:
    rows = connection.execute(
        """
        SELECT "MetricCode", "MetricValue", "SampleSize"
        FROM "CherryMon"."main"."cal_rs_evaluation_metric"
        WHERE "EvaluationRunId" = ?
          AND "ScopeType" = ?
          AND "ScopeKey" = ?;
        """,
        [run_id, scope_type, scope_key],
    ).fetchall()
    if not rows:
        raise ValueError(
            f"metrics not found: run={run_id} scope={scope_type}/{scope_key}"
        )
    values = {row[0]: row[1] for row in rows}
    sample_size = max(int(row[2] or 0) for row in rows)

    def value(name: str, default=0.0):
        raw = values.get(name, default)
        return raw if raw is not None else default

    return EvaluationMetrics(
        event_count=sample_size,
        touch_count=int(value("touch_count", 0)),
        break_count=int(value("break_count", 0)),
        retest_count=int(value("retest_count", 0)),
        hold_count=int(value("hold_count", 0)),
        touch_rate=float(value("touch_rate")),
        break_rate_given_touch=float(value("break_rate_given_touch")),
        retest_rate_given_break=float(value("retest_rate_given_break")),
        hold_rate_given_touch=float(value("hold_rate_given_touch")),
        avg_bars_to_touch=(
            float(values["avg_bars_to_touch"])
            if values.get("avg_bars_to_touch") is not None
            else None
        ),
        avg_favorable_pct=float(value("avg_favorable_pct")),
        avg_adverse_pct=float(value("avg_adverse_pct")),
        directional_edge_pct=float(value("directional_edge_pct")),
        quality_score=float(value("quality_score")),
    )


def _load_regime_quality(connection, run_id: str) -> dict[str, float]:
    rows = connection.execute(
        """
        SELECT "ScopeKey", "MetricValue"
        FROM "CherryMon"."main"."cal_rs_evaluation_metric"
        WHERE "EvaluationRunId" = ?
          AND "ScopeType" = 'REGIME'
          AND "MetricCode" = 'quality_score'
        ORDER BY "ScopeKey";
        """,
        [run_id],
    ).fetchall()
    return {str(row[0]): float(row[1]) for row in rows if row[1] is not None}


def main() -> None:
    args = _parse_args()
    policy_payload = json.loads(args.policy_json)
    if not isinstance(policy_payload, dict):
        raise ValueError("--policy-json must decode to an object")
    policy = PromotionPolicy(**policy_payload)
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)

    with factory.reader() as connection:
        baseline_run = _load_run(connection, args.baseline_run)
        challenger_run = _load_run(connection, args.challenger_run)

        comparison_keys = ("dataset_start", "dataset_end", "horizon_bars")
        mismatches = [
            key
            for key in comparison_keys
            if baseline_run[key] != challenger_run[key]
        ]
        if mismatches:
            raise ValueError(
                "Promotion runs are not like-for-like; mismatched: "
                f"{mismatches}"
            )
        if baseline_run["status"] != "COMPLETED" or challenger_run["status"] != "COMPLETED":
            raise ValueError("both evaluation runs must be COMPLETED")

        baseline = _load_model(connection, baseline_run["model_version"])
        challenger = _load_model(connection, challenger_run["model_version"])

        decision = promotion_gate(
            baseline=baseline,
            challenger=challenger,
            baseline_validation=_load_scope_metrics(
                connection, args.baseline_run, "SPLIT", "VALIDATION"
            ),
            challenger_validation=_load_scope_metrics(
                connection, args.challenger_run, "SPLIT", "VALIDATION"
            ),
            baseline_test=_load_scope_metrics(
                connection, args.baseline_run, "SPLIT", "TEST"
            ),
            challenger_test=_load_scope_metrics(
                connection, args.challenger_run, "SPLIT", "TEST"
            ),
            baseline_regime_quality=_load_regime_quality(
                connection, args.baseline_run
            ),
            challenger_regime_quality=_load_regime_quality(
                connection, args.challenger_run
            ),
            policy=policy,
        )

    payload = asdict(decision)
    payload["apply_requested"] = bool(args.apply)
    print(json.dumps(payload, indent=2, sort_keys=True))

    if not args.apply:
        return
    if not decision.promote:
        raise RuntimeError(
            "Promotion Gate rejected challenger; no model status changes applied."
        )

    decision_id = args.decision_id or f"RSPROMO_{uuid.uuid4().hex[:16].upper()}"
    with DuckDBUnitOfWork(factory) as uow:
        if uow.rs_evaluations is None:
            raise RuntimeError("UnitOfWork did not initialize R/S evaluation repository")
        repository = uow.rs_evaluations
        repository.record_promotion_decision(
            decision_id=decision_id,
            baseline_version=decision.baseline_version,
            challenger_version=decision.challenger_version,
            evaluation_run_id=args.challenger_run,
            promote=decision.promote,
            validation_quality_delta=decision.validation_quality_delta,
            test_quality_delta=decision.test_quality_delta,
            complexity_delta=decision.complexity_delta,
            worst_regime_delta=decision.worst_regime_delta,
            reasons=decision.reasons,
            policy=asdict(policy),
            notes="Applied by scripts/promote_rs_v2_3_model.py",
        )
        repository.set_model_status(
            decision.challenger_version,
            status="PROMOTION_APPROVED",
            promoted=False,
        )
    print(f"Recorded promotion approval: {decision_id}")


if __name__ == "__main__":
    main()
