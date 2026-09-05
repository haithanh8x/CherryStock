-- AmiBroker Intraday recent-window data-quality smoke.
-- READ ONLY.
-- Window is bounded to each source's latest 30 calendar days.
-- Hard failures: required-field NULLs, DateTime/Date mismatch, invalid key sequence.
-- Warnings: negative Volume, invalid OHLC envelope, unexpected OpenInt distribution.

-- 1) Recent-window quality summary.
WITH q AS (
    SELECT
        'futures' AS source,
        COUNT(*) AS rows_checked,
        SUM(CASE WHEN "Ticker" IS NULL OR "Date" IS NULL OR "DateTime" IS NULL
                  OR "RawTime" IS NULL OR "TickSeq" IS NULL THEN 1 ELSE 0 END) AS required_nulls,
        SUM(CASE WHEN CAST("DateTime" AS DATE) <> "Date" THEN 1 ELSE 0 END) AS datetime_date_mismatch,
        SUM(CASE WHEN "TickSeq" < 0 THEN 1 ELSE 0 END) AS negative_tickseq,
        SUM(CASE WHEN "RawTime" < 0 THEN 1 ELSE 0 END) AS negative_rawtime,
        SUM(CASE WHEN "Volume" < 0 THEN 1 ELSE 0 END) AS negative_volume,
        SUM(CASE
            WHEN "High" < "Low"
              OR "Open" > "High"
              OR "Open" < "Low"
              OR "Close" > "High"
              OR "Close" < "Low"
            THEN 1 ELSE 0
        END) AS invalid_ohlc
    FROM "CherryMon"."main"."raw_futures_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_futures_intraday"
    )

    UNION ALL

    SELECT
        'index',
        COUNT(*),
        SUM(CASE WHEN "Ticker" IS NULL OR "Date" IS NULL OR "DateTime" IS NULL
                  OR "RawTime" IS NULL OR "TickSeq" IS NULL THEN 1 ELSE 0 END),
        SUM(CASE WHEN CAST("DateTime" AS DATE) <> "Date" THEN 1 ELSE 0 END),
        SUM(CASE WHEN "TickSeq" < 0 THEN 1 ELSE 0 END),
        SUM(CASE WHEN "RawTime" < 0 THEN 1 ELSE 0 END),
        SUM(CASE WHEN "Volume" < 0 THEN 1 ELSE 0 END),
        SUM(CASE
            WHEN "High" < "Low"
              OR "Open" > "High"
              OR "Open" < "Low"
              OR "Close" > "High"
              OR "Close" < "Low"
            THEN 1 ELSE 0
        END)
    FROM "CherryMon"."main"."raw_index_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_index_intraday"
    )

    UNION ALL

    SELECT
        'stock',
        COUNT(*),
        SUM(CASE WHEN "Ticker" IS NULL OR "Date" IS NULL OR "DateTime" IS NULL
                  OR "RawTime" IS NULL OR "TickSeq" IS NULL THEN 1 ELSE 0 END),
        SUM(CASE WHEN CAST("DateTime" AS DATE) <> "Date" THEN 1 ELSE 0 END),
        SUM(CASE WHEN "TickSeq" < 0 THEN 1 ELSE 0 END),
        SUM(CASE WHEN "RawTime" < 0 THEN 1 ELSE 0 END),
        SUM(CASE WHEN "Volume" < 0 THEN 1 ELSE 0 END),
        SUM(CASE
            WHEN "High" < "Low"
              OR "Open" > "High"
              OR "Open" < "Low"
              OR "Close" > "High"
              OR "Close" < "Low"
            THEN 1 ELSE 0
        END)
    FROM "CherryMon"."main"."raw_stock_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_stock_intraday"
    )

    UNION ALL

    SELECT
        'warrant',
        COUNT(*),
        SUM(CASE WHEN "Ticker" IS NULL OR "Date" IS NULL OR "DateTime" IS NULL
                  OR "RawTime" IS NULL OR "TickSeq" IS NULL THEN 1 ELSE 0 END),
        SUM(CASE WHEN CAST("DateTime" AS DATE) <> "Date" THEN 1 ELSE 0 END),
        SUM(CASE WHEN "TickSeq" < 0 THEN 1 ELSE 0 END),
        SUM(CASE WHEN "RawTime" < 0 THEN 1 ELSE 0 END),
        SUM(CASE WHEN "Volume" < 0 THEN 1 ELSE 0 END),
        SUM(CASE
            WHEN "High" < "Low"
              OR "Open" > "High"
              OR "Open" < "Low"
              OR "Close" > "High"
              OR "Close" < "Low"
            THEN 1 ELSE 0
        END)
    FROM "CherryMon"."main"."raw_warrant_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_warrant_intraday"
    )
)
SELECT
    source,
    rows_checked,
    required_nulls,
    datetime_date_mismatch,
    negative_tickseq,
    negative_rawtime,
    negative_volume,
    invalid_ohlc,
    CASE
        WHEN required_nulls = 0
         AND datetime_date_mismatch = 0
         AND negative_tickseq = 0
         AND negative_rawtime = 0
        THEN 'PASS'
        ELSE 'FAIL'
    END AS hard_status,
    CASE
        WHEN negative_volume = 0 AND invalid_ohlc = 0 THEN 'PASS'
        ELSE 'WARNING'
    END AS market_data_status
