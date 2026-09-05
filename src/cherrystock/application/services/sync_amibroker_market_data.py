from __future__ import annotations

from pathlib import Path

from cherrystock.application.ports.market_data_sync import MarketDataSyncPort


class SyncAmiBrokerMarketDataService:
    """Application service for syncing AmiBroker EOD and tick-level intraday data."""

    def __init__(self, sync_port: MarketDataSyncPort):
        self._sync_port = sync_port

    def sync_eod(
        self,
        eod_targets: tuple[tuple[Path, str], ...],
        from_last_day: int | None = None,
    ) -> None:
        total_categories = len(eod_targets)
        for index, (folder_path, table_name) in enumerate(eod_targets, start=1):
            print(f"[{index}/{total_categories}] Tiến hành xử lý dữ liệu EOD cho bảng: {table_name}")
            self._sync_port.upsert_stock_eod(
                folder_path=folder_path,
                table_name=table_name,
                from_last_day=from_last_day,
            )
            print("-" * 50)

    def sync_intraday(
        self,
        intraday_targets: tuple[tuple[Path, str], ...],
        from_last_day: int | None = None,
        reset: bool = False,
    ) -> None:
        """
        Sync all configured AmiBroker intraday sources.

        reset=True is intended for an init/full reload. All target tables are reset
        before the first source is loaded so the four datasets start from one clean
        state.
        """
        if reset:
            self._sync_port.reset_intraday_targets(
                tuple(table_name for _, table_name in intraday_targets)
            )

        total_categories = len(intraday_targets)
        for index, (folder_path, table_name) in enumerate(intraday_targets, start=1):
            print(
                f"[{index}/{total_categories}] Tiến hành xử lý dữ liệu Intraday "
                f"cho bảng: {table_name}"
            )
            self._sync_port.upsert_intraday(
                folder_path=folder_path,
                table_name=table_name,
                from_last_day=from_last_day,
            )
            print("-" * 50)
