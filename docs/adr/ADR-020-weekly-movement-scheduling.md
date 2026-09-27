# ADR-020 — Full-Universe Movement Runs Weekly

- **Status:** Accepted
- **Date:** 2026-09-23
- **Requirement:** REQ-0036
- **Supersedes:** ADR-018 normal daily Movement scheduling decision

## Context

REQ-0034 integrated Movement after the daily core commit.

Operational evidence shows a new trading date makes nearly the complete active universe stale.
The implementation then performs a deterministic full-history ZigZag rebuild for almost every
ticker. Normal daily Movement therefore takes approximately 60 minutes.

Price Movement already avoids some unnecessary work, but ZigZag dominates the runtime.

## Decision

Move normal full-universe Movement from daily to weekly.

~~~text
run.py
→ core daily only

runWeekly.py
→ full active-universe ZigZag
→ Price Movement
→ MovementContext
~~~

Keep explicit on-demand ticker refresh.

Do not introduce a new stateful ZigZag algorithm in this change.

## Freshness Decision

Because weekly scheduling intentionally allows lag, MovementContext exposes:

~~~text
MovementAgeTradingDays
MovementFreshnessStatus
~~~

Policy:

~~~text
0        FRESH
1..5     AGING
>5       STALE
missing  UNKNOWN
~~~

This prevents consumers from interpreting weekly-lagged current-leg context as daily-current.

## Why Not Keep Daily

Daily full-history rebuild costs approximately five times the weekly compute burden and delays the
normal daily operational path.

The current strategy layer does not yet require Movement to be refreshed every trading day.

## Why Not Implement True Incremental ZigZag Now

A stateful bar-advance implementation would create a second calculation path.

It remains deferred until a separate requirement proves exact historical replay parity against the
canonical full-history ZigZag engine.

## Consequences

Positive:
- normal daily pipeline no longer pays the approximately 60-minute Movement cost;
- full-universe Movement cost becomes approximately once per week;
- analytical semantics remain unchanged;
- on-demand repair remains available;
- freshness is explicit to consumers.

Trade-offs:
- current-leg movement may lag up to five sessions;
- weekly job becomes an operational SLA;
- a missed weekly run produces STALE context;
- consumers needing daily-current Movement must use on-demand refresh or wait for a future true-incremental implementation.

## ADR-018 Relationship

ADR-018 remains useful documentation for per-ticker isolation and on-demand recovery behavior.

Its decision to invoke Movement automatically after every daily core commit is superseded by this ADR.
