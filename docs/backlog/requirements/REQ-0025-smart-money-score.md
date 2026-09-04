---
id: REQ-0025
title: Ticker-level SmartMoneyScore
status: READY_FOR_IMPLEMENTATION
priority: P1
owner: BusinessAnalyst
primary_next_owner: GeneralCoding
related:
  architecture: docs/architecture/SmartMoneyScore.md
  adr: docs/adr/ADR-009-smart-money-score-state-aware-scoring.md
  implementation:
  test:
  change_request:
---

# REQ-0025 — Ticker-level SmartMoneyScore

## Business Objective

CherryStock cần một `SmartMoneyScore` theo từng ticker và từng ngày giao dịch để nhận diện sớm dòng tiền có chất lượng đang dịch chuyển vào/ra cổ phiếu, phân biệt tích lũy, mở rộng cầu, khóa cung và phân phối, đồng thời tạo nền tảng để aggregate lên Industry / Sector / Custom Group trong các phase tiếp theo.

Mục tiêu nghiệp vụ chính là trả lời được:

- Smart Money đang bắt đầu vào ticker nào?
- Ticker nào đang được tích lũy trước breakout?
- Ticker nào đang có Demand Expansion?
- Ticker tăng mạnh nhưng volume thấp là thiếu cầu hay thiếu cung?
- Ticker nào đang có dấu hiệu Distribution?
- Smart Money đã vào trước đó nhưng volume hiện tại giảm thì sức mạnh trước đó còn ảnh hưởng hay không?
- Tín hiệu có đủ đáng tin để sử dụng hay chỉ là một biến động mạnh ở cổ phiếu quá illiquid?

## Background / Problem

Một scoring đơn giản dựa trên Price + Volume có thể cho tín hiệu sai trong nhiều trạng thái thị trường.

Ví dụ:

- Volume cao + giá tăng có thể là dòng tiền mới tích cực.
- Volume cao + Close gần Low có thể là phân phối.
- Volume thấp + giá yếu thường là thiếu cầu.
- Volume thấp + giá tăng mạnh/giữ sát High sau giai đoạn tích lũy có thể là Supply Contraction.
- Ticker tăng trần liên tiếp có thể có volume giảm vì nguồn cung bị khóa, không đồng nghĩa Smart Money đã biến mất.
- Một cổ phiếu rất kém thanh khoản có thể tăng mạnh bằng lượng vốn nhỏ và không nên được đánh giá với cùng độ tin cậy như cổ phiếu thanh khoản cao.

Do đó `SmartMoneyScore` phải phản ánh market state và phải giải thích được nguồn gốc của score.

## Stakeholders / Consumers

- CherryStock owner / analyst.
- Stock Screener.
- Sector / Industry / Custom Group analytics trong phase tiếp theo.
- Chart / dashboard.
- Backtest / research.
- Future ranking / rotation engine.
- TestEngineer và data-quality workflow để kiểm chứng calculation.

## Functional Requirements

### FR-01 — Daily ticker score

Hệ thống phải tạo một `SmartMoneyScore` cho mỗi ticker đủ điều kiện tại mỗi trading date.

Score phải nằm trong thang:

`0..100`.

### FR-02 — Independent ConfidenceScore

Mỗi SmartMoneyScore phải có `ConfidenceScore` riêng biệt trong thang `0..100`.

Confidence không được đồng nhất với SmartMoneyScore.

Một ticker có thể có:

- SmartMoneyScore cao + Confidence cao;
- SmartMoneyScore cao + Confidence thấp;
- SmartMoneyScore thấp + Confidence cao.

### FR-03 — Explainable component scores

SmartMoneyScore phải giải thích được bằng các component tối thiểu:

- Fresh Money Flow.
- Relative Trading Value / Relative Liquidity.
- Liquidity Acceleration.
- Relative Strength.
- Accumulation.
- Accumulation Memory.
- Supply Lock.
- Limit-Up evidence khi dữ liệu tin cậy tồn tại.
- Trend.
- Distribution.

