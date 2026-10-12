# CherryStock Backlog Status

- **Last reviewed:** 2026-10-12
- **Purpose:** One topic-oriented dashboard grouped by target Quant Trading architecture.
- **Status authority:** Canonical requirement/architecture/harness files remain authoritative. This summary does not prove runtime acceptance.
- **Organization:** Each backlog ID appears once in its primary domain; dependencies are cross-referenced separately.

## 1. Executive Summary

| Area | Canonical items | Status summary |
|---|---:|---|
| Requirements | 18 | 6 DONE · 5 READY_FOR_DESIGN · 4 IMPLEMENTED_PENDING_VALIDATION · 1 IMPLEMENTED_PENDING_VISUAL_ACCEPTANCE · 2 DRAFT |
| Architecture | 10 | 2 DONE · 3 IN_PROGRESS · 5 TODO |
| Agent Harness | 14 | 2 DONE · 12 TODO |
| **Canonical total** | **42** | **10 DONE · 3 IN_PROGRESS · 5 READY_FOR_DESIGN · 4 IMPLEMENTED_PENDING_VALIDATION · 1 IMPLEMENTED_PENDING_VISUAL_ACCEPTANCE · 17 TODO · 2 DRAFT** |
| **Quant proposals (excluded)** | **15** | 5 P0 · 7 P1 · 3 P2; all PROPOSED_FOR_BA_REVIEW |

**Canonical priorities:** P0 4 · P1 28 · P2 7 · P3 3. Proposed QT priorities are separate. The 15 QT aliases are not approved REQ IDs and must not be counted as delivery backlog until BusinessAnalyst intake.

**Status authority:** [Requirements](requirements/README.md) · [Architecture](Architecture_Backlog.md) · [Agent Harness](Harness_Backlog.md). Preserve the original status in the owner file, including IMPLEMENTED_PENDING_VISUAL_ACCEPTANCE; do not map engineering and BA workflows into invented equivalent states.

## 2. Backlog by Quant Trading Architecture

**Flow:** Data Platform → Analytics/Alternative Data → Quant Research & ML → Signal/Strategy → Portfolio/Risk/Execution → UI/Research API. Architecture and agent governance are cross-cutting.

### 2.1 Data Platform & Market Data Quality

| ID | Feature / backlog | Priority | Status | Owner / note | Source |
|---|---|---|---|---|---|
| REQ-0033 | Active Ticker ZigZag + Price Movement Initial Load | P1 | **DONE** | None | [[requirements/REQ-0033-active-ticker-movement-initload | REQ-0033]] |
| REQ-0034 | Daily Incremental Movement Pipeline | P1 | **DONE** | None | [[requirements/REQ-0034-daily-incremental-movement-pipeline | REQ-0034]] |
| REQ-0035 | Hybrid Cloud Deployment — Railway + MotherDuck with Local AmiBroker Pipeline | P1 | **READY_FOR_DESIGN** | SolutionArchitect | [[requirements/REQ-0035-hybrid-cloud-railway-motherduck | REQ-0035]] |
| **QT-01** | Point-in-Time Data & Survivorship-Safe Universe | P0 (proposed) | **PROPOSED_FOR_BA_REVIEW** | BusinessAnalyst intake; not canonical | Proposal |

### 2.2 Analytics, Indicators & Alternative Data

