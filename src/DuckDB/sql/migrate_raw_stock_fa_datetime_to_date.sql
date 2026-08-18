-- Convert raw_stock_fa."Date/Time" from VARCHAR to DATE.
-- TRY_CAST keeps the migration safe: invalid/blank values become NULL instead of aborting.
ALTER TABLE raw_stock_fa
ALTER COLUMN "Date/Time" TYPE DATE
USING TRY_CAST("Date/Time" AS DATE);
