from __future__ import annotations

from pathlib import Path

from cherrystock.application.ports.amibroker import AmiBrokerPort


class SyncAmiBrokerFAService:
    """Application service that orchestrates FA export through an abstract port."""

    def __init__(self, amibroker: AmiBrokerPort):
        self._amibroker = amibroker

    def run_latest_export(
        self,
        formula_path: Path,
        export_path: Path,
        apply_to: int = 0,
        range_mode: int = 2,
        range_n: int = 1,
    ) -> None:
        self._amibroker.run_explore_export(
            formula_path=formula_path,
            export_path=export_path,
            apply_to=apply_to,
            range_mode=range_mode,
            range_n=range_n,
        )
