# CherryStock Backlog Status

- **Last reviewed:** 2026-10-12
- **Purpose:** Central status dashboard for planned CherryStock engineering work.
- **Scope:** Requirement backlog, Architecture backlog, Agent Harness backlog, and a separate non-canonical Quant Trading proposal register (Sections 10–16).
- **Status authority:** This file is a summary/index only. The detailed backlog/requirement file remains the authoritative material for each item.

> Backlog status describes planned delivery state. It is not the Source of Truth for current runtime behavior.

## 1. Executive Summary

| Backlog area | Logical items | Current status summary |
|---|---:|---|
| Requirements | 18 canonical requirements | 6 DONE · 5 READY_FOR_DESIGN · 4 IMPLEMENTED_PENDING_VALIDATION · 1 IMPLEMENTED_PENDING_VISUAL_ACCEPTANCE · 2 DRAFT |
| Architecture | 10 | 2 DONE · 3 IN_PROGRESS · 5 TODO |
| Agent Harness | 14 | 2 DONE · 12 TODO |
| **Total** | **42** | **10 DONE · 3 IN_PROGRESS · 5 READY_FOR_DESIGN · 4 IMPLEMENTED_PENDING_VALIDATION · 1 IMPLEMENTED_PENDING_VISUAL_ACCEPTANCE · 17 TODO · 2 DRAFT** |

### Priority Summary

| Priority | Count | Notes |
|---|---:|---|
| P0 | 4 | REQ-0022, REQ-0023, REQ-0024, CS-ARCH-010 |
| P1 | 28 | REQ-0025 through REQ-0039 + 6 Architecture + 7 Harness |
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
| REQ-0037 | R/S-based Averaging Down Strategy and Position Sizing | P1 | **READY_FOR_DESIGN** | SolutionArchitect | [[requirements/REQ-0037-rs-averaging-down-position-sizing|REQ-0037]] |
| REQ-0038 | R/S V2.4 Daily Incremental Source Effectiveness Evaluation | P1 | **DRAFT** | BusinessAnalyst | [[requirements/REQ-0038-rs-v2-4-daily-incremental-source-effectiveness|REQ-0038]] |
| REQ-0039 | Market News Collection, Entity Linking and Sentiment Intelligence | P1 | **DRAFT** | BusinessAnalyst | [[requirements/REQ-0039-news-collection-sentiment-intelligence|REQ-0039]] |

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
5. REQ-0038 is now registered as a DRAFT canonical requirement; total was 41 before REQ-0039; current total is 42. Do not count it as READY_FOR_DESIGN until BusinessAnalyst confirms readiness.

## 2026-10-11 Backlog Addition — REQ-0038

- **REQ-0038:** Daily incremental R/S V2.4 Source Effectiveness; **P1 / DRAFT**.
- Reuse REQ-0022 full evaluation as parity baseline; post-EOD processing, horizon-maturity checkpoints, replay on corrections/version changes, idempotent publish, no promotion side effects.
- Requires BusinessAnalyst confirmation, SolutionArchitect design and independent test evidence before delivery-state advancement.
- Canonical requirement: [[requirements/REQ-0038-rs-v2-4-daily-incremental-source-effectiveness|REQ-0038]].

## 2026-10-11 Backlog Addition — REQ-0039

- **REQ-0039:** Market News Collection, Entity Linking and Sentiment Intelligence; **P1 / DRAFT**.
- Incremental compliant collection, deduplication, ticker/sector mapping, topic/event tagging, explainable sentiment, point-in-time historical evidence and quality/cost monitoring.
- Future news-driven strategy integration requires separate approval and independent OOS validation; no automatic SmartMoney or R/S production changes.
- Canonical requirement: [[requirements/REQ-0039-news-collection-sentiment-intelligence|REQ-0039]].

---

# 10. Quant Trading Completion Roadmap — Research Review 2026-10-12

## 10.1 Governance and Counting Boundary

**Purpose:** Close the gap between CherryStock's existing market-data/indicator/SmartMoney analytics and a reproducible, risk-controlled stock quant-trading research system for Vietnam.

**Important:** Sections 10–16 contain **15 new proposed work items** named QT-01 through QT-15. These are *planning aliases only*, NOT canonical requirement IDs, NOT BA-approved READY items, and NOT part of the 42 canonical backlog count in Section 1. P0/P1/P2 in the proposal table are **recommended quant-roadmap urgency**, not modifications to the authoritative requirement priority or status.

