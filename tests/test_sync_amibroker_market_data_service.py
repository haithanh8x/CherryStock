from pathlib import Path

from src.cherrystock.application.services.sync_amibroker_market_data import (
    SyncAmiBrokerMarketDataService,
)


class FakeMarketDataSyncPort:
    def __init__(self) -> None:
        self.eod_calls: list[tuple[Path, str, int | None]] = []
        self.intraday_calls: list[tuple[Path, str, int | None]] = []
        self.reset_calls: list[tuple[str, ...]] = []

    def upsert_stock_eod(
        self,
        folder_path: Path,
        table_name: str,
        from_last_day: int | None = None,
    ) -> None:
        self.eod_calls.append((folder_path, table_name, from_last_day))

    def reset_intraday_targets(self, table_names: tuple[str, ...]) -> None:
        self.reset_calls.append(tuple(table_names))

    def upsert_intraday(
        self,
        folder_path: Path,
        table_name: str,
        from_last_day: int | None = None,
    ) -> None:
        self.intraday_calls.append((folder_path, table_name, from_last_day))


def test_sync_market_data_service_uses_all_eod_targets() -> None:
    fake = FakeMarketDataSyncPort()
    service = SyncAmiBrokerMarketDataService(sync_port=fake)

    targets = (
        (Path("eod/stock"), "raw_stock_eod"),
        (Path("eod/index"), "raw_index_eod"),
    )

    service.sync_eod(eod_targets=targets, from_last_day=7)

    assert fake.eod_calls == [
        (Path("eod/stock"), "raw_stock_eod", 7),
        (Path("eod/index"), "raw_index_eod", 7),
    ]
    assert fake.intraday_calls == []
    assert fake.reset_calls == []


def test_sync_intraday_service_resets_then_uses_all_four_targets() -> None:
    fake = FakeMarketDataSyncPort()
    service = SyncAmiBrokerMarketDataService(sync_port=fake)

    targets = (
        (Path("intra/futures"), "raw_futures_intraday"),
        (Path("intra/index"), "raw_index_intraday"),
        (Path("intra/stock"), "raw_stock_intraday"),
        (Path("intra/warrant"), "raw_warrant_intraday"),
    )

    service.sync_intraday(
        intraday_targets=targets,
        from_last_day=None,
        reset=True,
    )

    assert fake.reset_calls == [
        (
            "raw_futures_intraday",
            "raw_index_intraday",
            "raw_stock_intraday",
            "raw_warrant_intraday",
        )
    ]
    assert fake.intraday_calls == [
        (Path("intra/futures"), "raw_futures_intraday", None),
        (Path("intra/index"), "raw_index_intraday", None),
        (Path("intra/stock"), "raw_stock_intraday", None),
        (Path("intra/warrant"), "raw_warrant_intraday", None),
    ]


def test_sync_intraday_incremental_does_not_reset_targets() -> None:
    fake = FakeMarketDataSyncPort()
    service = SyncAmiBrokerMarketDataService(sync_port=fake)

    targets = (
        (Path("intra/stock"), "raw_stock_intraday"),
    )

    service.sync_intraday(
        intraday_targets=targets,
        from_last_day=2,
        reset=False,
    )

    assert fake.reset_calls == []
    assert fake.intraday_calls == [
        (Path("intra/stock"), "raw_stock_intraday", 2),
    ]
