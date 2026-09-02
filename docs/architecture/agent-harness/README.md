# CherryStock Agent Harness

## Purpose

This document is the canonical architecture and ownership map for AI-assisted software delivery in CherryStock.

`.github/copilot-instructions.md` is the executable repository-level router. Files under `.github/agents/` define WHO owns an outcome. Files under `.github/instructions/` define mandatory domain execution rules. Files under `docs/` store durable engineering materials.

## Roles and Outcomes

| Role | Owned outcome | Durable material |
|---|---|---|
| User | Product priority, scope approval and final business decision | Approved requirement/change context |
| Business Analyst | Requirement is complete, testable and ready for design or implementation | `docs/backlog/requirements/REQ-*.md` |
| Solution Architect | Technical design is approved and implementable | `docs/architecture/**`, `docs/adr/**` |
| Indicator Management | Concrete indicator lifecycle is implemented/backfilled and ready for independent validation | Existing indicator architecture/specification and lifecycle material |
| General Coding | Clear requirement/design is implemented and ready for independent validation | `src/**`, `scripts/**`, affected canonical docs, optional `docs/development/implementation-notes/**` |
| Test Engineer | Evidence-backed terminal verdict | `tests/**` and focused test/runbook evidence |
| Default repository agent | Intent classification, routing, handoff and consolidated user response | No duplicate domain material |

## Default Routing

| Primary intent | Owner |
|---|---|
| Requirement analysis, clarification, acceptance criteria, backlog | `BusinessAnalyst.agent.md` |
| Architecture/design/cross-module contract | `SolutionArchitect.agent.md` |
| Concrete indicator lifecycle | `Indicator_Management.agent.md` |
| Clear general implementation or bug fix | `GeneralCoding.agent.md` |
| Test strategy, test execution, regression or validation | `TestEngineer.agent.md` |

A small, explicit change may route directly to General Coding. Do not require BA or Solution Architect when scope, behavior and existing contract are already clear.

## Handoff Lifecycle

```text
Unclear or material new request
    → BusinessAnalyst
    → READY_FOR_DESIGN
        → SolutionArchitect
        → APPROVED_FOR_IMPLEMENTATION
            → GeneralCoding or authoritative domain agent
    → READY_FOR_IMPLEMENTATION
        → GeneralCoding or authoritative domain agent
    → IMPLEMENTED_PENDING_VALIDATION
        → TestEngineer
        → PASS / FAIL / BLOCKED / REGRESSION
```

Concrete indicator lifecycle:

```text
User request
    → Indicator_Management
    → IMPLEMENTED_PENDING_VALIDATION
    → TestEngineer
    → PASS / FAIL / BLOCKED / REGRESSION
```

## Material Structure

```text
docs/
├── 00_HOME.md
├── backlog/
│   ├── README.md
│   ├── requirements/
│   │   ├── README.md
│   │   └── REQUIREMENT_TEMPLATE.md
│   ├── Architecture_Backlog.md
│   └── Harness_Backlog.md
├── architecture/
│   ├── agent-harness/
│   │   └── README.md
│   └── ...
├── adr/
│   └── ADR-*.md
├── development/
│   ├── README.md
│   ├── Development_Workflow.md
│   └── implementation-notes/
│       └── README.md
├── runbook/
│   └── ...
└── ChangeRequest/
    └── ...
```

## Material Rules

- `.github/**` contains executable governance, not long-form system knowledge.
- `docs/**` is the durable engineering knowledge base.
- Update an existing authoritative document instead of duplicating it.
- Backlog records planned behavior; implemented behavior must be reflected in architecture/domain/runbook documentation.
- Every material requirement uses a stable `REQ-*` identifier.
- Architecture, implementation, test and Change Request materials should link back to the requirement when one exists.
- Introducing a new canonical document requires updating `docs/00_HOME.md`.

## Separation of Duties

Each role confirms only its own outcome:

- Business Analyst confirms requirement readiness.
- Solution Architect confirms design readiness.
- General Coding or a domain agent confirms implementation readiness for validation.
- Test Engineer confirms the evidence-backed verdict.
- The user approves product priority, scope and material business decisions.

No role may self-approve the downstream role's outcome.

## Harness Ownership

At CherryStock's current single-user scale:

- the default repository agent performs task orchestration;
- `.github/copilot-instructions.md` performs deterministic routing;
- Solution Architect owns the design and governance of the Agent Harness;
- no separate Delivery Lead, PM, Orchestrator agent or Agent Platform Engineer is required.
