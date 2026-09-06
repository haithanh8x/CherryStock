# CherryStock Backlog Status

- **Last reviewed:** 2026-09-06
- **Purpose:** Central status dashboard for planned CherryStock engineering work.
- **Scope:** Requirement backlog, Architecture backlog, and Agent Harness backlog.
- **Status authority:** This file is a summary/index only. The detailed backlog/requirement file remains the authoritative material for each item.

> Backlog status describes planned delivery state. It is not the Source of Truth for current runtime behavior.

## 1. Executive Summary

| Backlog area | Logical items | Current status summary |
|---|---:|---|
| Requirements | 4 canonical requirements | 2 DONE · 2 READY_FOR_DESIGN |
| Architecture | 10 | 10 TODO |
| Agent Harness | 14 | 14 TODO |
| **Total** | **28** | **2 DONE · 2 READY_FOR_DESIGN · 24 TODO** |

### Priority Summary

| Priority | Count | Notes |
|---|---:|---|
| P0 | 4 | REQ-0022, REQ-0023, REQ-0024, CS-ARCH-010 |
| P1 | 14 | REQ-0025 + 6 Architecture + 7 Harness |
| P2 | 7 | 2 Architecture + 5 Harness |
| P3 | 3 | 1 Architecture + 2 Harness |

## 2. Status Semantics

Requirement materials under `docs/backlog/requirements/**` use the Business Analyst workflow states:

```text
DRAFT
NEEDS_CLARIFICATION
READY_FOR_DESIGN
READY_FOR_IMPLEMENTATION
BLOCKED
IN_IMPLEMENTATION
IMPLEMENTED_PENDING_VALIDATION
DONE
DEFERRED
```

Engineering backlog files use:

```text
TODO
READY
IN_PROGRESS
BLOCKED
DONE
DEFERRED
```

This dashboard preserves the status defined by the owning backlog material instead of force-mapping all states into one vocabulary.

---

# 3. Requirement Backlog

Canonical index:

[[requirements/README|Requirements Backlog]]

| ID | Requirement | Priority | Status | Next owner | Material |
|---|---|---:|---|---|---|
| REQ-0022 | R/S V2.4 Source Effectiveness & Indicator Promotion Framework | P0 | **DONE** | None | [[requirements/REQ-0022-rs-v2-4-source-effectiveness|REQ-0022]] |
| REQ-0023 | R/S V2.5 Historical Reliability & Confident Strength Shadow Evaluation | P0 | **READY_FOR_DESIGN** | SolutionArchitect | [[requirements/REQ-0023-rs-v2-5-historical-reliability-confident-strength|REQ-0023]] |
| REQ-0024 | R/S V2.6 Production Confident Strength Integration | P0 | **READY_FOR_DESIGN** | SolutionArchitect | [[requirements/REQ-0024-rs-v2-6-production-confident-strength|REQ-0024]] |
| REQ-0025 | Ticker-level SmartMoneyScore | P1 | **DONE** | None | [[requirements/REQ-0025-smart-money-score|REQ-0025]] |

## Requirement Delivery Flow

```text
REQ-0022  R/S V2.4
DONE
   ↓
REQ-0023  R/S V2.5
READY_FOR_DESIGN
   ↓
REQ-0024  R/S V2.6
READY_FOR_DESIGN
```

Smart Money is an independent workstream:

```text
REQ-0025 SmartMoneyScore
DONE
(TestEngineer PASS / KEEP on 2026-09-06)
```

Related approved Smart Money design:

- [[../architecture/SmartMoneyScore|SmartMoneyScore Architecture]]
- [[../adr/ADR-009-smart-money-score-state-aware-scoring|ADR-009 SmartMoneyScore State-Aware Scoring]]

## Requirement Data-Hygiene Warning

Two logical requirement IDs currently have duplicate Markdown files:

### REQ-0023

Canonical file currently indexed by the Requirements README:

`REQ-0023-rs-v2-5-historical-reliability-confident-strength.md`

Legacy/duplicate file also present:

`REQ-0023-rs-v2-5-historical-confidence-shadow.md`

### REQ-0024

Canonical file currently indexed by the Requirements README:

`REQ-0024-rs-v2-6-production-confident-strength.md`

Legacy/duplicate file also present:

`REQ-0024-rs-v2-6-production-confidence-integration.md`

Until cleaned up, agents MUST use the canonical files listed in the table above.

Recommended cleanup:

1. compare duplicate contents for any unique requirement/acceptance criteria;
2. merge any missing information into the canonical file;
3. remove or archive the duplicate;
4. preserve one stable requirement ID → one canonical requirement file.

---

# 4. Architecture Backlog

Detailed backlog:

[[Architecture_Backlog|Architecture Backlog]]

| ID | Item | Priority | Status |
|---|---|---:|---|
| CS-ARCH-001 | Canonical runtime package under `src/cherrystock` | P1 | **TODO** |
| CS-ARCH-002 | Remove direct legacy imports from Application Services | P1 | **TODO** |
| CS-ARCH-003 | Refactor `AiModels` into an LLM provider layer | P1 | **TODO** |
| CS-ARCH-004 | Move MCP into the Interface Layer | P1 | **TODO** |
| CS-ARCH-005 | Migrate domain knowledge out of `.github/agents/Instructions` | P1 | **TODO** |
| CS-ARCH-006 | Eliminate legacy project-structure documentation | P1 | **TODO** |
| CS-ARCH-007 | Reduce and dissolve generic `Ults` ownership | P2 | **TODO** |
| CS-ARCH-008 | Add centralized observability contracts | P2 | **TODO** |
| CS-ARCH-009 | Add AI evaluation layer for production agents | P3 | **TODO** |
| CS-ARCH-010 | Repository hygiene: remove tracked local/sensitive artifacts | P0 | **TODO** |

