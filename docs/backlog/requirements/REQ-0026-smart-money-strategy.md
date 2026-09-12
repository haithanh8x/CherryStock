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

Public contract đồng thời phải expose `TradeActionConfidenceScore` để downstream biết mức độ tin cậy của action hiện tại. Score này phải giữ nguyên tính explainable của REQ-0025 và không được hiểu như xác suất lợi nhuận hoặc xác suất trade thắng.

Người dùng vẫn phải xem được `SmartMoneyScore`, `ConfidenceScore`, `MarketState` và các factor score gốc để hiểu vì sao action và confidence được tạo ra.

## Background / Problem

REQ-0025 cố ý tách scoring/state khỏi automated buy/sell recommendation. Public view cung cấp score, confidence, state và factor evidence nhưng downstream vẫn phải tự map state thành hành động.

Nếu mỗi consumer tự định nghĩa mapping riêng, CherryStock sẽ có nhiều semantics BUY/HOLD/SELL khác nhau và khó backtest/audit. REQ-0026 bổ sung một strategy overlay duy nhất, mỏng và deterministic trên public Smart Money contract mà không thay đổi công thức scoring của REQ-0025.

Sau khi `TradeAction` được đưa vào production, downstream còn thiếu một thước đo phân biệt:

```text
BUY vừa đủ điều kiện
vs
BUY có evidence rất mạnh
```

và tương tự cho HOLD/SELL. `TradeActionConfidenceScore` giải quyết khoảng trống này nhưng phải bị giới hạn bởi upstream `ConfidenceScore` để strategy không tự tạo ra mức tin cậy cao hơn chất lượng evidence gốc.

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

`TradeAction` và `TradeActionConfidenceScore` là derived fields của public view. V1 không persist action/action-confidence vào `cal_smart_money_ticker_score` và không tạo strategy table riêng.

### FR-08 — Preserve SmartMoneyScore contracts

Thay đổi không được làm thay đổi:

- công thức factor;
- `SmartMoneyScore`;
- upstream `ConfidenceScore`;
- `MarketState` detection/precedence;
- logical grain của score/factor persistence;
- model code/version hiện tại.

### FR-09 — Explainability

Tài liệu strategy phải mô tả rõ ý nghĩa BUY/HOLD/SELL, quality gate, mapping theo state, `TradeActionConfidenceScore` và các factor tạo nên state-confidence.

### FR-10 — Public TradeActionConfidenceScore

`"CherryMon"."main"."vw_Ticker_SmartMoney"` phải expose:

```text
TradeActionConfidenceScore DOUBLE
```

với contract:

```text
0 <= TradeActionConfidenceScore <= 100
TradeActionConfidenceScore <= ConfidenceScore
```

Score phải non-NULL cho mọi public row.

### FR-11 — Non-PASS confidence gate

Nếu:

```text
DataQualityStatus <> PASS
```

thì:

```text
TradeAction = HOLD
TradeActionConfidenceScore = 0
```

`0` ở đây có nghĩa HOLD được phát như safety fallback vì evidence chưa đạt quality gate; không phải một "high-confidence HOLD".

### FR-12 — PASS confidence formula

Với `DataQualityStatus='PASS'`, strategy xác định một `StateEvidenceStrength` từ các factor trực tiếp xác nhận `MarketState`:

| MarketState | StateEvidenceStrength |
|---|---|
| `ACCUMULATION` | `min(AccumulationScore, AccumulationMemoryScore)` |
| `BREAKOUT` | `min(FreshFlowScore, RelativeLiquidityScore, RelativeStrengthScore)` |
| `DEMAND_EXPANSION` | `min(RelativeLiquidityScore, LiquidityAccelerationScore, RelativeStrengthScore)` |
| `SUPPLY_LOCK` | `min(SupplyLockScore, AccumulationMemoryScore)` |
| `DISTRIBUTION` | `DistributionScore` |
| `MARKUP` | `min(TrendScore, RelativeStrengthScore)` |
| `SELLING_CLIMAX` | `min(DistributionScore, RelativeLiquidityScore)` |
| `LIQUIDITY_DRYUP` | `ConfidenceScore` because LiquidityCompressionScore is not currently public |
| `NEUTRAL` | `ConfidenceScore` |

Sau đó:

```text
CandidateActionConfidence
    = 0.60 * ConfidenceScore
    + 0.40 * StateEvidenceStrength

TradeActionConfidenceScore
    = min(ConfidenceScore, CandidateActionConfidence)
```

