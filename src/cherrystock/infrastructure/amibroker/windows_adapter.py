from __future__ import annotations

import time
from pathlib import Path


class WindowsAmiBrokerAdapter:
    """Windows COM adapter for AmiBroker integration.

    FA export uses AmiBroker New Analysis (AnalysisDocs/AnalysisDoc), because the
    Stocks collection can be empty for plugin-backed databases even when the New
    Analysis UI has valid data.
    """

    def __init__(self, database_path: Path | None = None):
        self._database_path = database_path

    @staticmethod
    def _is_duckdb_path(path: Path | str | None) -> bool:
        if not path:
            return False
        try:
            return Path(path).suffix.lower() == ".duckdb"
        except Exception:
            return str(path).lower().endswith(".duckdb")

    @staticmethod
    def _wait_analysis(doc, pythoncom, timeout_seconds: float = 120.0) -> None:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                busy = bool(doc.IsBusy)
            except Exception as exc:
                raise RuntimeError(f"Không đọc được trạng thái AnalysisDoc.IsBusy: {exc}") from exc

            if not busy:
                return

            if time.monotonic() >= deadline:
                try:
                    doc.Abort()
                except Exception:
                    pass
                raise TimeoutError(
                    f"AmiBroker New Analysis không hoàn tất sau {timeout_seconds:.0f}s"
                )

            try:
                pythoncom.PumpWaitingMessages()
            except Exception:
                pass
            time.sleep(0.5)

    @staticmethod
    def _csv_has_data(export_path: Path) -> bool:
        if not export_path.exists() or export_path.stat().st_size <= 0:
            return False
        try:
            with export_path.open("r", encoding="utf-8-sig", errors="ignore") as handle:
                non_empty = [line for line in handle if line.strip()]
            return len(non_empty) >= 2
        except Exception:
            return export_path.stat().st_size > 128

    def run_explore_export(
        self,
        formula_path: Path,
        export_path: Path,
        apply_to: int = 0,
        range_mode: int = 2,
        range_n: int = 1,
    ) -> None:
        """Run FA exploration using AmiBroker New Analysis and export CSV.

        Preferred source is an ``Export Shares.apx`` project next to the AFL. If
        it does not exist, the most recently opened New Analysis document is used.
        ``apply_to`` / ``range_mode`` / ``range_n`` are retained for interface
        compatibility; New Analysis settings live in the APX/project itself.
        """
        del apply_to, range_mode, range_n

        try:
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore
        except ImportError as exc:  # pragma: no cover - Windows/local dependency
            raise RuntimeError(
                "Windows AmiBroker adapter requires pywin32 (win32com/pythoncom)."
            ) from exc

        formula_path = Path(formula_path).resolve()
        export_path = Path(export_path).resolve()
        export_path.parent.mkdir(parents=True, exist_ok=True)
        apx_path = formula_path.with_suffix(".apx")

        if export_path.exists():
            export_path.unlink()

        pythoncom.CoInitialize()
        analysis_doc = None
        close_analysis_when_done = False
        try:
            attached_to_running = False
            try:
                app = win32com.client.GetActiveObject("Broker.Application")
                attached_to_running = True
            except Exception:
                app = win32com.client.Dispatch("Broker.Application")

            try:
                app.Visible = 1
            except Exception:
                pass

            try:
                version = str(app.Version or "")
            except Exception:
                version = "unknown"

            try:
                active_db = str(app.DatabasePath or "")
            except Exception:
                active_db = ""

            if self._is_duckdb_path(active_db):
                raise RuntimeError(
                    "AmiBroker đang bị trỏ nhầm tới DuckDB: "
                    f"{active_db}. Hãy mở đúng database AmiBroker trước khi chạy FA."
                )

            analysis_docs = app.AnalysisDocs
            try:
                open_count = int(analysis_docs.Count)
            except Exception:
                open_count = 0

            source = ""
            if apx_path.exists():
                analysis_doc = analysis_docs.Open(str(apx_path))
                close_analysis_when_done = True
                source = f"apx={apx_path}"
                if analysis_doc is None:
                    raise RuntimeError(f"AmiBroker không mở được Analysis project: {apx_path}")
            elif open_count > 0:
                # Use the most recently opened New Analysis document. This matches
                # the manual workflow where Export Shares.afl is already open and
                # produces valid rows in the GUI.
                analysis_doc = analysis_docs.Item(open_count - 1)
                source = f"open_analysis_index={open_count - 1}"
            else:
                configured = ""
                if self._database_path is not None:
                    configured = str(Path(self._database_path).expanduser())
                raise RuntimeError(
                    "Không có New Analysis project để chạy FA. "
                    f"Hãy mở '{formula_path.name}' trong New Analysis rồi chạy lại, "
                    f"hoặc Save As thành '{apx_path.name}' tại {apx_path.parent}. "
                    f"AmiBroker database config={configured!r}."
                )

            print(
                "[*] AmiBroker New Analysis FA: "
                f"version={version} | attached={attached_to_running} | "
                f"database={active_db!r} | source={source}"
            )

            # If this document was already running, wait for it before launching
            # the FA exploration.
            self._wait_analysis(analysis_doc, pythoncom, timeout_seconds=120.0)

            started = int(analysis_doc.Run(1))  # 1 = Exploration
            if started != 1:
                raise RuntimeError(
                    "AmiBroker AnalysisDoc.Run(1) không khởi động được Exploration. "
                    "Analysis window có thể đang bận hoặc project không hợp lệ."
                )

            self._wait_analysis(analysis_doc, pythoncom, timeout_seconds=120.0)

            exported = int(analysis_doc.Export(str(export_path), 0))
            if exported != 1:
                raise RuntimeError(
                    f"AmiBroker AnalysisDoc.Export thất bại: {export_path}"
                )

            if not self._csv_has_data(export_path):
                raise ValueError(
                    "New Analysis đã chạy nhưng CSV không có dòng dữ liệu. "
                    f"source={source}; database={active_db!r}; file={export_path}. "
                    "Kiểm tra project đang dùng đúng Export Shares.afl, Apply to=All symbols "
                    "và Range=1 recent bar(s)."
                )

            print(
                "[*] AmiBroker New Analysis export complete: "
                f"file={export_path} | size={export_path.stat().st_size} bytes"
            )
        finally:
            if close_analysis_when_done and analysis_doc is not None:
                try:
                    self._wait_analysis(analysis_doc, pythoncom, timeout_seconds=10.0)
                except Exception:
                    pass
                try:
                    analysis_doc.Close()
                except Exception:
                    pass
            pythoncom.CoUninitialize()