Mỗi component dùng để scoring phải có giá trị chuẩn hóa và có thể audit lại.

### FR-04 — Fresh Money Flow

Hệ thống phải nhận diện dòng tiền mới bằng hành vi kết hợp giữa giá, vị trí đóng cửa trong range và thanh khoản.

Raw Volume không được sử dụng đơn độc như bằng chứng Smart Money.

### FR-05 — Relative Liquidity

Hệ thống phải so sánh thanh khoản hiện tại với baseline lịch sử của chính ticker.

Tối thiểu phải hỗ trợ logic tương đương:

- current value/volume so với 20-session average;
- 5-session average so với 20-session average.

Tên metric và implementation chi tiết thuộc Solution Architecture.

### FR-06 — Relative Strength

Hệ thống phải đánh giá strength của ticker so với benchmark chung.

V1 tối thiểu phải hỗ trợ VNINDEX hoặc benchmark được cấu hình tương đương.

Thiết kế phải cho phép mở rộng sang Sector Index / Custom Index mà không thay đổi business semantics của SmartMoneyScore.

### FR-07 — Accumulation

Hệ thống phải có khả năng nhận diện giai đoạn tích lũy nhiều phiên trước breakout dựa trên sự kết hợp của:

- hành vi Close trong daily range;
- price persistence;
- liquidity behavior;
- relative strength;
- volume-based accumulation indicators nếu có;
- price structure / breakout behavior.

### FR-08 — Accumulation Memory

Tín hiệu tích lũy trước đó phải có memory và decay theo thời gian.

Smart Money đã tích lũy trước breakout không được tự động mất tín hiệu chỉ vì volume hiện tại giảm.

### FR-09 — Supply Lock

Hệ thống phải nhận diện `SUPPLY_LOCK` hoặc trạng thái nghiệp vụ tương đương khi có bằng chứng kết hợp rằng:

- price strength cao;
- Close duy trì gần High / vùng mạnh;
- relative strength tốt;
- thanh khoản co lại;
- trend vẫn tích cực;
- không có Distribution evidence mạnh;
- accumulation memory hỗ trợ tín hiệu khi có.

Volume thấp không được tự động làm SmartMoneyScore giảm trong trạng thái này.

### FR-10 — Limit-Up streak

Khi có dữ liệu market-limit đáng tin cậy, hệ thống phải nhận diện:

- is_limit_up;
- limit_up_streak.

Limit-up evidence phải hỗ trợ Supply Lock nhưng không được là điều kiện duy nhất để kết luận Smart Money.

Nếu dữ liệu market-limit tin cậy không tồn tại, hệ thống không được gán một ticker là exact limit-up chỉ bằng phỏng đoán.

### FR-11 — Distribution

Hệ thống phải nhận diện Distribution khi thanh khoản tăng nhưng hành vi giá yếu, ví dụ:

- Trading Value / Volume tăng;
- Return yếu/âm;
- Close gần Low;
- Relative Strength suy giảm;
- failed breakout / upper rejection khi có.

Distribution phải làm giảm SmartMoneyScore hoặc tạo negative evidence tương đương.

### FR-12 — Market-state classification

Mỗi ticker/date phải có một primary market state tối thiểu thuộc tập:

- ACCUMULATION
- BREAKOUT
- DEMAND_EXPANSION
- SUPPLY_LOCK
- MARKUP
- DISTRIBUTION
- LIQUIDITY_DRYUP
- SELLING_CLIMAX
- NEUTRAL

State phải được lưu cùng score để người dùng hiểu bối cảnh của tín hiệu.

### FR-13 — State-aware scoring

Không được sử dụng một fixed-weight formula duy nhất cho mọi market state.

Từng state phải có weighting profile phù hợp với semantics của state đó.

Ví dụ business expectation:

- NORMAL ưu tiên Fresh Flow và liquidity.
- ACCUMULATION ưu tiên accumulation evidence.
- BREAKOUT / DEMAND_EXPANSION ưu tiên fresh flow + abnormal liquidity.
- SUPPLY_LOCK ưu tiên accumulation memory + supply contraction + strength, và giảm phụ thuộc vào current volume.
- DISTRIBUTION phải có negative penalty.

### FR-14 — Missing-factor handling

Missing factor vì thiếu nguồn dữ liệu không được mặc định biến thành score 0.

Hệ thống phải:

- phân biệt `missing/unavailable` với `negative evidence`;
- vẫn tính score từ các factor đủ điều kiện khi business logic cho phép;
- phản ánh factor coverage/data quality vào ConfidenceScore.

### FR-15 — Illiquidity control

Hệ thống phải giảm độ tin cậy của tín hiệu khi ticker có:

- thanh khoản lịch sử quá thấp;
- quá ít active trading sessions;
- price move quá lớn so với lượng vốn/volume tham gia;
- thiếu dữ liệu quan trọng.

Một ticker illiquid vẫn có thể có SmartMoneyScore cao nhưng ConfidenceScore phải phản ánh rủi ro false positive.

### FR-16 — Historical reproducibility

SmartMoneyScore phải reproducible theo:

- ticker;
- trade date;
- model version;
- configuration version hoặc equivalent traceable configuration identity.

Historical recalculation không được phụ thuộc vào dữ liệu tương lai.

### FR-17 — Historical and incremental execution

Hệ thống phải hỗ trợ:

- full historical backfill;
- date-range recalculation;
- selected ticker recalculation;
- incremental daily refresh.

Rerun cùng input/model/config phải cho kết quả deterministic và không tạo duplicate logical records.

### FR-18 — Downstream consumption

Kết quả phải có read contract ổn định để downstream có thể lấy tối thiểu:

- Ticker.
- Date.
- SmartMoneyScore.
- ConfidenceScore.
- MarketState.
- các component score quan trọng.
- model/config identity.

Phase tiếp theo phải có thể aggregate ticker score lên Sector / Industry / Custom Group mà không phải reverse-engineer internal calculation storage.

## Business Rules

1. `Volume thấp` không có bullish/bearish meaning độc lập; meaning phụ thuộc price behavior và market state.
2. `Volume thấp + price yếu` không được classify là Supply Lock chỉ vì volume co lại.
3. `Volume thấp + price mạnh + Close gần High + RS mạnh + prior accumulation` có thể tạo Supply Lock evidence.
4. Trading Value được ưu tiên hơn raw Volume khi dữ liệu chính xác tồn tại.
5. Nếu Trading Value chính xác chưa có, hệ thống được phép dùng liquidity proxy nhưng phải đánh dấu data quality/provenance và phản ánh vào Confidence.
6. Exact limit-up chỉ được xác nhận từ authoritative market-limit/reference data hoặc equivalent validated source.
7. Missing exact limit-up data không được biến thành negative score; chỉ làm giảm evidence coverage/confidence.
8. SmartMoneyScore và ConfidenceScore là hai dimensions độc lập.
9. Distribution là negative evidence, không phải absence of positive evidence.
10. Accumulation Memory phải decay theo thời gian và không được giữ tín hiệu cao vô hạn.
11. Score phải được clamp trong `0..100`.
12. Component values phải audit được; chỉ lưu final score mà không có evidence là không đạt yêu cầu.
13. Không sử dụng future data của ticker hoặc benchmark để tính score cho ngày hiện tại.
14. Smart Money ở V1 là behavioral proxy từ market data, không phải khẳng định danh tính nhà đầu tư tổ chức thực tế.
15. Sector aggregation không được double-count SmartMoneyScore vừa làm value vừa làm dynamic weight; weighting cấp sector thuộc requirement riêng.

## Scope

### In Scope

