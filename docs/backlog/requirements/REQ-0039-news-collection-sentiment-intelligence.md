---
id: REQ-0039
title: Market News Collection, Entity Linking and Sentiment Intelligence
status: DRAFT
priority: P1
owner: BusinessAnalyst
primary_next_owner: BusinessAnalyst
related:
  requirements: REQ-0025, REQ-0035
  architecture:
  adr:
  implementation:
  test:
  change_request:
---

# REQ-0039 — Market News Collection, Entity Linking and Sentiment Intelligence

## Business Objective

Build a reliable, cost-aware news intelligence pipeline for CherryStock that collects relevant Vietnam and global financial/industry/company news, deduplicates and links stories to listed tickers, measures explainable sentiment and event relevance, and exposes point-in-time correct signals for research, dashboards and future trading strategies.

## Background / Problem

Price/volume and technical indicators alone may not explain earnings announcements, regulatory changes, corporate actions, industry developments or AI-related events. Raw headlines are noisy, duplicated across publishers, may mention many entities, and often have delayed publication or ingestion timestamps. CherryStock needs an auditable data foundation before news sentiment can influence any model or strategy.

## Stakeholders / Consumers

- Market research and ticker-analysis UI.
- Quant/strategy research and backtesting.
- Future event-driven analytics and Smart Money research (integration only by separate approval).
- Daily data pipeline operator.

## Functional Requirements

1. Ingest news from approved licensed/accessible RSS, official disclosures, APIs and other permitted sources; record source identity, URL, language, title, available excerpt/body, and source metadata.
2. Track distinct publication, update, ingestion and first-seen timestamps with source timezone and confidence/quality indicators.
3. Support configurable scheduled incremental collection, backfill and safe retries; use source-specific rate limits and terms-compliant access.
4. Normalize Vietnamese/English text, identify duplicate/near-duplicate stories and syndicated coverage while preserving original source lineage.
5. Classify content into company-specific, industry, macroeconomic, policy/regulatory and global/AI-related themes, with event categories such as earnings, dividends, corporate actions, M&A and material announcements.
6. Extract and resolve mentioned companies/tickers using authoritative ticker/company mappings; distinguish primary subject from passing mention, handle aliases and ambiguous symbols.
7. Produce explainable sentiment (positive/neutral/negative and optional score/confidence), event relevance, impacted entity and evidence span; distinguish factual event polarity from opinion tone.
8. Preserve raw/source evidence and versioned derived labels so classification/sentiment can be recalculated without rewriting historical facts.
9. Aggregate news counts, source diversity, sentiment trend, freshness and event categories by ticker/sector/time window without treating repeated syndication as independent evidence.
10. Expose read-only latest-news and historical point-in-time query contracts for UI and analytics; provide source citations/links and explainability.
11. Maintain a review/feedback mechanism for low-confidence entity matching and sentiment errors, including unknown/uncertain states rather than forced labels.
12. Capture coverage, ingestion lag, duplicate rate, error rate, classification quality and per-source/model compute costs.
13. Enable historical research relating news/event/sentiment to subsequent price/volume outcomes, with trading costs and leakage-safe backtesting only in a separately approved strategy/evaluation scope.
14. Support configurable data retention, copyright/licensing restrictions, PII minimization and secure API credential handling.

## Business Rules

1. News/sentiment is research evidence, not an automatic BUY/SELL instruction or direct modification of production SmartMoneyScore, R/S Strength or portfolio decisions.
2. A historical simulation may only consume articles and derived signals demonstrably available by the decision timestamp; use first-seen/availability time, not merely a backdated published timestamp.
3. Publisher duplication and repeated syndication must not inflate sentiment magnitude or event importance.
4. No invented article text, ticker association, sentiment rationale or publication time; missing values remain explicitly unknown.
5. Sentiment and event impact are distinct: favorable language does not guarantee positive price reaction.
6. Store permitted text only; preserve URL, metadata and evidence references subject to source licenses.
7. Automated collection must respect robots/terms, API limits, paywalls and approved access rights.
8. Any integration into production trading models requires independent validation, OOS tests and separate release approval.

## Scope

### In Scope

- Approved multi-source collection and incremental ingestion.
- News normalization, deduplication and provenance.
- Ticker/company/sector entity linking.
- Topic/event categorization and explainable sentiment.
- Time-window aggregation, historical archive and research-facing read contracts.
- Freshness, quality, cost and operational monitoring.

### Out of Scope

- Unlicensed full-text scraping or paywall circumvention.
- Automated trading or investment recommendations.
- Automatic production changes to Smart Money, R/S or other scoring engines.
- A guaranteed predictive sentiment model or fixed sentiment-to-return mapping.
- Prescribing exact data schema, vendor, LLM or architecture before SolutionArchitect review.

## Acceptance Criteria

- **AC-01 Provenance:** Every published item has an attributable source URL and traceable timestamps; missing publication time is explicit.
- **AC-02 Incremental/idempotent:** Repeated collection over the same window produces no duplicate canonical articles and supports restart after interruption.
- **AC-03 Deduplication:** Syndicated/near-duplicate stories are grouped while preserving all source references; ticker aggregates do not double-count them.
- **AC-04 Entity linking:** A multi-company story can link to multiple verified tickers, with role/relevance and ambiguity recorded; unrelated mentions are not promoted to primary subject.
- **AC-05 Sentiment:** Results expose label, confidence, model/rule version and evidence; neutral/uncertain cases remain representable.
- **AC-06 Point-in-time:** A historical as-of query excludes articles/signals not available at that time, including late-ingested or subsequently reprocessed data.
- **AC-07 Source compliance:** Each configured source has documented permission/retention policy and access constraints.
- **AC-08 Reliability:** Failed source collection does not erase prior valid data; run status, source errors and freshness are observable.
- **AC-09 Cost:** A representative ingestion/sentiment benchmark records throughput, latency and API/model cost per article and per daily run.
- **AC-10 Read contract:** Ticker/sector dashboards can retrieve current and historical news with citations, event category and sentiment breakdown.
- **AC-11 Governance:** News signals do not automatically activate or change production strategy scores; future predictive usage requires separate validation.

## Non-functional Requirements

- Prefer cheap deterministic filtering/dedup/entity rules before expensive LLM classification; selectively escalate ambiguous or high-value cases.
- Vietnamese-first support with English/global coverage as source licenses permit.
- Auditable model/prompt/version lineage, replay and quality sampling.
- Scalable incremental operation on local pipeline with cloud read-serving compatible with REQ-0035.
- Resilient scheduling, bounded concurrency, source-specific retries and backpressure.

## Dependencies

- Canonical ticker/company/industry mappings and adjusted OHLC for subsequent event research.
- Existing daily data orchestration and DuckDB persistence.
- REQ-0035 cloud-serving design if news intelligence is exposed remotely.
- Future event-driven trading requirement (separate BusinessAnalyst intake), if predictive backtesting is approved.

## Open Questions / Design Handoff

- Which Vietnamese/foreign news feeds and official disclosure sources are legally and commercially acceptable?
- What update cadence and historical retention window are required?
- Is sentiment article-level, entity-specific, event-specific or all three in the first release?
- What human-labeled Vietnamese evaluation set and minimum quality thresholds should gate publication?
- Which UI surfaces and alert thresholds are in the first delivery scope?

## Next Step

BusinessAnalyst to confirm source scope, measurable quality gates, initial UI consumers and cost envelope before READY_FOR_DESIGN. SolutionArchitect to define collection, storage, entity resolution, classification and public data contracts. TestEngineer to independently validate point-in-time integrity, deduplication, sentiment quality and restartability before DONE.
