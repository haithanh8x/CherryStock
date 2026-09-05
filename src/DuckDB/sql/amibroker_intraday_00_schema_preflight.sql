-- AmiBroker Intraday schema preflight.
-- READ ONLY: SELECT only. Run after init/full reload.
-- Expected intraday contract:
--   Ticker, Date, DateTime, RawTime, TickSeq, Open, High, Low, Close, Volume, OpenInt
--   PRIMARY KEY (Ticker, Date, RawTime, TickSeq)

-- 1) Required source/target/reference tables.
WITH expected(table_name) AS (
    VALUES
        ('raw_futures_intraday'),
        ('raw_index_intraday'),
        ('raw_stock_intraday'),
        ('raw_warrant_intraday'),
        ('raw_futures_eod'),
        ('raw_index_eod'),
        ('raw_stock_eod'),
        ('raw_warrant_eod'),
        ('raw_lstTicker')
),
actual AS (
    SELECT lower(table_name) AS table_name
    FROM information_schema.tables
    WHERE lower(table_catalog) = 'cherrymon'
      AND lower(table_schema) = 'main'
)
SELECT
    e.table_name AS expected_table,
    CASE WHEN a.table_name IS NULL THEN 'MISSING' ELSE 'OK' END AS status
FROM expected AS e
LEFT JOIN actual AS a
    ON a.table_name = lower(e.table_name)
ORDER BY e.table_name;

-- PASS: all 9 rows have status=OK.


-- 2) Required columns on all four Intraday tables.
WITH expected_tables(table_name) AS (
    VALUES
        ('raw_futures_intraday'),
        ('raw_index_intraday'),
        ('raw_stock_intraday'),
        ('raw_warrant_intraday')
),
expected_columns(column_name) AS (
    VALUES
        ('Ticker'),
        ('Date'),
        ('DateTime'),
        ('RawTime'),
        ('TickSeq'),
        ('Open'),
        ('High'),
        ('Low'),
        ('Close'),
        ('Volume'),
        ('OpenInt')
),
expected AS (
    SELECT t.table_name, c.column_name
    FROM expected_tables AS t
    CROSS JOIN expected_columns AS c
),
actual AS (
    SELECT
        lower(table_name) AS table_name,
        lower(column_name) AS column_name,
        data_type
    FROM information_schema.columns
    WHERE lower(table_catalog) = 'cherrymon'
      AND lower(table_schema) = 'main'
)
SELECT
    e.table_name,
    e.column_name,
    a.data_type,
    CASE WHEN a.column_name IS NULL THEN 'MISSING' ELSE 'OK' END AS status
FROM expected AS e
LEFT JOIN actual AS a
    ON a.table_name = lower(e.table_name)
   AND a.column_name = lower(e.column_name)
ORDER BY e.table_name, e.column_name;

-- PASS: 44 rows, all status=OK.


-- 3) Primary-key contract.
WITH pk AS (
    SELECT
        lower(tc.table_name) AS table_name,
        string_agg(kcu.column_name, ',' ORDER BY kcu.ordinal_position) AS pk_columns
    FROM information_schema.table_constraints AS tc
    INNER JOIN information_schema.key_column_usage AS kcu
        ON kcu.constraint_catalog = tc.constraint_catalog
       AND kcu.constraint_schema = tc.constraint_schema
       AND kcu.constraint_name = tc.constraint_name
       AND kcu.table_name = tc.table_name
    WHERE lower(tc.table_catalog) = 'cherrymon'
      AND lower(tc.table_schema) = 'main'
      AND tc.constraint_type = 'PRIMARY KEY'
      AND lower(tc.table_name) IN (
          'raw_futures_intraday',
          'raw_index_intraday',
          'raw_stock_intraday',
          'raw_warrant_intraday'
      )
    GROUP BY lower(tc.table_name)
),
expected(table_name) AS (
    VALUES
        ('raw_futures_intraday'),
        ('raw_index_intraday'),
        ('raw_stock_intraday'),
        ('raw_warrant_intraday')
)
SELECT
    e.table_name,
    p.pk_columns,
    CASE
        WHEN p.pk_columns = 'Ticker,Date,RawTime,TickSeq' THEN 'OK'
        WHEN p.pk_columns IS NULL THEN 'MISSING_PK'
        ELSE 'WRONG_PK'
    END AS status
FROM expected AS e
LEFT JOIN pk AS p
    ON p.table_name = e.table_name
ORDER BY e.table_name;

-- PASS: all 4 rows status=OK.