- Daily ticker-level SmartMoneyScore.
- Daily ConfidenceScore.
- Component score/evidence.
- Market-state classification.
- Fresh Flow.
- Relative liquidity.
- Liquidity acceleration.
- Relative Strength.
- Accumulation and memory.
- Supply Lock.
- Limit-Up evidence when source data supports it.
- Trend.
- Distribution.
- Historical backfill and incremental refresh.
- Explainability and version traceability.
- Data-quality behavior for missing factors.

### Out of Scope

- Sector/Industry/Custom Group SmartMoneyScore aggregation.
- Custom Index OHLC construction.
- Tick-by-tick aggressor classification.
- Broker-level Smart Money identification.
- Level-2 order-book imbalance.
- Foreign/proprietary trading attribution as mandatory V1 inputs.
- ML/AI trained SmartMoney model.
- Automated buy/sell recommendation.
- Order execution.
- Guaranteed identification of institutional investors.

## Acceptance Criteria

### AC-01 — Positive fresh flow

Given a liquid ticker with strong positive price behavior, Close near High, and materially elevated relative liquidity  
When SmartMoneyScore is calculated  
Then Fresh Flow must be positive/high relative to the eligible universe and the final score must not classify the event as Distribution without stronger contradictory evidence.

### AC-02 — Distribution

Given a ticker with materially elevated liquidity, weak/negative return, Close near Low and deteriorating relative strength  
When SmartMoneyScore is calculated  
Then Distribution evidence must be high and must reduce the final SmartMoneyScore.

### AC-03 — Supply lock with falling volume

Given a ticker with prior positive accumulation, strong trend/relative strength, price persistently near High and declining current liquidity  
When current volume/value falls below its recent average  
Then the system must be able to classify the ticker as SUPPLY_LOCK and keep SmartMoneyScore positive/high even when Fresh Flow is low.

### AC-04 — Weak low-volume ticker

Given a ticker with low/falling liquidity, weak price momentum and weak relative strength  
When SmartMoneyScore is calculated  
Then it must not be classified as SUPPLY_LOCK solely because liquidity contracted.

### AC-05 — Consecutive exact limit-up

Given authoritative market-limit data and a ticker closing at limit-up for multiple consecutive sessions  
When SmartMoneyScore is calculated  
Then limit-up streak evidence must increase with the streak but must not increase without bound, and current low volume must not automatically erase prior accumulation/supply-lock evidence.

### AC-06 — Missing market-limit data

Given current source data does not provide authoritative reference/ceiling information  
When SmartMoneyScore is calculated  
Then exact `is_limit_up` must be unavailable/unknown rather than guessed, the score may still use non-limit Supply Lock evidence, and Confidence must reflect missing evidence.

### AC-07 — Illiquid price spike

Given a ticker with extremely low historical liquidity that moves strongly on small participation  
When SmartMoneyScore is calculated  
Then a high raw SmartMoneyScore is allowed if behavioral evidence is strong, but ConfidenceScore must be materially lower than an equivalent signal in a liquid ticker.

### AC-08 — Accumulation memory

Given a ticker with high accumulation evidence before breakout  
When subsequent sessions remain strong but current liquidity falls  
Then accumulation memory must decay gradually instead of dropping immediately to zero.

### AC-09 — No look-ahead

Given a historical score date T  
When historical recalculation is performed  
Then no market/indicator/benchmark data after T may affect the result for T.

### AC-10 — Idempotent rerun

Given the same ticker/date range, input data, model version and configuration  
When the calculation is rerun  
Then the persisted logical result must be replaced/upserted deterministically without duplicate rows.

### AC-11 — Explainability

Given a stored SmartMoneyScore  
When a downstream consumer requests the score  
Then it must be possible to retrieve the market state, confidence and factor/component evidence that produced the score.

### AC-12 — Score range

Given any valid input combination  
When scoring completes  
Then SmartMoneyScore and ConfidenceScore must remain within `0..100`.

## Non-functional Requirements

