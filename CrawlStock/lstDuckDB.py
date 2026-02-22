import duckdb
import pandas as pd

def prc_upsert_by_ticker(con: duckdb.DuckDBPyConnection,
                     table: str,
                     df: pd.DataFrame,
                     ticker: str,
                     ticker_col: str = "Ticker"):
    """
    Delete old rows in `table` where ticker_col = ticker, then insert df rows.
    Assumes df has same columns as table.
    """
    if df is None or df.empty:
        print(f"[SKIP] {table}: df is empty for ticker={ticker}")
        return

    # Optional: normalize ticker column in df
    if ticker_col not in df.columns:
        raise ValueError(f"DataFrame missing column '{ticker_col}'. Columns: {list(df.columns)[:20]}")

    df = df.copy()
    df[ticker_col] = ticker  # ensure correct ticker value

    view = f"df_{table}_tmp"
    con.register(view, df)

    con.execute("BEGIN TRANSACTION;")
    try:
        con.execute(f"DELETE FROM {table} WHERE {ticker_col} = ?;", [ticker])
        con.execute(f"INSERT INTO {table} SELECT * FROM {view};")
        con.execute("COMMIT;")
        #print(f"[OK] {table}: replaced data for {ticker} ({len(df)} rows)")
    except Exception:
        con.execute("ROLLBACK;")
        raise
    finally:
        con.unregister(view)