from __future__ import annotations

import pandas as pd


class TickerRepository:
    def __init__(self, connection) -> None:
        self._connection = connection

    def replace_from_dataframe(self, dataframe: pd.DataFrame, table_name: str = "raw_lstTicker") -> None:
        if dataframe is None or dataframe.empty:
            return

        self._connection.register("df_ticker_tmp", dataframe)
        self._connection.execute("CREATE TEMPORARY TABLE _tmp_ticker_schema AS SELECT * FROM df_ticker_tmp LIMIT 0;")
        schema_info = self._connection.execute("DESCRIBE _tmp_ticker_schema;").fetchall()

        cols_def = []
        update_cols = []

        for col_name, col_type, *_ in schema_info:
            if col_name == "Ticker":
                cols_def.append(f'"{col_name}" {col_type} PRIMARY KEY')
            else:
                cols_def.append(f'"{col_name}" {col_type}')
                update_cols.append(col_name)

        create_sql = f"DROP TABLE IF EXISTS {table_name}; CREATE TABLE {table_name} ({', '.join(cols_def)});"
        self._connection.execute(create_sql)

        update_clause = ", ".join([f'"{c}" = EXCLUDED."{c}"' for c in update_cols])
        upsert_query = f"""
            INSERT INTO {table_name}
            SELECT * FROM df_ticker_tmp
            ON CONFLICT (Ticker) DO UPDATE SET {update_clause};
        """
        self._connection.execute(upsert_query)

        self._connection.execute("DROP TABLE _tmp_ticker_schema;")
        self._connection.unregister("df_ticker_tmp")
