-- AmiBroker Intraday smoke overview.
-- READ ONLY.
-- Purpose: row/ticker/date coverage, recent daily counts and ticker-size outliers.

-- 1) Whole-table overview.
SELECT
    'futures' AS source,
    COUNT(*) AS row_count,
    COUNT(DISTINCT "Ticker") AS ticker_count,
    COUNT(DISTINCT "Date") AS date_count,
    MIN("Date") AS min_date,
    MAX("Date") AS max_date,
    MIN("DateTime") AS min_datetime,
    MAX("DateTime") AS max_datetime
FROM "CherryMon"."main"."raw_futures_intraday"

UNION ALL

SELECT
    'index',
    COUNT(*),
    COUNT(DISTINCT "Ticker"),
    COUNT(DISTINCT "Date"),
    MIN("Date"),
    MAX("Date"),
    MIN("DateTime"),
    MAX("DateTime")
FROM "CherryMon"."main"."raw_index_intraday"

UNION ALL

SELECT
    'stock',
    COUNT(*),
    COUNT(DISTINCT "Ticker"),
    COUNT(DISTINCT "Date"),
    MIN("Date"),
    MAX("Date"),
    MIN("DateTime"),
    MAX("DateTime")
FROM "CherryMon"."main"."raw_stock_intraday"

UNION ALL

SELECT
    'warrant',
    COUNT(*),
    COUNT(DISTINCT "Ticker"),
    COUNT(DISTINCT "Date"),
    MIN("Date"),
    MAX("Date"),
    MIN("DateTime"),
    MAX("DateTime")
FROM "CherryMon"."main"."raw_warrant_intraday"
ORDER BY source;

-- Smoke expectation:
-- - row_count > 0 for sources that have local FireAnt files;
-- - max_date should be close to the latest loaded trading date;
-- - stock should normally have the largest ticker/row counts.


-- 2) Last 15 loaded dates per source.
WITH daily AS (
    SELECT
        'futures' AS source,
        "Date" AS trade_date,
        COUNT(*) AS tick_count,
        COUNT(DISTINCT "Ticker") AS ticker_count
    FROM "CherryMon"."main"."raw_futures_intraday"
    GROUP BY "Date"

    UNION ALL

    SELECT
        'index',
        "Date",
        COUNT(*),
        COUNT(DISTINCT "Ticker")
    FROM "CherryMon"."main"."raw_index_intraday"
    GROUP BY "Date"

    UNION ALL

    SELECT
        'stock',
        "Date",
        COUNT(*),
        COUNT(DISTINCT "Ticker")
    FROM "CherryMon"."main"."raw_stock_intraday"
    GROUP BY "Date"

    UNION ALL

    SELECT
        'warrant',
        "Date",
        COUNT(*),
        COUNT(DISTINCT "Ticker")
    FROM "CherryMon"."main"."raw_warrant_intraday"
    GROUP BY "Date"
),
ranked AS (
    SELECT
        source,
        trade_date,
        tick_count,
        ticker_count,
        ROW_NUMBER() OVER (
            PARTITION BY source
            ORDER BY trade_date DESC
        ) AS date_rank
    FROM daily
)
SELECT
    source,
    trade_date,
    tick_count,
    ticker_count
FROM ranked
WHERE date_rank <= 15
ORDER BY source, trade_date DESC;

-- Review for abrupt day-to-day collapse in tick_count/ticker_count.


-- 3) Ticker distribution for the most recent 30 calendar days.
WITH ticker_counts AS (
    SELECT
        'futures' AS source,
        "Ticker" AS ticker,
        COUNT(*) AS tick_count,
        COUNT(DISTINCT "Date") AS traded_dates,
        MIN("Date") AS min_date,
        MAX("Date") AS max_date
    FROM "CherryMon"."main"."raw_futures_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_futures_intraday"
    )
    GROUP BY "Ticker"

    UNION ALL

    SELECT
        'index',
        "Ticker",
        COUNT(*),
        COUNT(DISTINCT "Date"),
        MIN("Date"),
        MAX("Date")
    FROM "CherryMon"."main"."raw_index_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_index_intraday"
    )
    GROUP BY "Ticker"

    UNION ALL

    SELECT
        'stock',
        "Ticker",
        COUNT(*),
        COUNT(DISTINCT "Date"),
        MIN("Date"),
        MAX("Date")
    FROM "CherryMon"."main"."raw_stock_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_stock_intraday"
    )
    GROUP BY "Ticker"

    UNION ALL

    SELECT
        'warrant',
        "Ticker",
        COUNT(*),
        COUNT(DISTINCT "Date"),
        MIN("Date"),
        MAX("Date")
    FROM "CherryMon"."main"."raw_warrant_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_warrant_intraday"
    )
    GROUP BY "Ticker"
),
ranked AS (
    SELECT
        source,
        ticker,
        tick_count,
        traded_dates,
        min_date,
        max_date,
        ROW_NUMBER() OVER (
            PARTITION BY source
            ORDER BY tick_count DESC, ticker
        ) AS high_rank,
        ROW_NUMBER() OVER (
            PARTITION BY source
            ORDER BY tick_count ASC, ticker
        ) AS low_rank
    FROM ticker_counts
)
SELECT
    source,
    CASE WHEN high_rank <= 10 THEN 'TOP' ELSE 'BOTTOM' END AS bucket,
    ticker,
    tick_count,
    traded_dates,
    min_date,
    max_date
FROM ranked
WHERE high_rank <= 10 OR low_rank <= 10
ORDER BY source, bucket DESC, tick_count DESC, ticker;
