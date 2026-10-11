# CherryStock Backlog Status

- **Last reviewed:** 2026-10-11
- **Purpose:** Central status dashboard for planned CherryStock engineering work.
- **Scope:** Requirement backlog, Architecture backlog, and Agent Harness backlog.
- **Status authority:** This file is a summary/index only. The detailed backlog/requirement file remains the authoritative material for each item.

> Backlog status describes planned delivery state. It is not the Source of Truth for current runtime behavior.

## 1. Executive Summary

| Backlog area | Logical items | Current status summary |
|---|---:|---|
| Requirements | 17 canonical requirements | 6 DONE · 5 READY_FOR_DESIGN · 4 IMPLEMENTED_PENDING_VALIDATION · 1 IMPLEMENTED_PENDING_VISUAL_ACCEPTANCE · 1 DRAFT |
| Architecture | 10 | 2 DONE · 3 IN_PROGRESS · 5 TODO |
| Agent Harness | 14 | 2 DONE · 12 TODO |
| **Total** | **41** | **10 DONE · 3 IN_PROGRESS · 5 READY_FOR_DESIGN · 4 IMPLEMENTED_PENDING_VALIDATION · 1 IMPLEMENTED_PENDING_VISUAL_ACCEPTANCE · 17 TODO · 1 DRAFT** |

### Priority Summary

| Priority | Count | Notes |
|---|---:|---|
| P0 | 4 | REQ-0022, REQ-0023, REQ-0024, CS-ARCH-010 |
| P1 | 27 | REQ-0025 through REQ-0038 + 6 Architecture + 7 Harness |
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
| REQ-0034 | Daily Incremental Movement Pipeline | P1 | **DONE** | None | [[requirements/REQ-0034-daily-incremental-movement-pipeline|REQ-0034]] |
| REQ-0035 | Hybrid Cloud Deployment — Railway + MotherDuck with Local AmiBroker Pipeline | P1 | **READY_FOR_DESIGN** | SolutionArchitect | [[requirements/REQ-0035-hybrid-cloud-railway-motherduck|REQ-0035]] |
| REQ-0036 | Pair Discovery and Stock Relationship Screening | P1 | **READY_FOR_DESIGN** | SolutionArchitect | [[requirements/REQ-0036-pair-discovery-stock-relationship-screening|REQ-0036]] |
| REQ-0037 | R/S-based Averaging Down Strategy and Position Sizing | P1 | **READY_FOR_DESIGN** | SolutionArchitect | [[requirements/REQ-0037-rs-averaging-down-position-sizing|REQ-0037]] |\n| REQ-0038 | R/S V2.4 Daily Incremental Source Effectiveness Evaluation | P1 | **DRAFT** | BusinessAnalyst | [[requirements/REQ-0038-rs-v2-4-daily-incremental-source-effectiveness|REQ-0038]] |

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
DONE
(Local TestEngineer PASS / KEEP on 2026-09-22)
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
| REQ-0035 Hybrid Cloud Deployment | Local daily/AmiBroker pipeline + cloud-serving data contract + Railway/MotherDuck architecture design |
| REQ-0036 Pair Discovery & Relationship Screening | Active ticker universe + adjusted/synchronized price history + classification metadata + daily analytical boundary |
| REQ-0037 R/S Averaging Down Strategy | R/S support/zone evidence + point-in-time price/R/S history + position/risk contract + leakage-safe backtest validation |
| REQ-0024 R/S V2.6 | Requires V2.5 evidence/promotion gate before production confidence integration |

---

# 7. Recommended Immediate Queue

Based on current status and priority, the next actionable queue is:

| Order | Item | Why now |
|---:|---|---|
| 1 | **CS-ARCH-010** | P0 repository-integrity/security hygiene remains TODO; `.env`, workspace file and `__pycache__` are still tracked. |
| 2 | **REQ-0023** | P0 requirement ready for SolutionArchitect design. |
| 3 | **REQ-0024** | P0 but logically follows V2.5 evidence/design gate. |
| 4 | **REQ-0026** | Implementation exists but still needs independent local validation to close. |
| 5 | **CS-HARNESS-003** | Complete deterministic developer-hook foundation after harness architecture + native Skills. |
| 6 | **CS-ARCH-001 / 002** | Continue the already-started canonical runtime package and dependency inversion migration. |
| 7 | **REQ-0035** | Hybrid cloud requirement is ready for SolutionArchitect design; defines Railway + MotherDuck target while preserving local AmiBroker processing and cost constraints. |
| 8 | **REQ-0036** | Pair discovery requirement is ready for SolutionArchitect design; establishes compute-efficient coarse-to-fine screening before expensive pair analysis. |
| 9 | **REQ-0037** | R/S averaging-down requirement is ready for SolutionArchitect design; establishes bounded staged entries, invalidation, position-risk limits and backtest/OOS governance. |
| 10 | **CS-HARNESS-004 / 005** | Define semantic read tools and read/admin security boundary before runtime agents. |

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

---

# 9. Review Update — 2026-10-11

## Status reconciliation boundary

