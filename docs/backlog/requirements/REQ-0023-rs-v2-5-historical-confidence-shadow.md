---
id: REQ-0023
title: R/S V2.5 Historical Reliability & Confident Strength Shadow
status: READY_FOR_DESIGN
priority: P1
owner: BusinessAnalyst
primary_next_owner: SolutionArchitect
related:
  prerequisite_requirement: docs/backlog/requirements/REQ-0022-rs-v2-4-source-effectiveness.md
  architecture:
    - docs/architecture/RS_Ladder.md
    - docs/architecture/RS_Source_Effectiveness.md
  adr: TBD
  implementation: TBD
  test: TBD
  change_request: TBD
---

# REQ-0023 — R/S V2.5 Historical Reliability & Confident Strength Shadow

## Business Objective

Bổ sung một lớp historical confidence cho từng current R/S level để trả lời câu hỏi:

> Current Strength của level hiện tại đáng tin đến đâu khi đối chiếu với historical out-of-sample evidence của chính các source đang tạo hoặc xác nhận level đó?

V2.5 phải tạo được Historical Reliability và Confident Strength ở chế độ shadow/research mà không làm thay đổi hành vi production của R/S Ladder hiện tại.

Mục tiêu của V2.5 là chứng minh bằng dữ liệu rằng việc kết hợp Current Strength với Source Effectiveness có cải thiện độ tin cậy, khả năng phân biệt Hold/Break và độ ổn định OOS hay không trước khi cho phép historical evidence tác động vào production ở V2.6.

## Background / Problem

V2.4 đã cung cấp Source Effectiveness theo ticker/source/horizon và recommendation như CORE, SUPPORTING, CONFIRM_ONLY, CONTEXT_ONLY, RESEARCH, DROP.

Tuy nhiên V2.4 hiện là một luồng một chiều:

```text
build_level_ladder()
    ↓
historical evaluation
    ↓
cal_rs_evaluation_event
    ↓
cal_rs_source_effectiveness
    ↓
vw_RS_Source_Effectiveness
```

Historical Source Effectiveness chưa quay trở lại current R/S level.

Current Strength hiện trả lời:

> Level hiện tại có chất lượng geometry/confluence/recency/touch/confirmation mạnh đến đâu?

Source Effectiveness trả lời:

> Source này historically có đáng tin và có incremental OOS value cho ticker/horizon này hay không?

V2.5 phải nối hai lớp evidence này nhưng vẫn giữ chúng tách biệt về semantics.

## Stakeholders / Consumers

- R/S Engine owner.
- Quant/research workflow.
- Indicator Management workflow.
- Solution Architect.
- Test Engineer.
- CherryStock UI/analytics consumers.
- V2.6 production confidence integration.

## Definitions

### Current Strength

Score runtime 0–100 của current R/S level theo logic hiện hành của `build_level_ladder()`.

Current Strength không phải calibrated probability.

### Historical Reliability

Score 0–100 phản ánh mức độ đáng tin của historical evidence thuộc các source đang đóng góp cho current level, có xét:

- Source Effectiveness;
- OOS marginal contribution;
- temporal stability;
- regime stability;
- evidence/sample sufficiency;
- recommendation;
- source role;
- evidence coverage.

Historical Reliability không được hiểu là forecast probability.

### Evidence Coverage

Tỷ lệ phần evidence/source contribution của current level đã có matching historical Source Effectiveness đủ điều kiện sử dụng.

Missing evidence phải được nhận diện là `UNASSESSED`, không được mặc định thành `DROP` hoặc score 0.

### Confident Strength

Một derived research score 0–100 kết hợp Current Strength với Historical Reliability theo policy/version có kiểm soát.

Trong V2.5, Confident Strength chỉ được chạy ở shadow mode và không được thay thế Current Strength trong production.

### Confidence Adjustment

Chênh lệch có dấu giữa Confident Strength và Current Strength để thể hiện historical evidence đang nâng, giữ nguyên hay hạ confidence.

## Target Outcome

