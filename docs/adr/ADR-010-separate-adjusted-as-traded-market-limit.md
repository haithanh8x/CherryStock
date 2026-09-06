# ADR-010 — Separate Adjusted Analytical Prices from As-Traded Market-Limit Prices

- **Status:** Accepted
- **Date:** 2026-09-06
- **Decision owner:** Solution Architecture
- **Related architecture:** [[../architecture/AsTraded_Market_Limit|As-Traded Market Limit Architecture]]
- **Related SmartMoney:** [[../architecture/SmartMoneyScore|SmartMoneyScore Architecture]]

## Context

CherryStock's existing `raw_stock_eod` can be historically adjusted after corporate
actions. That behavior is desirable for analytical return/trend continuity, but it
is unsafe for point-in-time exchange facts such as ReferencePrice, CeilingPrice,
FloorPrice and historical LimitUp/LimitDown streaks.

Random external validation identified cases where current market-limit formulas are
internally consistent but their historical ReferencePrice is derived from an
adjusted Close that no longer equals the original as-traded price.

## Decision

CherryStock will maintain two distinct price domains:

```text
Adjusted analytical history
    -> raw_stock_eod
    -> returns / MA / RS / trend / analytical OHLC

As-traded point-in-time history
    -> raw_stock_eod_astraded
    -> market-limit resolution
    -> cal_stock_market_limit_eod
    -> vw_stock_market_limit_eod
```

Historical market-limit fields MUST NOT be derived from adjusted
`raw_stock_eod.Close`.

`vw_raw_stock_eod` remains a compatibility/enrichment view and will join market
limit fields from `vw_stock_market_limit_eod`; it will no longer own market-limit
calculation logic.

SmartMoney `MarketLimitAdapter` will consume `vw_stock_market_limit_eod`
directly.

## Source policy

Resolution priority:

1. exchange-published authoritative daily market-limit values;
2. validated point-in-time/as-traded provider values;
3. derived HOSE/HNX ordinary-session values from as-traded history;
4. UPCOM derivation only with explicit eligible regular-lot continuous-matching
   weighted-average evidence;
5. otherwise NULL / UNAVAILABLE.

A missing as-traded source MUST NOT fall back to adjusted `raw_stock_eod`.

## Why this decision

This preserves both required semantics:

- analytical price continuity for indicators and returns;
- historical point-in-time reproducibility for exchange price limits.

Keeping the two concepts in one mutable adjusted dataset would make historical
LimitUp/Down facts non-deterministic across corporate-action refreshes.

## Consequences

### Positive

- corporate actions no longer retroactively alter historical market-limit evidence;
- LimitUp/Down and streaks become auditable;
- SmartMoney can separate score strength from market-limit evidence quality;
- source correction and analytical adjustment become independent workflows.

### Cost

- one additional raw as-traded dataset;
- one calculated market-limit dataset;
- ingestion/backfill and source-quality validation are required;
- UPCOM may remain unavailable for dates without a compliant point-in-time
  reference source.

### Compatibility

Existing adjusted analytical consumers remain on `raw_stock_eod` /
`vw_Ticker_OHLC_D`.

The compatibility `vw_raw_stock_eod` can preserve its public column names while
changing the lineage of market-limit columns.

## Alternatives rejected

### Continue deriving from adjusted raw_stock_eod

Rejected because corporate-action back-adjustment changes historical facts.

### Use adjusted data only but store one-time derived results

Rejected because first build/backfill can already contain historically adjusted,
not as-traded values and therefore cannot prove point-in-time correctness.

### Derive UPCOM from current Intraday proxy universally

Rejected because current Intraday does not explicitly prove regular-lot versus
negotiated/odd-lot scope for the required reference calculation.

### Treat missing LimitUp as FALSE

Rejected because missing evidence is not negative evidence and would bias
SmartMoney scoring.

## Validation gate

The cutover is accepted only after:

- corporate-action regression cases remain stable;
- random HOSE/HNX/UPCOM samples reconcile;
- full/incremental overlap converges;
- no market-limit path reads adjusted `raw_stock_eod.Close`;
- TestEngineer returns PASS for the new contract.

Until then, production SmartMoney LimitUp evidence remains disabled or
PARTIAL/UNAVAILABLE.
