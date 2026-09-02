"""Calculate and persist R/S V2.4 per-ticker Source Effectiveness.

Prerequisite:
    python scripts/run_rs_v2_4_migration.py

Example:
    python scripts/run_rs_v2_4_source_effectiveness.py \
        --baseline-run RSV24_BASELINE_H20 \
        --ablation-run RSV24_DROP_MA50_D_H20 \
        --source-key MA50_D \
        --source-family TREND_AVERAGE \
        --source-role LEVEL \
        --scope-type SOURCE_CONFIG \
        --run-id RSEFF_MA50_D_H20
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from calcEngine.rsEvaluation import LevelEvaluationEvent  # noqa: E402
from calcEngine.rsSourceEffectiveness import (  # noqa: E402
    SourceEffectivenessPolicy,
    calculate_source_effectiveness,
    effectiveness_to_dataframe,
)
from calcEngine.rsSourceIdentity import canonical_source_key  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="R/S V2.4 Source Effectiveness")
    parser.add_argument("--baseline-run", required=True)
    parser.add_argument("--ablation-run", required=True)
    parser.add_argument("--standalone-run", default=None)
    parser.add_argument("--source-key", required=True)
    parser.add_argument("--source-family", required=True)
    parser.add_argument(
        "--source-role",
        required=True,
        choices=("LEVEL", "CONTEXT", "CONFIRMATION"),
    )
    parser.add_argument(
        "--scope-type",
        default="SOURCE_CONFIG",
        choices=("SOURCE_CONFIG", "SOURCE_FAMILY"),
    )
    parser.add_argument("--policy-json", default="{}")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--notes", default=None)
    return parser.parse_args()


def _ensure_v24_tables(connection) -> None:
    required = {
        "cal_rs_source_effectiveness_run",
        "cal_rs_source_effectiveness",
        "sys_rs_source_promotion_audit",
    }
    rows = connection.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE lower(table_catalog) = 'cherrymon'
          AND lower(table_schema) = 'main'
          AND lower(table_name) IN (
              'cal_rs_source_effectiveness_run',
              'cal_rs_source_effectiveness',
              'sys_rs_source_promotion_audit'
          );
        """
    ).fetchall()
    found = {str(row[0]).lower() for row in rows}
    missing = {value.lower() for value in required} - found
    if missing:
        raise RuntimeError(
            "R/S V2.4 tables missing: "
            f"{sorted(missing)}. Run scripts/run_rs_v2_4_migration.py first."
        )


def _load_run(connection, run_id: str) -> dict:
    row = connection.execute(
        """
        SELECT
            "EvaluationRunId", "ModelVersion", "DatasetStart", "DatasetEnd",
            "HorizonBars", "SplitConfigJson", "Status",
            "IncludeSourceKeysJson", "ExcludeSourceKeysJson"
        FROM "CherryMon"."main"."cal_rs_evaluation_run"
        WHERE "EvaluationRunId" = ?;
        """,
        [run_id],
    ).fetchone()
    if row is None:
        raise ValueError(f"evaluation run not found: {run_id}")
    return {
        "run_id": str(row[0]),
        "model_version": str(row[1]),
        "dataset_start": row[2],
        "dataset_end": row[3],
        "horizon_bars": int(row[4]),
        "split_config_json": str(row[5]),
        "status": str(row[6]),
        "include_source_keys_json": row[7],
        "exclude_source_keys_json": row[8],
    }


def _assert_compatible(baseline: dict, ablation: dict) -> None:
    keys = ("dataset_start", "dataset_end", "horizon_bars", "split_config_json")
    mismatches = [key for key in keys if baseline[key] != ablation[key]]
    if mismatches:
        raise ValueError(
            "baseline and ablation runs are not like-for-like; "
            f"mismatched={mismatches}"
        )
    if baseline["status"] != "COMPLETED" or ablation["status"] != "COMPLETED":
        raise ValueError("baseline and ablation runs must both be COMPLETED")


def _load_complexity(connection, model_version: str) -> float:
    row = connection.execute(
        """
        SELECT "ComplexityScore"
        FROM "CherryMon"."main"."dim_rs_model_version"
        WHERE "ModelVersion" = ?;
        """,
        [model_version],
    ).fetchone()
    if row is None:
        raise ValueError(f"model version not found: {model_version}")
    return float(row[0] or 0.0)


def _to_date(value):
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return value.date() if hasattr(value, "date") else date.fromisoformat(str(value))


