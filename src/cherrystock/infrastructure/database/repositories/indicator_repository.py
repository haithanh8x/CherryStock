from __future__ import annotations

import pandas as pd


class IndicatorRepository:
    """Write-side repository for the config-driven technical indicator engine."""

    def __init__(self, connection) -> None:
        self._connection = connection

    def ensure_storage(self) -> None:
        """Create indicator engine tables that can be safely bootstrapped at runtime."""
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS "CherryMon"."main"."dim_indicator_component" (
                IndicatorCode VARCHAR NOT NULL,
                ComponentCode VARCHAR NOT NULL,
                ComponentName VARCHAR NOT NULL,
                OutputPrefix VARCHAR,
                SortOrder INTEGER,
                IsPrimary BOOLEAN NOT NULL DEFAULT FALSE,
                IsActive BOOLEAN NOT NULL DEFAULT TRUE,
                PRIMARY KEY (IndicatorCode, ComponentCode)
            );
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS "CherryMon"."main"."dim_indicator_config" (
                ConfigId BIGINT NOT NULL,
                ConfigCode VARCHAR NOT NULL,
                IndicatorCode VARCHAR NOT NULL,
                Timeframe VARCHAR NOT NULL,
                Parameters JSON NOT NULL,
                WarmupBars INTEGER,
                IsEnabled BOOLEAN NOT NULL DEFAULT TRUE,
                Description VARCHAR,
                CreatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UpdatedAt TIMESTAMP,
                PRIMARY KEY (ConfigId),
                UNIQUE (ConfigCode)
            );
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_indicator_values" (
                Ticker VARCHAR NOT NULL,
                Date DATE NOT NULL,
                ConfigId BIGINT NOT NULL,
                ComponentCode VARCHAR NOT NULL,
                Value DOUBLE,
                CalculatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (Ticker, Date, ConfigId, ComponentCode)
            );
            """
        )

    def replace_indicator_checkpoint(
        self,
        dataframe: pd.DataFrame,
        cleanup_dataframe: pd.DataFrame,
        table_name: str = '"CherryMon"."main"."cal_indicator_values"',
    ) -> int:
        """Replace values inside a calculated checkpoint and return rows written."""
        self.ensure_storage()

        cleanup_registered = False
        values_registered = False
        try:
            if cleanup_dataframe is not None and not cleanup_dataframe.empty:
                self._connection.register("df_indicator_cleanup", cleanup_dataframe)
                cleanup_registered = True
                self._connection.execute(
                    f"""
                    DELETE FROM {table_name} AS target
                    WHERE EXISTS (
                        SELECT 1
                        FROM df_indicator_cleanup AS cleanup
                        WHERE cleanup.Ticker = target.Ticker
                          AND cleanup.ConfigId = target.ConfigId
                          AND target.Date >= cleanup.StartDate
                    );
                    """
                )

            if dataframe is None or dataframe.empty:
                return 0

            self._connection.register("df_indicator_values", dataframe)
            values_registered = True
            self._connection.execute(
                f"""
                INSERT INTO {table_name} (
                    Ticker,
                    Date,
                    ConfigId,
                    ComponentCode,
                    Value,
                    CalculatedAt
                )
                SELECT
                    Ticker,
                    Date,
                    ConfigId,
                    ComponentCode,
                    Value,
                    CURRENT_TIMESTAMP
                FROM df_indicator_values
                ON CONFLICT (Ticker, Date, ConfigId, ComponentCode) DO UPDATE SET
                    Value = EXCLUDED.Value,
                    CalculatedAt = EXCLUDED.CalculatedAt;
                """
            )
            return len(dataframe)
        finally:
            if values_registered:
                self._connection.unregister("df_indicator_values")
            if cleanup_registered:
                self._connection.unregister("df_indicator_cleanup")