FROM q
ORDER BY source;


-- 2) Duplicate logical keys in recent window.
WITH duplicates AS (
    SELECT
        'futures' AS source,
        "Ticker" AS ticker,
        "Date" AS trade_date,
        "RawTime" AS raw_time,
        "TickSeq" AS tick_seq,
        COUNT(*) AS duplicate_rows
    FROM "CherryMon"."main"."raw_futures_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_futures_intraday"
    )
    GROUP BY "Ticker", "Date", "RawTime", "TickSeq"
    HAVING COUNT(*) > 1

    UNION ALL

    SELECT
        'index', "Ticker", "Date", "RawTime", "TickSeq", COUNT(*)
    FROM "CherryMon"."main"."raw_index_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_index_intraday"
    )
    GROUP BY "Ticker", "Date", "RawTime", "TickSeq"
    HAVING COUNT(*) > 1

    UNION ALL

    SELECT
        'stock', "Ticker", "Date", "RawTime", "TickSeq", COUNT(*)
    FROM "CherryMon"."main"."raw_stock_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_stock_intraday"
    )
    GROUP BY "Ticker", "Date", "RawTime", "TickSeq"
    HAVING COUNT(*) > 1

    UNION ALL

    SELECT
        'warrant', "Ticker", "Date", "RawTime", "TickSeq", COUNT(*)
    FROM "CherryMon"."main"."raw_warrant_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_warrant_intraday"
    )
    GROUP BY "Ticker", "Date", "RawTime", "TickSeq"
    HAVING COUNT(*) > 1
)
SELECT
    source,
    COUNT(*) AS duplicate_key_groups,
    COALESCE(SUM(duplicate_rows - 1), 0) AS excess_rows,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM duplicates
GROUP BY source

UNION ALL

SELECT 'futures', 0, 0, 'PASS'
WHERE NOT EXISTS (SELECT 1 FROM duplicates WHERE source = 'futures')

UNION ALL

SELECT 'index', 0, 0, 'PASS'
WHERE NOT EXISTS (SELECT 1 FROM duplicates WHERE source = 'index')

UNION ALL

SELECT 'stock', 0, 0, 'PASS'
WHERE NOT EXISTS (SELECT 1 FROM duplicates WHERE source = 'stock')

UNION ALL

SELECT 'warrant', 0, 0, 'PASS'
WHERE NOT EXISTS (SELECT 1 FROM duplicates WHERE source = 'warrant')
ORDER BY source;


