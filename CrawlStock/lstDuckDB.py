import duckdb
import pandas as pd

_NUMERIC_BASE = {
    "TINYINT", "SMALLINT", "INTEGER", "INT", "BIGINT", "HUGEINT",
    "UTINYINT", "USMALLINT", "UINTEGER", "UINT", "UBIGINT",
    "FLOAT", "REAL", "DOUBLE",
    "DECIMAL", "NUMERIC",
}
_BOOL_BASE = {"BOOLEAN", "BOOL"}
_DATE_BASE = {"DATE"}
_TIME_BASE = {"TIME"}
_TS_BASE = {"TIMESTAMP", "DATETIME"}  # DuckDB uses TIMESTAMP; keep DATETIME just in case
# Note: DuckDB may show "TIMESTAMP WITH TIME ZONE" / "TIMESTAMPTZ" depending on DDL

def _base_type(duckdb_type: str) -> str:
    if not duckdb_type:
        return ""
    t = duckdb_type.strip().upper()
    # normalize some common variants
    if t.startswith("TIMESTAMP WITH TIME ZONE"):
        return "TIMESTAMPTZ"
    if t in ("TIMESTAMPTZ",):
        return "TIMESTAMPTZ"
    return t.split("(")[0].strip()

def _needs_try_cast(duckdb_type: str) -> bool:
    b = _base_type(duckdb_type)
    return (
        b in _NUMERIC_BASE
        or b in _BOOL_BASE
        or b in _DATE_BASE
        or b in _TIME_BASE
        or b in _TS_BASE
        or b == "TIMESTAMPTZ"
    )

def prc_upsert_by_ticker(
    con: duckdb.DuckDBPyConnection,
    table: str,
    df: pd.DataFrame,
    ticker: str,
    ticker_col: str = "Ticker"
):
    """
    Delete old rows in 'table' where ticker_col = ticker, then insert df rows.
    Insert aligned to TABLE columns (no SELECT *).
    - Missing table cols in df/view -> NULL::<coltype>
    - Extra df cols ignored
    - TRY_CAST for numeric / bool / date / time / timestamp types to survive "dirty" strings
    """
    if df is None or df.empty:
        print(f"[SKIP] {table}: df is empty for ticker={ticker}")
        return

    if ticker_col not in df.columns:
        raise ValueError(
            f"DataFrame missing column '{ticker_col}'. Columns (head): {list(df.columns)[:30]}"
        )

    df = df.copy()
    df[ticker_col] = ticker

    view = f"df_{table}_tmp"
    con.register(view, df)

    # table schema (cid, name, type, notnull, dflt_value, pk)
    tbl_info = con.execute(f"PRAGMA table_info('{table}')").fetchall()
    table_cols = [(r[1], r[2]) for r in tbl_info]  # (name, type)

    # view columns
    view_desc = con.execute(f"DESCRIBE {view}").fetchall()
    view_cols = {r[0] for r in view_desc}

    insert_cols_sql = ", ".join([f'"{c}"' for c, _t in table_cols])

    select_exprs = []
    for c, t in table_cols:
        if c in view_cols:
            if _needs_try_cast(t):
                select_exprs.append(f'TRY_CAST("{c}" AS {t}) AS "{c}"')
            else:
                select_exprs.append(f'"{c}"')
        else:
            select_exprs.append(f'NULL::{t} AS "{c}"')

    select_sql = ", ".join(select_exprs)

    con.execute("BEGIN TRANSACTION;")
    try:
        con.execute(f'DELETE FROM "{table}" WHERE "{ticker_col}" = ?;', [ticker])
        con.execute(
            f'INSERT INTO "{table}" ({insert_cols_sql}) '
            f'SELECT {select_sql} FROM "{view}";'
        )
        con.execute("COMMIT;")
    except Exception:
        con.execute("ROLLBACK;")
        raise
    finally:
        con.unregister(view)