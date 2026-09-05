-- AmiBroker Intraday <-> EOD reconciliation.
-- READ ONLY.
-- Recent window: 30 calendar days ending at each source's latest EOD date.
--
-- Price tolerance used only to classify suspect rows:
--   absolute OHLC difference > 0.05 => mismatch candidate.
-- Volume is reported separately because intraday/EOD trade-scope semantics may differ.
-- Do not repair data automatically from this script.

WITH
stock_i AS (
    SELECT
        "Ticker" AS ticker,
        "Date" AS trade_date,
        FIRST("Open" ORDER BY "DateTime", "RawTime", "TickSeq") AS i_open,
        MAX("High") AS i_high,
        MIN("Low") AS i_low,
        LAST("Close" ORDER BY "DateTime", "RawTime", "TickSeq") AS i_close,
        SUM("Volume") AS i_volume,
        COUNT(*) AS tick_count
    FROM "CherryMon"."main"."raw_stock_intraday"
    WHERE "Date" BETWEEN
        (SELECT MAX("Date") - INTERVAL 30 DAY FROM "CherryMon"."main"."raw_stock_eod")
        AND
        (SELECT MAX("Date") FROM "CherryMon"."main"."raw_stock_eod")
    GROUP BY "Ticker", "Date"
),
stock_e AS (
    SELECT
        "Ticker" AS ticker,
        "Date" AS trade_date,
        "Open" AS e_open,
        "High" AS e_high,
        "Low" AS e_low,
        "Close" AS e_close,
        "Volume" AS e_volume
    FROM "CherryMon"."main"."raw_stock_eod"
    WHERE "Date" BETWEEN
        (SELECT MAX("Date") - INTERVAL 30 DAY FROM "CherryMon"."main"."raw_stock_eod")
        AND
        (SELECT MAX("Date") FROM "CherryMon"."main"."raw_stock_eod")
),
futures_i AS (
    SELECT
        "Ticker" AS ticker,
        "Date" AS trade_date,
        FIRST("Open" ORDER BY "DateTime", "RawTime", "TickSeq") AS i_open,
        MAX("High") AS i_high,
        MIN("Low") AS i_low,
        LAST("Close" ORDER BY "DateTime", "RawTime", "TickSeq") AS i_close,
        SUM("Volume") AS i_volume,
        COUNT(*) AS tick_count
    FROM "CherryMon"."main"."raw_futures_intraday"
    WHERE "Date" BETWEEN
        (SELECT MAX("Date") - INTERVAL 30 DAY FROM "CherryMon"."main"."raw_futures_eod")
        AND
        (SELECT MAX("Date") FROM "CherryMon"."main"."raw_futures_eod")
    GROUP BY "Ticker", "Date"
),
futures_e AS (
    SELECT
        "Ticker" AS ticker,
        "Date" AS trade_date,
        "Open" AS e_open,
        "High" AS e_high,
        "Low" AS e_low,
        "Close" AS e_close,
        "Volume" AS e_volume
    FROM "CherryMon"."main"."raw_futures_eod"
    WHERE "Date" BETWEEN
        (SELECT MAX("Date") - INTERVAL 30 DAY FROM "CherryMon"."main"."raw_futures_eod")
        AND
        (SELECT MAX("Date") FROM "CherryMon"."main"."raw_futures_eod")
),
index_i AS (
    SELECT
        "Ticker" AS ticker,
        "Date" AS trade_date,
        FIRST("Open" ORDER BY "DateTime", "RawTime", "TickSeq") AS i_open,
        MAX("High") AS i_high,
        MIN("Low") AS i_low,
        LAST("Close" ORDER BY "DateTime", "RawTime", "TickSeq") AS i_close,
        SUM("Volume") AS i_volume,
        COUNT(*) AS tick_count
    FROM "CherryMon"."main"."raw_index_intraday"
    WHERE "Date" BETWEEN
        (SELECT MAX("Date") - INTERVAL 30 DAY FROM "CherryMon"."main"."raw_index_eod")
        AND
        (SELECT MAX("Date") FROM "CherryMon"."main"."raw_index_eod")
    GROUP BY "Ticker", "Date"
),
index_e AS (
    SELECT
        "Ticker" AS ticker,
        "Date" AS trade_date,
        "Open" AS e_open,
        "High" AS e_high,
        "Low" AS e_low,
        "Close" AS e_close,
        "Volume" AS e_volume
    FROM "CherryMon"."main"."raw_index_eod"
    WHERE "Date" BETWEEN
        (SELECT MAX("Date") - INTERVAL 30 DAY FROM "CherryMon"."main"."raw_index_eod")
        AND
        (SELECT MAX("Date") FROM "CherryMon"."main"."raw_index_eod")
),
warrant_i AS (
    SELECT
        "Ticker" AS ticker,
        "Date" AS trade_date,
        FIRST("Open" ORDER BY "DateTime", "RawTime", "TickSeq") AS i_open,
        MAX("High") AS i_high,
        MIN("Low") AS i_low,
        LAST("Close" ORDER BY "DateTime", "RawTime", "TickSeq") AS i_close,
        SUM("Volume") AS i_volume,
        COUNT(*) AS tick_count
    FROM "CherryMon"."main"."raw_warrant_intraday"
    WHERE "Date" BETWEEN
        (SELECT MAX("Date") - INTERVAL 30 DAY FROM "CherryMon"."main"."raw_warrant_eod")
        AND
        (SELECT MAX("Date") FROM "CherryMon"."main"."raw_warrant_eod")
    GROUP BY "Ticker", "Date"
),
warrant_e AS (
    SELECT
        "Ticker" AS ticker,
        "Date" AS trade_date,
        "Open" AS e_open,
        "High" AS e_high,
        "Low" AS e_low,
        "Close" AS e_close,
        "Volume" AS e_volume
    FROM "CherryMon"."main"."raw_warrant_eod"
    WHERE "Date" BETWEEN
        (SELECT MAX("Date") - INTERVAL 30 DAY FROM "CherryMon"."main"."raw_warrant_eod")
        AND
        (SELECT MAX("Date") FROM "CherryMon"."main"."raw_warrant_eod")
),
pairs AS (
    SELECT
        'stock' AS source,
        COALESCE(i.ticker, e.ticker) AS ticker,
        COALESCE(i.trade_date, e.trade_date) AS trade_date,
        i.tick_count,
        i.i_open, i.i_high, i.i_low, i.i_close, i.i_volume,
        e.e_open, e.e_high, e.e_low, e.e_close, e.e_volume
    FROM stock_i AS i
    FULL OUTER JOIN stock_e AS e
        ON e.ticker = i.ticker
       AND e.trade_date = i.trade_date

    UNION ALL

    SELECT
        'futures',
        COALESCE(i.ticker, e.ticker),
        COALESCE(i.trade_date, e.trade_date),
        i.tick_count,
        i.i_open, i.i_high, i.i_low, i.i_close, i.i_volume,
        e.e_open, e.e_high, e.e_low, e.e_close, e.e_volume
    FROM futures_i AS i
    FULL OUTER JOIN futures_e AS e
        ON e.ticker = i.ticker
       AND e.trade_date = i.trade_date

    UNION ALL

    SELECT
        'index',
        COALESCE(i.ticker, e.ticker),
        COALESCE(i.trade_date, e.trade_date),
        i.tick_count,
        i.i_open, i.i_high, i.i_low, i.i_close, i.i_volume,
        e.e_open, e.e_high, e.e_low, e.e_close, e.e_volume
    FROM index_i AS i
    FULL OUTER JOIN index_e AS e
        ON e.ticker = i.ticker
       AND e.trade_date = i.trade_date

    UNION ALL

    SELECT
        'warrant',
        COALESCE(i.ticker, e.ticker),
        COALESCE(i.trade_date, e.trade_date),
        i.tick_count,
        i.i_open, i.i_high, i.i_low, i.i_close, i.i_volume,
        e.e_open, e.e_high, e.e_low, e.e_close, e.e_volume
    FROM warrant_i AS i
    FULL OUTER JOIN warrant_e AS e
        ON e.ticker = i.ticker
       AND e.trade_date = i.trade_date
),
classified AS (
    SELECT
        source,
        ticker,
        trade_date,
        tick_count,
        i_open, e_open,
        i_high, e_high,
        i_low, e_low,
        i_close, e_close,
        i_volume, e_volume,
        CASE
            WHEN tick_count IS NULL THEN 'EOD_ONLY'
            WHEN e_close IS NULL THEN 'INTRADAY_ONLY'
            ELSE 'MATCHED'
        END AS coverage_status,
        ABS(i_open - e_open) AS open_abs_diff,
        ABS(i_high - e_high) AS high_abs_diff,
        ABS(i_low - e_low) AS low_abs_diff,
        ABS(i_close - e_close) AS close_abs_diff,
        i_volume - e_volume AS volume_diff,
        CASE
            WHEN e_volume IS NULL OR e_volume = 0 THEN NULL
            ELSE (i_volume - e_volume) * 1.0 / e_volume
        END AS volume_diff_pct
    FROM pairs
)

