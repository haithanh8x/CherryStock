# ADR-001 — Centralized DuckDB Connection and Transaction Management

## Status
Accepted

## Context
CherryStock historically used multiple DuckDB connection patterns. Direct or independently managed connections can create inconsistent transaction boundaries, connection leaks and DuckDB conflicts when multiple attached databases/writers participate in the same workflow.

## Decision
- Normal application code must not introduce direct `duckdb.connect()` usage.
- Read-side workflows should use short-lived read-oriented access through project utilities.
- Multi-step write workflows that require atomicity should use one shared writer transaction through `DuckDBConnectionFactory` + `DuckDBUnitOfWork`.
- The same connection/repository should be passed through write steps rather than opening independent connections inside each step.
- `DuckDBManager.get_connection()` / `close_connection()` remain legacy compatibility patterns, not the preferred pattern for new code.
- Existing `executeDuckSQL()` and `returnSQL()` helpers remain valid where their abstraction matches the use case.

## Alternatives Considered
### Direct `duckdb.connect()` in each module
Rejected because connection ownership and transaction boundaries become fragmented.

### Global long-lived connection
Rejected because lifecycle and concurrency become difficult to reason about and test.

### Short-lived reads + explicit Unit of Work for writes
Accepted because connection intent and transaction ownership are explicit.

## Consequences
Positive:
- clearer transaction boundaries;
- fewer connection lifecycle errors;
- easier idempotency and rollback reasoning;
- easier testing of write workflows.

Trade-off:
- legacy modules may require gradual migration rather than immediate rewrite.

## Related Documents
- [[../../.github/instructions/database.instructions|Database Instructions]]
- [[../architecture/Data_Architecture|Data Architecture]]
- [[../00_HOME|Knowledge Home]]