| ID | Feature / backlog | Priority | Status | Owner / note | Source |
|---|---|---|---|---|---|
| REQ-0022 | R/S V2.4 Source Effectiveness & Indicator Promotion Framework | P0 | **DONE** | None | [[requirements/REQ-0022-rs-v2-4-source-effectiveness | REQ-0022]] |
| REQ-0023 | R/S V2.5 Historical Reliability & Confident Strength Shadow Evaluation | P0 | **READY_FOR_DESIGN** | SolutionArchitect | [[requirements/REQ-0023-rs-v2-5-historical-reliability-confident-strength | REQ-0023]] |
| REQ-0024 | R/S V2.6 Production Confident Strength Integration | P0 | **READY_FOR_DESIGN** | SolutionArchitect | [[requirements/REQ-0024-rs-v2-6-production-confident-strength | REQ-0024]] |
| REQ-0025 | Ticker-level SmartMoneyScore | P1 | **DONE** | None | [[requirements/REQ-0025-smart-money-score | REQ-0025]] |
| REQ-0027 | ZigZag-based Price Movement Foundation | P1 | **IMPLEMENTED_PENDING_VISUAL_ACCEPTANCE** | User | [[requirements/REQ-0027-price-movement-characterization | REQ-0027]] |
| REQ-0028 | ZigZag Deviation Calibration V1.1 | P1 | **IMPLEMENTED_PENDING_VALIDATION** | TestEngineer | [[requirements/REQ-0028-zigzag-deviation-calibration-v1-1 | REQ-0028]] |
| REQ-0029 | ZigZag Multi-Ticker Pilot V1.2 | P1 | **IMPLEMENTED_PENDING_VALIDATION** | TestEngineer | [[requirements/REQ-0029-zigzag-multi-ticker-pilot-v1-2 | REQ-0029]] |
| REQ-0030 | ZigZag Regime-Aware Swing-Locked Deviation V2 | P1 | **IMPLEMENTED_PENDING_VALIDATION** | TestEngineer | [[requirements/REQ-0030-zigzag-regime-aware-v2 | REQ-0030]] |
| REQ-0031 | ZigZag-based Price Movement Characterization V2 | P1 | **DONE** | None | [[requirements/REQ-0031-zigzag-price-movement-character-v2 | REQ-0031]] |
| REQ-0032 | MovementContext V1 | P1 | **DONE** | None | [[requirements/REQ-0032-movement-context-v1 | REQ-0032]] |
| REQ-0036 | Pair Discovery and Stock Relationship Screening | P1 | **READY_FOR_DESIGN** | SolutionArchitect | [[requirements/REQ-0036-pair-discovery-stock-relationship-screening | REQ-0036]] |
| REQ-0038 | R/S V2.4 Daily Incremental Source Effectiveness Evaluation | P1 | **DRAFT** | BusinessAnalyst | [[requirements/REQ-0038-rs-v2-4-daily-incremental-source-effectiveness | REQ-0038]] |
| REQ-0039 | Market News Collection, Entity Linking and Sentiment Intelligence | P1 | **DRAFT** | BusinessAnalyst | [[requirements/REQ-0039-news-collection-sentiment-intelligence | REQ-0039]] |
| **QT-06** | Market Regime, Breadth & Sector Rotation Engine | P1 (proposed) | **PROPOSED_FOR_BA_REVIEW** | BusinessAnalyst intake; not canonical | Proposal |
| **QT-07** | Multi-Factor Alpha & Fundamental Feature Store | P1 (proposed) | **PROPOSED_FOR_BA_REVIEW** | BusinessAnalyst intake; not canonical | Proposal |
| **QT-10** | Event Impact & News Alpha Research | P1 (proposed) | **PROPOSED_FOR_BA_REVIEW** | BusinessAnalyst intake; not canonical | Proposal |

### 2.3 Quant Research, Backtesting & ML

| ID | Feature / backlog | Priority | Status | Owner / note | Source |
|---|---|---|---|---|---|
| **QT-02** | Event-Driven Backtesting Engine | P0 (proposed) | **PROPOSED_FOR_BA_REVIEW** | BusinessAnalyst intake; not canonical | Proposal |
| **QT-03** | Vietnam Market Execution & Transaction Cost Simulator | P0 (proposed) | **PROPOSED_FOR_BA_REVIEW** | BusinessAnalyst intake; not canonical | Proposal |
| **QT-04** | Quant Research Validation & Alpha Audit | P0 (proposed) | **PROPOSED_FOR_BA_REVIEW** | BusinessAnalyst intake; not canonical | Proposal |
| **QT-09** | ML Cross-Sectional Stock Ranking | P1 (proposed) | **PROPOSED_FOR_BA_REVIEW** | BusinessAnalyst intake; not canonical | Proposal |
| **QT-12** | Quant Model Registry, Drift & Retraining Governance | P1 (proposed) | **PROPOSED_FOR_BA_REVIEW** | BusinessAnalyst intake; not canonical | Proposal |