Với mỗi current level và mỗi horizon được hỗ trợ, V2.5 phải có khả năng cung cấp tối thiểu:

```text
Ticker
AsOfDate
LevelRank
LevelType
LevelPrice

CurrentStrength
HorizonBars

HistoricalReliability
EvidenceCoveragePct
AssessedSourceCount
UnassessedSourceCount

PositiveEvidenceSourceCount
ResearchSourceCount
DropSourceCount

ConfidenceAdjustment
ConfidentStrength

DecisionClass
DecisionReason
PolicyVersion
ModelVersion
```

Tên contract/table/view/module cụ thể thuộc Solution Architecture, không được coi là quyết định của requirement này.

## Functional Requirements

1. V2.5 phải tính Historical Reliability cho từng current R/S level dựa trên chính source lineage/context/confirmation đang đóng góp cho level tại thời điểm runtime.

2. Matching historical evidence phải tối thiểu theo:
   - ticker;
   - canonical SourceKey;
   - SourceRole;
   - HorizonBars.

3. V2.5 phải hỗ trợ các horizon hiện hành:
   - H5;
   - H10;
   - H20;
   - H40.

4. Historical Reliability phải được tính riêng theo horizon, không được trộn H5/H10/H20/H40 thành một score duy nhất mà không có policy rõ ràng.

5. V2.5 phải sử dụng latest completed public Source Effectiveness contract thay vì phụ thuộc vào một effectiveness run nội bộ cụ thể.

6. Historical Reliability phải xét tối thiểu các evidence hiện có khi applicable:
   - EffectivenessScore;
   - ValidationMarginalLift;
   - TestMarginalLift;
   - TemporalStability;
   - RegimeStability;
   - ValidationEventCount;
   - TestEventCount;
   - Recommendation;
   - SourceRole.

7. LEVEL, CONTEXT và CONFIRMATION phải được xử lý theo role semantics của V2.4.

8. LEVEL positive evidence phải ưu tiên các recommendation hợp lệ cho LEVEL như CORE/SUPPORTING.

9. CONTEXT positive evidence phải sử dụng role-appropriate recommendation như CONTEXT_ONLY khi policy cho phép.

10. CONFIRMATION positive evidence phải sử dụng role-appropriate recommendation như CONFIRM_ONLY khi policy cho phép.

11. RESEARCH phải được hiểu là chưa đủ confidence, không đồng nghĩa với positive evidence đã được xác nhận.

12. DROP phải được hiểu là negative/unsupported evidence theo policy và phải có khả năng làm giảm reliability/confidence.

13. Missing Source Effectiveness phải trở thành UNASSESSED, không được tự động coi là DROP.

14. V2.5 phải tính Evidence Coverage để ngăn hệ thống overconfident khi chỉ một phần source của current level đã được đánh giá.

15. Historical Reliability phải bị bounded về 0–100.

16. Confident Strength phải bị bounded về 0–100.

17. Historical evidence có thể làm Confident Strength tăng hoặc giảm so với Current Strength.

18. Mức adjustment phải bounded và policy-driven; không được cho một historical component đơn lẻ làm thay đổi Current Strength không giới hạn.

19. Current Strength gốc phải luôn được bảo tồn và truy xuất độc lập.

20. V2.5 phải sinh DecisionClass ở mức research/shadow, tối thiểu hỗ trợ:
   - STRONG;
   - VALID;
   - CAUTION;
   - UNCONFIRMED;
   - REJECT/NEGATIVE_EVIDENCE hoặc semantic tương đương.

21. DecisionClass phải giải thích được bằng DecisionReason/reason codes.

22. V2.5 phải lưu hoặc xuất đủ policy/model/evidence identifiers để một result có thể reproduce và audit.

23. V2.5 phải hỗ trợ historical replay/backtest để so sánh Current Strength với Confident Strength trên cùng snapshot/outcome.

24. V2.5 phải báo cáo riêng hiệu quả trên VALIDATION và TEST/OOS.

