from __future__ import annotations

import pandas as pd


class IndexRepository:
    def __init__(self, connection) -> None:
        self._connection = connection

    def replace_index_series(
        self,
        index_name: str,
        dataframe: pd.DataFrame,
        table_name: str = '"CherryMon"."main"."cal_Indexes"',
    ) -> None:
        if dataframe is None or dataframe.empty:
            return

        self._connection.execute(f"DELETE FROM {table_name} WHERE INDEX_NAME = ?", [index_name])
        self._connection.register("df_index_series", dataframe)
        self._connection.execute(
            f"""
            INSERT INTO {table_name} (INDEX_NAME, Close, Date)
            SELECT ?, Close, Date
            FROM df_index_series
            """,
            [index_name],
        )
        self._connection.unregister("df_index_series")
