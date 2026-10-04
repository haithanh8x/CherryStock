---
id: REQ-0035
title: Hybrid Cloud Deployment — Railway + MotherDuck with Local AmiBroker Pipeline
status: READY_FOR_DESIGN
priority: P1
owner: BusinessAnalyst
primary_next_owner: SolutionArchitect
related:
  architecture:
  adr:
  implementation:
  test:
  change_request:
---

# REQ-0035 — Hybrid Cloud Deployment — Railway + MotherDuck with Local AmiBroker Pipeline

## Business Objective

Move CherryStock's user-facing application to a low-cost, maintainable cloud deployment while preserving the existing local Windows/AmiBroker data workflow and avoiding unnecessary always-on cloud compute for data collection and calculation.

The target operating model is hybrid:

- the local PC remains responsible for AmiBroker-dependent ingestion and daily calculation;
- only synchronized cloud-ready data is published to MotherDuck;
- the CherryStock application is deployed to Railway using a Hobby-class footprint where feasible;
- cloud application reads must not require the local PC to be online after the latest successful synchronization.

## Background / Problem

CherryStock currently relies on local capabilities, especially AmiBroker and the daily data/calculation pipeline. Moving the entire stack to cloud infrastructure would either require replacing AmiBroker-dependent functions or paying for cloud compute that duplicates an already-working local environment.

The desired outcome is therefore not a full cloud migration. It is a cost-conscious split between:

1. local data production and AmiBroker integration; and
2. cloud data serving and application hosting.

This requirement records WHAT the hybrid deployment must achieve. Detailed choices for synchronization protocol, schemas, deployment topology, credentials, retries, consistency boundaries and operational recovery belong to Solution Architecture.

## Stakeholders / Consumers

- CherryStock owner/operator.
- CherryStock web/application users.
- Local daily data pipeline.
- Cloud application runtime.
- Future automated deployment and monitoring workflows.

## Functional Requirements

1. CherryStock shall support a hybrid operating mode where the local PC remains the system responsible for AmiBroker-dependent processing.
2. The local workflow shall continue to run the canonical CherryStock daily data/calculation pipeline before publishing cloud-consumable data.
3. A synchronization step shall publish the latest required CherryStock data from the local environment to MotherDuck.
4. The synchronization shall be incremental where practical and shall avoid full-database transfer as the normal daily path.
5. The cloud application shall be deployable on Railway and shall consume cloud-accessible data without direct dependency on the local DuckDB file or AmiBroker runtime.
6. The cloud application shall remain usable when the local PC is offline, using the most recent successfully synchronized MotherDuck state.
7. The system shall expose enough synchronization state to identify:
   - last successful local pipeline completion;
   - last successful cloud synchronization;
   - data freshness;
   - failed or partial synchronization attempts.
8. Re-running the same synchronization for an already-published data boundary shall not corrupt or duplicate cloud data.
9. A failed cloud synchronization shall not invalidate the successfully completed local daily pipeline.
10. Secrets and credentials used for Railway and MotherDuck shall be supplied through environment/configuration mechanisms and shall not be committed to Git.
11. The migration shall preserve the existing CherryStock repository as the engineering Single Source of Truth.
12. The cloud deployment shall support an operational rollback or fallback path so that failure of the cloud application does not prevent continued local data production.
13. The design shall define which datasets are cloud-required versus local-only so that unnecessary local/internal data is not replicated by default.
14. The cloud application shall use stable CherryStock public/application contracts where they exist rather than depending on local-only implementation details.

## Business Rules

1. AmiBroker-dependent work remains local unless a later approved requirement explicitly replaces that dependency.
2. Local CherryStock daily data generation remains authoritative for the data it produces; MotherDuck is the cloud serving/synchronization target, not a replacement for AmiBroker ingestion in this requirement.
3. A synchronization is considered successful only when the intended published data boundary is complete and queryable from the cloud side.
4. Partial publication must be detectable and must not be reported as the latest successful synchronized state.
5. The normal cloud application read path must not require direct network access to the local PC.
6. The design should optimize recurring cost before optimizing for fully managed/always-on processing.
7. Backlog status or deployment documentation must not be treated as evidence that cloud migration is complete; implementation and TestEngineer validation are required before DONE.
8. Data replicated to MotherDuck should be the minimum sufficient serving dataset unless an approved architecture decision requires broader replication.

## Scope

### In Scope

- Hybrid local/cloud operating model.
- Local AmiBroker + CherryStock daily pipeline retained.
- Local-to-MotherDuck synchronization.
- Railway deployment target for the CherryStock Python application.
- Cloud data freshness and synchronization status.
- Idempotent/recoverable daily publishing.
- Environment/secrets configuration expectations.
- Cloud-read independence from local-PC uptime.
- Definition of local-only versus cloud-required datasets.
- Cost-conscious deployment constraints.

### Out of Scope

- Replacing AmiBroker with a cloud-native market-data engine.
- Rewriting CherryStock into another web framework solely to use Vercel.
- Moving the full local DuckDB file to a Railway persistent volume as the primary cloud database.
- Multi-region/high-availability enterprise deployment.
- Real-time tick-by-tick streaming unless separately approved.
- Automated trading/execution.
- Final choice of synchronization algorithm, table layout, CDC mechanism or deployment topology; these belong to architecture/design.
- Production activation without independent validation.

## Acceptance Criteria

### AC-01 — Local pipeline remains operational

Given the cloud migration work is introduced,
When the canonical local daily CherryStock/AmiBroker workflow is executed,
Then the local pipeline can complete without requiring Railway or MotherDuck to be online for its core local processing.

### AC-02 — Successful cloud publication

Given a completed local daily data boundary,
When the cloud synchronization runs successfully,
Then the required cloud datasets are available in MotherDuck and the synchronization state records the corresponding successful boundary/freshness timestamp.