## Suggested Architecture Priority

```text
P0
CS-ARCH-010 Repository hygiene
        ↓
P1
CS-ARCH-005 Knowledge migration
CS-ARCH-006 Legacy documentation cleanup
CS-ARCH-001 Canonical runtime package
CS-ARCH-002 Dependency inversion
CS-ARCH-003 LLM provider layer
CS-ARCH-004 MCP interface refactor
        ↓
P2
CS-ARCH-007 Reduce Ults
CS-ARCH-008 Observability
        ↓
P3
CS-ARCH-009 AI evaluations
```

---

# 5. Agent Harness Backlog

Detailed backlog:

[[Harness_Backlog|Agent Harness Backlog]]

| ID | Item | Priority | Status |
|---|---|---:|---|
| CS-HARNESS-001 | Formalize Developer Harness Architecture | P1 | **TODO** |
| CS-HARNESS-002 | Introduce Native Skill Files | P1 | **TODO** |
| CS-HARNESS-003 | Introduce Developer Harness Hooks | P1 | **TODO** |
| CS-HARNESS-004 | Define Semantic Tool Contracts for Agents | P1 | **TODO** |
| CS-HARNESS-005 | Separate Read Tools from Privileged Admin Tools | P1 | **TODO** |
| CS-HARNESS-006 | Define Runtime Agent Tool Loop | P2 | **TODO** |
| CS-HARNESS-007 | Introduce Runtime Working-Memory Contract | P2 | **TODO** |
| CS-HARNESS-008 | Introduce Runtime Episodic Memory | P2 | **TODO** |
| CS-HARNESS-009 | Introduce Agent Run Identity and Correlation | P1 | **TODO** |
| CS-HARNESS-010 | Centralize Agent Observability | P1 | **TODO** |
| CS-HARNESS-011 | Add Runtime Harness Hooks | P2 | **TODO** |
| CS-HARNESS-012 | Define Execution Budgets and Recovery Policy | P2 | **TODO** |
| CS-HARNESS-013 | Define Context Handoff / Compaction Strategy | P3 | **TODO** |
| CS-HARNESS-014 | Add Harness Evaluation Suite | P3 | **TODO** |

## Suggested Harness Priority

```text
P1 — Developer harness foundation
CS-HARNESS-001
CS-HARNESS-002
CS-HARNESS-003

P1 — Runtime contracts / safety foundation
CS-HARNESS-004
CS-HARNESS-005
CS-HARNESS-009
CS-HARNESS-010

P2 — Runtime harness
CS-HARNESS-006
CS-HARNESS-007
CS-HARNESS-008
CS-HARNESS-011
CS-HARNESS-012

P3 — Advanced harness
CS-HARNESS-013
CS-HARNESS-014
```

---

# 6. Cross-Backlog Dependencies

| Workstream | Depends on / related to |
|---|---|
| CS-HARNESS-004 Semantic Tools | CS-ARCH-002, CS-ARCH-004 |
| CS-HARNESS-005 Read/Admin separation | CS-ARCH-004 |
| CS-HARNESS-006 Runtime Tool Loop | CS-ARCH-003 |
| CS-HARNESS-009 Run Identity | CS-ARCH-008 |
| CS-HARNESS-010 Agent Observability | CS-ARCH-008 |
| CS-HARNESS-014 Harness Evaluation | CS-ARCH-009 |
| REQ-0025 SmartMoneyScore | Data Architecture, Indicator Engine public SSOT, ADR-009 |
| REQ-0024 R/S V2.6 | Requires V2.5 evidence/promotion gate before production confidence integration |

---

# 7. Recommended Immediate Queue

Based on current status and priority, the next actionable queue is:

| Order | Item | Why now |
|---:|---|---|
| 1 | **CS-ARCH-010** | P0 repository-integrity/security hygiene remains TODO. |
| 2 | **REQ-0025** | Design + ADR are already approved; ready for GeneralCoding implementation. |
| 3 | **REQ-0023** | P0 requirement ready for SolutionArchitect design. |
| 4 | **REQ-0024** | P0 but logically follows V2.5 evidence/design gate. |
| 5 | **CS-HARNESS-001 / 002 / 003** | Formalize the developer harness before adding more repeatable agent procedures. |
| 6 | **CS-ARCH-005 / 006** | Reduce knowledge duplication/legacy routing before larger package migration. |

This order is a planning recommendation only; it does not change status in the owning backlog files.

---

# 8. Maintenance Rules

When any backlog item changes state:

1. update the authoritative requirement/backlog item first;
2. update this `Backlog_Status.md` dashboard in the same change when practical;
3. link architecture / ADR / implementation / test evidence when it exists;
4. only mark `DONE` after implementation, independent validation and documentation are complete;
5. do not use this dashboard as evidence that runtime behavior has changed.

## Traceability

Preferred chain:

```text
Requirement / Backlog
        ↓
Architecture / ADR
        ↓
Implementation / PR / Commit
        ↓
Test Evidence
        ↓
DONE
```
