from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence


class MarketDataSyncPort(Protocol):
    """Port for syncing AmiBroker market data into storage."""

    def upsert_stock_eod(
        self,
        folder_path: Path,
        table_name: str,
        from_last_day: int | None = None,
    ) -> None:
        """Sync one EOD source folder into one target table."""

    def reset_intraday_targets(self, table_names: Sequence[str]) -> None:
        """Drop/reset all intraday target tables before an init reload."""

    def upsert_intraday(
        self,
        folder_path: Path,
        table_name: str,
        from_last_day: int | None = None,
    ) -> None:
        """Sync one tick-level intraday source folder into one target table."""
