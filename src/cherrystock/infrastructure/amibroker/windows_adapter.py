from __future__ import annotations

from pathlib import Path


class WindowsAmiBrokerAdapter:
    """Windows COM adapter for AmiBroker integration.

    This adapter intentionally contains platform-specific dependencies and paths,
    keeping them out of application/core modules.
    """

    def __init__(self, database_path: Path | None = None):
        self._database_path = database_path

    def run_explore_export(
        self,
        formula_path: Path,
        export_path: Path,
        apply_to: int = 0,
        range_mode: int = 2,
        range_n: int = 1,
    ) -> None:
        try:
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on local environment
            raise RuntimeError(
                "Windows AmiBroker adapter requires pywin32 (win32com/pythoncom)."
            ) from exc

        pythoncom.CoInitialize()
        try:
            app = win32com.client.Dispatch("Broker.Application")
            if self._database_path is not None:
                app.LoadDatabase(str(self._database_path))

            analysis = app.Analysis
            analysis.LoadFormula(formula_path.as_posix())
            analysis.ApplyTo = apply_to
            analysis.RangeMode = range_mode
            analysis.RangeN = range_n
            analysis.Explore()
            analysis.Export(export_path.as_posix())
        finally:
            pythoncom.CoUninitialize()