### 2.4 Signal & Strategy Engine

| ID | Feature / backlog | Priority | Status | Owner / note | Source |
|---|---|---|---|---|---|
| REQ-0026 | Smart Money BUY / HOLD / SELL Strategy Action | P1 | **IMPLEMENTED_PENDING_VALIDATION** | TestEngineer | [[requirements/REQ-0026-smart-money-strategy | REQ-0026]] |
| REQ-0037 | R/S-based Averaging Down Strategy and Position Sizing | P1 | **READY_FOR_DESIGN** | SolutionArchitect | [[requirements/REQ-0037-rs-averaging-down-position-sizing | REQ-0037]] |
| **QT-08** | Unified Trading Setup & Signal Engine | P1 (proposed) | **PROPOSED_FOR_BA_REVIEW** | BusinessAnalyst intake; not canonical | Proposal |
| **QT-13** | Pairs Trading & Statistical Arbitrage Strategy | P2 (proposed) | **PROPOSED_FOR_BA_REVIEW** | BusinessAnalyst intake; not canonical | Proposal |

### 2.5 Portfolio, Risk & Execution

| ID | Feature / backlog | Priority | Status | Owner / note | Source |
|---|---|---|---|---|---|
| **QT-05** | Portfolio, Position & Risk Management Engine | P0 (proposed) | **PROPOSED_FOR_BA_REVIEW** | BusinessAnalyst intake; not canonical | Proposal |
| **QT-11** | Paper Trading & Shadow Portfolio | P1 (proposed) | **PROPOSED_FOR_BA_REVIEW** | BusinessAnalyst intake; not canonical | Proposal |
| **QT-14** | Robust Portfolio Optimization & Tail-Risk Models | P2 (proposed) | **PROPOSED_FOR_BA_REVIEW** | BusinessAnalyst intake; not canonical | Proposal |

### 2.6 UI, Research API & AI Agents

| ID | Feature / backlog | Priority | Status | Owner / note | Source |
|---|---|---|---|---|---|
| **QT-15** | Financial Knowledge Graph & AI Research Agent | P2 (proposed) | **PROPOSED_FOR_BA_REVIEW** | BusinessAnalyst intake; not canonical | Proposal |
| CS-HARNESS-004 | Define Semantic Tool Contracts for Agents | P1 | **TODO** | See owning backlog | [Harness](Harness_Backlog.md) |
| CS-HARNESS-005 | Separate Read Tools from Privileged Admin Tools | P1 | **TODO** | See owning backlog | [Harness](Harness_Backlog.md) |
| CS-HARNESS-006 | Define Runtime Agent Tool Loop | P2 | **TODO** | See owning backlog | [Harness](Harness_Backlog.md) |
| CS-HARNESS-007 | Introduce Runtime Working-Memory Contract | P2 | **TODO** | See owning backlog | [Harness](Harness_Backlog.md) |
| CS-HARNESS-008 | Introduce Runtime Episodic Memory | P2 | **TODO** | See owning backlog | [Harness](Harness_Backlog.md) |
| CS-HARNESS-011 | Add Runtime Harness Hooks | P2 | **TODO** | See owning backlog | [Harness](Harness_Backlog.md) |
| CS-HARNESS-012 | Define Execution Budgets and Recovery Policy | P2 | **TODO** | See owning backlog | [Harness](Harness_Backlog.md) |
| CS-HARNESS-013 | Define Context Handoff / Compaction Strategy | P3 | **TODO** | See owning backlog | [Harness](Harness_Backlog.md) |
| CS-HARNESS-014 | Add Harness Evaluation Suite | P3 | **TODO** | See owning backlog | [Harness](Harness_Backlog.md) |