The previous 40 canonical items and their status counts were aligned with the owning requirement, architecture and harness backlog documents reviewed on 2026-10-11. No requirement is promoted to DONE solely because a PR exists or focused tests have been run. This review does not constitute a new TestEngineer sign-off or runtime acceptance.

## R/S V2.4 — active follow-up / validation evidence

REQ-0022 remains **DONE** according to its canonical requirement record, but subsequent R/S V2.4 monthly/full-evaluation work has produced fixes and still requires verification of the current operational evaluation path. Do not silently reopen or close REQ-0022 without updating its authoritative material and recording the validation decision.

Recent PRs to reconcile with their actual merge status and independent evidence:

| PR | Change | Follow-up |
|---|---|---|
| [#8](https://github.com/haithanh8x/CherryStock/pull/8) | R/S Ladder V2.4 Source Effectiveness governance | Preserve REQ-0022 baseline |
| [#9](https://github.com/haithanh8x/CherryStock/pull/9) | Monthly R/S V2.4 full Source Effectiveness runner | Verify full-evaluation run |
| [#10](https://github.com/haithanh8x/CherryStock/pull/10) | Monthly active-ticker universe restriction | Verify universe parity |
| [#11](https://github.com/haithanh8x/CherryStock/pull/11), [#12](https://github.com/haithanh8x/CherryStock/pull/12) | Provider warm-up / immature snapshot handling | Verify historical evaluation behavior |
| [#13](https://github.com/haithanh8x/CherryStock/pull/13) | Non-positive BB price-level handling | Regression-check BB candidates |
| [#25](https://github.com/haithanh8x/CherryStock/pull/25) | VP P0–P2 scoring, explainability, intraday research, validation | Reconcile research/production boundary |
| [#26](https://github.com/haithanh8x/CherryStock/pull/26) | Insufficient point-in-time VP warm-up handling | Validate full evaluation |
| [#27](https://github.com/haithanh8x/CherryStock/pull/27) | Historical non-positive BB levels | Validate BB provider and full evaluation |

As of this review, PR titles are discoverable but merge/acceptance states have not been independently established. A local branch/test invocation is not proof of PASS. In particular, the 2026-10-11 BB-provider focused pytest invocation requires its final result before recording validation as passed.

## Pipeline / UI work to reconcile

| PR | Scope | Backlog impact |
|---|---|---|
| [#19](https://github.com/haithanh8x/CherryStock/pull/19), [#20](https://github.com/haithanh8x/CherryStock/pull/20) | Yahoo OHLC diagnostics and VND=X source-specific DQ policy | Review the operational blocker documented under REQ-0034; do not alter its canonical DONE state without evidence |
| [#21](https://github.com/haithanh8x/CherryStock/pull/21) | Full-universe Movement moved to weekly pipeline | Reconcile REQ-0034 runtime scheduling documentation |
| [#22](https://github.com/haithanh8x/CherryStock/pull/22), [#23](https://github.com/haithanh8x/CherryStock/pull/23), [#24](https://github.com/haithanh8x/CherryStock/pull/24) | SmartMoney ticker interaction, TradingView, R/S popup, UI diagnostics | Review feature and regression evidence separately from REQ-0025/0026 delivery state |

## Backlog coverage / intake check

The current canonical dashboard covers hybrid cloud (REQ-0035), pair screening (REQ-0036), and averaging down (REQ-0037). The following discussed concept is **not yet registered as a separately numbered canonical requirement in the requirements index**:

- AI event tracking: timestamped events linked to listed companies, post-announcement price/volume response, point-in-time-safe event-driven backtesting and trading costs. Route through BusinessAnalyst intake and the requirement template before assigning an ID or delivery status.

Long-term/episodic agent memory is already represented by CS-HARNESS-007/008/013; observability by CS-ARCH-008 and CS-HARNESS-009/010. Avoid duplicate backlog IDs for the same intended outcome.

## Next evidence required

1. Confirm PR #25–#27 merge state and final R/S BB/VP focused and full-evaluation test results.
2. Update the owning R/S requirement or add a distinct scoped defect/task if a regression remains; only then adjust dashboard statuses/counts.
3. Reconcile weekly Movement scheduling and SmartMoney UI behavior against approved docs and tests.
4. Route AI-event trading through BusinessAnalyst intake; do not count it as an approved canonical requirement yet.
5. REQ-0038 is now registered as a DRAFT canonical requirement; total is 41. Do not count it as READY_FOR_DESIGN until BusinessAnalyst confirms readiness.

## 2026-10-11 Backlog Addition — REQ-0038

- **REQ-0038:** Daily incremental R/S V2.4 Source Effectiveness; **P1 / DRAFT**.
- Reuse REQ-0022 full evaluation as parity baseline; post-EOD processing, horizon-maturity checkpoints, replay on corrections/version changes, idempotent publish, no promotion side effects.
- Requires BusinessAnalyst confirmation, SolutionArchitect design and independent test evidence before delivery-state advancement.
- Canonical requirement: [[requirements/REQ-0038-rs-v2-4-daily-incremental-source-effectiveness|REQ-0038]].
