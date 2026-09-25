# CherryStock Backlog Status

- **Last reviewed:** 2026-09-23
- **Purpose:** Central status dashboard for planned CherryStock engineering work.
- **Scope:** Requirement backlog, Architecture backlog, and Agent Harness backlog.
- **Status authority:** This file is a summary/index only. The detailed backlog/requirement file remains the authoritative material for each item.

> Backlog status describes planned delivery state. It is not the Source of Truth for current runtime behavior.

## 1. Executive Summary

| Backlog area | Logical items | Current status summary |
|---|---:|---|
| Requirements | 14 canonical requirements | 6 DONE · 2 READY_FOR_DESIGN · 5 IMPLEMENTED_PENDING_VALIDATION · 1 IMPLEMENTED_PENDING_VISUAL_ACCEPTANCE |
| Architecture | 10 | 2 DONE · 3 IN_PROGRESS · 5 TODO |
| Agent Harness | 14 | 2 DONE · 12 TODO |
| **Total** | **38** | **10 DONE · 3 IN_PROGRESS · 2 READY_FOR_DESIGN · 5 IMPLEMENTED_PENDING_VALIDATION · 1 IMPLEMENTED_PENDING_VISUAL_ACCEPTANCE · 17 TODO** |

### Priority Summary

| Priority | Count | Notes |
|---|---:|---|
| P0 | 4 | REQ-0022, REQ-0023, REQ-0024, CS-ARCH-010 |
| P1 | 24 | REQ-0025 through REQ-0034 + REQ-0036 + 6 Architecture + 7 Harness |
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
| REQ-0026 | Smart Money BUY / HOLD / SELL Strategy Action | P1 | **IMPLEMENTED_PENDING_VALIDATION** | TestEngineer | [[requirements/REQ-0026-smart-money-strategy|REQ-0026]] |
| REQ-0027 | ZigZag-based Price Movement Foundation | P1 | **IMPLEMENTED_PENDING_VISUAL_ACCEPTANCE** | User | [[requirements/REQ-0027-price-movement-characterization|REQ-0027]] |
| REQ-0028 | ZigZag Deviation Calibration V1.1 | P1 | **IMPLEMENTED_PENDING_VALIDATION** | TestEngineer | [[requirements/REQ-0028-zigzag-deviation-calibration-v1-1|REQ-0028]] |
| REQ-0029 | ZigZag Multi-Ticker Pilot V1.2 | P1 | **IMPLEMENTED_PENDING_VALIDATION** | TestEngineer | [[requirements/REQ-0029-zigzag-multi-ticker-pilot-v1-2|REQ-0029]] |
| REQ-0030 | ZigZag Regime-Aware Swing-Locked Deviation V2 | P1 | **IMPLEMENTED_PENDING_VALIDATION** | TestEngineer | [[requirements/REQ-0030-zigzag-regime-aware-v2|REQ-0030]] |
| REQ-0031 | ZigZag-based Price Movement Characterization V2 | P1 | **DONE** | None | [[requirements/REQ-0031-zigzag-price-movement-character-v2|REQ-0031]] |
| REQ-0032 | MovementContext V1 | P1 | **DONE** | None | [[requirements/REQ-0032-movement-context-v1|REQ-0032]] |
| REQ-0033 | Active Ticker ZigZag + Price Movement Initial Load | P1 | **DONE** | None | [[requirements/REQ-0033-active-ticker-movement-initload|REQ-0033]] |
| REQ-0034 | Daily Incremental Movement Pipeline | P1 | **DONE / HISTORICAL SCHEDULING** | None | [[requirements/REQ-0034-daily-incremental-movement-pipeline|REQ-0034]] |
| REQ-0036 | Weekly Full-Universe Movement Pipeline | P1 | **IMPLEMENTED_PENDING_VALIDATION** | TestEngineer | [[requirements/REQ-0036-weekly-movement-pipeline|REQ-0036]] |

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
        ↓
REQ-0026 Smart Money Strategy
IMPLEMENTED_PENDING_VALIDATION
```

Price Movement Character is an independent analytical workstream that may become a future upstream dependency for SmartMoney or strategy only through a separate approved requirement:

```text
REQ-0027 ZigZag Foundation
IMPLEMENTED_PENDING_VISUAL_ACCEPTANCE
        ↓
REQ-0028 V1.1 Calibration
IMPLEMENTED_PENDING_VALIDATION
        ↓
REQ-0029 V1.2 Multi-Ticker Pilot
IMPLEMENTED_PENDING_VALIDATION
        ↓
REQ-0030 V2 Regime-Aware
IMPLEMENTED_PENDING_VALIDATION
        ↓
REQ-0031 Price Movement Character V2
DONE
(TestEngineer PASS / reconciliation PASS on 2026-09-19)
        ↓
REQ-0032 MovementContext V1
DONE
(TestEngineer PASS / KEEP on 2026-09-21)
        ↓
REQ-0033 Active Ticker Movement Initial Load
DONE
(TestEngineer PASS / KEEP on 2026-09-22)
        ↓
REQ-0034 Daily Incremental Movement Pipeline
DONE / scheduling superseded
        ↓
