# -*- coding: utf-8 -*-
"""Kiểm tra schema và dữ liệu raw_lstTicker."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from Ults.DuckLib import DuckDBManager  # noqa: E402

with DuckDBManager(read_only=True) as con:
    print(con.sql('DESCRIBE "CherryMon"."main"."raw_lstTicker"').df())
    print(con.sql("SELECT * FROM \"CherryMon\".\"main\".\"raw_lstTicker\" WHERE Ticker = 'MWG'").df())
    print(con.sql(
        'SELECT Ticker, Status FROM "CherryMon"."main"."raw_lstTicker" LIMIT 5'
    ).df())
