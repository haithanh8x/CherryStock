from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class SmartMoneyModel:
    model_id: int
    model_code: str
    model_version: str
    effective_from: date
    effective_to: date | None


class SmartMoneyRepository:
    """DuckDB repository for SmartMoneyScore metadata and checkpoint persistence."""

    FACTOR_TABLE = '"CherryMon"."main"."cal_smart_money_factor_values"'
    SCORE_TABLE = '"CherryMon"."main"."cal_smart_money_ticker_score"'

    def __init__(self, connection) -> None:
        self._connection = connection

    def load_enabled_models(self, model_ids: Iterable[int] | None = None) -> list[SmartMoneyModel]:
        params: list[object] = []
        model_filter = ""
        if model_ids:
            ids = [int(value) for value in model_ids]
            placeholders = ", ".join("?" for _ in ids)
            model_filter = f" AND ModelId IN ({placeholders})"
            params.extend(ids)

        rows = self._connection.execute(
            f"""
            SELECT
                ModelId,
                ModelCode,
                ModelVersion,
                EffectiveFrom,
                EffectiveTo
            FROM "CherryMon"."main"."dim_smart_money_model"
            WHERE IsEnabled = TRUE
              {model_filter}
            ORDER BY ModelId
            """,
            params,
        ).fetchall()

        return [
            SmartMoneyModel(
                model_id=int(row[0]),
                model_code=str(row[1]),
                model_version=str(row[2]),
                effective_from=row[3],
                effective_to=row[4],
            )
            for row in rows
        ]

    def load_factor_catalog(self) -> pd.DataFrame:
        return self._connection.execute(
            """
            SELECT
                FactorId,
                FactorCode,
                ContributionType,
                IsEnabled
            FROM "CherryMon"."main"."dim_smart_money_factor"
            WHERE IsEnabled = TRUE
            ORDER BY FactorId
            """
        ).df()

    def load_model_config(self, model_id: int, as_of_date: date) -> dict[str, object]:
        rows = self._connection.execute(
            """
            WITH ranked AS (
                SELECT
                    ConfigKey,
                    ConfigValue,
                    ValueType,
                    ROW_NUMBER() OVER (
                        PARTITION BY ConfigKey
                        ORDER BY EffectiveFrom DESC
                    ) AS rn
                FROM "CherryMon"."main"."dim_smart_money_config"
                WHERE ModelId = ?
                  AND EffectiveFrom <= ?
                  AND (EffectiveTo IS NULL OR EffectiveTo >= ?)
            )
            SELECT ConfigKey, ConfigValue, ValueType
            FROM ranked
            WHERE rn = 1
            ORDER BY ConfigKey
            """,
            [int(model_id), as_of_date, as_of_date],
        ).fetchall()

        result: dict[str, object] = {}
        for key, raw_value, value_type in rows:
            normalized_type = str(value_type).upper()
            if normalized_type == "FLOAT":
                value: object = float(raw_value)
            elif normalized_type == "INT":
                value = int(raw_value)
            elif normalized_type == "BOOL":
                value = str(raw_value).strip().lower() in {"1", "true", "yes", "y"}
            else:
                value = str(raw_value)
            result[str(key)] = value
        return result

    def load_state_weights(self, model_id: int, as_of_date: date) -> pd.DataFrame:
        return self._connection.execute(
            """
            WITH ranked AS (
                SELECT
                    w.ModelId,
                    w.MarketState,
                    f.FactorCode,
                    w.Weight,
                    ROW_NUMBER() OVER (
                        PARTITION BY w.MarketState, w.FactorId
                        ORDER BY w.EffectiveFrom DESC
                    ) AS rn
                FROM "CherryMon"."main"."dim_smart_money_state_weight" AS w
                INNER JOIN "CherryMon"."main"."dim_smart_money_factor" AS f
                    ON f.FactorId = w.FactorId
                WHERE w.ModelId = ?
                  AND w.EffectiveFrom <= ?
                  AND (w.EffectiveTo IS NULL OR w.EffectiveTo >= ?)
                  AND f.IsEnabled = TRUE
            )
            SELECT MarketState, FactorCode, Weight
            FROM ranked
            WHERE rn = 1
            ORDER BY MarketState, FactorCode
            """,
            [int(model_id), as_of_date, as_of_date],
        ).df()

    def replace_checkpoint(
        self,
        *,
        factor_values: pd.DataFrame,
        ticker_scores: pd.DataFrame,
        cleanup: pd.DataFrame,
    ) -> tuple[int, int]:
        """Replace one logical checkpoint inside the caller-owned transaction."""
        cleanup_registered = False
        factor_registered = False
        score_registered = False
        try:
            if cleanup is not None and not cleanup.empty:
                self._connection.register("df_smart_money_cleanup", cleanup)
                cleanup_registered = True
                self._connection.execute(
                    f"""
                    DELETE FROM {self.FACTOR_TABLE} AS target
                    WHERE EXISTS (
                        SELECT 1
                        FROM df_smart_money_cleanup AS cleanup
                        WHERE cleanup.ModelId = target.ModelId
                          AND cleanup.Ticker = target.Ticker
                          AND target.Date >= cleanup.StartDate
                    );
                    """
                )
                self._connection.execute(
                    f"""
                    DELETE FROM {self.SCORE_TABLE} AS target
                    WHERE EXISTS (
                        SELECT 1
                        FROM df_smart_money_cleanup AS cleanup
                        WHERE cleanup.ModelId = target.ModelId
                          AND cleanup.Ticker = target.Ticker
                          AND target.Date >= cleanup.StartDate
                    );
                    """
                )

            factor_count = 0
            if factor_values is not None and not factor_values.empty:
                self._connection.register("df_smart_money_factor_values", factor_values)
                factor_registered = True
                self._connection.execute(
                    f"""
                    INSERT INTO {self.FACTOR_TABLE} (
                        ModelId,
                        Ticker,
                        Date,
                        FactorId,
                        RawValue,
                        NormalizedValue,
                        DataQuality,
                        SourceCode,
                        CalculatedAt
                    )
                    SELECT
                        ModelId,
                        Ticker,
                        Date,
                        FactorId,
                        RawValue,
                        NormalizedValue,
                        DataQuality,
                        SourceCode,
                        CURRENT_TIMESTAMP
                    FROM df_smart_money_factor_values
                    ON CONFLICT (ModelId, Ticker, Date, FactorId) DO UPDATE SET
                        RawValue = EXCLUDED.RawValue,
                        NormalizedValue = EXCLUDED.NormalizedValue,
                        DataQuality = EXCLUDED.DataQuality,
                        SourceCode = EXCLUDED.SourceCode,
                        CalculatedAt = EXCLUDED.CalculatedAt;
                    """
                )
                factor_count = len(factor_values)

            score_count = 0
            if ticker_scores is not None and not ticker_scores.empty:
                self._connection.register("df_smart_money_ticker_scores", ticker_scores)
                score_registered = True
                self._connection.execute(
                    f"""
                    INSERT INTO {self.SCORE_TABLE} (
                        ModelId,
                        Ticker,
                        Date,
                        SmartMoneyScore,
                        ConfidenceScore,
                        MarketState,
                        FactorCoverage,
                        DataQualityStatus,
                        CalculatedAt
                    )
                    SELECT
                        ModelId,
                        Ticker,
                        Date,
                        SmartMoneyScore,
                        ConfidenceScore,
                        MarketState,
                        FactorCoverage,
                        DataQualityStatus,
                        CURRENT_TIMESTAMP
                    FROM df_smart_money_ticker_scores
                    ON CONFLICT (ModelId, Ticker, Date) DO UPDATE SET
                        SmartMoneyScore = EXCLUDED.SmartMoneyScore,
                        ConfidenceScore = EXCLUDED.ConfidenceScore,
                        MarketState = EXCLUDED.MarketState,
                        FactorCoverage = EXCLUDED.FactorCoverage,
                        DataQualityStatus = EXCLUDED.DataQualityStatus,
                        CalculatedAt = EXCLUDED.CalculatedAt;
                    """
                )
                score_count = len(ticker_scores)

            return factor_count, score_count
        finally:
            if score_registered:
                self._connection.unregister("df_smart_money_ticker_scores")
            if factor_registered:
                self._connection.unregister("df_smart_money_factor_values")
            if cleanup_registered:
                self._connection.unregister("df_smart_money_cleanup")
