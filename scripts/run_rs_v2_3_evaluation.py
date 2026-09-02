"""Run and persist an R/S V2.3 historical evaluation.

Prerequisite:
    execute src/DuckDB/sql/rs_v2_3_evaluation_governance.sql

Example:
    python scripts/run_rs_v2_3_evaluation.py \
        --tickers MWG,FPT,HPG \
        --start 2026-01-01 \
        --end 2026-08-28 \
        --snapshot-step 5
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from calcEngine.levelLadder import (  # noqa: E402
    RS_MODEL_VERSION,
    StrengthConfig,
    StructuralSourceConfig,
    build_level_ladder,
)
from calcEngine.rsEvaluation import (  # noqa: E402
    EvaluationConfig,
    RSModelSpec,
    TemporalSplitConfig,
    assign_temporal_splits,
    calculate_complexity_score,
    classify_market_regime,
    evaluate_ladder_result,
    events_to_dataframe,
    metrics_to_dataframe,
)
from calcEngine.volumeProfile import VolumeProfileConfig  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


DEFAULT_SOURCES = (
    "MA",
    "BB",
    "SWING",
    "PREVIOUS_HL",
    "52W_HL",
    "VOLUME_PROFILE",
    "ATR",
    "RSI",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run R/S V2.3 historical evaluation")
    parser.add_argument("--tickers", default="MWG", help="Comma-separated tickers")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--snapshot-step", type=int, default=5, help="Every N trading bars")
    parser.add_argument("--horizon-bars", type=int, default=20)
    parser.add_argument("--model-version", default=RS_MODEL_VERSION)
    parser.add_argument(
        "--enabled-sources",
        default=",".join(DEFAULT_SOURCES),
        help="Comma-separated R/S provider keys",
    )
    parser.add_argument("--strength-config-json", default="{}")
    parser.add_argument("--volume-profile-config-json", default="{}")
    parser.add_argument("--structural-config-json", default="{}")
    parser.add_argument("--run-id", default=None)
    return parser.parse_args()


def _parse_json_object(raw: str, name: str) -> dict:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{name} must decode to a JSON object")
    return value


def _ensure_v23_tables(connection) -> None:
    required = {
        "dim_rs_model_version",
        "cal_rs_evaluation_run",
        "cal_rs_evaluation_event",
        "cal_rs_evaluation_metric",
        "sys_rs_model_promotion_audit",
    }
    rows = connection.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE lower(table_catalog) = 'cherrymon'
          AND table_schema = 'main'
          AND table_name IN (
              'dim_rs_model_version',
              'cal_rs_evaluation_run',
              'cal_rs_evaluation_event',
              'cal_rs_evaluation_metric',
              'sys_rs_model_promotion_audit'
          );
        """
    ).fetchall()
    found = {row[0] for row in rows}
    missing = required - found
    if missing:
        raise RuntimeError(
            "R/S V2.3 evaluation tables missing: "
            f"{sorted(missing)}. Execute "
            "src/DuckDB/sql/rs_v2_3_evaluation_governance.sql first."
        )


def _load_raw_history(
    connection,
    tickers: tuple[str, ...],
    future_end_date: date,
) -> pd.DataFrame:
    placeholders = ",".join("?" for _ in tickers)
    return connection.execute(
        f"""
        SELECT "Ticker", "Date", "High", "Low", "Close", "Volume"
        FROM "CherryMon"."main"."raw_stock_eod"
        WHERE "Ticker" IN ({placeholders})
          AND "Date" <= ?
        ORDER BY "Ticker", "Date";
        """,
        [*tickers, future_end_date],
    ).df()