### 2.7 Cross-Cutting Architecture, Security & Developer Harness

| ID | Feature / backlog | Priority | Status | Owner / note | Source |
|---|---|---|---|---|---|
| CS-ARCH-001 | Canonical runtime package under `src/cherrystock` | P1 | **IN_PROGRESS** | See owning backlog | [Architecture](Architecture_Backlog.md) |
| CS-ARCH-002 | Remove direct legacy imports from Application Services | P1 | **IN_PROGRESS** | See owning backlog | [Architecture](Architecture_Backlog.md) |
| CS-ARCH-003 | Refactor `AiModels` into an LLM provider layer | P1 | **TODO** | See owning backlog | [Architecture](Architecture_Backlog.md) |
| CS-ARCH-004 | Move MCP into the Interface Layer | P1 | **TODO** | See owning backlog | [Architecture](Architecture_Backlog.md) |
| CS-ARCH-005 | Migrate domain knowledge out of `.github/agents/Instructions` | P1 | **DONE** | See owning backlog | [Architecture](Architecture_Backlog.md) |
| CS-ARCH-006 | Eliminate legacy project-structure documentation | P1 | **DONE** | See owning backlog | [Architecture](Architecture_Backlog.md) |
| CS-ARCH-007 | Reduce and dissolve generic `Ults` ownership | P2 | **IN_PROGRESS** | See owning backlog | [Architecture](Architecture_Backlog.md) |
| CS-ARCH-008 | Add centralized observability contracts | P2 | **TODO** | See owning backlog | [Architecture](Architecture_Backlog.md) |
| CS-ARCH-009 | Add AI evaluation layer for production agents | P3 | **TODO** | See owning backlog | [Architecture](Architecture_Backlog.md) |
| CS-ARCH-010 | Repository hygiene: remove tracked local/sensitive artifacts | P0 | **TODO** | See owning backlog | [Architecture](Architecture_Backlog.md) |
| CS-HARNESS-001 | Formalize Developer Harness Architecture | P1 | **DONE** | See owning backlog | [Harness](Harness_Backlog.md) |
| CS-HARNESS-002 | Introduce Native Skill Files | P1 | **DONE** | See owning backlog | [Harness](Harness_Backlog.md) |
| CS-HARNESS-003 | Introduce Developer Harness Hooks | P1 | **TODO** | See owning backlog | [Harness](Harness_Backlog.md) |
| CS-HARNESS-009 | Introduce Agent Run Identity and Correlation | P1 | **TODO** | See owning backlog | [Harness](Harness_Backlog.md) |
| CS-HARNESS-010 | Centralize Agent Observability | P1 | **TODO** | See owning backlog | [Harness](Harness_Backlog.md) |

## 3. Dependency Map and Overlap Controls

| Flow | Dependency / no-duplication rule |
|---|---|
| REQ-0022 → 0023 → 0024 | R/S V2.4 baseline → V2.5 shadow reliability → V2.6 promotion; REQ-0038 daily incremental evaluation must preserve full-run parity and not auto-promote scoring. |
| REQ-0025 → REQ-0026 → QT-08 | SmartMoneyScore DONE; strategy action pending TestEngineer validation; use as candidate signal, not proven alpha. |
| REQ-0027–0034 → QT-08/QT-02 | ZigZag/Movement outputs must honor confirmed-at timestamps, no repainting, freshness and weekly/manual pipeline scheduling. |
| QT-01 → QT-02/03 → QT-04/05 | Point-in-time correctness, event-driven fills, Vietnam execution rules, OOS audit, common portfolio/risk ledger. |
| REQ-0036 → QT-13 | Pair discovery is screening; QT-13 is trade entry/exit/risk, constrained by Vietnam short-selling feasibility. |
| REQ-0037 → QT-02/03/04/05 | R/S averaging down must reuse shared backtest, cost and risk contracts. |
| REQ-0039 → QT-10 → QT-15 | News/entity/sentiment → event impact research → cited read-only AI knowledge agent; avoid duplicating ingestion. |
| QT-06/07 → QT-08/09 → QT-12 → QT-11 | Regime/factors → strategies/ranking → governed model lifecycle → paper trading. |
| CS-ARCH-001/002/003/004 + CS-HARNESS-004/005 | Layered runtime, provider interfaces, read/admin isolation and safe agent tools. |
| Security prerequisite (CS-ARCH-010) | P0 repository hygiene/security remains urgent independent of Quant roadmap. |

