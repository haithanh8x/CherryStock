---
id: REQ-0026
title: Smart Money BUY / HOLD / SELL Strategy Action
status: IMPLEMENTED_PENDING_VALIDATION
priority: P1
owner: BusinessAnalyst
primary_next_owner: TestEngineer
related:
  architecture: docs/architecture/SmartMoneyStrategy.md
  adr: docs/adr/ADR-009-smart-money-score-state-aware-scoring.md
  implementation: src/DuckDB/sql/smart_money_v1_schema.sql
  test: tests/test_smart_money_strategy.py
  change_request:
---

# REQ-0026 — Smart Money BUY / HOLD / SELL Strategy Action

## Business Objective

CherryStock cần một nhãn hành động đơn giản `BUY / HOLD / SELL` theo từng ticker và từng ngày để Screener, Chart, Dashboard và research/backtest có thể sử dụng trực tiếp kết quả Smart Money mà không phải tự diễn giải chín `MarketState` ở mỗi consumer.

Nhãn hành động phải giữ nguyên tính explainable của REQ-0025: người dùng vẫn xem được `SmartMoneyScore`, `ConfidenceScore`, `MarketState` và các factor score gốc để hiểu vì sao action được tạo ra.

## Background / Problem

REQ-0025 cố ý tách scoring/state khỏi automated buy/sell recommendation. Public view hiện cung cấp score, confidence, state và factor evidence nhưng downstream vẫn phải tự map state thành hành động.

Nếu mỗi consumer tự định nghĩa mapping riêng, CherryStock sẽ có nhiều semantics BUY/HOLD/SELL khác nhau và khó backtest/audit. REQ-0026 bổ sung một strategy overlay duy nhất, mỏng và deterministic trên public Smart Money contract mà không thay đổi công thức scoring của REQ-0025.

## Stakeholders / Consumers

- CherryStock owner / analyst.
- Stock Screener.
- Chart / Dashboard.
- Backtest / research.
- Future alert/ranking consumers.

## Functional Requirements

### FR-01 — Public TradeAction

`"CherryMon"."main"."vw_Ticker_SmartMoney"` phải expose một column `TradeAction` cho mỗi row hiện hữu của public Smart Money view.

### FR-02 — Closed action set

`TradeAction` chỉ được nhận một trong ba giá trị:

```text
BUY
HOLD
SELL
```

### FR-03 — Quality gate

Nếu `DataQualityStatus <> 'PASS'`, `TradeAction` phải là `HOLD` bất kể `MarketState` là gì.

Strategy không được phát BUY/SELL từ evidence đang `WARNING` hoặc `INVALID`.

### FR-04 — BUY states

Khi `DataQualityStatus = 'PASS'`, các primary state sau map thành `BUY`:

```text
ACCUMULATION
BREAKOUT
DEMAND_EXPANSION
SUPPLY_LOCK
```

### FR-05 — SELL state

Khi `DataQualityStatus = 'PASS'` và `MarketState = 'DISTRIBUTION'`, `TradeAction` phải là `SELL`.

### FR-06 — HOLD states

Khi `DataQualityStatus = 'PASS'`, các state còn lại map thành `HOLD`:

```text
MARKUP
LIQUIDITY_DRYUP
SELLING_CLIMAX
NEUTRAL
```

### FR-07 — Derived read contract

`TradeAction` là derived field của public view. V1 không persist action vào `cal_smart_money_ticker_score` hoặc tạo một action table riêng.

### FR-08 — Preserve SmartMoneyScore contracts

Thay đổi không được làm thay đổi:

- công thức factor;
- `SmartMoneyScore`;
- `ConfidenceScore`;
- `MarketState` detection/precedence;
- logical grain của score/factor persistence;
- model code/version hiện tại.

### FR-09 — Explainability

Tài liệu strategy phải mô tả rõ ý nghĩa BUY/HOLD/SELL, quality gate, mapping theo state và các công thức/điều kiện state upstream tạo nên action.

## Business Rules

1. `DataQualityStatus` là quality gate có precedence cao nhất của `TradeAction`.
2. `DISTRIBUTION` là SELL state duy nhất của Strategy V1.
3. `ACCUMULATION`, `BREAKOUT`, `DEMAND_EXPANSION`, `SUPPLY_LOCK` là BUY states của Strategy V1.
4. `MARKUP` map `HOLD` vì strategy coi đây là pha quản trị vị thế đã chạy, không phải điểm khởi tạo BUY mới.
5. `SELLING_CLIMAX` map `HOLD` vì capitulation có thể là rủi ro hoặc exhaustion; V1 không tự động SELL/BUY trong trạng thái này.
6. `LIQUIDITY_DRYUP` map `HOLD` vì thanh khoản cạn không có bullish/bearish meaning độc lập.
7. `NEUTRAL` map `HOLD`.
8. `HOLD` có nghĩa **không phát sinh hành động mới từ Strategy V1**. Với ticker chưa có vị thế, có thể đọc là `WAIT`; không đồng nghĩa bắt buộc phải tiếp tục nắm giữ.
9. `TradeAction` là technical strategy classification, không phải lệnh giao dịch và không thực hiện order execution.
10. Mapping V1 phải deterministic và point-in-time vì nó chỉ dùng `MarketState`/`DataQualityStatus` của cùng row/date.
11. Nếu thay đổi materially mapping BUY/HOLD/SELL trong tương lai, phải version hóa strategy semantics thay vì âm thầm thay đổi cách diễn giải lịch sử.

