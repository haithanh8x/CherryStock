from __future__ import annotations

from pathlib import Path

from cherrystock.application.ports.market_data_sync import MarketDataSyncPort


class SyncAmiBrokerMarketDataService:
    """Application service for syncing AmiBroker EOD/Intraday market data."""

    def __init__(self, sync_port: MarketDataSyncPort):
        self._sync_port = sync_port

    def sync_targets(
        self,
        targets: tuple[tuple[Path, str], ...],
        from_last_day: int | None = None,
    ) -> None:
        total_categories = len(targets)
        for index, (folder_path, table_name) in enumerate(targets, start=1):
            print(f"[{index}/{total_categories}] Tiến hành xử lý dữ liệu cho bảng: {table_name}")
            self._sync_port.upsert_stock_eod(
                folder_path=folder_path,
                table_name=table_name,
                from_last_day=from_last_day,
            )
            print("-" * 50)

    def sync_eod(
        self,
        eod_targets: tuple[tuple[Path, str], ...],
        from_last_day: int | None = None,
    ) -> None:
        self.sync_targets(targets=eod_targets, from_last_day=from_last_day)

    def sync_intraday(
        self,
        intraday_targets: tuple[tuple[Path, str], ...],
        from_last_day: int | None = None,
    ) -> None:
        self.sync_targets(targets=intraday_targets, from_last_day=from_last_day)