def main() -> None:
    args = _parse_args()
    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)
    if end_date < start_date:
        raise ValueError("--end must be >= --start")
    if args.snapshot_step <= 0:
        raise ValueError("--snapshot-step must be > 0")

    tickers = tuple(
        sorted({item.strip().upper() for item in args.tickers.split(",") if item.strip()})
    )
    if not tickers:
        raise ValueError("at least one ticker is required")

    enabled_sources = tuple(
        sorted(
            {
                item.strip().upper()
                for item in args.enabled_sources.split(",")
                if item.strip()
            }
        )
    )
    strength_kwargs = _parse_json_object(args.strength_config_json, "strength-config-json")
    profile_kwargs = _parse_json_object(
        args.volume_profile_config_json, "volume-profile-config-json"
    )
    structural_kwargs = _parse_json_object(
        args.structural_config_json, "structural-config-json"
    )

    strength_config = StrengthConfig(**strength_kwargs)
    volume_profile_config = VolumeProfileConfig(**profile_kwargs)
    structural_config = StructuralSourceConfig(**structural_kwargs)
    evaluation_config = EvaluationConfig(horizon_bars=args.horizon_bars)
    split_config = TemporalSplitConfig()
    run_id = args.run_id or f"RSV23_{uuid.uuid4().hex[:16].upper()}"

    model = RSModelSpec(
        model_version=args.model_version,
        enabled_sources=enabled_sources,
        strength_config=strength_kwargs,
        volume_profile_config=profile_kwargs,
        structural_config=structural_kwargs,
        parent_version="RS_V2_2_PROD",
        notes="Generated by scripts/run_rs_v2_3_evaluation.py",
    )

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)

    # Historical calculation is read-only and may be long-running. Keep it
    # outside the writer transaction to avoid holding a DuckDB write lock.
    with factory.reader() as connection:
        _ensure_v23_tables(connection)

        future_end_date = end_date + timedelta(
            days=max(60, evaluation_config.horizon_bars * 4)
        )
        history = _load_raw_history(connection, tickers, future_end_date)
        if history.empty:
            raise RuntimeError("No raw_stock_eod history found for requested tickers")

        snapshot_dates: list[date] = []
        snapshot_count = 0
        ticker_frames: dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            frame = history[history["Ticker"] == ticker].copy()
            if frame.empty:
                raise RuntimeError(f"No raw_stock_eod history for ticker={ticker}")
            frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
            frame = frame.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
            ticker_frames[ticker] = frame
            eligible = frame[
                (frame["Date"].dt.date >= start_date)
                & (frame["Date"].dt.date <= end_date)
            ]
            sampled = eligible.iloc[:: args.snapshot_step]
            snapshot_count += len(sampled)
            snapshot_dates.extend(pd.Timestamp(value).date() for value in sampled["Date"])

        split_map = assign_temporal_splits(snapshot_dates, config=split_config)
        unique_snapshots = sorted(set(snapshot_dates))
        if len(unique_snapshots) < 3:
            raise ValueError(
                "V2.3 evaluation requires at least 3 unique snapshot dates "
                "for TRAIN/VALIDATION/TEST"
            )

        events = []
        for ticker in tickers:
            frame = ticker_frames[ticker]
            eligible = frame[
                (frame["Date"].dt.date >= start_date)
                & (frame["Date"].dt.date <= end_date)
            ].iloc[:: args.snapshot_step]

            for raw_date in eligible["Date"]:
                as_of_date = pd.Timestamp(raw_date).date()
                result = build_level_ladder(
                    ticker,
                    as_of_date=as_of_date,
                    enabled_sources=enabled_sources,
                    strength_config=strength_config,
                    structural_config=structural_config,
                    volume_profile_config=volume_profile_config,
                    model_version=model.model_version,
                    connection=connection,
                )
                regime = classify_market_regime(
                    frame,
                    as_of_date=as_of_date,
                    config=evaluation_config,
                )
                events.extend(
                    evaluate_ladder_result(
                        model_version=model.model_version,
                        result=result,
                        future_history=frame,
                        config=evaluation_config,
                        regime=regime,
                        split=split_map.get(as_of_date),
                    )
                )

    event_df = events_to_dataframe(run_id, events)
    metric_df = metrics_to_dataframe(run_id, events)

    # Persist all evaluation artifacts atomically in one short writer UoW.
    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None or uow.rs_evaluations is None:
            raise RuntimeError("UnitOfWork did not initialize R/S evaluation dependencies.")
        repository = uow.rs_evaluations
        repository.upsert_model_version(
            model_version=model.model_version,
            parent_version=model.parent_version,
            status="CANDIDATE" if model.model_version != RS_MODEL_VERSION else "BASELINE",
            signature=model.signature,
            config_json=model.canonical_json(),
            complexity_score=calculate_complexity_score(model),
            notes=model.notes,
        )
        repository.upsert_evaluation_run(
            evaluation_run_id=run_id,
            model_version=model.model_version,
            dataset_start=start_date,
            dataset_end=end_date,
            horizon_bars=evaluation_config.horizon_bars,
            ticker_count=len(tickers),
            snapshot_count=snapshot_count,
            split_config_json=json.dumps(asdict(split_config), sort_keys=True),
            status="COMPLETED",
            notes=f"enabled_sources={','.join(enabled_sources)}",
        )
        repository.replace_events(run_id, event_df)
        repository.replace_metrics(run_id, metric_df)
        repository.mark_evaluation_run_complete(run_id)

    print(
        json.dumps(
            {
                "evaluation_run_id": run_id,
                "model_version": model.model_version,
                "signature": model.signature,
                "tickers": list(tickers),
                "snapshots": snapshot_count,
                "events": len(events),
                "metrics": len(metric_df),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