-- 3) TickSeq continuity within each same-timestamp group.
WITH seq_groups AS (
    SELECT
        'futures' AS source,
        "Ticker" AS ticker,
        "Date" AS trade_date,
        "RawTime" AS raw_time,
        COUNT(*) AS row_count,
        MIN("TickSeq") AS min_seq,
        MAX("TickSeq") AS max_seq
    FROM "CherryMon"."main"."raw_futures_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_futures_intraday"
    )
    GROUP BY "Ticker", "Date", "RawTime"

    UNION ALL

    SELECT
        'index', "Ticker", "Date", "RawTime",
        COUNT(*), MIN("TickSeq"), MAX("TickSeq")
    FROM "CherryMon"."main"."raw_index_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_index_intraday"
    )
    GROUP BY "Ticker", "Date", "RawTime"

    UNION ALL

    SELECT
        'stock', "Ticker", "Date", "RawTime",
        COUNT(*), MIN("TickSeq"), MAX("TickSeq")
    FROM "CherryMon"."main"."raw_stock_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_stock_intraday"
    )
    GROUP BY "Ticker", "Date", "RawTime"

    UNION ALL

    SELECT
        'warrant', "Ticker", "Date", "RawTime",
        COUNT(*), MIN("TickSeq"), MAX("TickSeq")
    FROM "CherryMon"."main"."raw_warrant_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_warrant_intraday"
    )
    GROUP BY "Ticker", "Date", "RawTime"
),
bad AS (
    SELECT
        source,
        ticker,
        trade_date,
        raw_time,
        row_count,
        min_seq,
        max_seq
    FROM seq_groups
    WHERE min_seq <> 0
       OR max_seq <> row_count - 1
)
SELECT
    source,
    COUNT(*) AS bad_sequence_groups,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM bad
GROUP BY source

UNION ALL

SELECT 'futures', 0, 'PASS'
WHERE NOT EXISTS (SELECT 1 FROM bad WHERE source = 'futures')

UNION ALL

SELECT 'index', 0, 'PASS'
WHERE NOT EXISTS (SELECT 1 FROM bad WHERE source = 'index')

UNION ALL

SELECT 'stock', 0, 'PASS'
WHERE NOT EXISTS (SELECT 1 FROM bad WHERE source = 'stock')

UNION ALL

SELECT 'warrant', 0, 'PASS'
WHERE NOT EXISTS (SELECT 1 FROM bad WHERE source = 'warrant')
ORDER BY source;


-- 4) OpenInt source-value distribution, recent window.
-- Informational only. Do not auto-fix unexpected values from this query.
WITH oi AS (
    SELECT 'futures' AS source, "OpenInt" AS open_int, COUNT(*) AS rows
    FROM "CherryMon"."main"."raw_futures_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_futures_intraday"
    )
    GROUP BY "OpenInt"

    UNION ALL

    SELECT 'index', "OpenInt", COUNT(*)
    FROM "CherryMon"."main"."raw_index_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_index_intraday"
    )
    GROUP BY "OpenInt"

    UNION ALL

    SELECT 'stock', "OpenInt", COUNT(*)
    FROM "CherryMon"."main"."raw_stock_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_stock_intraday"
    )
    GROUP BY "OpenInt"

    UNION ALL

    SELECT 'warrant', "OpenInt", COUNT(*)
    FROM "CherryMon"."main"."raw_warrant_intraday"
    WHERE "Date" >= (
        SELECT MAX("Date") - INTERVAL 30 DAY
        FROM "CherryMon"."main"."raw_warrant_intraday"
    )
    GROUP BY "OpenInt"
),
ranked AS (
    SELECT
        source,
        open_int,
        rows,
        ROW_NUMBER() OVER (
            PARTITION BY source
            ORDER BY rows DESC, open_int
        ) AS value_rank
    FROM oi
)
SELECT
    source,
    open_int,
    rows
FROM ranked
WHERE value_rank <= 20
ORDER BY source, rows DESC, open_int;