Public view phải giữ full calculation precision cho `TradeActionConfidenceScore`. Không được round trước khi trả về vì upward rounding có thể làm `TradeActionConfidenceScore > ConfidenceScore`. UI/report consumer được phép round chỉ ở presentation layer.

Nếu một state có explicit factor list ở bảng trên nhưng factor bắt buộc bị NULL trên public view, `TradeActionConfidenceScore = 0` để lộ rõ inconsistency thay vì silently tăng confidence.

### FR-13 — Historical deployment validation

Deployment acceptance của extension này phải chạy canonical full historical SmartMoney initload:

```powershell
python scripts\initload\init_reload_smart_money_score.py
```

và chứng minh:

```text
ScoreRows > 0
ViewRows = ScoreRows
ViewMinDate = ScoreMinDate
ViewMaxDate = ScoreMaxDate
InvalidRange = 0
AboveUpstreamConfidence = 0
NonPassConfidenceMismatch = 0
InvalidTradeAction = 0
```

Strategy fields vẫn là derived view fields; full historical initload được yêu cầu để validate underlying historical score/factor coverage và public historical contract end-to-end.

## Business Rules

1. `DataQualityStatus` là quality gate có precedence cao nhất của `TradeAction` và `TradeActionConfidenceScore`.
2. `DISTRIBUTION` là SELL state duy nhất của Strategy V1.
3. `ACCUMULATION`, `BREAKOUT`, `DEMAND_EXPANSION`, `SUPPLY_LOCK` là BUY states của Strategy V1.
4. `MARKUP` map `HOLD` vì strategy coi đây là pha quản trị vị thế đã chạy, không phải điểm khởi tạo BUY mới.
5. `SELLING_CLIMAX` map `HOLD` vì capitulation có thể là rủi ro hoặc exhaustion; V1 không tự động SELL/BUY trong trạng thái này.
6. `LIQUIDITY_DRYUP` map `HOLD` vì thanh khoản cạn không có bullish/bearish meaning độc lập.
7. `NEUTRAL` map `HOLD`.
8. `HOLD` có nghĩa **không phát sinh hành động mới từ Strategy V1**. Với ticker chưa có vị thế, có thể đọc là `WAIT`; không đồng nghĩa bắt buộc phải tiếp tục nắm giữ.
9. `TradeActionConfidenceScore` đo độ tin cậy của strategy classification hiện tại; nó **không phải** win probability, expected return, risk/reward ratio hay position-sizing signal.
10. `TradeActionConfidenceScore` không bao giờ được lớn hơn upstream `ConfidenceScore`.
11. Public contract giữ full precision; presentation rounding không được thay đổi business invariant.
12. Với state có nhiều điều kiện, weakest confirming factor được dùng làm `StateEvidenceStrength` để tránh một factor cực mạnh che lấp một factor chỉ vừa đủ hoặc yếu.
13. `TradeAction` là technical strategy classification, không phải lệnh giao dịch và không thực hiện order execution.
14. Mapping và confidence phải deterministic và point-in-time vì chỉ dùng dữ liệu của cùng row/date.
15. Nếu thay đổi materially mapping BUY/HOLD/SELL hoặc công thức action confidence trong tương lai, phải version hóa strategy semantics thay vì âm thầm thay đổi cách diễn giải lịch sử.

## Scope

### In Scope

- `TradeAction` trên `vw_Ticker_SmartMoney`.
- `TradeActionConfidenceScore` trên `vw_Ticker_SmartMoney`.
- BUY/HOLD/SELL mapping từ primary `MarketState`.
- Data-quality gate trước khi phát BUY/SELL.
- State-evidence-strength confidence overlay.
- Full historical deployment validation.
- Documentation và focused validation cho mapping/confidence.
- Backward-compatible public-view extension.

### Out of Scope

- Order placement / broker execution.
- Position sizing.
- Stop-loss / take-profit pricing.
- Portfolio allocation.
- Personal investment recommendation.
- Machine-learning trading policy.
- Predictive probability of future return or trade success.
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
Then no new action/action-confidence column is required in `cal_smart_money_ticker_score` or `cal_smart_money_factor_values`.

### AC-07 — Existing outputs unchanged

Given identical persisted score/factor rows before and after this extension  
When pre-existing Smart Money columns are read  
Then their values and semantics remain unchanged; strategy columns are additive public fields only.

### AC-08 — Explainability

