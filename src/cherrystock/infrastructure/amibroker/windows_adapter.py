from __future__ import annotations

import csv
from pathlib import Path


class WindowsAmiBrokerAdapter:
    """Windows COM adapter for AmiBroker integration.

    Fundamental data is read directly from AmiBroker's Stocks/Quotations COM
    collections instead of the obsolete ``Application.Analysis`` object.  The
    latter controls the old Automatic Analysis window and can return an empty
    exploration while the New Analysis UI shows valid rows.
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

    def run_explore_export(
        self,
        formula_path: Path,
        export_path: Path,
        apply_to: int = 0,
        range_mode: int = 2,
        range_n: int = 1,
    ) -> None:
        """Export latest stock FA to CSV using AmiBroker COM objects directly.

        ``formula_path``/analysis arguments are kept for port compatibility, but
        the export no longer depends on Automatic/New Analysis state.
        """
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
            app = win32com.client.Dispatch("Broker.Application")

            # If a database is explicitly configured, only load it when it differs
            # from the database already open in AmiBroker. This avoids resetting a
            # valid GUI database/context unnecessarily.
            configured_db = None
            if self._database_path is not None:
                configured_db = Path(self._database_path).resolve()
                current_db = ""
                try:
                    current_db = str(app.DatabasePath or "")
                except Exception:
                    pass

                if current_db:
                    try:
                        current_resolved = Path(current_db).resolve()
                    except Exception:
                        current_resolved = None
                else:
                    current_resolved = None

                if current_resolved != configured_db:
                    loaded = bool(app.LoadDatabase(str(configured_db)))
                    if not loaded:
                        raise RuntimeError(
                            f"AmiBroker không load được database: {configured_db}"
                        )

            try:
                active_db = str(app.DatabasePath or "")
            except Exception:
                active_db = str(configured_db or "")

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

                    # The former AFL selected the equity group.  COM does not expose
                    # group names, so use stable characteristics of listed shares:
                    # indexes are excluded and equities must have SharesOut > 0.
                    # This also avoids exporting most indices/futures/FX symbols.
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
                f"database={active_db!r} | stocks={stock_count} | rows={len(rows)} | "
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
