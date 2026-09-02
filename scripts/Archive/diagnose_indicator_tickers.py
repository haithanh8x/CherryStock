# -*- coding: utf-8 -*-
"""Chẩn đoán nhanh: vì sao cal_indicator_values chỉ có MWG."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from Ults.DuckLib import DuckDBManager

with DuckDBManager(read_only=True) as con:
    print("--- raw_lstTicker status ---")
    print(con.sql('SELECT status, count(*) AS n FROM "CherryMon"."main"."raw_lstTicker" GROUP BY status').df())

    print("--- active tickers in raw_stock_eod ---")
    print(con.sql(
        '''
        SELECT eod.Ticker, count(*) AS rows, max(eod.Date) AS max_date
        FROM "CherryMon"."main"."raw_stock_eod" eod
        INNER JOIN "CherryMon"."main"."raw_lstTicker" t ON t.Ticker = eod.Ticker
        WHERE t.status = 'Y'
        GROUP BY eod.Ticker ORDER BY eod.Ticker
        '''
    ).df())

    print("--- all tickers in raw_stock_eod ---")
    print(con.sql(
        'SELECT Ticker, count(*) AS n FROM "CherryMon"."main"."raw_stock_eod" GROUP BY Ticker ORDER BY Ticker'
    ).df())

    print("--- cal_indicator_values ---")
    print(con.sql(
        'SELECT Ticker, count(*) AS n FROM "CherryMon"."main"."cal_indicator_values" GROUP BY Ticker ORDER BY Ticker'
    ).df())