-- 1) Reconciliation summary by source.
SELECT
    source,
    COUNT(*) AS ticker_date_pairs,
    SUM(CASE WHEN coverage_status = 'MATCHED' THEN 1 ELSE 0 END) AS matched_pairs,
    SUM(CASE WHEN coverage_status = 'EOD_ONLY' THEN 1 ELSE 0 END) AS eod_only_pairs,
    SUM(CASE WHEN coverage_status = 'INTRADAY_ONLY' THEN 1 ELSE 0 END) AS intraday_only_pairs,
    SUM(CASE WHEN coverage_status = 'MATCHED' AND open_abs_diff > 0.05 THEN 1 ELSE 0 END) AS open_mismatch_gt_005,
    SUM(CASE WHEN coverage_status = 'MATCHED' AND high_abs_diff > 0.05 THEN 1 ELSE 0 END) AS high_mismatch_gt_005,
    SUM(CASE WHEN coverage_status = 'MATCHED' AND low_abs_diff > 0.05 THEN 1 ELSE 0 END) AS low_mismatch_gt_005,
    SUM(CASE WHEN coverage_status = 'MATCHED' AND close_abs_diff > 0.05 THEN 1 ELSE 0 END) AS close_mismatch_gt_005,
    SUM(CASE WHEN coverage_status = 'MATCHED' AND volume_diff <> 0 THEN 1 ELSE 0 END) AS volume_mismatch_nonzero,
    SUM(CASE WHEN coverage_status = 'MATCHED' AND ABS(volume_diff_pct) > 0.01 THEN 1 ELSE 0 END) AS volume_mismatch_gt_1pct
