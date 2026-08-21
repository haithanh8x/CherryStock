from __future__ import annotations

import time
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
            # Dispatch attaches to/creates the AmiBroker COM application.  When a
            # database path is configured, make sure that the exact same database
            # used by the application is loaded before configuring Analysis.
            app = win32com.client.Dispatch("Broker.Application")
            if self._database_path is not None:
                database_path = Path(self._database_path).resolve()
                print(f"[*] AmiBroker COM database: {database_path}")
                app.LoadDatabase(str(database_path))

            formula_path = Path(formula_path).resolve()
            export_path = Path(export_path).resolve()
            export_path.parent.mkdir(parents=True, exist_ok=True)

            analysis = app.Analysis
            analysis.LoadFormula(str(formula_path))
            analysis.ApplyTo = apply_to
            analysis.RangeMode = range_mode
            analysis.RangeN = range_n

            print(
                "[*] AmiBroker COM Explore: "
                f"formula={formula_path} | ApplyTo={apply_to} | "
                f"RangeMode={range_mode} | RangeN={range_n}"
            )

            # AmiBroker's Analysis.Explore() is asynchronous through COM.  The old
            # implementation exported immediately, which can produce a CSV that
            # contains only the header even though the same Exploration works in
            # the AmiBroker UI.  Wait until Analysis reports completion first.
            analysis.Explore()

            timeout_seconds = 120.0
            poll_seconds = 0.1
            deadline = time.monotonic() + timeout_seconds

            while True:
                try:
                    busy = bool(analysis.IsBusy)
                except Exception:
                    # Older AmiBroker COM versions may not expose IsBusy. Give the
                    # asynchronous Explore a short grace period before exporting.
                    time.sleep(1.0)
                    break

                if not busy:
                    break
                if time.monotonic() >= deadline:
                    try:
                        analysis.Abort()
                    except Exception:
                        pass
                    raise TimeoutError(
                        f"AmiBroker Explore did not finish within {timeout_seconds:.0f}s"
                    )
                time.sleep(poll_seconds)

            analysis.Export(str(export_path))

            if export_path.exists():
                print(
                    f"[*] AmiBroker COM export complete: {export_path} | "
                    f"size={export_path.stat().st_size} bytes"
                )
            else:
                print(f"[!] AmiBroker COM did not create export file: {export_path}")
        finally:
            pythoncom.CoUninitialize()
