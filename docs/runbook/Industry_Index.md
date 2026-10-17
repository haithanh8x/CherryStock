# Industry Index — Local Agent Runbook

- Status: IMPLEMENTED_PENDING_VALIDATION (runtime/data quality must be checked on local DuckDB)
- Repository: haithanh8x/CherryStock
- Calculation: src/calcEngine/industryIndex.py
- Schema: src/DuckDB/sql/industry_index_v1_schema.sql
- CLI: scripts/run_industry_index.py
- Daily entry: run.py (ENABLE_INDUSTRY_INDEX_REFRESH=True)
- Output: CherryMon.main.cal_Industry_Index_D, cal_Industry_Index_Weights
- Public read view: CherryMon.main.vw_Industry_Index_D

## 1. Business contract

The industry universe comes from **vw_Ticker_Active**. Ticker joins to
**vw_Ticker_OHLC_D**; **IndustryCode** is the key and Industry is only a label.

**FreeFloat is the latest number of floating shares**, as sourced from AmiBroker
SharesFloat (not a percentage). FFMC capitalization proxy at the current date
is adjusted Close (thousand VND/share) multiplied by current FreeFloat shares.
This produces **thousand VND**. Shares Outstanding and MarketCap are never
multiplied into the index: Shares Outstanding is only used to detect impossible
floating-share counts. NULL/non-positive FreeFloat excludes a ticker from FFMC,
not from EW. NULL/non-positive prices exclude the observation from both.

Two methods are published: FFMC (daily floating-cap-weighted returns) and
EW (equal-weighted daily returns). No 20% capping is applied in V1. Base is
1,000 for each IndustryCode + Index_Method series.

Constituents are the **current active universe** applied backwards; FreeFloat
and industry membership are current snapshots. Older values are proxies and
must NOT be used as point-in-time historical backtest truth. EOD close is the
adjusted analytical series, not an exchange-published investable total-return
index. Explicitly label analytics as HISTORICAL_PROXY_LATEST_FLOAT.

For each ticker/date, previous close is its latest earlier available valid close.
The ticker's first available day has a 0% return; no artificial index jump on
entry. A ticker without OHLC that day is absent from that day's constituents,
not silently recorded as an explicit 0% return. Suspended/relisted tickers may
therefore have stale prior closes; inspect coverage when using the result.
No historical constituent reconstruction and no full corporate-action divisor
model are claimed.

FFMC daily returns are weighted by **prior-price × latest free-float shares**;
EW daily returns are arithmetic means of constituent price returns. The index
chains daily returns. Each constituent's Return_Weight and
Return_Contribution record return attribution; Weight records **end-of-day**
weight (different from return weight). Advancers/Decliners are based on adjusted
daily stock close returns. Volume and TradingValue are summed over eligible
members; TradingValue_Known_Count and TradingValue_Proxy_Count disclose incomplete
or derived source coverage. Max_Weight and Top3_Weight measure concentration.

## 2. Update local agent checkout

From the repository root in PowerShell:

~~~powershell
git status --short
git pull --ff-only origin main
~~~

Preserve any uncommitted local work before pulling. Read database rules at
.github/instructions/database.instructions.md and Python invocation conventions
at docs/development/Python_Execution_Conventions.md.

The job uses the configured DuckDB path via DuckDBConnectionFactory (settings
or LOCAL_DB_PATH). It writes in DuckDBUnitOfWork, one transaction for schema,
date-window replacement and weights. It does not require MotherDuck, AmiBroker
COM, a web server or React to run by itself, but does require existing source
views and the Python dependencies of CherryStock.

## 3. First execution (entire history)

~~~powershell
python scripts\run_industry_index.py
~~~

This is equivalent to:

~~~powershell
python scripts\run_industry_index.py --days null
~~~

The initial run automatically creates the two cal_* tables and the public view.
It then backfills all valid history using the latest available FreeFloat snapshot.
This is a potentially substantial DuckDB read/write workload; prefer after daily
sync and close competing DuckDB writers.

## 4. Incremental refresh / rerun

~~~powershell
python scripts\run_industry_index.py --days 10
~~~

Here 10 means **10 latest distinct available trading dates**, not 10 calendar
days. The function also accepts direct application invocation:

