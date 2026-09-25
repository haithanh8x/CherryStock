# ADR-019 — Yahoo VND=X OHLC Anomalies Are Non-Blocking Warnings

- **Status:** Accepted
- **Date:** 2026-09-22
- **Requirement:** REQ-0035
- **Evidence:** docs/reference/data/data_quality/yahoo_raw_other_eod/

## Context

The Yahoo EOD source mixes index, crypto, FX and futures instruments in `raw_other_eod`.

A diagnostic investigation found recurrent material OHLC envelope violations in Yahoo's
`VND=X` data. Historical provider refetch reproduced the same source geometry, showing the
condition is upstream and recurrent rather than a CherryStock floating-point artifact.

The generic DataValidation rule is correct: a Close outside [Low, High], or Open outside [Low, High],
is invalid OHLC geometry.

However, treating the known `VND=X` upstream anomaly as a blocking error rolls back the complete
core daily transaction, including unrelated market data and calculations.

## Decision

Keep the generic OHLC predicate unchanged.

Introduce a Yahoo-specific orchestration policy:

~~~text
VND=X OHLC envelope violation
    → WARNING
    → preserve raw values
    → continue pipeline

Any other Yahoo ticker OHLC violation
    → FAIL

Any non-OHLC VND=X validation failure
    → FAIL
~~~

The exception is explicit and observable in audit metrics.

## Why Severity Policy Instead of Data Repair

Rejected:

~~~text
High = max(Open, High, Close)
Low  = min(Open, Low, Close)
~~~

because it manufactures market data and destroys provenance.

Rejected:

~~~text
global OHLC tolerance
~~~

because evidence shows material deviations up to approximately 180 price units, not numerical noise.

Rejected:

~~~text
remove VND=X from Yahoo ingestion / validation
~~~

because the data remains useful and should stay observable.

Rejected:

~~~text
disable OHLC validation for all Yahoo instruments
~~~

because there is no evidence supporting weaker validation for DX-Y.NYB, BTC-USD or GC=F.

## Audit Decision

The original total invalid count is preserved.

The policy adds warning/blocking counts and per-symbol breakdown into the existing metrics JSON.
No audit schema migration is introduced.

## Consequences

Positive:

- one evidenced Yahoo FX anomaly no longer blocks the complete daily core transaction;
- raw source provenance is preserved;
- strict validation remains for every other Yahoo instrument;
- warning frequency remains measurable;
- the exception can later be retired if Yahoo behavior changes.

Trade-offs:

- `raw_other_eod` may contain known-invalid OHLC geometry for `VND=X`;
- downstream consumers must distinguish raw source fidelity from cleaned/validated market bars;
- warning audit rows commit only when the enclosing core transaction commits.

## Revisit Criteria

Reconsider or remove the exception if:

- Yahoo stops reproducing the anomaly over a meaningful observation period;
- CherryStock migrates `VND=X` to a more reliable source;
- a dedicated FX data model replaces generic OHLC assumptions;
- evidence shows similar anomalies for additional instruments, which requires a separate decision rather than silently expanding this list.
