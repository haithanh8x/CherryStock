"""Four market-cap indices from latest vw_Ticker_Info membership and daily OHLC.

Caller owns DuckDB transaction. Full bootstrap; bounded daily refresh is idempotent.
Historical classification and float are latest-snapshot proxies, NOT point-in-time.
"""
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "DuckDB" / "sql" / "marketcap_index_schema.sql"
TARGET = '"CherryMon"."main"."cal_MarketCap_Index_D"'
MEMBERS = '"CherryMon"."main"."vw_Ticker_Info"'
OHLC = "(SELECT * FROM \"CherryMon\".\"main\".\"vw_Ticker_OHLC\" WHERE \"AssetType\" = 'STOCK')"
GROUPS = ("Large Cap", "Mid Cap", "Small Cap", "Micro Cap")


def refresh_marketcap_index(*, connection, days: int | None = None) -> dict:
    if days is not None and (type(days) is not int or days < 1):
        raise ValueError("days must be positive or None")
    connection.execute(SCHEMA.read_text(encoding="utf-8"))
    connection.execute(f"""
        CREATE OR REPLACE TEMP TABLE _mc_members AS
        SELECT UPPER(TRIM(CAST("Ticker" AS VARCHAR))) AS ticker,
          CASE REPLACE(UPPER(TRIM(CAST("MarketCap_Group" AS VARCHAR))), '_', ' ')
            WHEN 'LARGE CAP' THEN 'Large Cap'
            WHEN 'MID CAP' THEN 'Mid Cap'
            WHEN 'SMALL CAP' THEN 'Small Cap'
            WHEN 'MICRO CAP' THEN 'Micro Cap'
          END AS grp,
          TRY_CAST("FreeFloat" AS DOUBLE) AS float_shares
        FROM {MEMBERS}
        WHERE "AssetType" = 'STOCK'
          AND "Ticker" IS NOT NULL
    """)
    invalid = connection.execute("""
        SELECT COUNT(*) FROM _mc_members WHERE grp IS NULL
    """).fetchone()[0]
    if invalid:
        raise RuntimeError(f"{invalid} ticker(s) have missing/invalid MarketCap_Group")
    dup = connection.execute("""
        SELECT COUNT(*) FROM (SELECT ticker FROM _mc_members
        GROUP BY ticker HAVING COUNT(*) > 1)
    """).fetchone()[0]
    if dup:
        raise RuntimeError(f"Duplicate active tickers: {dup}")
    count = connection.execute("SELECT COUNT(*) FROM _mc_members").fetchone()[0]
    if not count:
        raise RuntimeError("No MarketCap group members")
    existing = connection.execute(f"SELECT COUNT(*) FROM {TARGET}").fetchone()[0]
    full = days is None or existing == 0
    if full:
        cutoff = connection.execute(f"""
            SELECT MIN(o."Date") FROM {OHLC} o
            JOIN _mc_members m ON UPPER(TRIM(CAST(o."Ticker" AS VARCHAR)))=m.ticker
            WHERE o."Close">0 AND isfinite(o."Close")
        """).fetchone()[0]
    else:
        cutoff = connection.execute(f"""
            SELECT MIN("Date") FROM (
              SELECT DISTINCT o."Date" FROM {OHLC} o
              JOIN _mc_members m ON UPPER(TRIM(CAST(o."Ticker" AS VARCHAR)))=m.ticker
              WHERE o."Close">0 AND isfinite(o."Close")
              ORDER BY o."Date" DESC LIMIT ?
            )
        """, [days]).fetchone()[0]
    if cutoff is None:
        raise RuntimeError("No eligible daily OHLC")
    connection.execute(f"""
        CREATE OR REPLACE TEMP TABLE _mc_prices AS
        SELECT o."Date" AS dt, m.grp, m.ticker,
          CAST(o."Close" AS DOUBLE) AS price,
          TRY_CAST(o."Volume" AS BIGINT) AS volume,
          m.float_shares, FALSE AS seed
        FROM {OHLC} o JOIN _mc_members m
          ON UPPER(TRIM(CAST(o."Ticker" AS VARCHAR)))=m.ticker
        WHERE o."AssetType"='STOCK' AND o."Date">=? AND o."Close">0 AND isfinite(o."Close")
    """, [cutoff])
    duplicates = connection.execute("""
        SELECT COUNT(*) FROM (SELECT dt,ticker FROM _mc_prices
        GROUP BY dt,ticker HAVING COUNT(*)>1)
    """).fetchone()[0]
    if duplicates:
        raise RuntimeError(f"Duplicate OHLC ticker/date: {duplicates}")
    connection.execute("""
        CREATE OR REPLACE TEMP TABLE _mc_seeds AS
        SELECT * FROM _mc_prices WHERE FALSE
    """)
    if not full:
        connection.execute(f"""
            INSERT INTO _mc_seeds
            SELECT MAX(o."Date"), m.grp, m.ticker,
              ARG_MAX(CAST(o."Close" AS DOUBLE),o."Date"),
              NULL, MAX(m.float_shares), TRUE
            FROM {OHLC} o JOIN _mc_members m
              ON UPPER(TRIM(CAST(o."Ticker" AS VARCHAR)))=m.ticker
            WHERE o."Date"<? AND o."Close">0 AND isfinite(o."Close")
            GROUP BY m.grp,m.ticker
        """, [cutoff])
    connection.execute("""
        CREATE OR REPLACE TEMP TABLE _mc_daily AS
        WITH history AS (
          SELECT * FROM _mc_prices UNION ALL SELECT * FROM _mc_seeds
        ), lagged AS (
          SELECT *, LAG(price) OVER (PARTITION BY ticker ORDER BY dt) AS prev
          FROM history
        ), contrib AS (
          SELECT dt,grp,ticker,volume,'EW' AS method,
            (price / COALESCE(prev,price)-1) AS ret, 1.0 AS capital
          FROM lagged WHERE NOT seed
          UNION ALL
          SELECT dt,grp,ticker,volume,'FFMC',
            (price / COALESCE(prev,price)-1),
            COALESCE(prev,price)*float_shares
          FROM lagged WHERE NOT seed AND float_shares>0
            AND isfinite(float_shares)
        )
        SELECT dt,grp,method,
          SUM(ret*capital)/SUM(capital) AS daily_ret,
          COUNT(*)::INTEGER AS ticker_count,
          SUM(COALESCE(volume,0))::BIGINT AS volume
        FROM contrib GROUP BY dt,grp,method
    """)
    # First full-history date of each group starts at base 1000.
    # Incremental windows use the last persisted close strictly before cutoff.
    anchor_filter = "AND FALSE" if full else ""
    connection.execute(f"""
        CREATE OR REPLACE TEMP TABLE _mc_results AS
        WITH anchors AS (
          SELECT "MarketCap_Group" AS grp,"Index_Method" AS method,
            ARG_MAX("Close","Date") anchor
          FROM {TARGET} WHERE "Date"<? {anchor_filter}
          GROUP BY 1,2
        ), staged AS (
          SELECT d.*,a.anchor,
            ROW_NUMBER() OVER (PARTITION BY d.grp,d.method ORDER BY d.dt) rn
          FROM _mc_daily d LEFT JOIN anchors a USING(grp,method)
        ), returns AS (
          SELECT *,CASE WHEN anchor IS NULL AND rn=1 THEN 0.0
            ELSE daily_ret END AS r FROM staged
        )
        SELECT dt,grp,method,
          COALESCE(anchor,1000.0)*
            EXP(SUM(LN(1+r)) OVER (
              PARTITION BY grp,method ORDER BY dt
              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)) AS idx,
          r,ticker_count,volume
        FROM returns
    """, [cutoff])
    n = connection.execute("SELECT COUNT(*) FROM _mc_results").fetchone()[0]
    if not n:
        raise RuntimeError("No MarketCap index rows; old results preserved")
    bad = connection.execute("SELECT COUNT(*) FROM _mc_results WHERE idx IS NULL OR NOT isfinite(idx) OR idx<=0 OR r<=-1").fetchone()[0]
    if bad:
        raise RuntimeError(f"Invalid index values: {bad}")
    if full:
        connection.execute(f"DELETE FROM {TARGET}")
    else:
        connection.execute(f'DELETE FROM {TARGET} WHERE "Date">=?', [cutoff])
    connection.execute(f"""
        INSERT INTO {TARGET}
          ("Date","MarketCap_Group","Index_Method","Close","Daily_Return",
           "Pct_Change","Ticker_Count","Volume","Calculation_Mode","Snapshot_Date")
        SELECT dt,grp,method,idx,r,r*100,ticker_count,volume,
          'HISTORICAL_PROXY_LATEST_MARKETCAP_GROUP',CURRENT_DATE
        FROM _mc_results
    """)
    return {"mode":"full" if full else "incremental",
            "days":days,"from_date":str(cutoff),
            "rows":n,"members":count}
