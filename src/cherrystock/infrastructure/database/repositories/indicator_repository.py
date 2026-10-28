from __future__ import annotations

class IndicatorRepository:
    """Storage bootstrap for the simple-name AFL indicator schema.

    Legacy pandas-ta writers are intentionally disabled. The production source
    of truth is Export_Indicator.apx via scripts.indicator_storage_v2.
    """

    def __init__(self, connection) -> None:
        self._connection = connection

    def ensure_storage(self) -> None:
        # Never auto-migrate an existing ConfigId fact: a one-time,
        # backup-preserving local migration is required.
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_indicator_values" (
                Ticker VARCHAR NOT NULL,
                Date DATE NOT NULL,
                IndicatorName VARCHAR NOT NULL,
                Timeframe VARCHAR NOT NULL CHECK (Timeframe IN ('D','W','M')),
                Value DOUBLE,
                UpdatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (Ticker, Date, IndicatorName, Timeframe)
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_indicator_current" (
                Ticker VARCHAR NOT NULL,
                Date DATE NOT NULL,
                IndicatorName VARCHAR NOT NULL,
                Timeframe VARCHAR NOT NULL CHECK (Timeframe IN ('W','M')),
                Value DOUBLE,
                UpdatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (Ticker, IndicatorName, Timeframe)
            )
            """
        )

    def replace_indicator_checkpoint(self, *args, **kwargs) -> int:
        raise RuntimeError(
            "Legacy ConfigId/ComponentCode indicator writer is disabled. "
            "Use scripts.sync_amibroker_indicator_full --mode incremental; "
            "first run scripts.migrate_indicator_storage_v2 locally."
        )
