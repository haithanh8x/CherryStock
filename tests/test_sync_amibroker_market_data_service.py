from pathlib import Path

from src.cherrystock.application.services.sync_amibroker_market_data import (
    SyncAmiBrokerMarketDataService,
)


class FakeMarketDataSyncPort:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, str, int | None]] = []

    def upsert_stock_eod(
        self,
        folder_path: Path,
        table_name: str,
        from_last_day: int | None = None,
    ) -> None:
        self.calls.append((folder_path, table_name, from_last_day))


def test_sync_market_data_service_uses_all_targets() -> None:
    fake = FakeMarketDataSyncPort()
    service = SyncAmiBrokerMarketDataService(sync_port=fake)

    targets = (
        (Path("eod/stock"), "raw_stock_eod"),
        (Path("eod/index"), "raw_index_eod"),
    )

    service.sync_eod(eod_targets=targets, from_last_day=7)

    assert fake.calls == [
        (Path("eod/stock"), "raw_stock_eod", 7),
        (Path("eod/index"), "raw_index_eod", 7),
    ]


def test_sync_intraday_service_uses_all_targets() -> None:
    fake = FakeMarketDataSyncPort()
    service = SyncAmiBrokerMarketDataService(sync_port=fake)

    targets = (
        (Path("intra/futures"), "raw_futures_intraday"),
        (Path("intra/stock"), "raw_stock_intraday"),
    )

    service.sync_intraday(intraday_targets=targets, from_last_day=1)

    assert fake.calls == [
        (Path("intra/futures"), "raw_futures_intraday", 1),
        (Path("intra/stock"), "raw_stock_intraday", 1),
    ]
