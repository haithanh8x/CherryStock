# -*- coding: utf-8 -*-
"""Kiểm tra phạm vi dữ liệu trong cal_indicator_values."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from Ults.DuckLib import DuckDBManager  # noqa: E402

with DuckDBManager(read_only=True) as con:
    print(con.sql(
        'SELECT count(DISTINCT Ticker) AS tickers, min(Date) AS min_d, max(Date) AS max_d '
        'FROM "CherryMon"."main"."cal_indicator_values"'
    ).df())
    print(con.sql(
        'SELECT ConfigId, count(*) AS n, min(Date) AS min_d, max(Date) AS max_d '
        'FROM "CherryMon"."main"."cal_indicator_values" GROUP BY ConfigId ORDER BY ConfigId'
    ).df())
    print(con.sql(
        'SELECT max(Date) AS max_d FROM "CherryMon"."main"."raw_stock_eod"'
    ).df())