### AC-03 — Cloud application independence

Given at least one successful synchronization exists,
When the local PC is offline,
Then the Railway-hosted CherryStock application can still serve supported read-only functionality from the latest successful MotherDuck state.

### AC-04 — Failure isolation

Given the local daily pipeline completes successfully,
When the subsequent MotherDuck synchronization fails,
Then the local pipeline result remains valid and the cloud synchronization is reported as failed/stale rather than falsely successful.

### AC-05 — Idempotent rerun

Given a synchronization boundary has already been published,
When the same synchronization is rerun without new source changes,
Then it does not create duplicate logical records or corrupt the previously published cloud state.

### AC-06 — Freshness visibility

Given the application is reading cloud data,
When the latest synchronization is older than the expected operating threshold,
Then operators can determine that the cloud data is stale from explicit synchronization/freshness metadata or observability.

### AC-07 — Secret hygiene

Given Railway and MotherDuck require credentials,
When the deployment is configured,
Then production secrets are not committed to the Git repository and are loaded through approved environment/configuration mechanisms.

### AC-08 — Minimal replication

Given local CherryStock contains datasets not required by the cloud application,
When the synchronization scope is defined,
Then those local-only datasets are excluded from normal cloud publication unless explicitly justified by the approved design.

### AC-09 — Repository traceability

Given the hybrid cloud design is approved and implemented,
When the change is reviewed,
Then requirement, architecture/ADR where needed, implementation, deployment/runbook and validation evidence are traceable from the CherryStock GitHub repository.

### AC-10 — Rollback/fallback

Given the cloud deployment becomes unavailable or a release fails,
When the operator follows the approved recovery path,
Then local daily data production can continue and the previous known-good cloud serving state can be restored or retained without data loss caused by the failed release.

## Non-functional Requirements

- Performance: Cloud read latency should be suitable for normal interactive CherryStock usage; exact SLOs are to be defined during architecture/design based on current application behavior.
- Reliability: Synchronization must be restartable and must make successful versus failed/partial publication unambiguous.
- Security: Secrets must not be stored in source control; cloud write credentials should follow least-privilege principles.
- Observability: Pipeline/sync/deployment logs must expose enough information to identify the failed stage and latest successful synchronized boundary.
- Compatibility: Existing local AmiBroker and daily CherryStock workflows must remain supported during migration; migration should be incremental and backward compatible unless separately approved.
- Cost: The design should target a Railway Hobby-class operating footprint plus MotherDuck Lite-class usage where feasible, while treating provider plan names/pricing as operational constraints that must be revalidated at implementation time.

## Dependencies

- Existing canonical local daily data pipeline and AmiBroker integration.
- Current CherryStock data contracts and public/serving datasets.
- MotherDuck account/database availability.
- Railway deployment account/runtime availability.
- Solution Architecture definition for synchronization boundary, cloud-serving contracts and recovery model.
- Applicable database, Python, testing and architecture instructions in the repository.

## Constraints

- AmiBroker requires the retained local environment for this requirement.
- GitHub repository remains the CherryStock engineering Single Source of Truth.
- ChatGPT/project changes must be written directly to the connected CherryStock GitHub repository according to repository governance.
- Cloud application must not require direct access to a local Windows filesystem path.
- Cloud credentials/tokens must not be committed.
- The requirement must not prescribe a specific CDC algorithm, table schema, module/class layout or synchronization implementation before architecture approval.

## Assumptions

- Daily/end-of-day synchronization is sufficient for the initial cloud deployment unless a later requirement adds intraday cloud freshness.
- The existing Python CherryStock application can be hosted on Railway without a mandatory framework rewrite.
- MotherDuck can serve the cloud-readable analytical data needed by the deployed application, subject to architecture validation.
- The local machine is expected to run at least during the scheduled local daily pipeline and synchronization window.
- The user prefers retaining local compute where it materially reduces recurring cloud cost.

## Open Questions

- Which exact CherryStock datasets/views constitute the minimum cloud-serving contract?
- Is the initial cloud freshness target strictly EOD/daily, or are selected intraday datasets required?
- Should cloud synchronization publish directly from application services, from an exported boundary, or through another approved adapter?
- What is the retention/history policy for synchronized data versus only the latest changed records?
- What health/freshness threshold should cause the cloud UI to display a stale-data warning?
- Is Railway deployment expected to host only the web application, or also scheduled lightweight cloud jobs unrelated to AmiBroker?
- What rollback strategy is preferred for schema changes that affect both local DuckDB and MotherDuck?

These questions require architecture/design decisions but do not prevent the business requirement from being ready for design.

## Risks

- Divergence between local DuckDB semantics and cloud-serving semantics if synchronization bypasses CherryStock public contracts.
- Partial/failed synchronization could expose inconsistent cloud state unless publication boundaries are explicit.
- Schema evolution may break cloud reads if local and MotherDuck migrations are not coordinated.
- Provider plan/pricing/limits can change and should not be hard-coded as permanent architecture assumptions.
- Local machine downtime can delay freshness even though the cloud app remains available on last-known-good data.
- Duplicating too much of the local database in MotherDuck can increase cost and operational complexity without user value.
- Making MotherDuck a second business-rule Source of Truth could create drift if business logic is duplicated in cloud SQL.

## Suggested Routing

- Architecture required: Yes
- Primary next owner: SolutionArchitect
- Domain instructions: database.instructions.md; python.instructions.md; testing.instructions.md; archify.instructions.md as applicable
- Validation owner: TestEngineer

## Handoff

```text
Status: READY_FOR_DESIGN
Primary next owner: SolutionArchitect
Acceptance criteria count: 10
Blocking questions: None; listed open questions are design decisions.
```