- **Performance:** Daily incremental refresh must support the active CherryStock ticker universe without requiring full-history recalculation for every run.
- **Reliability:** Multi-step persistence must be idempotent; partial writes must not expose a mixed model/config state as a successful result.
- **Security:** Not applicable beyond existing CherryStock database access policy; no new external secrets are required by V1.
- **Observability:** Calculation must expose counts for processed/skipped/invalid tickers and data-quality/factor-coverage warnings.
- **Compatibility:** Existing `raw_stock_eod`, Indicator Engine and downstream public contracts must not be broken.
- **Explainability:** Final score must remain traceable to component values and model/config identity.
- **Reproducibility:** Historical results must be deterministic for the same versioned inputs/configuration.

## Dependencies

- `main.raw_stock_eod` provides current OHLCV source.
- Active ticker universe is currently represented by `main.raw_lstTicker`.
- Technical-indicator outputs may be consumed through `main.vw_Ticker_indicators`.
- Benchmark time series must be available through an approved market-data source.
- Exact Trading Value is not currently present in `raw_stock_eod`.
- Exact reference/ceiling/floor data is not currently present in `raw_stock_eod`.
- Current `raw_lstTicker` metadata does not provide an authoritative market-cap/free-float contract for V1 confidence controls.

## Constraints

- Current `raw_stock_eod` schema is `Ticker, Date, Open, High, Low, Close, Volume, OpenInt`.
- V1 must be implementable without silently assuming columns that do not currently exist.
- Missing exact Trading Value or market-limit fields must be handled explicitly as lower-quality evidence, not fabricated.
- Smart Money factors must not overwrite or redefine existing technical-indicator semantics.

## Assumptions

- Daily OHLCV history is sufficiently complete for the majority of active tickers.
- A benchmark series such as VNINDEX can be resolved during implementation.
- `Close * Volume` or another architecture-approved proxy may be used temporarily for relative liquidity when exact Trading Value is unavailable, provided the result is clearly treated as a proxy.
- Cross-sectional comparisons are only meaningful over an eligible universe with adequate data coverage.

## Open Questions

No blocking business question remains for V1.

Non-blocking future decisions:

- Which authoritative source should supply exact Trading Value?
- Which source should supply exchange/reference/ceiling/floor data?
- Should foreign/proprietary flow become first-class factors in V2?
- What liquidity thresholds should be promoted from initial defaults after historical evaluation?

These are calibration/data-source decisions and do not block the V1 architecture/implementation contract.

## Risks

- OHLCV-only behavioral proxies can misclassify manipulation or event-driven price gaps as Smart Money.
- Missing exact Trading Value lowers precision of capital-flow interpretation.
- Missing market-limit data prevents exact limit-up classification.
- Strongly correlated factors can double-count the same behavior if weights are not governed.
- Fixed thresholds may behave differently across market regimes.
- Very illiquid tickers can generate high price-strength evidence with low capital participation.
- Cross-sectional normalization can be unstable when universe coverage is poor.
- State transitions may be noisy without persistence/hysteresis rules.

## Suggested Routing

- Architecture required: Yes — completed in `docs/architecture/SmartMoneyScore.md`.
- Primary next owner: `.github/agents/GeneralCoding.agent.md`.
- Domain instructions:
  - `.github/instructions/database.instructions.md`
  - `.github/instructions/indicators.instructions.md` when consuming indicator SSOT
  - `.github/instructions/testing.instructions.md` for validation handoff
- Validation owner: TestEngineer
- ADR: `docs/adr/ADR-009-smart-money-score-state-aware-scoring.md`

## Handoff

```text
Status: READY_FOR_IMPLEMENTATION
Primary next owner: GeneralCoding.agent.md
Acceptance criteria count: 12
Blocking questions: None
Architecture: docs/architecture/SmartMoneyScore.md
ADR: docs/adr/ADR-009-smart-money-score-state-aware-scoring.md
```