def _load_events(connection, run_id: str) -> list[LevelEvaluationEvent]:
    rows = connection.execute(
        """
        SELECT
            "ModelVersion", "Ticker", "AsOfDate", "LevelRank", "LevelType",
            "LevelPrice", "StrengthScore", "HorizonEndDate", "Touched",
            "TouchDate", "Broken", "BreakDate", "Retested", "RetestDate",
            "Held", "BarsToTouch", "MaxFavorablePct", "MaxAdversePct",
            "SourceCount", "SourceFamilyCount", "SourcesJson",
            "SourceFamiliesJson", "Regime", "Split"
        FROM "CherryMon"."main"."cal_rs_evaluation_event"
        WHERE "EvaluationRunId" = ?
        ORDER BY "Ticker", "AsOfDate", "LevelRank";
        """,
        [run_id],
    ).fetchall()

    events: list[LevelEvaluationEvent] = []
    for row in rows:
        events.append(
            LevelEvaluationEvent(
                model_version=str(row[0]),
                ticker=str(row[1]),
                as_of_date=_to_date(row[2]),
                level_rank=str(row[3]),
                level_type=str(row[4]),
                level_price=float(row[5]),
                strength_score=float(row[6] or 0.0),
                horizon_end_date=_to_date(row[7]),
                touched=bool(row[8]),
                touch_date=_to_date(row[9]),
                broken=bool(row[10]),
                break_date=_to_date(row[11]),
                retested=bool(row[12]),
                retest_date=_to_date(row[13]),
                held=bool(row[14]),
                bars_to_touch=int(row[15]) if row[15] is not None else None,
                max_favorable_pct=float(row[16] or 0.0),
                max_adverse_pct=float(row[17] or 0.0),
                source_count=int(row[18] or 0),
                source_family_count=int(row[19] or 0),
                sources=tuple(json.loads(row[20] or "[]")),
                source_families=tuple(json.loads(row[21] or "[]")),
                regime=str(row[22]) if row[22] is not None else None,
                split=str(row[23]) if row[23] is not None else None,
            )
        )
    return events


def main() -> None:
    args = _parse_args()
    policy_payload = json.loads(args.policy_json)
    if not isinstance(policy_payload, dict):
        raise ValueError("--policy-json must decode to an object")
    policy = SourceEffectivenessPolicy(**policy_payload)

    source_key = (
        str(args.source_family).upper()
        if args.scope_type == "SOURCE_FAMILY"
        else canonical_source_key(args.source_key)
    )
    source_family = str(args.source_family).upper()
    source_role = str(args.source_role).upper()
    run_id = args.run_id or f"RSEFF_{uuid.uuid4().hex[:16].upper()}"

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with factory.reader() as connection:
        _ensure_v24_tables(connection)
        baseline = _load_run(connection, args.baseline_run)
        ablation = _load_run(connection, args.ablation_run)
        _assert_compatible(baseline, ablation)

        if args.standalone_run:
            standalone = _load_run(connection, args.standalone_run)
            _assert_compatible(baseline, standalone)

        baseline_events = _load_events(connection, args.baseline_run)
        ablation_events = _load_events(connection, args.ablation_run)
        if not baseline_events or not ablation_events:
            raise ValueError("baseline and ablation runs must both contain events")

        baseline_complexity = _load_complexity(connection, baseline["model_version"])
        ablation_complexity = _load_complexity(connection, ablation["model_version"])
        complexity_delta = baseline_complexity - ablation_complexity

    tickers = sorted(
        {event.ticker for event in baseline_events}
        & {event.ticker for event in ablation_events}
    )
    if not tickers:
        raise ValueError("baseline and ablation runs have no common tickers")

    records = [
        calculate_source_effectiveness(
            ticker=ticker,
            scope_type=args.scope_type,
            source_key=source_key,
            source_family=source_family,
            source_role=source_role,
            horizon_bars=baseline["horizon_bars"],
            baseline_events=baseline_events,
            ablation_events=ablation_events,
            complexity_delta=complexity_delta,
            policy=policy,
        )
        for ticker in tickers
    ]

    if source_role == "LEVEL" and not any(record.lineage_event_count for record in records):
        raise ValueError(
            f"LEVEL source has no historical lineage in baseline: {source_key}"
        )

    dataframe = effectiveness_to_dataframe(run_id, records)
    with DuckDBUnitOfWork(factory) as uow:
        if uow.rs_evaluations is None:
            raise RuntimeError("UnitOfWork did not initialize R/S evaluation repository")
        repository = uow.rs_evaluations
        repository.upsert_source_effectiveness_run(
            effectiveness_run_id=run_id,
            scope_type=args.scope_type,
            source_key=source_key,
            source_family=source_family,
            source_role=source_role,
            horizon_bars=baseline["horizon_bars"],
            baseline_run_id=args.baseline_run,
            ablation_run_id=args.ablation_run,
            standalone_run_id=args.standalone_run,
            policy_json=json.dumps(asdict(policy), sort_keys=True),
            status="RUNNING",
            notes=args.notes,
        )
        repository.replace_source_effectiveness(run_id, dataframe)
        repository.mark_source_effectiveness_run_complete(run_id)

    print(
        json.dumps(
            {
                "effectiveness_run_id": run_id,
                "source_key": source_key,
                "source_family": source_family,
                "source_role": source_role,
                "scope_type": args.scope_type,
                "horizon_bars": baseline["horizon_bars"],
                "baseline_run": args.baseline_run,
                "ablation_run": args.ablation_run,
                "ticker_count": len(records),
                "recommendations": {
                    record.ticker: record.recommendation for record in records
                },
                "scores": {
                    record.ticker: record.effectiveness_score for record in records
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
