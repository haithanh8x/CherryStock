from __future__ import annotations

from pathlib import Path
from typing import Protocol


class AmiBrokerPort(Protocol):
    """Port for AmiBroker integration required by application services."""

    def run_explore_export(
        self,
        formula_path: Path,
        export_path: Path,
        apply_to: int = 0,
        range_mode: int = 2,
        range_n: int = 1,
    ) -> None:
        """Run AmiBroker analysis Explore and export the result to CSV."""
