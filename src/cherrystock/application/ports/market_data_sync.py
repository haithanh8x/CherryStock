from __future__ import annotations

from pathlib import Path
from typing import Protocol


class MarketDataSyncPort(Protocol):
    """Port for syncing market data snapshots into storage."""

    def upsert_stock_eod(
        self,
        folder_path: Path,
        table_name: str,
        from_last_day: int | None = None,
    ) -> None:
        """Sync one source folder into one target table."""
