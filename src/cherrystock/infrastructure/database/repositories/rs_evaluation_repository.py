from __future__ import annotations

import json
from typing import Any

import pandas as pd


class RSEvaluationRepository:
    """Write-side repository for R/S V2.3 evaluation and model governance.

    Required tables are created by:
    src/DuckDB/sql/rs_v2_3_evaluation_governance.sql
    """

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def upsert_model_version(
        self,
        *,
        model_version: str,
        parent_version: str | None,
        status: str,
        signature: str,
        config_json: str,
        complexity_score: float | None,
        notes: str | None = None,
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO "CherryMon"."main"."dim_rs_model_version" (
                "ModelVersion", "ParentVersion", "Status", "Signature",
                "ConfigJson", "ComplexityScore", "Notes"
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT ("ModelVersion") DO UPDATE SET
                "ParentVersion" = EXCLUDED."ParentVersion",
                "Status" = EXCLUDED."Status",
                "Signature" = EXCLUDED."Signature",
                "ConfigJson" = EXCLUDED."ConfigJson",
                "ComplexityScore" = EXCLUDED."ComplexityScore",
                "Notes" = EXCLUDED."Notes";
            """,
            [
                model_version,
                parent_version,
                status,
                signature,
                config_json,
                complexity_score,
                notes,
            ],
        )

    def upsert_evaluation_run(
        self,
        *,
        evaluation_run_id: str,
        model_version: str,
        dataset_start,
        dataset_end,
        horizon_bars: int,
        ticker_count: int,
        snapshot_count: int,
        split_config_json: str,
        status: str,
        notes: str | None = None,
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO "CherryMon"."main"."cal_rs_evaluation_run" (
                "EvaluationRunId", "ModelVersion", "DatasetStart", "DatasetEnd",
                "HorizonBars", "TickerCount", "SnapshotCount", "SplitConfigJson",
                "Status", "Notes"
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT ("EvaluationRunId") DO UPDATE SET
                "ModelVersion" = EXCLUDED."ModelVersion",
                "DatasetStart" = EXCLUDED."DatasetStart",
                "DatasetEnd" = EXCLUDED."DatasetEnd",
                "HorizonBars" = EXCLUDED."HorizonBars",
                "TickerCount" = EXCLUDED."TickerCount",
                "SnapshotCount" = EXCLUDED."SnapshotCount",
                "SplitConfigJson" = EXCLUDED."SplitConfigJson",
                "Status" = EXCLUDED."Status",
                "Notes" = EXCLUDED."Notes";
            """,
            [
                evaluation_run_id,
                model_version,
                dataset_start,
                dataset_end,
                horizon_bars,
                ticker_count,
                snapshot_count,
                split_config_json,
                status,
                notes,
            ],
        )

    def mark_evaluation_run_complete(
        self,
        evaluation_run_id: str,
        *,
        status: str = "COMPLETED",
    ) -> None:
        self._connection.execute(
            """
            UPDATE "CherryMon"."main"."cal_rs_evaluation_run"
            SET "Status" = ?, "CompletedAt" = CURRENT_TIMESTAMP
            WHERE "EvaluationRunId" = ?;
            """,
            [status, evaluation_run_id],
        )

    def replace_events(
        self,
        evaluation_run_id: str,
        dataframe: pd.DataFrame,
    ) -> int:
        self._connection.execute(
            """
            DELETE FROM "CherryMon"."main"."cal_rs_evaluation_event"
            WHERE "EvaluationRunId" = ?;
            """,
            [evaluation_run_id],
        )
        if dataframe is None or dataframe.empty:
            return 0

        required = {
            "EvaluationRunId", "ModelVersion", "Ticker", "AsOfDate", "LevelRank",
            "LevelType", "LevelPrice", "StrengthScore", "HorizonEndDate", "Touched",
            "TouchDate", "Broken", "BreakDate", "Retested", "RetestDate", "Held",
            "BarsToTouch", "MaxFavorablePct", "MaxAdversePct", "SourceCount",
            "SourceFamilyCount", "SourcesJson", "SourceFamiliesJson", "Regime", "Split",
        }
        missing = required - set(dataframe.columns)
        if missing:
            raise ValueError(f"evaluation event dataframe missing columns: {sorted(missing)}")

        self._connection.register("df_rs_evaluation_event", dataframe)
        try:
            self._connection.execute(
                """
                INSERT INTO "CherryMon"."main"."cal_rs_evaluation_event" (
                    "EvaluationRunId", "ModelVersion", "Ticker", "AsOfDate",
                    "LevelRank", "LevelType", "LevelPrice", "StrengthScore",
                    "HorizonEndDate", "Touched", "TouchDate", "Broken", "BreakDate",
                    "Retested", "RetestDate", "Held", "BarsToTouch",
                    "MaxFavorablePct", "MaxAdversePct", "SourceCount",
                    "SourceFamilyCount", "SourcesJson", "SourceFamiliesJson",
                    "Regime", "Split"
                )
                SELECT
                    "EvaluationRunId", "ModelVersion", "Ticker", "AsOfDate",
                    "LevelRank", "LevelType", "LevelPrice", "StrengthScore",
                    "HorizonEndDate", "Touched", "TouchDate", "Broken", "BreakDate",
                    "Retested", "RetestDate", "Held", "BarsToTouch",
                    "MaxFavorablePct", "MaxAdversePct", "SourceCount",
                    "SourceFamilyCount", "SourcesJson", "SourceFamiliesJson",
                    "Regime", "Split"
                FROM df_rs_evaluation_event;
                """
            )
        finally:
            self._connection.unregister("df_rs_evaluation_event")
        return len(dataframe)

    def replace_metrics(
        self,
        evaluation_run_id: str,
        dataframe: pd.DataFrame,
    ) -> int:
        self._connection.execute(
            """
            DELETE FROM "CherryMon"."main"."cal_rs_evaluation_metric"
            WHERE "EvaluationRunId" = ?;
            """,
            [evaluation_run_id],
        )
        if dataframe is None or dataframe.empty:
            return 0

        required = {
            "EvaluationRunId", "ScopeType", "ScopeKey",
            "MetricCode", "MetricValue", "SampleSize",
        }
        missing = required - set(dataframe.columns)
        if missing:
            raise ValueError(f"evaluation metric dataframe missing columns: {sorted(missing)}")

        self._connection.register("df_rs_evaluation_metric", dataframe)
        try:
            self._connection.execute(
                """
                INSERT INTO "CherryMon"."main"."cal_rs_evaluation_metric" (
                    "EvaluationRunId", "ScopeType", "ScopeKey",
                    "MetricCode", "MetricValue", "SampleSize"
                )
                SELECT
                    "EvaluationRunId", "ScopeType", "ScopeKey",
                    "MetricCode", "MetricValue", "SampleSize"
                FROM df_rs_evaluation_metric;
                """
            )
        finally:
            self._connection.unregister("df_rs_evaluation_metric")
        return len(dataframe)

    def set_model_status(
        self,
        model_version: str,
        *,
        status: str,
        promoted: bool = False,
    ) -> None:
        self._connection.execute(
            """
            UPDATE "CherryMon"."main"."dim_rs_model_version"
            SET "Status" = ?,
                "PromotedAt" = CASE
                    WHEN ? THEN CURRENT_TIMESTAMP
                    ELSE "PromotedAt"
                END
            WHERE "ModelVersion" = ?;
            """,
            [status, promoted, model_version],
        )

    def record_promotion_decision(
        self,
        *,
        decision_id: str,
        baseline_version: str,
        challenger_version: str,
        evaluation_run_id: str | None,
        promote: bool,
        validation_quality_delta: float,
        test_quality_delta: float,
        complexity_delta: float,
        worst_regime_delta: float,
        reasons: tuple[str, ...],
        policy: dict[str, Any],
        notes: str | None = None,
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO "CherryMon"."main"."sys_rs_model_promotion_audit" (
                "DecisionId", "BaselineVersion", "ChallengerVersion",
                "EvaluationRunId", "Promote", "ValidationQualityDelta",
                "TestQualityDelta", "ComplexityDelta", "WorstRegimeDelta",
                "ReasonsJson", "PolicyJson", "Notes"
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT ("DecisionId") DO UPDATE SET
                "BaselineVersion" = EXCLUDED."BaselineVersion",
                "ChallengerVersion" = EXCLUDED."ChallengerVersion",
                "EvaluationRunId" = EXCLUDED."EvaluationRunId",
                "Promote" = EXCLUDED."Promote",
                "ValidationQualityDelta" = EXCLUDED."ValidationQualityDelta",
                "TestQualityDelta" = EXCLUDED."TestQualityDelta",
                "ComplexityDelta" = EXCLUDED."ComplexityDelta",
                "WorstRegimeDelta" = EXCLUDED."WorstRegimeDelta",
                "ReasonsJson" = EXCLUDED."ReasonsJson",
                "PolicyJson" = EXCLUDED."PolicyJson",
                "Notes" = EXCLUDED."Notes";
            """,
            [
                decision_id,
                baseline_version,
                challenger_version,
                evaluation_run_id,
                promote,
                validation_quality_delta,
                test_quality_delta,
                complexity_delta,
                worst_regime_delta,
                json.dumps(list(reasons), sort_keys=True),
                json.dumps(policy, sort_keys=True),
                notes,
            ],
        )