FROM classified
GROUP BY source
ORDER BY source;

-- Hard expectation:
-- - investigate any EOD_ONLY/INTRADAY_ONLY pair before declaring reconciliation PASS.
-- Price/volume mismatches are WARNING until source semantics are confirmed.


-- 2) Highest-priority mismatch details (up to 200 rows).
SELECT
    source,
    ticker,
    trade_date,
    coverage_status,
    tick_count,
    i_open,
    e_open,
    open_abs_diff,
    i_high,
    e_high,
    high_abs_diff,
    i_low,
    e_low,
    low_abs_diff,
    i_close,
    e_close,
    close_abs_diff,
    i_volume,
    e_volume,
    volume_diff,
    volume_diff_pct
FROM classified
WHERE coverage_status <> 'MATCHED'
   OR open_abs_diff > 0.05
   OR high_abs_diff > 0.05
   OR low_abs_diff > 0.05
   OR close_abs_diff > 0.05
   OR ABS(volume_diff_pct) > 0.01
ORDER BY
    CASE coverage_status
        WHEN 'EOD_ONLY' THEN 1
        WHEN 'INTRADAY_ONLY' THEN 2
        ELSE 3
    END,
    close_abs_diff DESC NULLS LAST,
    ABS(volume_diff_pct) DESC NULLS LAST,
    source,
    trade_date DESC,
    ticker
LIMIT 200;


-- 3) Stock Intraday tickers not found in raw_lstTicker.
SELECT
    i."Ticker" AS intraday_ticker,
    MIN(i."Date") AS min_intraday_date,
    MAX(i."Date") AS max_intraday_date,
    COUNT(*) AS ticks
FROM "CherryMon"."main"."raw_stock_intraday" AS i
LEFT JOIN "CherryMon"."main"."raw_lstTicker" AS lt
    ON lt."Ticker" = i."Ticker"
WHERE i."Date" >= (
    SELECT MAX("Date") - INTERVAL 30 DAY
    FROM "CherryMon"."main"."raw_stock_intraday"
)
  AND lt."Ticker" IS NULL
GROUP BY i."Ticker"
ORDER BY ticks DESC, intraday_ticker;

-- Expected: normally 0 rows. Non-zero rows require universe/master review.


-- 4) Active stock universe with EOD on latest EOD date but no Intraday on that date.
-- WARNING only: suspended/no-trade symbols can be legitimate.
WITH latest AS (
    SELECT MAX("Date") AS latest_eod_date
    FROM "CherryMon"."main"."raw_stock_eod"
),
expected AS (
    SELECT DISTINCT e."Ticker" AS ticker
    FROM "CherryMon"."main"."raw_stock_eod" AS e
    INNER JOIN "CherryMon"."main"."raw_lstTicker" AS lt
        ON lt."Ticker" = e."Ticker"
    CROSS JOIN latest AS d
    WHERE e."Date" = d.latest_eod_date
      AND upper(COALESCE(lt."Status", '')) = 'Y'
),
actual AS (
    SELECT DISTINCT i."Ticker" AS ticker
    FROM "CherryMon"."main"."raw_stock_intraday" AS i
    CROSS JOIN latest AS d
    WHERE i."Date" = d.latest_eod_date
)
SELECT
    d.latest_eod_date,
    e.ticker AS active_eod_ticker_missing_intraday
FROM expected AS e
LEFT JOIN actual AS a
    ON a.ticker = e.ticker
CROSS JOIN latest AS d
WHERE a.ticker IS NULL
ORDER BY e.ticker;