## 4. Delivery Roadmap and Acceptance Gates

| Phase | Focus | Exit evidence |
|---|---|---|
| **1 — Quant Foundation** | QT-01/02/03/04/05; REQ-0026 validation; CS-ARCH-010 | Point-in-time/survivorship audit, reproducible signal/order/fill/cash ledger, Vietnam costs, portfolio risk reconciliation, TestEngineer PASS. |
| **2 — Rule-Based Alpha** | QT-06/07/08; REQ-0037; R/S REQ-0023/0024/0038 | Net-of-cost OOS/walk-forward, regime stability, turnover/drawdown and non-repainting tests. |
| **3 — ML & Alternative Data** | REQ-0039; QT-09/10/12 | News provenance and entity accuracy, feature as-of, incremental OOS improvement over simpler baselines, model lineage. |
| **4 — Portfolio Intelligence** | QT-11/13/14/15; optional RL/LLM research | Stable paper portfolio, risk caps, model drift/rollback, citation-backed read-only agent. |

**Recommended near-term queue:** CS-ARCH-010; REQ-0023/0024; REQ-0026 independent validation; CS-HARNESS-003; CS-ARCH-001/002; BA scoping of QT-01–05; REQ-0035/0036/0037 design; REQ-0038/0039 BA clarification. This does not change canonical status.

## 5. Common Quant Evaluation Scorecard

| Layer | Minimum metrics / evidence |
|---|---|
| Data | As-of/first-seen timestamps, delisted universe, adjusted vs as-traded, corporate actions, source freshness. |
| Prediction | Rank IC/ICIR, Top-K, calibration, uncertainty and availability time. |
| Strategy | Net CAGR, Sharpe, Sortino, expectancy, profit factor, turnover and benchmark. |
| Portfolio | MaxDD, CVaR, tail loss, sector/ticker concentration, liquidity capacity. |
| Execution | Fees/tax/spread/slippage, price band, lot/tick, settlement, non-fill and delay. |
| Scientific validation | TRAIN/VALIDATION/TEST, walk-forward OOS, regime robustness, multiple-testing and leakage audit. |
| Operations | Run ID, data/model/code versions, drift, failed jobs, compute/API cost, replay and rollback. |

No promotion from accuracy, attractive backtest or paper-only evidence. Compare strategies using the same tradable universe, decision-time cutoff, benchmark and cost model.

## 6. Review Findings Requiring Follow-up

