# CherryStock Backlog Status

- **Last reviewed:** 2026-10-24 (QT-17 macro research intake; existing canonical statuses not revalidated)
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
| **Quant proposals (excluded)** | **17** | 5 P0 · 8 P1 · 4 P2; all PROPOSED_FOR_BA_REVIEW |

**Canonical priorities:** P0 4 · P1 28 · P2 7 · P3 3. Proposed QT priorities are separate. The 17 QT aliases are not approved REQ IDs and must not be counted as delivery backlog until BusinessAnalyst intake.

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

| **INFRA-R2-01** | R2 Data Layout by Access Pattern (JSON snapshots + partitioned Parquet) | P1 (proposed) | **PROPOSED_FOR_DESIGN** | Local DuckDB/AmiBroker → R2 `cherrystock` → React; details §11 | Proposal; [scope](#11-infra-r2-01--r2-data-layout-by-access-pattern) |

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
| **QT-17** | Vietnam Macro Regime Detection & Economic Cycle Analysis | P1 (proposed) | **PROPOSED_FOR_BA_REVIEW** | Macro regime + sector rotation research; see §10 | Proposal; [study](#10-qt-17--vietnam-macro-regime-detection) |
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
| **QT-16** | Jev AI Typed-Decision Research for Microstructure, SmartMoney & Trading Signals | P2 (proposed) | **PROPOSED_FOR_BA_REVIEW** | Research only; no live market making or broker orders; see §9 | Proposal; [study](#9-qt-16--jev-ai-typed-decision-research) |

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
| QT-17 → QT-06/07 → QT-08/09 → QT-12 → QT-11 | Regime/factors → strategies/ranking → governed model lifecycle → paper trading. |
| REQ-0025/0026 + QT-08/02/03/04/12 → QT-16 → QT-11 (conditional) | Research Jev as a typed probabilistic **advisory** overlay on SmartMoney/signals; compare to deterministic and ML baselines on point-in-time data. Shadow/paper only after evidence and separate approval; no duplicate strategy or execution engine. |
| CS-ARCH-001/002/003/004 + CS-HARNESS-004/005 | Layered runtime, provider interfaces, read/admin isolation and safe agent tools. |
| Security prerequisite (CS-ARCH-010) | P0 repository hygiene/security remains urgent independent of Quant roadmap. |

## 4. Delivery Roadmap and Acceptance Gates

| Phase | Focus | Exit evidence |
|---|---|---|
| **1 — Quant Foundation** | QT-01/02/03/04/05; REQ-0026 validation; CS-ARCH-010 | Point-in-time/survivorship audit, reproducible signal/order/fill/cash ledger, Vietnam costs, portfolio risk reconciliation, TestEngineer PASS. |
| **2 — Rule-Based Alpha** | QT-06/07/08; REQ-0037; R/S REQ-0023/0024/0038 | Net-of-cost OOS/walk-forward, regime stability, turnover/drawdown and non-repainting tests. |
| **3 — ML & Alternative Data** | REQ-0039; QT-09/10/12 | News provenance and entity accuracy, feature as-of, incremental OOS improvement over simpler baselines, model lineage. |
| **4 — Portfolio Intelligence** | QT-11/13/14/15; QT-16 feasibility research (conditional, not delivery commitment); optional RL/LLM research | Stable paper portfolio, risk caps, model drift/rollback, citation-backed read-only agent; QT-16 Go/No-Go memo before any shadow integration. |

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
| Typed AI decisions / market microstructure | [Jev market-making architecture](https://medium.com/coding-nexus/how-to-use-jev-to-build-a-market-making-engine-from-scratch-a-complete-guide-fa5920e7bdb2), [independent Jev measurements](https://github.com/Siim/jev-claim-vs-measured) | QT-16: evaluate actual latency, probability calibration, and net-of-cost signal uplift; article claims do not establish alpha. |

Preprints are hypotheses, not validated Vietnam stock alpha. July is retained as an archive for later curation. RL, continual learning and financial LLMs are non-counted research tracks until a cost-adjusted OOS case is established.

## 8. Maintenance / BusinessAnalyst Intake

1. Update authoritative requirement/architecture/harness owner first, then synchronize this dashboard.
2. Each ID has one primary architectural domain; add dependency links instead of duplicate rows.
3. Mark DONE only after implementation, independent TestEngineer validation and required documentation/visual acceptance.
4. For QT-01–QT-17, BA checks overlap, objective, constraints, source licenses, measurable acceptance, dependencies and compute budget before creating an REQ or extending an existing one using [Requirement Template](requirements/REQUIREMENT_TEMPLATE.md).
5. Add approved requirements to [Requirements README](requirements/README.md); maintain QT→REQ mapping and recalculate canonical counts without double counting.
6. Preserve Requirement → Architecture/ADR → Implementation/PR → Test evidence → DONE traceability.
7. This dashboard does not authorize broker orders, privileged agent writes or production model promotion.

## 9. QT-16 — Jev AI Typed-Decision Research

| Field | Proposed scope |
|---|---|
| ID / title | **QT-16 — Jev AI Typed-Decision Research for Microstructure, SmartMoney & Trading Signals** |
| Priority / status | **P2 (proposed)** / **PROPOSED_FOR_BA_REVIEW**; **not** a canonical REQ or an approved implementation |
| Primary domain | §2.3 Quant Research, Backtesting & ML (one owner row only) |
| Goal | Falsify or support the hypothesis that structured probabilistic decisions from Jev add **incremental**, reproducible trading value to existing CherryStock rule/ML signals, net of costs and latency |
| Initial applicability | SmartMoney signal filtering / risk-off decisions, confidence-aware BUY/HOLD/SELL overlays, R/S breakout or breakdown context. Market-making quote/spread/inventory is **literature study only** without suitable L2 book, order/fill data, and venue permissions |
| Dependencies | REQ-0025 (SmartMoneyScore), REQ-0026 (strategy action), QT-08 (unified signals), QT-01/02/03/04 (point-in-time data, backtest, VN costs, validation), QT-12 (model governance); QT-11 only after independent research approval |
| Owner / output | BusinessAnalyst intake → Quant Research PoC → independent validation; research memo + reproducible benchmark + Go/No-Go recommendation |

### 9.1 Research questions

1. **Provider feasibility:** Verify Jev / TypeSafe API availability, typed `Choice`, `Score`, binary judgment interfaces, data-retention/licensing, stable output contracts, versioning, call costs, quotas, rate limits, determinism and real **p50/p95/p99** latency from the CherryStock deployment environment. Marketing latency and calibrated-probability claims are **unverified** until measured.
2. **Data feasibility:** Inventory AmiBroker EOD/intraday and DuckDB features: market/session regime, relative volume, realized volatility, price momentum, time-of-day, SmartMoneyScore, R/S distance/strength and quote proxies. Explicitly identify unavailable **L2 bid/ask depth, order cancellations, trade aggressor direction, queue position and actual fill** history. Do **not** label OHLCV-only heuristics as observed informed flow or simulate executable market-making profits without those inputs.
3. **Decision-schema experiment:** Evaluate (a) `ACT / HOLD / STEP_BACK` signal-risk gating, (b) `BUY / HOLD / SELL` signal ranking/confirmation, and (c) `HIGH / LOW` adverse-flow risk **only if defensible order-flow inputs exist**. Output schema must contain action, model/provider version, probability/score, as-of timestamp and explicit abstain/fallback reason. The Jev output is advice, never an executable broker instruction.
4. **Ablation and baselines:** Compare with current SmartMoney/R/S rules, simple volatility/volume thresholds, logistic regression or another small locally run model and the same features without Jev. Test whether relative/rolling-normalized features help; keep data cutoff, label horizon and transaction costs identical across variants.
5. **Evaluation and safety:** Pre-register label definitions, train/validation/test splits, rolling walk-forward OOS and minimum sample sizes. Evaluate Brier score, reliability diagram/ECE, confusion matrix and class imbalance, ablation uplift, regime robustness, turnover, slippage/fees/tax, max drawdown, net expectancy, p50/p95/p99 response time, timeout rate and total API cost. Avoid look-ahead leakage, data snooping and treating semantic-confidence scores as calibrated market probabilities.
6. **Failure behavior:** On stale features, insufficient confidence, API error, timeout, invalid schema or risk breach, deterministically **abstain / HOLD / STEP_BACK** as appropriate. Log source timestamps, features/labels (subject to data policy), model version, decision, latency and fallback. Enforce risk veto separately from the AI provider.

### 9.2 Proposed milestones (research only)

| Milestone | Deliverable / stop condition |
|---|---|
| M1 — Feasibility and data-gap audit | One-page API/licensing/latency feasibility note, available-feature matrix, explicit L2 gaps; stop if required data/rights or response times are infeasible |
| M2 — Offline typed-decision PoC | Replayable Jev adapter + schema contract and rule-based fallback on a bounded historical sample; **no live orders** |
| M3 — Independent OOS benchmark | Same-universe, same-cutoff, net-of-cost comparison with baseline; calibration, stability, latency and cost report including negative results |
| M4 — Go/No-Go | BA/Quant decision with evidence and any proposed successor REQ; only consider QT-11 shadow/paper mode after authorization; production/market making outside this backlog |

### 9.4 Research tracks from awesome-jev (24 October 2026)

**Discovery source:** [yibie/awesome-jev](https://github.com/yibie/awesome-jev) and its [Finance & Trading](https://github.com/yibie/awesome-jev/blob/main/categories/finance-trading.md), [Infra / SDKs / Integrations](https://github.com/yibie/awesome-jev/blob/main/categories/infra-sdks-integrations.md), [Evaluation & Benchmarking](https://github.com/yibie/awesome-jev/blob/main/categories/evaluation-benchmarking.md) and [Calibration & Research](https://github.com/yibie/awesome-jev/blob/main/categories/calibration-research.md) collections. The awesome list is **discovery only**, not a validated codebase, benchmark or vendor endorsement. Review each underlying repo's source, commits, license, runnable examples and independently reproducible numbers.

| Track | Priority within QT-16 | CherryStock experiment | Reference implementations | Deliverable |
|---|---|---|---|---|
| **A — DuckDB + typed decisions** | **First** | Test a read-only offline/SQL integration on `vw_Ticker_Active`, existing SmartMoneyScore and R/S features; compare a Python SDK adapter vs native extension for schema validation, version compatibility, throughput, batching, retries, caching and request costs. Use **time-correct** historical feature snapshots rather than only the latest active-ticker view for backtests. | [duckdb-jev](https://github.com/prasanthj/duckdb-jev) (SQL `jev_noul`, `jev_choice`, `jev_score`, `jev_eval`, `jev_stats`), [jev-trust](https://pypi.org/project/jev-trust/) (outcome-based calibration monitoring). | Proof of concept with verified Windows/DuckDB compatibility **or** Python SDK fallback; tested output contracts, latency/cost report and feature-as-of audit. |
| **B — Stock decision overlay** | Second, conditional on A | Evaluate `UP / FLAT / DOWN` direction judgments and `BUY / HOLD / SELL` **advisory** filters over VN equities (pilot VNINDEX, MWG, FPT, HPG where data qualify); mix price/volume, market regime, SmartMoney and R/S state. Benchmark identical horizon and features against rule-only SmartMoney/R/S and simple logistic/GBM baselines, with prospective predictions plus non-leaking walk-forward. | [jev_stock](https://github.com/sosopop/jev_stock) (HK price-direction pipeline and retrospective backtest), [JEV Trading Command Center](https://github.com/mars-tw/jev-trading-command-center) (paper-only design), [jev-trader](https://github.com/jarrodwatts/jev-trader) (book-driven crypto prototype; **not** proof of a robust market-making edge). | Consistent decision schema, per-ticker calibration, walk-forward results, net-of-cost signal uplift and GO/NO-GO. No real order routing. |
| **C — News / events impact** | Third, subject to event-data readiness | Classify event polarity, relevance to VN tickers and materiality as an **input feature**, aligned to first-public timestamp; correlate with forward returns after trading costs and decision-time availability. Reuse REQ-0039 ingest/entity linking and QT-10 event research; do not duplicate either pipeline. | [SEC 8-K filings and decision models](https://github.com/magilliam27/sec-8k-filings-and-decision-models) (26,962 US filings; small reported association, not demonstrated tradeable alpha), [Jev X Sentiment Analysis](https://github.com/brainstormity/Jev-X-Sentiment-Analysis). | Event labeling rubric, labeled sample, leakage audit and incremental value over simple keyword/sentiment baselines. |

**Cross-cutting experiments:** compare hosted Jev with deterministic gates and a lightweight local `Choice / Score / Noul` alternative; consider [Laya](https://github.com/NandhaKishorM/laya), [jev-local](https://github.com/us/jev-local), or [Verdict](https://github.com/Manavarya09/verdict) **only after verifying** model weights, licenses, serving costs, and task-specific accuracy. Use independent measurement designs from [jev-ood-calibration](https://github.com/scienthoon/jev-ood-calibration) and [jev-orderby-bench](https://github.com/yodablocks/jev-orderby-bench) to check option-order stability, probability calibration (Brier/ECE), rank stability, OOD degradation and false certainty. No benchmark figure quoted in those repositories should be generalized to VN trading without replication.

**Technical decision constraints:** CherryStock currently operates with local Windows/Python/AmiBroker/DuckDB; `duckdb-jev` native build compatibility depends on DuckDB binary version/OS/architecture and may require a custom Windows build, so retain a Python-based provider adapter as the baseline. Never embed TypeSafe API keys or send private datasets without checking data policy. Keep the Jev layer an optional, non-blocking research module, not a required dependency of `run.py`. Live-order execution and authentic market-making are **out of scope** until market microstructure data, broker capabilities and separate controls are available.

### 9.5 Evidence checklist for repository adoption

- [ ] Verify Jev/TypeSafe API access, provider version, price, permitted data use, and typed response serialization; preserve exact request/response examples without credentials.
- [ ] Reproduce a `duckdb-jev` demo against the actual CherryStock DuckDB version; document native-extension/Windows blockers and performance against Python adapter.
- [ ] Produce an as-of-correct historical sample from real CherryStock views/tables; document gaps including missing order-book L2 and unavailable event publish timestamps.
- [ ] Benchmark baseline, Jev and (if suitable) local decision model on identical train/validation/OOS dates, instruments, signal horizon and realistic Vietnam trade costs.
- [ ] Report accuracy, class balance, Brier/ECE, regime stability, uplift net of costs, API latency p50/p95/p99 and spend; include all failed/neutral results and repeated-run variance.
- [ ] Document deterministic fail-safe policy, abstention, decision audit trail, paper-only scope and Go/No-Go; request a separate canonical REQ before any production change.

### 9.3 Acceptance and decision gate

- **Research DONE** only when the feasibility matrix, documented typed schemas, replay artifacts, OOS results (including negative results), measured API p50/p95/p99, probability calibration, transaction-cost assumptions, and Go/No-Go memo are published and independently reviewed.
- **GO to a new, separately approved requirement** only on repeatable, economically meaningful **net-of-cost OOS uplift** versus simpler baselines, compatible latency/cost, credible probability calibration or an explicitly non-probabilistic use of scores, and safe fallback behavior. Pre-register thresholds before inspecting test results.
- **NO-GO / defer** if Jev has no incremental uplift, calibration is poor, data are insufficient, latency exceeds the signal horizon, or dependence on a remote API is operationally unacceptable. No automatic promotion to QT-08/REQ-0026 or live execution.

**Research references:** [Article / architecture](https://medium.com/coding-nexus/how-to-use-jev-to-build-a-market-making-engine-from-scratch-a-complete-guide-fa5920e7bdb2) (2026-09-26); [full technical thread](https://threadnavigator.com/thread/2102774731606991003/); [independent reproduction with negative trading results](https://github.com/Siim/jev-claim-vs-measured) (different instruments and tested use case; not conclusive for VN equities). The research must independently test the specific CherryStock task rather than assume claims generalize.

## 10. QT-17 — Vietnam Macro Regime Detection

| Field | Proposed scope |
|---|---|
| Priority / status | **P1 (proposed)** / **PROPOSED_FOR_BA_REVIEW**; not a canonical REQ |
| Domain | §2.2 Analytics, Indicators & Alternative Data; complements QT-06 rather than duplicating market breadth/sector rotation |
| Objective | Identify Vietnam economic regimes and test whether macro indicators predict VNINDEX, industry-index and market-cap-index relative performance after realistic costs |
| Hypothesis | Credit/deposit growth, rates, USD/VND, FDI disbursement, public investment, PMI, CPI, GDP and exports may explain regime transitions and sector leadership; podcast forecasts are unverified hypotheses |
| Source | [Vietnam Innovators — Michael Kokalari, October 2026](https://www.youtube.com/watch?v=hqqfCqRdfxA) |

### Work packages

1. **MACRO-01 Data:** inventory official/public sources and licenses for GDP, CPI, PMI, FDI **registered versus disbursed**, credit, deposits, interest rates, FX, trade and public investment. Store release timestamps, vintages/revisions, frequency, units, missingness and source provenance. Implement idempotent initload/incremental ingestion into DuckDB.
2. **MACRO-02 Regime engine:** start with interpretable rules and four labels **Expansion / Slowdown / Contraction / Recovery**; compare HMM or ML only after baseline. Preserve as-of cutoff and confidence, including ambiguous/unknown states.
3. **MACRO-03 Lag study:** analyze lead/lag and regime-conditional returns for `vw_Market_Index_D`, `cal_Industry_Index_D`, `cal_MarketCap_Index_D`; adjust for frequency mismatch and multiple testing.
4. **MACRO-04 Transition forecasts:** walk-forward, calibrated transition probabilities, uncertainty and drift; no claims of prediction from in-sample fit.
5. **MACRO-05 Sector rotation:** reuse QT-06 breadth/sector framework; test conditional relative strength, risk-adjusted returns and turnover across industries and cap buckets.
6. **MACRO-06 Portfolio research:** benchmark regime-based cash/equity/sector allocations against buy-and-hold using QT-01/02/03/04/05 for point-in-time history, execution rules, transaction costs and risk metrics.
7. **MACRO-07 Dashboard:** Macro Overview in React/TypeScript/Vite, with R2 JSON/Parquet snapshots, indicator freshness, current regime, history, transition uncertainty and sector heatmap; no direct client-side DuckDB access.

### Acceptance gates

- Document data provenance, revisions and publication delays; **never** backfill revised data into historical decision dates.
- Report regime stability, class balance, transition confusion/calibration and out-of-sample walk-forward results including negative findings.
- Compare against simple rules, buy-and-hold and QT-06 without duplicate sector-rotation logic; include Vietnam fees/tax/slippage, drawdown and sensitivity analysis.
- Rerunnable incremental ingestion with stale/missing-data fallback and run logs; dashboard clearly distinguishes observed metrics from scenarios.
- Deliver BA scope, research report, reproducible artifacts and Go/No-Go; no automatic trading or production signal promotion.

**Research scenarios, not model outputs:** 2027 slowdown possibility; 2028–2031 investment/industrial expansion; 2032–2035 productivity and demographic constraints. Explicitly evaluate counterexamples such as FX stress, inefficient USD borrowing, FDI non-disbursement and weak household demand. Do not treat the podcast's growth-rate or timing estimates as verified forecasts.


## 11. INFRA-R2-01 — R2 Data Layout by Access Pattern

- **Created:** 2026-10-25
- **Priority / status:** P1 (proposed) / PROPOSED_FOR_DESIGN; architecture proposal, not a canonical REQ or implemented feature.
- **Primary domain:** §2.1 Data Platform & Market Data Quality. Do not change canonical totals.
- **Goal:** Organize the existing Cloudflare R2 bucket `cherrystock` around frontend access patterns: small JSON for latest dashboards and chart slices, compressed partitioned Parquet for historical/bulk analytics; reduce transfer, object operations, latency and operational costs.
- **Architecture:** Local AmiBroker + DuckDB + Python computes and publishes → R2 object storage → React/TypeScript/Vite on GitHub Pages. Public immutable JSON may be fetched directly via configured R2 custom domain/CORS; a Worker API is optional only for authentication, aggregation or dynamic transformations. No mandatory D1/VPS/MotherDuck migration.

### Proposed object layout (illustrative, not yet deployed)

```text
cherrystock/
  manifest.json
  market/
    overview/latest.json
    intermarket/latest.json
    industry/latest.json
  stocks/
    MWG/ohlc_1y.json
    MWG/rs_latest.json
    FPT/ohlc_1y.json
  historical/
    ohlc/year=2026/month=10/data.parquet
```

### Scope and acceptance criteria

1. **Inventory and mapping:** Map current DuckDB views/tables (including `vw_Ticker_Active`, OHLC, industry/market-cap indexes, R/S, SmartMoney and intermarket data) to UI consumers, freshness, cardinality and desired file format. Do not blindly export every view or expose sensitive data.
2. **JSON serving contracts:** Define schema version, as-of trading date, generated-at timestamp, timezone, source, units, null handling, ticker keys, stable file paths and frontend types. Optimize dashboard payload size; use lazy ticker-level requests and compression.
3. **Parquet history:** Partition by dataset/date (and ticker only where query patterns justify it), avoid excessive tiny objects, and document retention, compaction and replay. Parquet is for bulk/history; do not require browser-side full dataset download to draw one chart.
4. **Incremental and safe publish:** Detect changed source partitions/rows, generate immutable versioned objects, validate count/schema/date/checksum, then atomically switch the small `manifest.json` pointer **last**. Ensure idempotent reruns, partial-failure recovery and rollback to prior manifest. Note R2 object update atomicity does not create a multi-object transaction; manifest-last is the publication boundary.
5. **Cache and frontend:** Immutable versioned objects get long cache TTL; mutable manifest gets short TTL/revalidation. Configure R2 domain, CORS and allowed origins. Avoid unnecessary Workers for public static JSON; abstract drivers for future FireAnt/Yahoo/other sources.
6. **Cost controls:** Measure R2 GB-month, Class A/B operations, cache hit ratio, frontend bytes/load and optional Worker requests/CPU; set budgets/alerts and request guardrails. Verify current official free-tier limits before deployment; free egress does not imply unlimited free R2 operations.
7. **Documentation:** Publish architecture, object naming/schema conventions, local-to-R2 sync runbook, rollback procedure and UI integration guide. No fixed daily 09:00 scheduling; pipeline trigger remains a separate decision.

**Out of scope:** Replacing the local quant engine, implementing R/S/SmartMoney calculations inside Workers, mandatory D1 adoption, live brokerage execution and an automatic refresh schedule.

**Dependencies:** Existing Cloudflare R2 bucket `cherrystock`, local DuckDB pipeline and React frontend. Coordinate with REQ-0035 architecture without silently changing its canonical scope/status.

**Done gate:** Representative Market Overview and one ticker page load correct, version-consistent snapshots; interrupted sync safely leaves last good manifest readable; repeated sync is idempotent; measured size/requests and rollback documented. Independent acceptance required before DONE.
