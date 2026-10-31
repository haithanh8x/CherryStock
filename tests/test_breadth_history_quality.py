"""Regression: partial-week/month indicator rows must not create false 0/100% breadth."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb

from scripts.cloudflare_sync.sync_indicators import _breadth


def test_sparse_monthly_2026_06_26_excluded(tmp_path: Path) -> None:
    db = tmp_path / "CherryMon.duckdb"
    connection = duckdb.connect(str(db))
    try:
        connection.execute("""
            CREATE TABLE cal_indicator_history(
                Ticker VARCHAR, Date DATE, IndicatorName VARCHAR,
                Timeframe VARCHAR, Value DOUBLE
            )
        """)
        connection.execute("""
            CREATE TABLE raw_stock_eod(
                Ticker VARCHAR, Date DATE, Close DOUBLE, Volume DOUBLE
            )
        """)
        daily = []
        eod = []
        for idx in range(40):
            ticker = f"T{idx:03}"
            for dt in (date(2026, 6, 26), date(2026, 6, 30)):
                price = 100.0 + idx
                eod.append((ticker, dt, price, 1000.0))
                for name in ("MA20", "MA50", "MA100", "MA200"):
                    daily.append((ticker, dt, name, "D", 110.0))
                    if dt == date(2026, 6, 30):
                        # The correct June month-end contains a real broad sample.
                        daily.append((ticker, dt, name, "M", 110.0))
                    elif idx == 0:
                        # Previously charted as 0% for all 4 MAs.
                        daily.append((ticker, dt, name, "M", 200.0))
                    if dt == date(2026, 6, 26):
                        daily.append((ticker, dt, name, "W", 110.0))
                    elif idx == 0:
                        daily.append((ticker, dt, name, "W", 200.0))
        connection.executemany("INSERT INTO cal_indicator_history VALUES (?,?,?,?,?)", daily)
        connection.executemany("INSERT INTO raw_stock_eod VALUES (?,?,?,?)", eod)

        result = _breadth(connection, date(2026, 6, 1))
        monthly = result["timeframes"]["M"]
        weekly = result["timeframes"]["W"]
        assert [row["date"] for row in monthly] == ["2026-06-30"]
        assert monthly[0]["coverage"] == 40
        assert all(monthly[0][name] > 0 for name in ("ma20", "ma50", "ma100", "ma200"))
        assert [row["date"] for row in weekly] == ["2026-06-26"]
        assert weekly[0]["coverage"] == 40
        assert len(result["timeframes"]["D"]) == 2
    finally:
        connection.close()
