"""Bounded read-only acquisition; no SQL or recalculation in the UI renderer."""
from __future__ import annotations

import logging
from Ults.DuckLib import DuckDBManager
from calcEngine.levelLadder import build_level_ladder
from webapp.ticker_detail_contract import FIELDS, detail_query, normalize_ticker

LOGGER = logging.getLogger(__name__)


def load_ticker_details(ticker: str) -> dict:
    ticker = normalize_ticker(ticker)
    result = {"ticker": ticker, "sections": {}, "errors": {}, "market": None, "ladder": None}
    # Independent read connections allow a missing view to leave other panels usable.
    for view in FIELDS:
        try:
            with DuckDBManager(read_only=True) as con:
                cursor = con.execute(detail_query(view), [ticker])
                columns = [item[0] for item in cursor.description]
                result["sections"][view] = [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception:
            LOGGER.exception("Ticker detail read failed | ticker=%s view=%s", ticker, view)
            result["errors"][view] = "Không đọc được nguồn dữ liệu; xem log ứng dụng."
    try:
        with DuckDBManager(read_only=True) as con:
            row = con.execute(
                'SELECT Market FROM "CherryMon"."main"."raw_stock_fa" '
                'WHERE UPPER(TRIM(Ticker)) = ? ORDER BY Date DESC NULLS LAST, '
                'Market ASC NULLS LAST LIMIT 1', [ticker]
            ).fetchone()
            result["market"] = row[0] if row else None
    except Exception:
        LOGGER.exception("Ticker listing read failed | ticker=%s", ticker)
        result["errors"]["market"] = "Chưa đọc được sàn; chọn sàn Việt Nam để xem biểu đồ."
    try:
        result["ladder"] = build_level_ladder(ticker)
    except Exception:
        LOGGER.exception("Ticker R/S read failed | ticker=%s", ticker)
        result["errors"]["ladder"] = "Chưa tải được R/S; kiểm tra nguồn giá/indicator trong log."
    return result
