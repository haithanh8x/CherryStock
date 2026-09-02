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
        include_source_keys_json: str | None = None,
        exclude_source_keys_json: str | None = None,
        research_indicator_specs_json: str | None = None,
        notes: str | None = None,
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO "CherryMon"."main"."cal_rs_evaluation_run" (
                "EvaluationRunId", "ModelVersion", "DatasetStart", "DatasetEnd",
                "HorizonBars", "TickerCount", "SnapshotCount", "SplitConfigJson",
                "Status", "IncludeSourceKeysJson", "ExcludeSourceKeysJson",
                "ResearchIndicatorSpecsJson", "Notes"
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT ("EvaluationRunId") DO UPDATE SET
                "ModelVersion" = EXCLUDED."ModelVersion",
                "DatasetStart" = EXCLUDED."DatasetStart",
                "DatasetEnd" = EXCLUDED."DatasetEnd",
                "HorizonBars" = EXCLUDED."HorizonBars",
                "TickerCount" = EXCLUDED."TickerCount",
                "SnapshotCount" = EXCLUDED."SnapshotCount",
                "SplitConfigJson" = EXCLUDED."SplitConfigJson",
                "Status" = EXCLUDED."Status",
                "IncludeSourceKeysJson" = EXCLUDED."IncludeSourceKeysJson",
                "ExcludeSourceKeysJson" = EXCLUDED."ExcludeSourceKeysJson",
                "ResearchIndicatorSpecsJson" = EXCLUDED."ResearchIndicatorSpecsJson",
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
                include_source_keys_json,
                exclude_source_keys_json,
                research_indicator_specs_json,
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

    def upsert_source_effectiveness_run(
        self,
        *,
        effectiveness_run_id: str,
        scope_type: str,
        source_key: str,
        source_family: str,
        source_role: str,
        horizon_bars: int,
        baseline_run_id: str,
        ablation_run_id: str,
        standalone_run_id: str | None,
        policy_json: str,
        status: str,
        notes: str | None = None,
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO "CherryMon"."main"."cal_rs_source_effectiveness_run" (
                "EffectivenessRunId", "ScopeType", "SourceKey", "SourceFamily",
                "SourceRole", "HorizonBars", "BaselineRunId", "AblationRunId",
                "StandaloneRunId", "PolicyJson", "Status", "Notes"
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT ("EffectivenessRunId") DO UPDATE SET
                "ScopeType" = EXCLUDED."ScopeType",
                "SourceKey" = EXCLUDED."SourceKey",
                "SourceFamily" = EXCLUDED."SourceFamily",
                "SourceRole" = EXCLUDED."SourceRole",
                "HorizonBars" = EXCLUDED."HorizonBars",
                "BaselineRunId" = EXCLUDED."BaselineRunId",
                "AblationRunId" = EXCLUDED."AblationRunId",
                "StandaloneRunId" = EXCLUDED."StandaloneRunId",
                "PolicyJson" = EXCLUDED."PolicyJson",
                "Status" = EXCLUDED."Status",
                "Notes" = EXCLUDED."Notes";
            """,
            [
                effectiveness_run_id,
                scope_type,
                source_key,
                source_family,
                source_role,
                horizon_bars,
                baseline_run_id,
                ablation_run_id,
                standalone_run_id,
                policy_json,
                status,
                notes,
            ],
        )

    def replace_source_effectiveness(
        self,
        effectiveness_run_id: str,
        dataframe: pd.DataFrame,
    ) -> int:
        self._connection.execute(
            """
            DELETE FROM "CherryMon"."main"."cal_rs_source_effectiveness"
            WHERE "EffectivenessRunId" = ?;
            """,
            [effectiveness_run_id],
        )
        if dataframe is None or dataframe.empty:
            return 0

        required = {
            "EffectivenessRunId", "Ticker", "ScopeType", "SourceKey",
            "SourceFamily", "SourceRole", "HorizonBars", "AttributionMode",
            "MarginalMetric", "LineageEventCount", "ValidationEventCount", "TestEventCount",
            "TouchRate", "HoldRateGivenTouch", "BreakRateGivenTouch",
            "RetestRateGivenBreak", "DirectionalEdgePct", "ValidationQuality",
            "TestQuality", "ValidationMarginalLift", "TestMarginalLift",
            "TemporalStability", "RegimeStability", "ComplexityDelta",
            "EffectivenessScore", "Recommendation", "EvidenceJson",
        }
        missing = required - set(dataframe.columns)
        if missing:
            raise ValueError(
                "source-effectiveness dataframe missing columns: "
                f"{sorted(missing)}"
            )

        self._connection.register("df_rs_source_effectiveness", dataframe)
        try:
            self._connection.execute(
                """
                INSERT INTO "CherryMon"."main"."cal_rs_source_effectiveness" (
                    "EffectivenessRunId", "Ticker", "ScopeType", "SourceKey",
                    "SourceFamily", "SourceRole", "HorizonBars",
                    "AttributionMode", "MarginalMetric", "LineageEventCount",
                    "ValidationEventCount", "TestEventCount", "TouchRate",
                    "HoldRateGivenTouch", "BreakRateGivenTouch",
                    "RetestRateGivenBreak", "DirectionalEdgePct",
                    "ValidationQuality", "TestQuality",
                    "ValidationMarginalLift", "TestMarginalLift",
                    "TemporalStability", "RegimeStability", "ComplexityDelta",
                    "EffectivenessScore", "Recommendation", "EvidenceJson"
                )
                SELECT
                    "EffectivenessRunId", "Ticker", "ScopeType", "SourceKey",
                    "SourceFamily", "SourceRole", "HorizonBars",
                    "AttributionMode", "MarginalMetric", "LineageEventCount",
                    "ValidationEventCount", "TestEventCount", "TouchRate",
                    "HoldRateGivenTouch", "BreakRateGivenTouch",
                    "RetestRateGivenBreak", "DirectionalEdgePct",
                    "ValidationQuality", "TestQuality",
                    "ValidationMarginalLift", "TestMarginalLift",
                    "TemporalStability", "RegimeStability", "ComplexityDelta",
                    "EffectivenessScore", "Recommendation", "EvidenceJson"
                FROM df_rs_source_effectiveness;
                """
            )
        finally:
            self._connection.unregister("df_rs_source_effectiveness")
        return len(dataframe)

    def mark_source_effectiveness_run_complete(
        self,
        effectiveness_run_id: str,
        *,
        status: str = "COMPLETED",
    ) -> None:
        self._connection.execute(
            """
            UPDATE "CherryMon"."main"."cal_rs_source_effectiveness_run"
            SET "Status" = ?, "CompletedAt" = CURRENT_TIMESTAMP
            WHERE "EffectivenessRunId" = ?;
            """,
            [status, effectiveness_run_id],
        )

    def record_source_promotion_decision(
        self,
        *,
        decision_id: str,
        effectiveness_run_id: str,
        source_key: str,
        source_family: str,
        source_role: str,
        horizon_bars: int,
        outcome: str,
        ticker_count: int,
        positive_ticker_count: int,
        positive_ticker_ratio: float,
        avg_effectiveness_score: float,
        avg_validation_lift: float,
        avg_test_lift: float,
        avg_temporal_stability: float,
        avg_regime_stability: float | None,
        max_complexity_delta: float,
        reasons: tuple[str, ...],
        policy: dict[str, Any],
        applied: bool,
        notes: str | None = None,
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO "CherryMon"."main"."sys_rs_source_promotion_audit" (
                "DecisionId", "EffectivenessRunId", "SourceKey",
                "SourceFamily", "SourceRole", "HorizonBars", "Outcome",
                "TickerCount", "PositiveTickerCount", "PositiveTickerRatio",
                "AvgEffectivenessScore", "AvgValidationLift", "AvgTestLift",
                "AvgTemporalStability", "AvgRegimeStability",
                "MaxComplexityDelta", "ReasonsJson", "PolicyJson",
                "Applied", "Notes"
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT ("DecisionId") DO UPDATE SET
                "EffectivenessRunId" = EXCLUDED."EffectivenessRunId",
                "SourceKey" = EXCLUDED."SourceKey",
                "SourceFamily" = EXCLUDED."SourceFamily",
                "SourceRole" = EXCLUDED."SourceRole",
                "HorizonBars" = EXCLUDED."HorizonBars",
                "Outcome" = EXCLUDED."Outcome",
                "TickerCount" = EXCLUDED."TickerCount",
                "PositiveTickerCount" = EXCLUDED."PositiveTickerCount",
                "PositiveTickerRatio" = EXCLUDED."PositiveTickerRatio",
                "AvgEffectivenessScore" = EXCLUDED."AvgEffectivenessScore",
                "AvgValidationLift" = EXCLUDED."AvgValidationLift",
                "AvgTestLift" = EXCLUDED."AvgTestLift",
                "AvgTemporalStability" = EXCLUDED."AvgTemporalStability",
                "AvgRegimeStability" = EXCLUDED."AvgRegimeStability",
                "MaxComplexityDelta" = EXCLUDED."MaxComplexityDelta",
                "ReasonsJson" = EXCLUDED."ReasonsJson",
                "PolicyJson" = EXCLUDED."PolicyJson",
                "Applied" = EXCLUDED."Applied",
                "Notes" = EXCLUDED."Notes";
            """,
            [
                decision_id,
                effectiveness_run_id,
                source_key,
                source_family,
                source_role,
                horizon_bars,
                outcome,
                ticker_count,
                positive_ticker_count,
                positive_ticker_ratio,
                avg_effectiveness_score,
                avg_validation_lift,
                avg_test_lift,
                avg_temporal_stability,
                avg_regime_stability,
                max_complexity_delta,
                json.dumps(list(reasons), sort_keys=True),
                json.dumps(policy, sort_keys=True),
                applied,
                notes,
            ],
        )