25. V2.5 phải đo ít nhất:
   - Hold discrimination;
   - Break discrimination;
   - Brier/calibration metric khi semantics phù hợp;
   - temporal stability;
   - regime stability;
   - coverage;
   - sample size.

26. V2.5 phải cho phép so sánh:
   - Current Strength only;
   - Current Strength + Historical Reliability.

27. V2.5 không được tự động đổi SourceRole, Recommendation hoặc Source Promotion Gate của V2.4.

28. V2.5 không được tự động promote một RESEARCH source thành positive source chỉ vì current level có Strength cao.

29. V2.5 không được tự động loại current level chỉ vì có source UNASSESSED.

30. V2.5 phải có policy versioning để thay đổi weighting/threshold mà vẫn giữ khả năng reproduce historical results.

## Business Rules

1. Current Strength và Historical Reliability là hai concepts khác nhau.

2. Current Strength mô tả current level quality; Historical Reliability mô tả historical evidence quality.

3. Confident Strength là derived confidence score, không phải forecast probability.

4. Historical Reliability chỉ có ý nghĩa khi đi kèm Evidence Coverage.

5. RESEARCH = insufficient confidence; DROP = evidence không ủng hộ hoặc materially negative theo policy.

6. Positive historical evidence phải dựa trên OOS/TEST evidence, không dựa TRAIN-only.

7. Negative TEST lift phải có khả năng giảm Historical Reliability hoặc block positive interpretation.

8. Low TEST sample phải làm giảm evidence confidence; không được làm score trông chắc chắn giả tạo.

9. Missing evidence không phải negative evidence.

10. Một source mạnh ở một horizon không mặc định mạnh ở horizon khác.

11. Một source mạnh ở ticker khác không được dùng để thay thế ticker-specific evidence nếu ticker-specific evidence được yêu cầu.

12. Recommendation là gate/decision output; underlying evidence vẫn phải được giữ để explain.

13. R1/S1 ranking hiện hành dựa trên proximity phải giữ nguyên trong V2.5.

14. V2.5 không được dùng Confident Strength để reorder S1/S2/S3 hoặc R1/R2/R3.

15. V2.5 không được dùng Confident Strength để hide/show production level.

16. V2.5 là shadow mode; production UI/decision behavior hiện hành phải không đổi.

## V2.5 Entry Readiness

V2.5 có thể bắt đầu design/implementation shadow khi:

- V2.4 Source Effectiveness pipeline hoạt động ổn định;
- source identity/canonical SourceKey đã ổn định;
- current level có thể truy ra source lineage/context/confirmation;
- Source Effectiveness có dữ liệu đủ để chạy ít nhất một research comparison.

Nếu target universe/horizon mới chỉ có RESEARCH/DROP, V2.5 vẫn được phép chạy research shadow nhưng kết quả không được dùng như production confidence uplift.

## V2.5 → V2.6 Promotion Gate

V2.6 chỉ được xem xét khi V2.5 chứng minh được trên TEST/OOS rằng historical confidence layer có giá trị thực tế.

Gate phải tối thiểu yêu cầu:

- có meaningful evidence coverage trên current levels;
- có role-appropriate positive recommendations đủ rộng:
  - LEVEL: CORE/SUPPORTING;
  - CONTEXT: CONTEXT_ONLY;
  - CONFIRMATION: CONFIRM_ONLY;
- không phụ thuộc chủ yếu vào RESEARCH sources;
- materially negative DROP evidence không chi phối level confidence;
- aggregate TEST marginal evidence không âm đáng kể;
- temporal stability đạt policy;
- regime stability đạt policy;
- Confident Strength không làm xấu đi materially so với Current Strength trên TEST;
- kết quả đủ sample và reproducible.

Các numeric threshold cụ thể phải là configurable policy và được Solution Architecture + validation xác nhận trước production. Requirement này không hard-code một weight/threshold chưa được empirical validation.

## In Scope

- Historical Reliability per current level.
- Evidence Coverage.
- role-aware evidence aggregation.
- horizon-specific confidence.
- Confidence Adjustment.
- Confident Strength shadow score.
- explainability/reason codes.
- policy/model versioning.
- historical replay/backtest.
- Current Strength vs Confident Strength comparison.
- V2.5→V2.6 promotion evidence package.