## Scope

### In Scope

- `TradeAction` trên `vw_Ticker_SmartMoney`.
- BUY/HOLD/SELL mapping từ primary `MarketState`.
- Data-quality gate trước khi phát BUY/SELL.
- Documentation và focused validation cho mapping.
- Backward-compatible public-view extension.

### Out of Scope

- Order placement / broker execution.
- Position sizing.
- Stop-loss / take-profit pricing.
- Portfolio allocation.
- Personal investment recommendation.
- Machine-learning trading policy.
- Recalibration của SmartMoneyScore factors/state thresholds.
- Multi-position lifecycle/P&L state (entry price, current holdings, realized return).

## Acceptance Criteria

### AC-01 — BUY mapping

Given a row with `DataQualityStatus='PASS'` and `MarketState` in `ACCUMULATION`, `BREAKOUT`, `DEMAND_EXPANSION`, `SUPPLY_LOCK`  
When the public Smart Money view is read  
Then `TradeAction='BUY'`.

### AC-02 — SELL mapping

Given a row with `DataQualityStatus='PASS'` and `MarketState='DISTRIBUTION'`  
When the public Smart Money view is read  
Then `TradeAction='SELL'`.

### AC-03 — HOLD mapping

Given a row with `DataQualityStatus='PASS'` and `MarketState` in `MARKUP`, `LIQUIDITY_DRYUP`, `SELLING_CLIMAX`, `NEUTRAL`  
When the public Smart Money view is read  
Then `TradeAction='HOLD'`.

### AC-04 — Quality gate

Given any row with `DataQualityStatus <> 'PASS'`  
When the public Smart Money view is read  
Then `TradeAction='HOLD'` even if its `MarketState` normally maps to BUY or SELL.

### AC-05 — Closed value set

Given any row returned by `vw_Ticker_SmartMoney`  
When `TradeAction` is inspected  
Then it is non-NULL and belongs to `BUY/HOLD/SELL` only.

### AC-06 — Persistence unchanged

Given the strategy extension  
When Smart Money storage metadata is inspected  
Then no new action column/table is required in `cal_smart_money_ticker_score` or `cal_smart_money_factor_values`.

### AC-07 — Existing outputs unchanged

Given identical persisted score/factor rows before and after this extension  
When existing Smart Money columns are read  
Then their values and semantics remain unchanged; only the additive `TradeAction` public field is new.

### AC-08 — Explainability

Given a BUY/HOLD/SELL output  
When a user follows the canonical Smart Money documentation  
Then the user can trace action → quality gate → MarketState → underlying state conditions/factor meanings.

## Non-functional Requirements

- Performance: `TradeAction` must be computed as a constant-time CASE expression per returned row and must not add joins or scans beyond the existing public view plan.
- Reliability: mapping must be deterministic and non-NULL for every public row.
- Security: Not applicable; no credential or authorization change.
- Observability: SQL preflight must validate allowed values and mapping consistency.
- Compatibility: additive public-view column only; existing columns/grain and internal persistence remain unchanged.

## Dependencies

- REQ-0025 — Ticker-level SmartMoneyScore.
- `docs/architecture/SmartMoneyScore.md`.
- ADR-009 — state-aware scoring and Smart Money data contracts.
- `DataQualityStatus` and primary `MarketState` already produced by SmartMoneyScore V1.

## Constraints

- V1 uses one primary `MarketState`; it does not introduce multi-label strategy arbitration.
- V1 does not use portfolio/position context, so `HOLD` is a no-new-action label rather than a literal portfolio instruction.
- Strategy must not duplicate factor persistence or create a second Smart Money Source of Truth.

## Assumptions

- Existing REQ-0025 MarketState rules and precedence remain authoritative upstream semantics.
- `DataQualityStatus='PASS'` remains the approved current evidence-quality gate (`ConfidenceScore >= 60` and `FactorCoverage >= 0.80`).

## Open Questions

- None blocking V1 implementation.
- Future research may decide whether `ACCUMULATION` should be split into WATCH/EARLY_BUY or whether action strength/position sizing deserves a separate strategy version.

## Risks

- BUY/HOLD/SELL compresses rich state information; consumers must retain access to `MarketState`, `SmartMoneyScore`, `ConfidenceScore` and component scores for explainability.
- `BUY` does not account for entry price, risk budget or portfolio exposure.
- A future change to upstream MarketState thresholds can change action distribution even if the mapping itself is unchanged; model/strategy version traceability must be preserved.

## Suggested Routing

- Architecture required: No new architecture boundary; additive derived field on the existing public Smart Money read contract.
- Primary next owner: TestEngineer.
- Domain instructions: `.github/instructions/database.instructions.md`, `.github/instructions/testing.instructions.md`.
- Validation owner: TestEngineer.

## Handoff

```text
Status: IMPLEMENTED_PENDING_VALIDATION
Primary next owner: TestEngineer
Acceptance criteria count: 8
Blocking questions: None
```