~~~python
from src.calcEngine.industryIndex import refresh_industry_index
from src.cherrystock.infrastructure.database.connection import DuckDBConnectionFactory
from src.cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork

with DuckDBUnitOfWork(DuckDBConnectionFactory()) as uow:
    summary = refresh_industry_index(days=10, connection=uow.connection)
print(summary)
~~~

Pass days=None for full history. The first incremental call on an empty target
automatically becomes a full-history initialization so every series has a true
base. The latest N daily dates are recalculated; a ticker's last valid pre-window
close is fetched as a lag seed. Each index series is chained from the last
persisted Close **before** that window, so the numeric level remains continuous.
The window's index and constituent-weight rows are **atomically replaced**
(delete + insert, idempotent upsert semantics); stale rows disappear on rerun.
Older rows are untouched on bounded refresh even if the current FreeFloat changed.
To apply a new FreeFloat snapshot consistently to *all* historical dates, rerun
with days=None. Avoid using these proxy series to backtest historical alpha.

A normal daily run:

~~~powershell
python run.py
~~~

After successful core EOD/Intraday/FA/Ticker sync commit, run.py executes the
Industry Index refresh with days=max(1,days_diff), in its **own** transaction.
A failed industry refresh rolls back only this derived-index transaction; the
already committed market-data sync is preserved. To temporarily disable it,
set ENABLE_INDUSTRY_INDEX_REFRESH=False in run.py.

## 5. Observe persistence and source coverage

The job prints an [IndustryIndex] COMMITTED summary, including: mode, date range,
number of index rows and weight rows, active ticker count, and count of tickers
lacking a positive FreeFloat. Inspect results read-only with DuckDB:

~~~sql
SELECT "Date", "IndustryCode", "Industry", "Index_Method",
       "Close", "Pct_Change", "Ticker_Count",
       "Max_Weight", "Top3_Weight", "Snapshot_Date"
FROM "CherryMon"."main"."vw_Industry_Index_D"
ORDER BY "Date" DESC, "IndustryCode", "Index_Method"
LIMIT 50;

SELECT "IndustryCode", "Index_Method", SUM("Weight") AS total_weight,
       SUM("Return_Weight") AS total_return_weight
FROM "CherryMon"."main"."cal_Industry_Index_Weights"
WHERE "Date" = (
    SELECT MAX("Date") FROM "CherryMon"."main"."cal_Industry_Index_Weights"
)
GROUP BY "IndustryCode", "Index_Method"
ORDER BY "IndustryCode", "Index_Method";

SELECT "Index_Method", MIN("Date") AS min_date,
       MAX("Date") AS max_date, COUNT(*) AS rows
FROM "CherryMon"."main"."cal_Industry_Index_D"
GROUP BY "Index_Method";
~~~

Expected weight sums are approximately 1 per industry/method/date (floating
point tolerance applies). TradingValue may contain intraday-derived values or
EOD proxy fallback; it is not uniformly source-reported.

The normal run.py exports database metadata at the end. If only using the
standalone command, refresh the generated DB metadata using the repository
metadata exporter **after** the schema migration has run:

~~~powershell
python -c "from src.Ults.DuckLib import exportDuckDB_metadata; exportDuckDB_metadata()"
~~~

Do not manually invent rows in docs/reference/DB_Metadata.md before local migration.
Local agent can commit the actual generated metadata in a separate follow-up
when it matches the database.

## 6. Failure, rerun and rollback

- An invalid source mapping (FreeFloat greater than positive Shares Outstanding)
  or duplicate active tickers / ticker-date OHLC aborts the transaction.
- NULL or zero FreeFloat is excluded only from FFMC; it is not replaced silently.
- Interrupted refresh rolls back both derived tables together; rerun the same
  command safely after correcting source data.
- Rerun days=None to rebuild the entire proxy series after a historical EOD
  correction, changes to membership, or methodology changes affecting history.
- If daily operation is disrupted, disable the new flag in run.py; the legacy
  cal_Indexes and source raw_* datasets are untouched. Avoid dropping cal_* tables
  without deliberately discarding derived history.

**No test-case files are required by this rollout.** Local execution and
read-only operational inspection are distinct from independent validation.
The repository implementation is not proof of a successful local DuckDB run.