REQ-0036 Weekly Full-Universe Movement Pipeline
IMPLEMENTED_PENDING_VALIDATION
```

Related approved Smart Money design:

- [[../architecture/SmartMoneyScore|SmartMoneyScore Architecture]]
- [[../adr/ADR-009-smart-money-score-state-aware-scoring|ADR-009 SmartMoneyScore State-Aware Scoring]]

Related Price Movement design:

- [[../architecture/Price_Movement_Character_V2|Price Movement Character V2 Architecture]]
- [[../adr/ADR-016-zigzag-price-movement-characterization-v2|ADR-016 ZigZag-based Price Movement Characterization]]
- [[../adr/ADR-012-price-movement-character-as-separate-analytics-domain|ADR-012 Price Movement Analytics Boundary]]

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
| CS-ARCH-001 | Canonical runtime package under `src/cherrystock` | P1 | **IN_PROGRESS** |
| CS-ARCH-002 | Remove direct legacy imports from Application Services | P1 | **IN_PROGRESS** |
| CS-ARCH-003 | Refactor `AiModels` into an LLM provider layer | P1 | **TODO** |
| CS-ARCH-004 | Move MCP into the Interface Layer | P1 | **TODO** |
| CS-ARCH-005 | Migrate domain knowledge out of `.github/agents/Instructions` | P1 | **DONE** |
| CS-ARCH-006 | Eliminate legacy project-structure documentation | P1 | **DONE** |
| CS-ARCH-007 | Reduce and dissolve generic `Ults` ownership | P2 | **IN_PROGRESS** |
| CS-ARCH-008 | Add centralized observability contracts | P2 | **TODO** |
| CS-ARCH-009 | Add AI evaluation layer for production agents | P3 | **TODO** |
| CS-ARCH-010 | Repository hygiene: remove tracked local/sensitive artifacts | P0 | **TODO** |

## Suggested Architecture Priority

```text
DONE
CS-ARCH-005 Knowledge migration
CS-ARCH-006 Legacy documentation cleanup

IN_PROGRESS
CS-ARCH-001 Canonical runtime package
CS-ARCH-002 Dependency inversion
CS-ARCH-007 Reduce Ults

NEXT
P0
CS-ARCH-010 Repository hygiene
        ↓
P1
continue CS-ARCH-001 / CS-ARCH-002
CS-ARCH-003 LLM provider layer
CS-ARCH-004 MCP interface refactor
        ↓
P2
continue CS-ARCH-007
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
| CS-HARNESS-001 | Formalize Developer Harness Architecture | P1 | **DONE** |
| CS-HARNESS-002 | Introduce Native Skill Files | P1 | **DONE** |
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
DONE — Developer harness foundation
CS-HARNESS-001
CS-HARNESS-002

NEXT — Developer harness foundation
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
| REQ-0026 SmartMoneyStrategy | REQ-0025 public SmartMoney contract + independent local validation |
| REQ-0027 ZigZag Foundation | Adjusted OHLC, Data Architecture, ADR-012/013 |
| REQ-0028 ZigZag V1.1 | REQ-0027 canonical ZigZag engine + adjusted OHLC |
| REQ-0029 ZigZag V1.2 | REQ-0028 calibrated ticker config |
| REQ-0030 ZigZag V2 | REQ-0028 calibrated base + ADR-015 swing-lock rule |
| REQ-0031 Price Movement V2 | Active ZigZag public swings + adjusted OHLC + ADR-016 |
| REQ-0032 MovementContext V1 | REQ-0031 movement profile + active ZigZag current leg + daily OHLC trading dates + ADR-017 |
| REQ-0033 Active Ticker Movement Initload | `vw_Ticker_Active` + REQ-0027 ZigZag + REQ-0031 Price Movement + REQ-0032 downstream context |
| REQ-0034 Daily Incremental Movement | REQ-0033 baseline + core daily post-commit boundary + ADR-018 |
| REQ-0036 Weekly Movement | REQ-0033 full-universe runner + REQ-0032 context + ADR-020; supersedes REQ-0034 normal scheduling |
| REQ-0024 R/S V2.6 | Requires V2.5 evidence/promotion gate before production confidence integration |

---

# 7. Recommended Immediate Queue

Based on current status and priority, the next actionable queue is:

| Order | Item | Why now |
|---:|---|---|
| 1 | **REQ-0036** | Weekly Movement scheduling is implemented and needs local full-universe/freshness validation before merge. |
| 2 | **CS-ARCH-010** | P0 repository-integrity/security hygiene remains TODO; `.env`, workspace file and `__pycache__` are still tracked. |
| 3 | **REQ-0023** | P0 requirement ready for SolutionArchitect design. |
| 4 | **REQ-0024** | P0 but logically follows V2.5 evidence/design gate. |
| 5 | **REQ-0026** | Implementation exists but still needs independent local validation to close. |
| 6 | **CS-HARNESS-003** | Complete deterministic developer-hook foundation after harness architecture + native Skills. |
| 7 | **CS-ARCH-001 / 002** | Continue the already-started canonical runtime package and dependency inversion migration. |
| 8 | **CS-HARNESS-004 / 005** | Define semantic read tools and read/admin security boundary before runtime agents. |

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