Given a BUY/HOLD/SELL output  
When a user follows the canonical Smart Money documentation  
Then the user can trace action → action confidence → quality gate → MarketState → underlying state conditions/factor meanings.

### AC-09 — Confidence range and cap

Given any public row, including upstream `ConfidenceScore` values with more than two decimal places  
When `TradeActionConfidenceScore` is read  
Then it is non-NULL, lies in `0..100`, and is not greater than `ConfidenceScore`.

### AC-10 — Non-PASS confidence

Given `DataQualityStatus <> 'PASS'`  
When the public view is read  
Then `TradeActionConfidenceScore = 0`.

### AC-11 — Action confidence formula

Given a PASS row in a state with explicit confirming factors  
When `TradeActionConfidenceScore` is calculated  
Then it uses the documented weakest-factor `StateEvidenceStrength`, 60/40 blend and upstream-confidence cap without view-level rounding.

### AC-12 — Missing required action evidence

Given a PASS row whose persisted state requires explicit public factors but one of those factor scores is NULL  
When the public view is read  
Then `TradeActionConfidenceScore = 0` rather than silently inferring high confidence.

### AC-13 — Historical deployment contract

Given the canonical historical initload is executed  
When deployment validation completes  
Then score/view row counts and min/max dates match, and all action-confidence violation counters are zero before metadata export and acceptance.

## Non-functional Requirements

- Performance: action/confidence must be computed from fields already participating in the public view; no new persistence scan or external data source.
- Reliability: mapping and confidence must be deterministic and non-NULL for every public row.
- Precision: business invariants apply to full-precision public values; UI/report rounding is presentation-only.
- Security: Not applicable; no credential or authorization change.
- Observability: SQL/pre-initload validation must validate allowed action values, mapping consistency, confidence range, upstream cap and non-PASS zero rule.
- Compatibility: additive public-view columns only; existing columns/grain and internal persistence remain unchanged.

## Dependencies

- REQ-0025 — Ticker-level SmartMoneyScore.
- `docs/architecture/SmartMoneyScore.md`.
- ADR-009 — state-aware scoring and Smart Money data contracts.
- `DataQualityStatus`, `ConfidenceScore`, primary `MarketState` and factor scores already produced by SmartMoneyScore V1.

## Constraints

- V1 uses one primary `MarketState`; it does not introduce multi-label strategy arbitration.
- V1 does not use portfolio/position context, so `HOLD` is a no-new-action label rather than a literal portfolio instruction.
- Strategy must not duplicate factor persistence or create a second Smart Money Source of Truth.
- `LiquidityCompressionScore` is not currently a public factor column; therefore PASS `LIQUIDITY_DRYUP` uses upstream `ConfidenceScore` as its action-confidence score until that evidence becomes public.

## Assumptions

- Existing REQ-0025 MarketState rules and precedence remain authoritative upstream semantics.
- `DataQualityStatus='PASS'` remains the approved current evidence-quality gate (`ConfidenceScore >= 60` and `FactorCoverage >= 0.80`).
- Existing `ConfidenceScore` already captures evidence completeness/quality; action confidence must refine/cap it, not replace it.

## Open Questions

- None blocking this additive implementation.
- Future research may introduce a separately versioned predictive effectiveness/probability score. That must not silently reuse `TradeActionConfidenceScore` semantics.
- Future architecture may expose `LiquidityCompressionScore` publicly and refine `LIQUIDITY_DRYUP` confidence accordingly.

## Risks

- BUY/HOLD/SELL compresses rich state information; consumers must retain access to `MarketState`, `SmartMoneyScore`, `ConfidenceScore`, `TradeActionConfidenceScore` and component scores for explainability.
- A high `TradeActionConfidenceScore` means the current action classification is well-supported by available evidence; it does not guarantee positive future return.
- `BUY` does not account for entry price, risk budget or portfolio exposure.
- A future change to upstream MarketState thresholds can change action distribution and confidence even if mapping is unchanged; model/strategy traceability must be preserved.

## Suggested Routing

- Architecture required: additive derived field on the existing public Smart Money read contract; update canonical strategy architecture.
- Primary next owner: TestEngineer.
- Domain instructions: `.github/instructions/database.instructions.md`, `.github/instructions/testing.instructions.md`.
- Validation owner: TestEngineer.

## Handoff

```text
Status: IMPLEMENTED_PENDING_VALIDATION
Primary next owner: TestEngineer
Acceptance criteria count: 13
Blocking questions: None
```