## Out of Scope

- thay đổi công thức Current Strength production;
- thay đổi S1/R1 ranking;
- hide/filter current level production;
- auto-deploy;
- tự động thay đổi Indicator Engine configs;
- tự động thay đổi provider/source registry;
- auto-reweight runtime source families;
- gọi Confident Strength là calibrated probability;
- ML black-box optimization chưa có explicit approved requirement;
- thay đổi V2.4 Source Promotion semantics.

## Acceptance Criteria

### AC-01 — Independent Current Strength

Given một current level có Current Strength  \
When V2.5 tính historical confidence  \
Then Current Strength gốc vẫn giữ nguyên và truy xuất độc lập.

### AC-02 — Per-level Historical Reliability

Given current level có source evidence  \
When V2.5 chạy  \
Then Historical Reliability được sinh cho chính level đó.

### AC-03 — Horizon separation

Given cùng một level có H5/H10/H20/H40 evidence  \
When V2.5 tính reliability  \
Then mỗi horizon có result riêng.

### AC-04 — Source lineage matching

Given một source hiện tại của level  \
When historical evidence được lookup  \
Then evidence chỉ match canonical ticker/source/horizon/role phù hợp.

### AC-05 — Missing evidence

Given một current source không có matching Source Effectiveness  \
When reliability được tính  \
Then source là UNASSESSED và không bị coi là DROP.

### AC-06 — Coverage

Given chỉ một phần source có evidence  \
When reliability được tính  \
Then EvidenceCoveragePct phản ánh phần evidence được assess.

### AC-07 — Low coverage protection

Given Evidence Coverage thấp  \
When Confident Strength được tính  \
Then hệ thống không được thể hiện confidence như thể full coverage.

### AC-08 — LEVEL recommendation semantics

Given LEVEL source = CORE/SUPPORTING  \
When reliability được tính  \
Then source có thể đóng góp positive historical evidence theo policy.

### AC-09 — RESEARCH semantics

Given source = RESEARCH  \
When reliability được tính  \
Then source không được coi như confirmed positive evidence.

### AC-10 — DROP semantics

Given source = DROP  \
When reliability được tính  \
Then negative evidence phải visible và có thể làm giảm confidence.

### AC-11 — OOS requirement

Given TRAIN tốt nhưng TEST materially negative  \
When reliability được tính  \
Then historical evidence không được coi là high-confidence positive.

### AC-12 — Sample sufficiency

Given TEST sample không đủ  \
When reliability được tính  \
Then result phải phản ánh low evidence confidence.

### AC-13 — Bounded Historical Reliability

Given bất kỳ valid inputs  \
When Historical Reliability được tính  \
Then score thuộc 0–100.

### AC-14 — Bounded Confident Strength

Given bất kỳ valid Current Strength và reliability  \
When Confident Strength được tính  \
Then score thuộc 0–100.

### AC-15 — Positive adjustment

Given strong, stable, sufficient OOS evidence  \
When confidence adjustment chạy  \
Then Confident Strength có thể cao hơn Current Strength trong bounded policy.

### AC-16 — Negative adjustment

Given materially negative OOS evidence  \
When confidence adjustment chạy  \
Then Confident Strength có thể thấp hơn Current Strength.

### AC-17 — Explainability

Given một confidence result  \
When consumer inspect result  \
Then có reason/evidence summary đủ giải thích adjustment.

### AC-18 — Ranking compatibility

Given S1/S2/S3 và R1/R2/R3 hiện tại  \
When V2.5 chạy  \
Then rank order production không đổi.

### AC-19 — UI/runtime compatibility

Given V2.5 được enable shadow  \
When user mở R/S tab  \
Then existing production level/Strength behavior không bị thay đổi trừ khi UI research field được explicitly enabled.

### AC-20 — Historical comparison

Given historical snapshots có outcomes  \
When V2.5 backtest  \
Then Current Strength và Confident Strength được so sánh trên cùng evaluation population.