- Canonical existing backlog: **42** (18 requirements, 10 architecture, 14 harness).
- Proposed new Quant/AI/ML work items: **15**, pending BusinessAnalyst de-duplication, scoping, REQ ID assignment and acceptance criteria.
- Research ideas for later experimentation (RL, continual learning, financial LLM forecasting) remain **research-only**, not additional counted backlog items.
- This dashboard remains a summary/index. No production readiness or validation is implied by these recommendations.

## 10.2 Current Capabilities and Gaps

| Domain | Evidence / existing capability | Current assessment and unmet need |
|---|---|---|
| Data and market contracts | AmiBroker EOD/intraday ingestion; DuckDB raw/cal/view pattern; adjusted vs as-traded domains in [Data Architecture](../architecture/Data_Architecture.md) | Strong data foundation; require complete point-in-time universe/corporate-action and delisting rules for unbiased portfolio backtests. |
| Technical/indicator analytics | Indicator Engine, R/S ladder; REQ-0022 R/S V2.4 Source Effectiveness marked DONE | Source evaluation exists. Recent BB/VP historical provider repairs require regression and full-run verification before treating every operational path as validated. |
| Smart Money | REQ-0025 DONE; REQ-0026 action/confidence IMPLEMENTED_PENDING_VALIDATION | Score/action != independently demonstrated tradable net-of-cost alpha. Finish validation, then measure strategy performance and calibration. |
| ZigZag / MovementContext | REQ-0031–0034 marked DONE; REQ-0027–0030 still have acceptance/validation gates | Confirm current runtime frequency and freshness. Weekly/manual Movement work (PR #21) means downstream consumers must detect stale/aging context. Avoid historical use of provisional/repainting swings. |
| News / events | REQ-0039 DRAFT | Ingestion/entity/sentiment planned; event-impact research and point-in-time price/volume attribution not yet a separately approved strategy requirement. |
| Pair relationships | REQ-0036 READY_FOR_DESIGN | Pair screening/relation score is not a trading strategy; position, entry/exit, spread behavior and Vietnam short-sale constraints need a separate scope. |
| R/S averaging down | REQ-0037 READY_FOR_DESIGN | Requires common portfolio risk, order/fill/cost and OOS backtest engines instead of isolated strategy-specific simulation. |
| Full portfolio research | Strategy domain reference: [Stock Strategies](../domain/strategy/Stock_Strategies.md) | Market → Breadth → Trend → Timing → Risk → Sentiment is documented guidance, **not** proof of a backtested executable system. |
| UI | [NiceGUI_chart.py](../../src/webapp/NiceGUI_chart.py) includes mock/demo OHLCV, Screener, Watchlist and Portfolio rows | Distinguish demo screen from production positions, orders, P&L and live market data. Verify individual pages before claiming functional completion. |
| Quant research infrastructure | R/S-specific historical evaluation and governance; existing focused validators | No confirmed shared event-driven portfolio simulator, execution/transaction-cost contract, walk-forward experiment registry and champion/challenger model governance across all strategies. |
| Architecture / security | CS-ARCH-001/002 IN_PROGRESS; CS-ARCH-010 P0 TODO; CS-HARNESS-004/005 TODO | Keep canonical package layering and secure read-only-by-default agent boundaries. Do not delay repository-hygiene security remediation for alpha work. |

**Evidence qualification:** “Not confirmed” means no complete cross-domain implementation/validation proof was established during this repository review; it does not assert that every supporting function is absent. Existing per-module implementation can be reused after SolutionArchitect and TestEngineer check.

## 10.3 Design Principles for Quant Trading

1. **Point-in-time evidence first:** use the universe, issuer mapping, trading constraints and feature values actually known at each historical decision time; distinguish publication timestamp from first accessible/ingested timestamp.
2. **Signal != trade:** indicator scores or LLM sentiment do not constitute an executable order, a probability of profit or a validated strategy.
3. **Execution-aware evaluation:** Vietnam-specific price bands, tick/lot sizes, liquidity/participation, non-fill, fees, taxes, slippage, trading calendar, settlement and corporate actions should be versioned by effective date. Do not assume equity long-short or unrestricted shorting.
4. **OOS and data leakage governance:** separate training, validation and holdout TEST, use walk-forward/purging where needed, account for multiple strategy/model trials, record full data/model/code lineage.
5. **Risk before leverage/complexity:** bound total portfolio exposure, concentration, sector overlap, liquidity risk, tail loss and drawdown before experimenting with RL or autonomous agents.
6. **Local-first cost discipline:** keep AmiBroker ETL, research/backtests and model training on the local PC where economical; publish validated cloud-serving results only, under REQ-0035 architecture.
7. **Reuse ownership:** new Quant features consume R/S, SmartMoney, Movement, News and canonical data contracts; do not silently recreate competing market-data SSOTs or alter runtime R/S ranking.
8. **Promotion requires independent evidence:** no new alpha/ML model is declared production-ready based only on unit tests, accuracy, TRAIN performance or an attractive single-period backtest.

---

# 11. Proposed Quant Trading Backlog — NOT YET CANONICAL

**Intake state for all entries:** PROPOSED_FOR_BA_REVIEW (proposal-only label, **not** a canonical Business Analyst status). The “Priority” below ranks *new Quant work*; it does not supersede existing P0 maintenance or R/S milestones.

## 11.1 P0 — Quant Foundation (5 proposals)

| Proposal | Backlog heading | Outcome / acceptance evidence | Existing dependencies |
|---|---|---|---|
| **QT-01** | **Point-in-Time Data & Survivorship-Safe Universe** | Reconstruct historical tradable stock universe, issuer/security mapping, listings/delistings, corporate actions, adjusted vs as-traded history, publication/availability timestamps; demonstrate replay without survivor/future-data leakage. | [Data Architecture](../architecture/Data_Architecture.md), historical OHLC, as-traded market-limit contract, REQ-0035 publication boundary. |
| **QT-02** | **Event-Driven Backtesting Engine** | Multi-ticker, multi-strategy event clock with signal → order → fill → cash/holdings; reproducible portfolio/trade ledgers and benchmark/equity curve; no same-bar decision/fill leakage. | QT-01, REQ-0025/0026 and 0031/0032 as optional signal sources. |
| **QT-03** | **Vietnam Market Execution & Transaction Cost Simulator** | Versioned fees, sell tax, bid/ask spread, market impact/slippage, lots/tick sizes, price limits, settlement, illiquidity and rejected/unfilled orders; net-of-cost and fill-rate validation against representative data. | QT-01/02 and as-traded exchange-rule metadata. |
| **QT-04** | **Quant Research Validation & Alpha Audit** | Walk-forward and OOS TEST, purged/embargoed CV when labels overlap, bootstrap uncertainty, multiple-testing/selection-bias checks, benchmark comparisons, experiment/version lineage; reject spurious alpha. | QT-01/02/03, existing R/S evaluation and TestEngineer governance. |
| **QT-05** | **Portfolio, Position & Risk Management Engine** | Cash/position ledger, realized/unrealized P&L, capped exposure, volatility/risk sizing, correlation/sector concentration, stop/invalidation, drawdown limits and risk halt; reconcile portfolio accounting and risk limits. | QT-02/03, REQ-0037 strategy risk, market and ticker data. |

**P0 sequencing:** QT-01 is a correctness prerequisite. QT-02 and QT-03 should be designed together; QT-04 should validate them continuously rather than only after implementation. QT-05 then supplies the common risk/portfolio contract. This is a planning dependency, not a promise of sequential team execution.

## 11.2 P1 — Rule-Based Alpha + ML/Alternative Data (7 proposals)

| Proposal | Backlog heading | Outcome / acceptance evidence | Existing dependencies |
|---|---|---|---|
| **QT-06** | **Market Regime, Breadth & Sector Rotation Engine** | Point-in-time VNINDEX/sector regime, advance/decline, share-above-MA, new highs/lows, sector participation and relative strength; quantify classification delay and stability across market regimes. | QT-01/04; existing index/OHLC/indicator data; [Stock Strategies](../domain/strategy/Stock_Strategies.md). |
| **QT-07** | **Multi-Factor Alpha & Fundamental Feature Store** | Availability-aware features for momentum, trend, value, quality, growth, volatility, liquidity, SmartMoney and R/S; factor IC/rank-IC, decay, crowding/correlation, turnover; no restated-FI leakage. | QT-01/04/06, canonical indicators, fundamental history and availability timestamps. |
| **QT-08** | **Unified Trading Setup & Signal Engine** | Independent explainable setup types (breakout, trend pullback, support reversal, continuation), with evidence/entry/exit/invalidation/confidence; compare each rule strategy net-of-cost versus baselines. | QT-02/03/04/05, REQ-0026, R/S, MovementContext and QT-06. |
| **QT-09** | **ML Cross-Sectional Stock Ranking** | Predict/score relative forward return or rank by horizon; compare linear models and LightGBM/XGBoost against rule-based baselines; calibrated uncertainty, OOS rank-IC, Top-K return and post-cost strategy metrics. | QT-01/04/07/08 and QT-12 for approved model lifecycle. |
| **QT-10** | **Event Impact & News Alpha Research** | Link event type, novelty, first-seen timestamps, issuer, abnormal return/volume and post-event drift; compare news features versus price-only baselines with trading costs and point-in-time tests. | REQ-0039, QT-01/02/03/04, canonical ticker mappings. Reuses the previously discussed AI-event-trading idea; do not create duplicate research requirements. |
| **QT-11** | **Paper Trading & Shadow Portfolio** | Scheduled end-of-day decision snapshots, simulated orders/fills, cash/holdings, P&L, costs, difference versus backtest and operational alerts; explicitly **no live broker submission**. | QT-02/03/05/08 and model/signal release gates. |
| **QT-12** | **Quant Model Registry, Drift & Retraining Governance** | Version feature sets, training cutoff, model, prompt/config, metrics; monitor coverage, drift, calibration, rank-IC decay, performance/cost; reproducible champion/challenger and rollback gate. | QT-01/04/07/09; reuse CS-ARCH-008/009 observability/evaluation concepts without duplicating agent-harness ownership. |

**Model ordering:** Start with interpretable factors and low-cost linear/tree baselines. Transformer, RL or fine-tuned financial LLM must demonstrate incremental, cost-adjusted, leakage-safe OOS value before approval.

## 11.3 P2 — Advanced Quant / AI Research (3 proposals)

| Proposal | Backlog heading | Outcome / acceptance evidence | Existing dependencies |
|---|---|---|---|
| **QT-13** | **Pairs Trading & Statistical Arbitrage Strategy** | Transform REQ-0036 discovery/watchlist into tested entry/exit, spread/half-life/stability, capital and risk rules; constrain implementation by actual Vietnam shorting/broker permissions; evaluate feasible long-only relative-value alternatives first. | REQ-0036, QT-02/03/04/05. |
| **QT-14** | **Robust Portfolio Optimization & Tail-Risk Models** | Benchmark equal-weight/risk parity, shrinkage covariance, volatility targeting and constrained CVaR/robust allocation, under turnover, liquidity, sector and drawdown caps; TEST net-of-cost comparison. | QT-05, QT-04, QT-07 and preferably QT-11. |
| **QT-15** | **Financial Knowledge Graph & AI Research Agent** | Explainable issuer/sector/ownership/supply-chain/news/event relations with source citations and valid timestamps; read-only research agent that produces evidence-backed watchlists and theses without broker/trading permissions. | REQ-0039, QT-01/07/10; CS-ARCH-003/004/008, CS-HARNESS-004/005/006/007/008. |

### 11.4 Non-counted Research Track

- **Reinforcement Learning:** Portfolio allocation, adaptive execution or position sizing only after QT-02/03/04/05/11 have validated realistic simulation and risk controls.
- **Regime-adaptive continual learning:** Test for model deterioration and constrained retraining after QT-06/09/12; benchmark against static models before promotion.
- **Financial LLM forecasting and multi-agent investment committee:** Research-only, citations + first-seen data boundaries, compare against simple tabular ML and rule strategies. AI should not self-certify its trading performance or issue privileged DB/broker writes.

---

# 12. Overlap Map — Existing Backlog vs Proposed Quant Work

| Canonical backlog | Existing scope / current status | Proposed Quant linkage and boundary |
|---|---|---|
| **REQ-0022** | R/S V2.4 Source Effectiveness — DONE in owner file | Use as historical source-attribution input; QT-04 does not replace the existing R/S Promotion Gate. |
| **REQ-0023 / 0024** | R/S V2.5/V2.6 — READY_FOR_DESIGN | Complete shadow TEST/OOS evidence before changing production confident strength; QT-08/09 may consume only approved outputs. |
| **REQ-0026** | SmartMoney BUY/HOLD/SELL — IMPLEMENTED_PENDING_VALIDATION | Close independent validator; QT-08 treats it as a candidate baseline signal, not a validated edge. |
| **REQ-0027–0030** | ZigZag foundation/calibration — visual acceptance and focused validation outstanding | Resolve acceptance and prevent use of future-confirmed pivots in QT-02 historical entries. |
| **REQ-0031–0034** | Price Movement, MovementContext, initial/daily pipeline — marked DONE | Reuse outputs and honor freshness/repainting constraints. Review the weekly Movement scheduling PR #21 separately from canonical DONE state. |
| **REQ-0035** | Hybrid cloud Railway + MotherDuck — READY_FOR_DESIGN | Preserve local compute/ETL/backtest and cloud read-serving without pushing sensitive/full intermediate history unnecessarily. |
| **REQ-0036** | Pair Discovery — READY_FOR_DESIGN | QT-13 is execution/strategy scope; do not duplicate pair screening. |
| **REQ-0037** | R/S averaging down — READY_FOR_DESIGN | Requires QT-02/03/05, plus OOS QT-04; do not build a separate incompatible backtesting ledger. |
| **REQ-0038** | Daily incremental R/S V2.4 — DRAFT | Continue cheap, maturity-aware incremental runs; protect full-run parity and avoid synthetic performance claims. |
| **REQ-0039** | News ingestion, ticker linkage, sentiment — DRAFT | QT-10 handles post-event market impact and predictive research; QT-15 handles citation-backed knowledge graph/agent; both reuse news SSOT. |
| **CS-ARCH-010** | Repository security/hygiene — P0 TODO | **Remains urgent regardless of new Quant P0 proposals.** |
| **CS-HARNESS-007/008/013** | Agent memory / compaction — TODO | QT-15 must use these existing contracts; do not invent a second runtime memory domain. |

### Documentation integrity / intake risks

1. [Weekly Movement Pipeline runbook](../runbook/Weekly_Movement_Pipeline.md) labels itself **REQ-0036**, while the canonical REQ-0036 is **Pair Discovery**. Reconcile the conflicting ID/reference through owning BA/docs and PR evidence before automating traceability. **Do not relabel an existing requirement unilaterally.**
2. The canonical REQ-0023 and REQ-0024 have duplicate/legacy Markdown files (see Section 3); settle canonical ownership before changing those requirements.
3. [NiceGUI_chart.py](../../src/webapp/NiceGUI_chart.py) contains demonstrative OHLCV/Watchlist/Screener/Portfolio arrays. Verify which UI components are real-data-connected; **do not claim Portfolio Engine DONE from a mock UI**.
4. The Section 9 AI-event-tracking idea should be refined into **QT-10 / REQ-0039 linkage**, not counted again as a standalone approved item without BA scoping.
5. Provider BB/VP fixes and SmartMoney Strategy validation pending from Section 9 must be independently verified; a passing focused test is not portfolio-level alpha proof.

---

# 13. Recommended Phased Delivery and Quality Gates

| Phase | Work items | Required exit evidence |
|---|---|---|
| **Phase 1 — Quant Foundation** | QT-01 → QT-02/03 → QT-04/05; close REQ-0026 and relevant data-quality blockers | Point-in-time & survivorship checks PASS; deterministic event/ledger replay; cost/limit/fill rules reconciled; portfolio accounting and risk tests PASS. |
| **Phase 2 — Rule-Based Alpha** | QT-06, QT-07, QT-08; REQ-0037; continue R/S 0023/0024/0038 governance | Independent multi-regime walk-forward, net-of-cost/turnover/drawdown results, baseline comparison, no provisional ZigZag future leakage. |
| **Phase 3 — ML and Alternative Data** | REQ-0039 + QT-09/10/12 | Sentiment/entity labels quality-checked; feature availability checks PASS; ML/event signals add incremental OOS value over simpler baselines after costs; monitored model lineage. |
| **Phase 4 — Portfolio Intelligence** | QT-11/13/14/15, bounded RL/LLM research track | Stable shadow trading with traceable simulated fills, portfolio risk compliance, data/model drift monitoring, security/read-only agent validation. |

**Gating principle:** Validation artifacts belong to the TestEngineer and owning business requirement. Paper trading does not authorize live trading. Do not promote an experiment because a paper reported positive results on another market.

## 13.1 Next Recommended Actions

1. Finish **CS-ARCH-010** and reconcile historical data correctness / point-in-time gaps; scope QT-01.
2. Scope the common **QT-02 + QT-03** simulation and market-cost contracts; use SmartMoney action as an initial research baseline once REQ-0026 passes.
3. Create **QT-04** shared validation and experiment governance before broad ML hyperparameter exploration.
4. Define **QT-05** portfolio ledger/risk before activating REQ-0037 or QT-13 strategies.
5. Advance **REQ-0039**, then QT-10, on properly sourced news and event timestamps; start QT-06/07/08 with existing market analytics.
6. Start **QT-09** with linear/gradient-boosted baselines, not RL/LLM-first; use QT-12 for controlled model lifecycle.
7. Prioritize QT-11 shadow execution prior to broker integration; hold QT-13/14/15 behind data/test/risk gates.

This queue is a planning recommendation only; it does **not** reorder or close canonical tasks in Sections 3–7.

---

# 14. Target Quant Architecture and Deployment Boundaries

### Target ownership flow

1. **Data & point-in-time source facts:** approved market feeds, AmiBroker, EOD/intraday, fundamentals, corporate actions, issuer metadata and news → canonical raw/dim facts + data-quality gates.
2. **Deterministic analytics:** indicators, R/S, SmartMoney, ZigZag/Movement, breadth/regime, factor store and event tagging → versioned cal tables / stable public views.
3. **Quant research:** signal/setup evaluation, label formation, ML training, walk-forward runs and experiments; all consume timestamp-correct source data.
4. **Strategy decision:** evidence-backed signal + entry/exit/invalidation + intended target position; explicitly **not** a fill.
5. **Execution simulation + portfolio/risk:** market rules, order state, fill simulation, cash, holdings, risk caps, constraints and attribution.
6. **Read-only serving:** latest approved snapshots of research, signals, risk, P&L and explanation → CherryStock UI / permitted agent tools.

**Local/cloud split:** Keep AmiBroker and cost-heavy historical processing on local PC/DuckDB. Publish only agreed, validated MotherDuck views/snapshots; Railway serves Python UI/APIs. Independent cloud reads must not silently rely on local-PC uptime. Define sync freshness and revision policy in REQ-0035 design.

**Contract rule:** New owners should align with CS-ARCH-001/002 canonical Domain/Application/Infrastructure/Interfaces design and DB raw/cal/vw/sys contracts, avoiding direct UI/agent ownership of SQL mutation rules.

---

# 15. Standard Evaluation Scorecard (Proposed)

| Layer | Minimum output metrics / evidence |
|---|---|
| Forecast / ranking | Rank IC, ICIR, Top-K precision/forward return, calibration, uncertainty/coverage, feature availability date. |
| Strategy | Net CAGR, net annualized return, Sharpe, Sortino, expectancy, profit factor, equity curve, benchmark, turnover. |
| Risk / portfolio | Max drawdown, CVaR/expected shortfall, tail loss, sector/ticker concentration, portfolio beta, liquidity capacity. |
| Execution | Fees/tax/slippage/impact breakdown, non-fill and limit-state behavior, participation, average realized execution delay. |
| Scientific validity | TRAIN/VALIDATION/TEST boundary, chronological OOS, walk-forward, regime stability, confidence intervals, multiple-testing control, leakage/survivorship audit. |
| Operations | Data freshness, job failures, reproducible run IDs, model/data version, drift, compute/API budget, safe resume/rollback. |

Comparison rule: All candidate strategies must be evaluated against a consistent benchmark, tradable universe, as-of cutoff, signal timing and identical market-cost/constraint assumptions. A candidate that fails to improve independent OOS net-of-cost performance and downside risk against its simpler baseline is **not** automatically promoted.

---

# 16. Research References — Jan–Oct 2026 Quant/AI Ideas

These are research inspirations and candidate methodologies, **not evidence of predictive alpha in Vietnam**. Papers may be preprints and must be independently replicated. Some research is filed in cs.AI/cs.LG with q-fin overlap; month follows the article identifier/archive rather than necessarily a q-fin primary category.

### User-provided monthly arXiv browsing corpus

[2026-01](https://arxiv.org/list/q-fin/2026-01) · [2026-02](https://arxiv.org/list/q-fin/2026-02) · [2026-03](https://arxiv.org/list/q-fin/2026-03) · [2026-04](https://arxiv.org/list/q-fin/2026-04) · [2026-05](https://arxiv.org/list/q-fin/2026-05) · [2026-06](https://arxiv.org/list/q-fin/2026-06) · [2026-07](https://arxiv.org/list/q-fin/2026-07) · [2026-08](https://arxiv.org/list/q-fin/2026-08) · [2026-09](https://arxiv.org/list/q-fin/2026-09) · [2026-10](https://arxiv.org/list/q-fin/2026-10)

### Selected papers and how they change the backlog

| Month | Source | Research interpretation → CherryStock candidate |
|---|---|---|
| Jan | [Look-Ahead-Bench, arXiv:2601.13770](https://arxiv.org/abs/2601.13770); [Uncertainty-Adjusted Sorting, arXiv:2601.00593](https://arxiv.org/abs/2601.00593) | Prevent LLM temporal leakage (QT-01/04/15); compare uncertainty-aware ranking to point-prediction ranking (QT-09/14). |
| Feb | [Impact of LLM News Sentiment, arXiv:2602.00086](https://arxiv.org/abs/2602.00086) | Benchmark news sentiment against price-only models instead of assuming improvement (REQ-0039, QT-10). |
| Mar | [Realistic Market Impact Modeling, arXiv:2603.29086](https://arxiv.org/abs/2603.29086) | Costs and nonlinear market impact can change model rankings; include costs within evaluation and RL simulation (QT-02/03/04). |
| Apr | [Spurious Predictability, arXiv:2604.15531](https://arxiv.org/abs/2604.15531); [Cross-Stock Semantic Networks, arXiv:2604.19476](https://arxiv.org/abs/2604.19476) | Audit selection/multiple tests (QT-04); economic relation validation for pair/entity graphs (QT-13/15). |
| May | [Deep RL Portfolio Management, arXiv:2605.17307](https://arxiv.org/abs/2605.17307) | Keep RL in a sandbox with simple baselines and transaction costs; no unproven default adoption. |
| Jun | [Regime-Adaptive Continual Learning, arXiv:2606.00143](https://arxiv.org/abs/2606.00143) | Compare regime-conditioned/static models and controlled retraining (QT-06/09/12). |
| Jul | [q-fin July 2026 archive](https://arxiv.org/list/q-fin/2026-07) | Research corpus to curate further; no July-specific unverified claim is needed to approve the proposed scope. |
| Aug | [Buy the Rumor, Sell the News, arXiv:2608.14014](https://arxiv.org/abs/2608.14014v1) | Event novelty, first-seen time and post-announcement return/volume response (REQ-0039, QT-10). |
| Sep | [CAST drawdown control, arXiv:2609.14205](https://arxiv.org/abs/2609.14205); [Language Models Forecasting Stocks, arXiv:2609.36914](https://arxiv.org/abs/2609.36914) | Separate prediction and downside-risk control (QT-05/14); assess financial LLMs only against honest OOS baseline (QT-04/09/15). |
| Oct | [Buying at Support, arXiv:2610.04990](https://arxiv.org/abs/2610.04990); [Robust CVaR Portfolio Management, arXiv:2610.09246](https://arxiv.org/abs/2610.09246) | Formalize support-entry testing (REQ-0037/QT-08) and robust tail-risk allocation (QT-14). |

**Research caution:** Research findings from U.S. equities, other assets or hypothetical long-short portfolios do not transfer directly to HOSE/HNX/UPCOM. Replication must include local universe, historical exchange rules, tradability, realistic cost and independent OOS evidence.

## 16.1 BusinessAnalyst Intake Checklist (Do Not Skip)

For each QT-01...QT-15 proposal:

1. Search the existing canonical requirement index and architecture/harness backlogs for duplicates or narrower existing owners.
2. Confirm target business value, stakeholder, scope, measurable acceptance criteria and nonfunctional/performance budget.
3. Decide whether to (a) extend an existing REQ or (b) assign a new unique REQ ID; do not bulk-number without decisions.
4. Write the authoritative requirement using [REQUIREMENT_TEMPLATE](requirements/REQUIREMENT_TEMPLATE.md); route BusinessAnalyst DRAFT → READY_FOR_DESIGN when appropriate.
5. Add approved canonical entries to [requirements/README](requirements/README.md), architecture/ADR/test references and **only then** recalculate Section 1 canonical counts.
6. Maintain the proposal-to-canonical mapping here as intake is completed; do not count the same need as both a proposal and a separate approved delivery item.
