from pathlib import Path

from src.cherrystock.application.services.sync_amibroker_fa import SyncAmiBrokerFAService


class FakeAmiBrokerAdapter:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run_explore_export(
        self,
        formula_path: Path,
        export_path: Path,
        apply_to: int = 0,
        range_mode: int = 2,
        range_n: int = 1,
    ) -> None:
        self.calls.append(
            {
                "formula_path": formula_path,
                "export_path": export_path,
                "apply_to": apply_to,
                "range_mode": range_mode,
                "range_n": range_n,
            }
        )


def test_sync_amibroker_fa_service_calls_port() -> None:
    fake = FakeAmiBrokerAdapter()
    service = SyncAmiBrokerFAService(amibroker=fake)

    formula_path = Path("Export Shares.afl")
    export_path = Path("tmp_Export_Shares.csv")

    service.run_latest_export(
        formula_path=formula_path,
        export_path=export_path,
        apply_to=3,
        range_mode=4,
        range_n=5,
    )

    assert len(fake.calls) == 1
    assert fake.calls[0]["formula_path"] == formula_path
    assert fake.calls[0]["export_path"] == export_path
    assert fake.calls[0]["apply_to"] == 3
    assert fake.calls[0]["range_mode"] == 4
    assert fake.calls[0]["range_n"] == 5