### AC-21 — TEST comparison

Given VALIDATION và TEST splits  \
When model comparison hoàn tất  \
Then TEST result được báo riêng và không bị gộp với TRAIN.

### AC-22 — Stability comparison

Given nhiều time/regime segments  \
When backtest hoàn tất  \
Then temporal/regime stability của confidence layer được báo cáo.

### AC-23 — Reproducibility

Given cùng dataset, model version, policy version và evidence inputs  \
When rerun  \
Then V2.5 outputs deterministic.

### AC-24 — No production promotion

Given Confident Strength tốt trên research run  \
When V2.5 hoàn tất  \
Then production behavior không tự thay đổi; V2.6 vẫn cần separate approval/release.

## Non-functional Requirements

- Performance:
  - ưu tiên reuse V2.4 public effectiveness output;
  - tránh full historical recomputation khi compatible evidence đã tồn tại;
  - shadow computation phải có thể chạy batch cho monthly evaluation.

- Reliability:
  - fail clearly khi evidence contract incompatible;
  - không silent fallback từ ticker-specific sang unrelated global evidence;
  - không silent fallback từ TEST sang TRAIN-only.

- Explainability:
  - result phải trace được current source → source evidence → aggregate confidence → adjustment.

- Observability:
  - ghi model/policy/evidence version;
  - summary phải hiển thị coverage, insufficient sample và negative evidence.

- Compatibility:
  - V2.4 Source Effectiveness giữ nguyên;
  - current R/S production behavior giữ nguyên trong V2.5 shadow.

## Dependencies

- REQ-0022 / R/S V2.4 Source Effectiveness.
- `vw_RS_Source_Effectiveness`.
- current R/S level source lineage/context/confirmation.
- V2.3/V2.4 historical evaluation events and OOS splits.
- stable canonical SourceKey/SourceRole contracts.

## Constraints

- GitHub Markdown là engineering SSOT.
- Requirement chỉ định WHAT/WHY; architecture quyết định HOW.
- Không hard-code confidence formula hoặc weights trước empirical validation.
- Không dùng future data trong historical replay.
- Không đổi production runtime behavior trong V2.5.

## Assumptions

- V2.4 recommendations và Source Promotion Gate tiếp tục là authoritative historical source governance.
- H5/H10/H20/H40 tiếp tục là future trading bars.
- Current Strength tiếp tục không phải calibrated probability.
- Missing Source Effectiveness có thể xảy ra và phải được xử lý như UNASSESSED.

## Open Questions

Không có blocking question cho architecture design.

Solution Architecture phải quyết định và document:
- exact aggregation formula;
- source contribution weighting;
- evidence-coverage penalty;
- adjustment bounds;
- DecisionClass thresholds;
- persistence/read contract;
- shadow execution path.

Các quyết định trên phải được validate empirically trước V2.6.

## Risks

- sparse TEST sample làm reliability không ổn định;
- coverage thấp tạo false confidence nếu không penalize;
- correlated sources bị double count;
- cùng source khác horizon có behavior trái chiều;
- ticker-specific evidence không đủ rộng;
- recommendation-only aggregation làm mất thông tin underlying evidence;
- overfitting weight/threshold trên VALIDATION;
- người dùng hiểu nhầm Confident Strength là probability.

## Suggested Routing

- Architecture required: Yes
- Primary next owner: SolutionArchitect
- Validation owner: TestEngineer
- Related domain instructions:
  - indicators.instructions.md
  - database.instructions.md
  - testing.instructions.md

## Handoff

```text
REQUIREMENT HANDOFF
Requirement ID: REQ-0023
Outcome: Define R/S V2.5 Historical Reliability & Confident Strength Shadow
Status: READY_FOR_DESIGN
Primary next owner: SolutionArchitect
Material: docs/backlog/requirements/REQ-0023-rs-v2-5-historical-confidence-shadow.md
Open questions: None blocking; technical policy parameters require design + empirical validation
Acceptance criteria count: 24
```
