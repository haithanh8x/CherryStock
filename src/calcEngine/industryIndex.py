"""Industry indices from current FreeFloat shares and adjusted daily ticker OHLC.

Independent implementation: never calls calculate_composite_index().
All mutations must run inside the caller-owned DuckDBUnitOfWork transaction.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

INDEX_TABLE = '"CherryMon"."main"."cal_Industry_Index_D"'
WEIGHT_TABLE = '"CherryMon"."main"."cal_Industry_Index_Weights"'
MEMBERS_VIEW = '"CherryMon"."main"."vw_Ticker_Info"'
OHLC_VIEW = "(SELECT * FROM \"CherryMon\".\"main\".\"vw_Ticker_OHLC\" WHERE \"AssetType\" = 'STOCK')"
SCHEMA_FILE = Path(__file__).resolve().parents[1] / "DuckDB" / "sql" / "industry_index_v1_schema.sql"
BASE_INDEX = 1000.0
CALCULATION_MODE = "HISTORICAL_PROXY_LATEST_FLOAT"


def _scalar(connection, statement: str, parameters=None):
    row = connection.execute(statement, parameters or []).fetchone()
    return None if row is None else row[0]


def refresh_industry_index(*, days: int | None = None, connection) -> dict[str, object]:
    """Refresh the most recent N *trading sessions*, or all history if days=None.

    The caller owns BEGIN/COMMIT/ROLLBACK. Checkpoint replacement of index rows
    and constituent weights is atomic and idempotent for the selected date range.
    A first run with days=N automatically bootstraps full history.
    """
    if days is not None and (isinstance(days, bool) or not isinstance(days, int) or days < 1):
        raise ValueError("days must be a positive number of trading sessions or None")

    connection.execute(SCHEMA_FILE.read_text(encoding="utf-8"))

    # The active universe is a latest snapshot. No historical survivorship claim.
    connection.execute(f"""
        CREATE OR REPLACE TEMP TABLE _industry_members AS
        SELECT
            UPPER(TRIM(CAST("Ticker" AS VARCHAR))) AS "Ticker",
            TRIM(CAST("IndustryCode" AS VARCHAR)) AS "IndustryCode",
            TRIM(CAST("Industry" AS VARCHAR)) AS "Industry",
            TRY_CAST("FreeFloat" AS DOUBLE) AS "FloatShares",
            TRY_CAST("Shares Outstanding" AS DOUBLE) AS "OutstandingShares"
        FROM {MEMBERS_VIEW}
        WHERE "AssetType" = 'STOCK'
          AND "Ticker" IS NOT NULL
          AND TRIM(CAST("Ticker" AS VARCHAR)) <> ''
          AND "IndustryCode" IS NOT NULL
          AND TRIM(CAST("IndustryCode" AS VARCHAR)) <> ''
    """)
    duplicates = _scalar(connection, """
        SELECT COUNT(*) FROM (
            SELECT "Ticker" FROM _industry_members
            GROUP BY "Ticker" HAVING COUNT(*) > 1
        ) AS duplicated
    """)
    if duplicates:
        raise RuntimeError(f"vw_Ticker_Info has {duplicates} duplicate ticker(s)")
    if not _scalar(connection, "SELECT COUNT(*) FROM _industry_members"):
        raise RuntimeError("No active stock with IndustryCode; industry index not refreshed")

    invalid_shares = _scalar(connection, """
        SELECT COUNT(*) FROM _industry_members
        WHERE "FloatShares" > 0 AND "OutstandingShares" > 0
          AND "FloatShares" > "OutstandingShares"
    """)
    if invalid_shares:
        raise RuntimeError(
            f"{invalid_shares} ticker(s): FreeFloat shares exceed Shares Outstanding; "
            "verify source field units before calculating"
        )

    # For a brand-new database, a bounded refresh must establish an actual base.
    existing = _scalar(connection, f"SELECT COUNT(*) FROM {INDEX_TABLE}")
    full = days is None or existing == 0

    if full:
        cutoff = _scalar(connection, f"""
            SELECT MIN(o."Date")
            FROM {OHLC_VIEW} AS o
            INNER JOIN _industry_members AS m
              ON UPPER(TRIM(CAST(o."Ticker" AS VARCHAR))) = m."Ticker"
            WHERE o."Close" > 0 AND isfinite(o."Close")
        """)
    else:
        cutoff = _scalar(connection, f"""
            SELECT MIN("Date") FROM (
                SELECT DISTINCT o."Date"
                FROM {OHLC_VIEW} AS o
                INNER JOIN _industry_members AS m
                  ON UPPER(TRIM(CAST(o."Ticker" AS VARCHAR))) = m."Ticker"
                WHERE o."Close" > 0 AND isfinite(o."Close")
                ORDER BY o."Date" DESC
                LIMIT ?
            ) AS trading_sessions
        """, [days])

    if cutoff is None:
        raise RuntimeError("No valid stock OHLC for the current industry universe")

    # Persist all eligible OHLC rows for the selected days; EW includes tickers
    # without FreeFloat, whereas FFMC requires positive free-float shares.
    connection.execute(f"""
        CREATE OR REPLACE TEMP TABLE _industry_prices AS
        SELECT
            o."Date", m."IndustryCode", m."Industry", m."Ticker",
            CAST(o."Close" AS DOUBLE) AS "Close",
            o."Volume", o."TradingValue", o."TradingValue_IsProxy",
            m."FloatShares",
            FALSE AS "IsSeed"
        FROM {OHLC_VIEW} AS o
        INNER JOIN _industry_members AS m
          ON UPPER(TRIM(CAST(o."Ticker" AS VARCHAR))) = m."Ticker"
        WHERE o."AssetType" = 'STOCK'
          AND o."Date" >= ?
          AND o."Close" > 0 AND isfinite(o."Close")
    """, [cutoff])

    # A seed is the last available closing price for each ticker before the
    # checkpoint. Lag must not start at the checkpoint itself.
    connection.execute("""
        CREATE OR REPLACE TEMP TABLE _industry_seed AS
        SELECT "Date", "IndustryCode", "Industry", "Ticker", "Close",
               "Volume", "TradingValue", "TradingValue_IsProxy",
               "FloatShares", "IsSeed"
        FROM _industry_prices WHERE FALSE
    """)
    if not full:
        connection.execute(f"""
            INSERT INTO _industry_seed (
                "Date", "IndustryCode", "Industry", "Ticker", "Close",
                "Volume", "TradingValue", "TradingValue_IsProxy",
                "FloatShares", "IsSeed"
            )
            SELECT
                MAX(o."Date"), m."IndustryCode", MAX(m."Industry"), m."Ticker",
                ARG_MAX(CAST(o."Close" AS DOUBLE), o."Date"),
                NULL, NULL, NULL, MAX(m."FloatShares"), TRUE
            FROM {OHLC_VIEW} AS o
            INNER JOIN _industry_members AS m
              ON UPPER(TRIM(CAST(o."Ticker" AS VARCHAR))) = m."Ticker"
            WHERE o."Date" < ? AND o."Close" > 0 AND isfinite(o."Close")
            GROUP BY m."Ticker", m."IndustryCode"
        """, [cutoff])

    # Inputs are expected to honor the OHLC consumer grain Ticker + Date.
    duplicated_prices = _scalar(connection, """
        SELECT COUNT(*) FROM (
            SELECT "Ticker", "Date" FROM _industry_prices
            GROUP BY "Ticker", "Date" HAVING COUNT(*) > 1
        ) AS duplicated
    """)
    if duplicated_prices:
        raise RuntimeError(
            f"vw_Ticker_OHLC_D has {duplicated_prices} duplicate ticker/date group(s)"
        )

    connection.execute("""
        CREATE OR REPLACE TEMP TABLE _industry_stage AS
        WITH history AS (
            SELECT
                "Date", "IndustryCode", "Industry", "Ticker", "Close",
                "Volume", "TradingValue", "TradingValue_IsProxy",
                "FloatShares", "IsSeed"
            FROM _industry_prices
            UNION ALL
            SELECT
                "Date", "IndustryCode", "Industry", "Ticker", "Close",
                "Volume", "TradingValue", "TradingValue_IsProxy",
                "FloatShares", "IsSeed"
            FROM _industry_seed
        ), lagged AS (
            SELECT
                "Date", "IndustryCode", "Industry", "Ticker", "Close",
                "Volume", "TradingValue", "TradingValue_IsProxy",
                "FloatShares", "IsSeed",
                LAG("Close") OVER (
                    PARTITION BY "Ticker" ORDER BY "Date"
                ) AS "LagClose"
            FROM history
        )
        SELECT
            "Date", "IndustryCode", "Industry", "Ticker", "Close",
            COALESCE("LagClose", "Close") AS "PreviousClose",
            "Volume", "TradingValue", "TradingValue_IsProxy",
            "FloatShares"
        FROM lagged
        WHERE NOT "IsSeed"
    """)

    connection.execute("""
        CREATE OR REPLACE TEMP TABLE _industry_contrib AS
        SELECT
            "Date", "IndustryCode", "Industry", "Ticker", "Close",
            "PreviousClose", "Volume", "TradingValue", "TradingValue_IsProxy",
            "FloatShares", 'EW' AS "Index_Method",
            1.0 AS "PreviousCapital", 1.0 AS "ClosingCapital",
            "Close" / "PreviousClose" - 1.0 AS "PriceReturn"
        FROM _industry_stage
        UNION ALL
        SELECT
            "Date", "IndustryCode", "Industry", "Ticker", "Close",
            "PreviousClose", "Volume", "TradingValue", "TradingValue_IsProxy",
            "FloatShares", 'FFMC' AS "Index_Method",
            "PreviousClose" * "FloatShares" AS "PreviousCapital",
            "Close" * "FloatShares" AS "ClosingCapital",
            "Close" / "PreviousClose" - 1.0 AS "PriceReturn"
        FROM _industry_stage
        WHERE "FloatShares" > 0 AND isfinite("FloatShares")
    """)

    connection.execute("""
        CREATE OR REPLACE TEMP TABLE _industry_weights AS
        WITH weighted AS (
            SELECT
                "Date", "IndustryCode", "Industry", "Ticker", "Close",
                "PreviousClose", "Volume", "TradingValue",
                "TradingValue_IsProxy", "FloatShares", "Index_Method",
                "PriceReturn", "ClosingCapital",
                "ClosingCapital" / SUM("ClosingCapital") OVER (
                    PARTITION BY "Date", "IndustryCode", "Index_Method"
                ) AS "Weight",
                "PreviousCapital" / SUM("PreviousCapital") OVER (
                    PARTITION BY "Date", "IndustryCode", "Index_Method"
                ) AS "ReturnWeight"
            FROM _industry_contrib
        )
        SELECT
            "Date", "IndustryCode", "Industry", "Ticker", "Close",
            "PreviousClose", "Volume", "TradingValue",
            "TradingValue_IsProxy", "FloatShares", "Index_Method",
            "ClosingCapital", "Weight", "ReturnWeight", "PriceReturn",
            "ReturnWeight" * "PriceReturn" AS "ReturnContribution",
            ROW_NUMBER() OVER (
                PARTITION BY "Date", "IndustryCode", "Index_Method"
                ORDER BY "Weight" DESC, "Ticker"
            ) AS "WeightRank"
        FROM weighted
    """)

    connection.execute("""
        CREATE OR REPLACE TEMP TABLE _industry_daily AS
        SELECT
            "Date", "IndustryCode", MAX("Industry") AS "Industry",
            "Index_Method",
            SUM("ReturnContribution") AS "ComputedReturn",
            CAST(SUM(COALESCE("Volume", 0)) AS BIGINT) AS "Volume",
            CASE WHEN COUNT("TradingValue") = 0 THEN NULL
                 ELSE CAST(SUM("TradingValue") AS HUGEINT)
            END AS "TradingValue",
            CAST(COUNT("TradingValue") AS INTEGER) AS "TradingValueKnownCount",
            CAST(COUNT(*) FILTER (WHERE "TradingValue_IsProxy" = TRUE)
                 AS INTEGER) AS "TradingValueProxyCount",
            CAST(COUNT(*) AS INTEGER) AS "TickerCount",
            CAST(COUNT(*) FILTER (WHERE "PriceReturn" > 0) AS INTEGER)
                AS "Advancers",
            CAST(COUNT(*) FILTER (WHERE "PriceReturn" < 0) AS INTEGER)
                AS "Decliners",
            CAST(COUNT(*) FILTER (WHERE "PriceReturn" = 0) AS INTEGER)
                AS "Unchanged",
            CASE WHEN "Index_Method" = 'FFMC'
                 THEN SUM("ClosingCapital") ELSE NULL
            END AS "FloatMarketCap",
            MAX("Weight") AS "MaxWeight",
            SUM("Weight") FILTER (WHERE "WeightRank" <= 3) AS "Top3Weight"
        FROM _industry_weights
        GROUP BY "Date", "IndustryCode", "Index_Method"
    """)

    # For partial reruns, chain only from the immediately preceding persisted
    # industry/method close; for full rebuild, deliberately ignore old anchors.
    no_anchor = "AND FALSE" if full else ""
    connection.execute(f"""
        CREATE OR REPLACE TEMP TABLE _industry_result AS
        WITH anchor AS (
            SELECT "IndustryCode", "Index_Method",
                   ARG_MAX("Close", "Date") AS "AnchorClose"
            FROM {INDEX_TABLE}
            WHERE "Date" < ? {no_anchor}
            GROUP BY "IndustryCode", "Index_Method"
        ), numbered AS (
            SELECT d.*, a."AnchorClose",
                   ROW_NUMBER() OVER (
                       PARTITION BY d."IndustryCode", d."Index_Method"
                       ORDER BY d."Date"
                   ) AS "Seq"
            FROM _industry_daily AS d
            LEFT JOIN anchor AS a
              ON a."IndustryCode" = d."IndustryCode"
             AND a."Index_Method" = d."Index_Method"
        ), returns AS (
            SELECT *,
                CASE WHEN "AnchorClose" IS NULL AND "Seq" = 1
                     THEN 0.0 ELSE "ComputedReturn"
                END AS "DailyReturn"
            FROM numbered
        )
        SELECT
            "Date", "IndustryCode", "Industry", "Index_Method",
            COALESCE("AnchorClose", {BASE_INDEX}) *
              EXP(SUM(LN(1.0 + "DailyReturn")) OVER (
                  PARTITION BY "IndustryCode", "Index_Method"
                  ORDER BY "Date" ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
              )) AS "IndexClose",
            "DailyReturn", "DailyReturn" * 100.0 AS "PctChange",
            "Volume", "TradingValue", "TradingValueKnownCount",
            "TradingValueProxyCount", "TickerCount", "Advancers",
            "Decliners", "Unchanged", "FloatMarketCap",
            "MaxWeight", "Top3Weight"
        FROM returns
    """, [cutoff])

    generated = _scalar(connection, "SELECT COUNT(*) FROM _industry_result")
    if not generated:
        raise RuntimeError("Industry result empty; existing industry index was not touched")
    min_factor = _scalar(connection, """
        SELECT MIN(1.0 + "DailyReturn") FROM _industry_result
    """)
    if min_factor is None or min_factor <= 0:
        raise RuntimeError("Industry return chain contains a non-positive factor")

    # Window replacement is an atomic date-key upsert: changed rows are rewritten
    # and stale sector/constituent rows in this window are removed as well.
    if full:
        connection.execute(f"DELETE FROM {WEIGHT_TABLE}")
        connection.execute(f"DELETE FROM {INDEX_TABLE}")
    else:
        connection.execute(f'DELETE FROM {WEIGHT_TABLE} WHERE "Date" >= ?', [cutoff])
        connection.execute(f'DELETE FROM {INDEX_TABLE} WHERE "Date" >= ?', [cutoff])

    connection.execute(f"""
        INSERT INTO {INDEX_TABLE} (
            "Date", "IndustryCode", "Industry", "Index_Method",
            "Close", "Daily_Return", "Pct_Change", "Volume",
            "TradingValue", "TradingValue_Known_Count",
            "TradingValue_Proxy_Count", "Ticker_Count", "Advancers",
            "Decliners", "Unchanged", "FloatMarketCap_ThousandVND",
            "Max_Weight", "Top3_Weight", "Calculation_Mode",
            "Snapshot_Date", "Calculated_At"
        )
        SELECT
            "Date", "IndustryCode", "Industry", "Index_Method",
            "IndexClose", "DailyReturn", "PctChange", "Volume",
            "TradingValue", "TradingValueKnownCount",
            "TradingValueProxyCount", "TickerCount", "Advancers",
            "Decliners", "Unchanged", "FloatMarketCap",
            "MaxWeight", "Top3Weight", ?, CURRENT_DATE, CURRENT_TIMESTAMP
        FROM _industry_result
    """, [CALCULATION_MODE])
    connection.execute(f"""
        INSERT INTO {WEIGHT_TABLE} (
            "Date", "IndustryCode", "Index_Method", "Ticker",
            "Close", "Previous_Close", "FloatShares", "Weight",
            "Return_Weight", "Price_Return", "Return_Contribution",
            "Snapshot_Date"
        )
        SELECT "Date", "IndustryCode", "Index_Method", "Ticker",
               "Close", "PreviousClose", "FloatShares", "Weight",
               "ReturnWeight", "PriceReturn", "ReturnContribution",
               CURRENT_DATE
        FROM _industry_weights
    """)

    result = {
        "mode": "full" if full else "incremental",
        "requested_days": days,
        "from_date": str(cutoff),
        "through_date": str(_scalar(connection, 'SELECT MAX("Date") FROM _industry_result')),
        "index_rows": int(generated),
        "weight_rows": int(_scalar(connection, "SELECT COUNT(*) FROM _industry_weights")),
        "active_tickers": int(_scalar(connection, "SELECT COUNT(*) FROM _industry_members")),
        "without_positive_float": int(_scalar(connection, """
            SELECT COUNT(*) FROM _industry_members
            WHERE "FloatShares" IS NULL OR "FloatShares" <= 0
        """)),
        "calculation_mode": CALCULATION_MODE,
    }
    return result
