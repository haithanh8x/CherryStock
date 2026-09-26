"""Bounded read-only acquisition; query, connection and R/S timing are separate."""
from __future__ import annotations

import logging
import sys
from contextlib import contextmanager
from Ults.DuckLib import DuckDBManager
from calcEngine.levelLadder import build_level_ladder
from webapp.ticker_detail_contract import FIELDS, detail_query, normalize_ticker
from webapp.ticker_detail_trace import TickerTrace

LOGGER = logging.getLogger(__name__)


@contextmanager
def _connection(trace, source):
    with trace.span(source + ".connect"):
        manager = DuckDBManager(read_only=True)
        con = manager.__enter__()
    try:
        yield con
    except BaseException:
        with trace.span(source + ".close"):
            suppressed = manager.__exit__(*sys.exc_info())
        if not suppressed:
            raise
    else:
        with trace.span(source + ".close"):
            manager.__exit__(None, None, None)


def load_ticker_details(ticker: str, trace: TickerTrace | None = None) -> dict:
    ticker = normalize_ticker(ticker)
    trace = trace or TickerTrace(ticker)
    result = {"ticker": ticker, "sections": {}, "errors": {}, "market": None, "ladder": None}
    with trace.span("data.total"):
        for view in FIELDS:
            try:
                with _connection(trace, view) as con:
                    with trace.span(view + ".execute"):
                        cursor = con.execute(detail_query(view), [ticker])
                    with trace.span(view + ".fetch_map"):
                        columns = [item[0] for item in cursor.description]
                        result["sections"][view] = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    trace.record(view + ".rows", 0, rows=len(result["sections"][view]))
            except Exception:
                LOGGER.exception("Ticker detail read failed | ticker=%s view=%s", ticker, view)
                result["errors"][view] = "Không đọc được nguồn dữ liệu; xem log ứng dụng."
        try:
            with _connection(trace, "market") as con:
                with trace.span("market.query"):
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
            with trace.span("rs.total"):
                result["ladder"] = build_level_ladder(ticker)
        except Exception:
            LOGGER.exception("Ticker R/S read failed | ticker=%s", ticker)
            result["errors"]["ladder"] = "Chưa tải được R/S; kiểm tra nguồn giá/indicator trong log."
    return result