- **R/S V2.4:** REQ-0022 remains DONE per owner. [PR #8–13](https://github.com/haithanh8x/CherryStock/pulls) and [PR #25–27](https://github.com/haithanh8x/CherryStock/pulls) contain monthly evaluation, VP/BB historical provider changes; confirm merge and independent full-evaluation evidence. A focused pytest invocation is not PASS evidence.
- **Movement and DQ:** PR #19–21 include Yahoo/VND=X data quality and full-universe Movement weekly scheduling. Reconcile REQ-0034 freshness without silently changing its DONE status.
- **UI:** [NiceGUI_chart.py](../../src/webapp/NiceGUI_chart.py) contains demo/mock Watchlist/Screener/Portfolio data. A visible Portfolio tab is not proof of a live position/P&L engine; PR #22–24 require separate UI regression evidence.
- **Requirement collision:** [Weekly Movement runbook](../runbook/Weekly_Movement_Pipeline.md) references REQ-0036, but canonical REQ-0036 is Pair Discovery. Resolve through owning docs/BA process.
- **Duplicate requirement files:** REQ-0023 canonical vs legacy historical-confidence-shadow; REQ-0024 canonical vs legacy production-confidence-integration. Preserve unique criteria and one canonical file per ID.
- **AI event tracking** maps to REQ-0039 + QT-10, not another counted requirement. Agent memory and observability reuse CS-HARNESS-007/008/013 and CS-ARCH-008/CS-HARNESS-009/010.
- Statuses reflect authoritative backlog documents, not new runtime validation in this reorganization.

## 7. Research Sources Organized by Quant Theme

Monthly arXiv q-fin discovery corpus: [Jan](https://arxiv.org/list/q-fin/2026-01) · [Feb](https://arxiv.org/list/q-fin/2026-02) · [Mar](https://arxiv.org/list/q-fin/2026-03) · [Apr](https://arxiv.org/list/q-fin/2026-04) · [May](https://arxiv.org/list/q-fin/2026-05) · [Jun](https://arxiv.org/list/q-fin/2026-06) · [Jul](https://arxiv.org/list/q-fin/2026-07) · [Aug](https://arxiv.org/list/q-fin/2026-08) · [Sep](https://arxiv.org/list/q-fin/2026-09) · [Oct](https://arxiv.org/list/q-fin/2026-10).

| Domain | Selected research | Relevance |
|---|---|---|
| Data / validation | [Look-Ahead-Bench 2601.13770](https://arxiv.org/abs/2601.13770), [Spurious Predictability 2604.15531](https://arxiv.org/abs/2604.15531) | QT-01/04: time leakage and false-alpha audit. |
| News / event | [News Sentiment 2602.00086](https://arxiv.org/abs/2602.00086), [Buy the Rumor, Sell the News 2608.14014](https://arxiv.org/abs/2608.14014) | REQ-0039/QT-10: event novelty, impact and price-only baseline. |
| Backtest / execution | [Market Impact 2603.29086](https://arxiv.org/abs/2603.29086) | QT-02/03: realistic transaction costs. |
| Regime / ML | [Uncertainty-Adjusted Sorting 2601.00593](https://arxiv.org/abs/2601.00593), [Regime-Adaptive Learning 2606.00143](https://arxiv.org/abs/2606.00143), [LLM Forecasting 2609.36914](https://arxiv.org/abs/2609.36914) | QT-06/07/09/12: baseline, calibrated rank and drift. |
| Portfolio | [Deep RL Portfolio 2605.17307](https://arxiv.org/abs/2605.17307), [CAST 2609.14205](https://arxiv.org/abs/2609.14205), [Robust CVaR 2610.09246](https://arxiv.org/abs/2610.09246) | QT-05/14: risk-first evaluation. |
| Signals / AI graph | [Cross-Stock Semantic Networks 2604.19476](https://arxiv.org/abs/2604.19476), [Buying at Support 2610.04990](https://arxiv.org/abs/2610.04990) | QT-08/13/15: relations and support-entry tests. |

Preprints are hypotheses, not validated Vietnam stock alpha. July is retained as an archive for later curation. RL, continual learning and financial LLMs are non-counted research tracks until a cost-adjusted OOS case is established.

## 8. Maintenance / BusinessAnalyst Intake

1. Update authoritative requirement/architecture/harness owner first, then synchronize this dashboard.
2. Each ID has one primary architectural domain; add dependency links instead of duplicate rows.
3. Mark DONE only after implementation, independent TestEngineer validation and required documentation/visual acceptance.
4. For QT-01–QT-15, BA checks overlap, objective, constraints, source licenses, measurable acceptance, dependencies and compute budget before creating an REQ or extending an existing one using [Requirement Template](requirements/REQUIREMENT_TEMPLATE.md).
5. Add approved requirements to [Requirements README](requirements/README.md); maintain QT→REQ mapping and recalculate canonical counts without double counting.
6. Preserve Requirement → Architecture/ADR → Implementation/PR → Test evidence → DONE traceability.
7. This dashboard does not authorize broker orders, privileged agent writes or production model promotion.
