from __future__ import annotations

import pandas as pd


class TrendRepository:
    def __init__(self, connection) -> None:
        self._connection = connection

    def upsert_moving_average(self, dataframe: pd.DataFrame, table_name: str = '"CherryMon"."main"."cal_Trends"') -> None:
        if dataframe is None or dataframe.empty:
            return

        self._connection.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                Ticker VARCHAR,
                Date DATE,
                Close DOUBLE,
                MA20 DOUBLE,
                MA50 DOUBLE,
                MA100 DOUBLE,
                MA200 DOUBLE,
                PRIMARY KEY (Ticker, Date)
            );
        """)
        self._connection.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS Close DOUBLE;")

        self._connection.register("df_moving_average", dataframe)
        self._connection.execute(f"""
            INSERT INTO {table_name} (Ticker, Date, Close, MA20, MA50, MA100, MA200)
            SELECT Ticker, Date, Close, MA20, MA50, MA100, MA200
            FROM df_moving_average
            ON CONFLICT (Ticker, Date) DO UPDATE SET
                Close = EXCLUDED.Close,
                MA20 = EXCLUDED.MA20,
                MA50 = EXCLUDED.MA50,
                MA100 = EXCLUDED.MA100,
                MA200 = EXCLUDED.MA200;
        """)
        self._connection.unregister("df_moving_average")
