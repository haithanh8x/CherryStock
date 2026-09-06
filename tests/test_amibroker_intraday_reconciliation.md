# AmiBroker Intraday Reconciliation Smoke

## Objective

Validate the four AmiBroker Intraday raw tables after init/full load or incremental
load, using read-only DuckDB evidence.

## Scope

In scope:

- `raw_futures_intraday`
- `raw_index_intraday`
- `raw_stock_intraday`
- `raw_warrant_intraday`
- schema/key contract
- row/ticker/date coverage
- recent-window data quality
- Intraday versus matching EOD tables
- stock universe versus `raw_lstTicker`

Out of scope:

- repairing source data
- changing parser semantics
- changing `OpenInt` semantics
- proving FireAnt trade-scope equivalence for EOD versus Intraday Volume
- full-history OHLCV reconciliation

## Preconditions

1. Pull latest `main`.
2. Local CherryMon DuckDB is available.
3. For init validation, run:
   `python scripts\initload\init_reload_raw_intraday_tables.py`
4. For incremental validation, run the normal incremental pipeline first.
5. Execute all SQL in read-only mode.

## Execution Order

Run each SQL file in order and capture every result set.

### Step 1 — Schema preflight

`src/DuckDB/sql/amibroker_intraday_00_schema_preflight.sql`

PASS when:

- all 9 required tables are `OK`;
- all 44 Intraday expected columns are `OK`;
- all 4 Intraday primary keys are exactly
  `Ticker,Date,RawTime,TickSeq`.

Any missing/wrong schema is **FAIL**.

### Step 2 — Coverage overview

`src/DuckDB/sql/amibroker_intraday_01_overview.sql`

Record:

- row count per source;
- ticker count per source;
- min/max date;
- last 15 loaded dates;
- obvious ticker-count/tick-count collapses.

A source that has local `.dat` files but loads zero rows is **FAIL**.

Abrupt recent coverage collapse is **WARNING** pending source-file comparison.

### Step 3 — Data quality

`src/DuckDB/sql/amibroker_intraday_02_data_quality.sql`

Hard PASS requires for all 4 sources:

- `required_nulls = 0`;
- `datetime_date_mismatch = 0`;
- `negative_tickseq = 0`;
- `negative_rawtime = 0`;
- `duplicate_key_groups = 0`;
- `bad_sequence_groups = 0`.

Negative Volume or invalid OHLC envelope is **WARNING** first. Inspect raw source
records before treating it as a parser defect.

`OpenInt` distribution is informational only. Do not mutate values from this test.

### Step 4 — Intraday versus EOD reconciliation

`src/DuckDB/sql/amibroker_intraday_03_reconcile_eod.sql`

The script aggregates recent Intraday ticks into daily OHLCV and cross-checks:

- stock Intraday versus `raw_stock_eod`;
- futures Intraday versus `raw_futures_eod`;
- index Intraday versus `raw_index_eod`;
- warrant Intraday versus `raw_warrant_eod`;
- stock Intraday tickers versus `raw_lstTicker`;
- active stock EOD universe versus latest-date Intraday coverage.

Classification:

- `EOD_ONLY` / `INTRADAY_ONLY`: investigate as **FAIL candidate**;
- OHLC absolute difference > 0.05: **WARNING**;
- Volume difference > 1%: **WARNING**;
- stock Intraday ticker absent from `raw_lstTicker`: **WARNING/FAIL candidate**;
- active EOD ticker missing Intraday: **WARNING** because suspended/no-trade symbols
  can be legitimate.

Do not automatically repair any mismatch.

## Reconciliation Drill-down

For every non-zero mismatch category, the local agent must report:

1. source;
2. ticker;
3. trade date;
4. Intraday value;
5. EOD/reference value;
6. absolute/percentage difference;
7. whether source files contain the same discrepancy.

Use a maximum of 5 representative tickers per mismatch category before escalating.

## Result Format

Return exactly one terminal verdict:

```text
AmiBroker Intraday Reconciliation
---------------------------------
Schema: PASS | FAIL
Coverage: PASS | WARNING | FAIL
Data quality: PASS | WARNING | FAIL
EOD reconciliation: PASS | WARNING | FAIL

Evidence:
- futures: <rows/tickers/min-max date>
- index: <rows/tickers/min-max date>
- stock: <rows/tickers/min-max date>
- warrant: <rows/tickers/min-max date>
- duplicate keys: <count>
- bad TickSeq groups: <count>
- EOD_ONLY pairs: <count by source>
- INTRADAY_ONLY pairs: <count by source>
- OHLC mismatch candidates: <count by source>
- Volume mismatch >1%: <count by source>
- stock tickers missing raw_lstTicker: <count>

Verdict: PASS | WARNING | FAIL
Action: KEEP | INVESTIGATE | FIX ONCE | STOP
```

## Stop Condition

- PASS: keep implementation and STOP.
- WARNING: report evidence and STOP. Do not modify production code.
- FAIL with a deterministic parser/schema defect: hand one focused correction to
  GeneralCoding, rerun only the failing SQL, then STOP.
- Do not expand into full-history reconciliation unless explicitly requested.
