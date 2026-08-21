from __future__ import annotations

import csv
from pathlib import Path


class WindowsAmiBrokerAdapter:
    """Windows COM adapter for AmiBroker integration.

    Fundamental data is read directly from AmiBroker's Stocks/Quotations COM
    collections instead of the obsolete ``Application.Analysis`` object.
    """

    def __init__(self, database_path: Path | None = None):
        self._database_path = database_path

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _market_name(app, market_id: int) -> str:
        try:
            return str(app.Markets.Item(int(market_id)).Name)
        except Exception:
            return str(market_id)

    @staticmethod
    def _is_duckdb_path(path: Path | str | None) -> bool:
        if not path:
            return False
        try:
            return Path(path).suffix.lower() == ".duckdb"
        except Exception:
            return str(path).lower().endswith(".duckdb")

    def run_explore_export(
        self,
        formula_path: Path,
        export_path: Path,
        apply_to: int = 0,
        range_mode: int = 2,
        range_n: int = 1,
    ) -> None:
        """Export latest stock FA to CSV using AmiBroker COM objects directly."""
        del formula_path, apply_to, range_mode, range_n

        try:
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on local environment
            raise RuntimeError(
                "Windows AmiBroker adapter requires pywin32 (win32com/pythoncom)."
            ) from exc

        export_path = Path(export_path).resolve()
        export_path.parent.mkdir(parents=True, exist_ok=True)

        pythoncom.CoInitialize()
        try:
            # Prefer the already-running AmiBroker GUI instance so the COM code
            # sees the same database/context the user sees on screen.
            attached_to_running = False
            try:
                app = win32com.client.GetActiveObject("Broker.Application")
                attached_to_running = True
            except Exception:
                app = win32com.client.Dispatch("Broker.Application")

            current_db = ""
            try:
                current_db = str(app.DatabasePath or "")
            except Exception:
                pass

            configured_db: Path | None = None
            if self._database_path is not None:
                candidate = Path(self._database_path).expanduser().resolve()
                if self._is_duckdb_path(candidate):
                    print(
                        "[!] Bỏ qua AMIBROKER_DATABASE_PATH sai vì đang trỏ tới DuckDB: "
                        f"{candidate}"
                    )
                else:
                    configured_db = candidate

            current_is_invalid = self._is_duckdb_path(current_db)
            current_resolved: Path | None = None
            if current_db and not current_is_invalid:
                try:
                    current_resolved = Path(current_db).resolve()
                except Exception:
                    pass

            # Load the real AmiBroker database directory when the current COM
            # instance is empty/wrong or points elsewhere.
            if configured_db is not None and current_resolved != configured_db:
                if not configured_db.exists():
                    if current_resolved is None:
                        raise FileNotFoundError(
                            "Không tìm thấy AmiBroker database directory: "
                            f"{configured_db}. Hãy cấu hình AMIBROKER_DATABASE_PATH đúng."
                        )
                    print(
                        f"[!] AmiBroker database cấu hình không tồn tại: {configured_db}; "
                        f"giữ database đang mở: {current_db}"
                    )
                else:
                    loaded = bool(app.LoadDatabase(str(configured_db)))
                    if not loaded:
                        raise RuntimeError(
                            f"AmiBroker không load được database: {configured_db}"
                        )

            try:
                active_db = str(app.DatabasePath or "")
            except Exception:
                active_db = str(configured_db or current_db or "")

            if self._is_duckdb_path(active_db):
                raise RuntimeError(
                    "AmiBroker đang bị trỏ nhầm tới file DuckDB: "
                    f"{active_db}. Database AmiBroker phải là một thư mục."
                )

            stocks = app.Stocks
            stock_count = int(stocks.Count)
            rows: list[list[object]] = []
            skipped_no_quotes = 0
            skipped_non_equity = 0
            failed_symbols = 0

            for index in range(stock_count):
                try:
                    stock = stocks.Item(index)
                    ticker = str(stock.Ticker or "").strip().upper()
                    if not ticker:
                        continue

                    quotations = stock.Quotations
                    quote_count = int(quotations.Count)
                    if quote_count <= 0:
                        skipped_no_quotes += 1
                        continue

                    shares_out = self._safe_float(stock.SharesOut)
                    is_index = bool(stock.Index)
                    if is_index or shares_out <= 0:
                        skipped_non_equity += 1
                        continue

                    quote = quotations.Item(quote_count - 1)
                    open_price = self._safe_float(quote.Open)
                    close_price = self._safe_float(quote.Close)
                    shares_float = self._safe_float(stock.SharesFloat)
                    eps = self._safe_float(stock.EPS)
                    book_value = self._safe_float(stock.BookValuePerShare)
                    roa = self._safe_float(stock.ReturnOnAssets)
                    roe = self._safe_float(stock.ReturnOnEquity)
                    pe = close_price / eps if eps > 0 else None
                    capital = close_price * shares_out

                    quote_date = quote.Date
                    try:
                        date_value = quote_date.strftime("%Y-%m-%d")
                    except Exception:
                        date_value = str(quote_date)

                    rows.append(
                        [
                            ticker,
                            date_value,
                            open_price,
                            close_price,
                            str(stock.FullName or ""),
                            self._market_name(app, int(stock.MarketID)),
                            capital,
                            shares_float,
                            shares_out,
                            eps,
                            pe,
                            book_value,
                            roa,
                            roe,
                        ]
                    )
                except Exception:
                    failed_symbols += 1
                    continue

            headers = [
                "Ticker",
                "Date",
                "Open",
                "Close",
                "Full Name",
                "Market",
                "Capital",
                "Shares Float",
                "Shares Outstanding",
                "EPS",
                "PE",
                "Book Value",
                "ROA",
                "ROE",
            ]

            with export_path.open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(headers)
                writer.writerows(rows)

            print(
                "[*] AmiBroker direct COM FA export: "
                f"attached={attached_to_running} | database={active_db!r} | "
                f"stocks={stock_count} | rows={len(rows)} | "
                f"no_quotes={skipped_no_quotes} | non_equity={skipped_non_equity} | "
                f"failed={failed_symbols} | file={export_path}"
            )

            if not rows:
                raise ValueError(
                    "AmiBroker COM Stocks không trả về cổ phiếu FA hợp lệ. "
                    f"Database đang mở: {active_db!r}; tổng symbols: {stock_count}."
                )
        finally:
            pythoncom.CoUninitialize()
