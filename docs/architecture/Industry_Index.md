# Industry Index V1 — FFMC + Equal Weight

Status: IMPLEMENTED_PENDING_VALIDATION
Owner: Analytics Calculation Engine / DuckDB
Operations: docs/runbook/Industry_Index.md

## Objective and scope

Build close-only daily industry indices for the Vietnamese stock universe using
the existing latest data in vw_Ticker_Active and the adjusted daily close history
in vw_Ticker_OHLC_D. No call to calculate_composite_index and no mutation of
legacy cal_Indexes. This is an *analytical proxy*, not an official HOSE sector
index or a point-in-time-safe historical benchmark.

V1 explicitly excludes historical free-float membership reconstruction,
free-float capping, intra-session true index OHLC and dividend total returns.

## Lineage and ownership

~~~text
vw_Ticker_Active: Ticker, IndustryCode, Industry, FreeFloat, Shares Outstanding
vw_Ticker_OHLC_D: Ticker, Date, Close, Volume, TradingValue, TradingValue_IsProxy
                |
                v
src/calcEngine/industryIndex.py: refresh_industry_index(days, connection)
                |
                +--> cal_Industry_Index_D       (close and daily breadth)
                +--> cal_Industry_Index_Weights (constituent audit)
                          |
                          v
                 vw_Industry_Index_D --> React / Analytics
~~~

This is a post-sync calculated analytics path. Source market data remains owned by
the existing raw/view contracts. Connection and transaction are owned by
DuckDBUnitOfWork. The daily call in run.py uses a new transaction after core
ingestion has committed; the independent CLI is scripts/run_industry_index.py.

## Formulas

AmiBroker raw_stock_eod Close is stored in thousand VND/share and is the
adjusted analytical price. FreeFloat is **float shares**, not a percent.
For current ticker i and date t:

- Effective close: P(i,t) > 0; last valid earlier close: Pprev(i,t).
- For first available observation, Pprev(i,t) := P(i,t), so return is 0.
- Daily price return: r(i,t) = P(i,t)/Pprev(i,t) - 1.
- FFMC prior notional: Nprev(i,t) = Pprev(i,t) * FloatShares_latest(i).
- FFMC daily return: R(t) = sum(Nprev * r) / sum(Nprev).
- EW daily return: R(t) = average(r) across valid participating stocks.
- Index(t) = Index(previous industry session) * (1 + R(t)).
- Base Index = 1000 points on the first valid day for each industry + method.
- Closing weight for FFMC = P(i,t)*FloatShares_latest(i) / sector sum.
- Return weight for FFMC = Nprev(i,t) / sector sum.
- EW weight and return weight = 1 / constituent count.

The current membership is used for all dates; float-share changes are applied
only to refreshed dates in bounded mode. This is deliberate for practical
historical-proxy dashboards but introduces historical survivorship and look-ahead
bias. The daily returns rely on price adjustments supplied by AmiBroker.
Constituent absence on a day does not create a dummy return row. Tickers entering
are neutral on their first observation; a ticker reappearing after suspension
uses its last valid earlier close. No historical corporate-action divisor
correction or free-float capped rules are claimed.

## Data model

cal_Industry_Index_D:
- grain/primary key: Date + IndustryCode + Index_Method.
- Index_Method: FFMC or EW.
- Close, Daily_Return, Pct_Change, Volume, TradingValue and coverage,
  Ticker_Count, Advancers, Decliners, Unchanged, Max_Weight, Top3_Weight.
- FloatMarketCap_ThousandVND is populated for FFMC only.
- Calculation_Mode = HISTORICAL_PROXY_LATEST_FLOAT, Snapshot_Date,
  Calculated_At.

cal_Industry_Index_Weights:
- grain/primary key: Date + IndustryCode + Index_Method + Ticker.
- Close, Previous_Close, FloatShares, Weight, Return_Weight, Price_Return,
  Return_Contribution, Snapshot_Date.
- This is internal constituent-level lineage; the public industry trend
  consumer is vw_Industry_Index_D.

View exposes explicit columns and is backward compatible: it does not alter
any pre-existing table or stock view.

## Incremental semantics and failure behavior

- days=None: full series rebuilt from current source using today's float-share
  snapshot. Replaces all V1 index and weight rows inside one transaction.
- days=N: determine the last N *distinct trading dates* present in the
  eligible current active universe. Fetch last pre-window valid ticker close
  to construct a lag seed and last pre-window index close per method/industry
  to preserve chaining. Replace rows in the checkpoint range.
- If target is empty, days=N automatically performs full initialization.
- On snapshot/source change, earlier dates stay untouched in bounded mode;
  perform full rebuild when consistent historical restatement is needed.
- A failed calculation/constraint rolls back all calculated writes, leaving
  existing source data and previous committed derived snapshots unchanged.
- One writer per DB; no independent connection hidden in calculation code.

## Operational governance

The key is IndustryCode, not industry display name. Current active universe,
FreeFloat and shares validity must be checked at runtime. Invalid floating
shares exceeding positive outstanding share count stop the run. Missing or
nonpositive float shares are not silently replaced (EW can still include them).
Invalid close rows do not contribute.

This additive implementation does not automatically publish R2 JSON/Parquet.
That is a separate distribution pipeline. It also does not assert independent
test PASS: local data validation and Archify artifact synchronization remain
operational follow-up work.
