---
id: REQ-0024
title: R/S V2.6 Production Confidence Integration
status: READY_FOR_DESIGN
priority: P1
owner: BusinessAnalyst
primary_next_owner: SolutionArchitect
related:
  prerequisite_requirement:
    - docs/backlog/requirements/REQ-0022-rs-v2-4-source-effectiveness.md
    - docs/backlog/requirements/REQ-0023-rs-v2-5-historical-confidence-shadow.md
  architecture:
    - docs/architecture/RS_Ladder.md
    - docs/architecture/RS_Source_Effectiveness.md
  adr: TBD
  implementation: TBD
  test: TBD
  change_request: TBD
---

# REQ-0024 — R/S V2.6 Production Confidence Integration

## Business Objective

Đưa historical confidence đã được chứng minh ở V2.5 vào production R/S experience theo cách bounded, explainable, reversible và không làm mất semantics của Current Strength.

V2.6 phải giúp người dùng phân biệt rõ:

```text
Current Strength
= level hiện tại mạnh đến đâu theo runtime evidence

Historical Reliability
= source lineage historically đáng tin đến đâu

Confident Strength
= confidence cuối cùng sau khi historical evidence đã điều chỉnh Current Strength
```

Production integration chỉ được thực hiện sau khi V2.5 vượt qua promotion gate trên TEST/OOS.

## Background / Problem

V2.5 chạy Historical Reliability và Confident Strength ở shadow mode để xác minh historical source evidence có thực sự cải thiện confidence quality hay không.

Một research score không được phép tự động trở thành production score chỉ vì có vẻ hợp lý trên một số examples.

V2.6 cần một contract production rõ ràng để:

- chỉ sử dụng evidence đủ mạnh;
- không overreact với RESEARCH/UNASSESSED evidence;
- preserve raw Current Strength;
- giữ R1/S1 semantics;
- giải thích được vì sao confidence tăng/giảm;
- rollback được nếu production monitoring xấu đi;
- version được policy để audit/reproduce.

## Preconditions / Release Gate

V2.6 ở trạng thái BLOCKED_FOR_PRODUCTION cho đến khi V2.5 evidence package chứng minh các điều kiện tối thiểu sau:

1. Historical confidence layer có sufficient Evidence Coverage trên target scope.

2. Positive evidence được hỗ trợ bởi role-appropriate recommendation:
   - LEVEL: CORE/SUPPORTING;
   - CONTEXT: CONTEXT_ONLY;
   - CONFIRMATION: CONFIRM_ONLY.

3. RESEARCH không chiếm phần lớn evidence weight dùng để tăng confidence.

4. DROP/materially negative evidence được phản ánh và không bị che bởi aggregate average.

5. TEST/OOS comparison không materially worse so với Current Strength baseline.

6. Aggregate TEST marginal evidence không âm đáng kể theo approved policy.

7. Temporal Stability đạt approved policy.

8. Regime Stability đạt approved policy.

9. Sample size đạt approved sufficiency policy.

10. V2.5 result deterministic/reproducible.

11. Solution Architecture, Test Engineer và release owner có explicit approval evidence.

Numeric thresholds phải versioned/configurable và được xác nhận từ V2.5 evidence; không được hard-code chỉ từ heuristic.

## Target Production Outcome

Với mỗi production current R/S level, consumer có thể đọc tối thiểu:

```text
Ticker
AsOfDate
LevelRank
LevelType
LevelPrice

CurrentStrength

SelectedHorizon / HorizonBars
HistoricalReliability
EvidenceCoveragePct

ConfidenceAdjustment
ConfidentStrength

DecisionClass
DecisionReason

ConfidencePolicyVersion
RSModelVersion
EvidenceAsOf
```

Current Strength phải vẫn tồn tại như raw runtime score.

## Functional Requirements

1. V2.6 phải consume V2.5-approved Historical Reliability logic/policy; không được tạo một production formula khác chưa qua shadow validation.

2. V2.6 phải preserve Current Strength như một field/contract độc lập.

3. V2.6 phải expose Historical Reliability riêng khỏi Current Strength.

4. V2.6 phải expose Evidence Coverage cùng Historical Reliability.

5. V2.6 phải expose Confidence Adjustment để người dùng biết historical evidence nâng hay hạ confidence.

6. V2.6 phải expose Confident Strength bounded 0–100.

7. Confident Strength phải sử dụng explicit selected horizon hoặc horizon context; không được silently mix H5/H10/H20/H40.

8. Nếu consumer chỉ hiển thị một Confident Strength, horizon được dùng phải visible/configured.

9. Nếu historical evidence không đủ coverage/sufficiency, production output phải degrade gracefully về trạng thái UNCONFIRMED hoặc equivalent thay vì fabricate high confidence.

10. UNASSESSED source không được tự động làm level bị DROP.

11. RESEARCH evidence không được dùng như confirmed positive uplift trừ khi explicit policy đã được validate và approved.

12. DROP/materially negative evidence phải có khả năng giảm Confident Strength hoặc DecisionClass.

13. Positive evidence chỉ được tăng confidence trong bounded policy.

14. Negative evidence chỉ được giảm confidence trong bounded policy; behavior phải explainable.

15. V2.6 phải cung cấp DecisionClass production tối thiểu:
    - STRONG;
    - VALID;
    - CAUTION;
    - UNCONFIRMED;
    - REJECT/NEGATIVE_EVIDENCE hoặc semantic tương đương.

16. DecisionClass phải có reason codes hoặc evidence summary.

17. V2.6 không được thay đổi SourceRole hoặc Recommendation của V2.4.

18. V2.6 không được tự động thay đổi Indicator Engine metadata/config activation.

19. V2.6 không được tự động thay đổi provider/source registry ngoài approved release scope.

20. V2.6 phải hỗ trợ feature toggle/rollback hoặc equivalent release control để tắt confidence integration mà không phá Current Strength baseline.

21. V2.6 phải persist hoặc expose policy/model/evidence version để result reproducible.

22. V2.6 phải hỗ trợ production monitoring so sánh Confident Strength với observed outcomes.

23. V2.6 phải hỗ trợ drift monitoring theo time/regime/coverage.

24. V2.6 phải giữ historical and production evaluation point-in-time safe.

25. V2.6 phải có deterministic fallback khi historical confidence service/data unavailable.

26. Fallback không được tự thay đổi current R/S geometry/ranking.

27. V2.6 production consumers phải có khả năng hiển thị raw và adjusted score đồng thời trong giai đoạn rollout.

28. V2.6 phải hỗ trợ phased rollout trước khi trở thành default presentation/decision score.

## Business Rules

1. Confident Strength không thay thế ý nghĩa của Current Strength; nó là confidence-adjusted score.

2. Current Strength phải luôn visible/auditable trong data contract kể cả khi UI chọn ưu tiên Confident Strength.

3. Historical Reliability không phải probability.

4. Confident Strength không được gọi là probability nếu chưa có separate calibrated probability requirement/model.

5. Positive confidence uplift phải có OOS evidence.

6. CORE/SUPPORTING chỉ áp dụng positive LEVEL evidence; role-specific sources dùng CONFIRM_ONLY/CONTEXT_ONLY theo V2.4 semantics.

7. RESEARCH = chưa đủ chắc chắn, không phải positive production endorsement.

8. DROP = evidence không ủng hộ/materially negative và phải ảnh hưởng risk/confidence policy.

9. UNASSESSED = thiếu evidence, không phải DROP.

10. Evidence Coverage phải được xem cùng Historical Reliability.

11. R1/S1 tiếp tục biểu diễn nearest resistance/support theo runtime ladder hiện hành.

12. Confident Strength không được reorder R1/R2/R3 hoặc S1/S2/S3 trong V2.6 trừ khi có separate approved requirement/ADR.

13. V2.6 không được hide current level chỉ dựa trên low confidence nếu chưa có separate approved filtering policy.

14. V2.6 production behavior phải versioned.

15. Rollback phải quay được về Current Strength-only behavior.

## In Scope

- production exposure of Historical Reliability;
- production Confident Strength;
- selected-horizon semantics;
- Evidence Coverage;
- bounded confidence adjustment;
- production DecisionClass/reasons;
- feature toggle/rollback;
- policy/model/evidence versioning;
- phased rollout;
- production monitoring;
- TEST/OOS release gate;
- documentation and runbook for interpreting scores.

## Out of Scope

- changing R1/S1 ranking semantics;
- automatic level deletion/filtering without separate requirement;
- automatic Indicator Engine activation/deactivation;
- auto-deploy from V2.4 Source Promotion Gate;
- black-box ML replacement of R/S Ladder;
- current price direction forecast;
- calibrated Hold/Break probability unless separately designed and validated;
- intraday R/S unless separately approved.

## Acceptance Criteria

### AC-01 — Production gate enforced

Given V2.5 has not passed approved TEST/OOS gate  \
When V2.6 release is requested  \
Then production confidence integration remains blocked.

### AC-02 — Raw Strength preserved

Given V2.6 production integration is enabled  \
When a current level is returned  \
Then Current Strength remains available unchanged as raw runtime score.

### AC-03 — Historical Reliability exposed

Given sufficient matching evidence  \
When a current level is returned  \
Then Historical Reliability is available separately.

### AC-04 — Evidence Coverage exposed

Given current level source evidence  \
When confidence is returned  \
Then EvidenceCoveragePct is available and interpretable.

### AC-05 — Confident Strength bounded

Given valid production inputs  \
When Confident Strength is produced  \
Then result is 0–100.

### AC-06 — Explicit horizon

Given confidence is produced  \
When consumer reads result  \
Then the horizon used is explicit.

### AC-07 — No silent horizon mixing

Given H5/H10/H20/H40 differ  \
When a production score is selected  \
Then system does not silently average them without an approved policy.

### AC-08 — Positive evidence uplift

Given sufficient CORE/SUPPORTING or role-appropriate approved evidence and positive OOS behavior  \
When confidence is produced  \
Then bounded positive adjustment is permitted.

### AC-09 — Negative evidence reduction

Given materially negative/DROP evidence  \
When confidence is produced  \
Then bounded negative adjustment is permitted and explained.

### AC-10 — RESEARCH protection

Given evidence is predominantly RESEARCH  \
When production confidence is produced  \
Then system does not present high-confidence positive uplift as confirmed.

### AC-11 — UNASSESSED protection

Given some source evidence is missing  \
When production confidence is produced  \
Then missing evidence is UNASSESSED and does not become DROP.

### AC-12 — Low coverage behavior

Given coverage below approved sufficiency policy  \
When result is returned  \
Then DecisionClass is degraded to UNCONFIRMED/CAUTION or equivalent.

### AC-13 — Explainable adjustment

Given Confident Strength differs from Current Strength  \
When consumer inspects result  \
Then reason codes/evidence summary explain the change.

### AC-14 — Rank compatibility

Given current R/S ladder  \
When V2.6 confidence integration is enabled  \
Then R1/S1 proximity ranking remains unchanged.

### AC-15 — No automatic filtering

Given a low Confident Strength  \
When R/S levels are rendered  \
Then level is not automatically hidden solely for that reason without separate approved policy.

### AC-16 — Runtime fallback

Given historical confidence data/service is unavailable  \
When current R/S is requested  \
Then fallback returns Current Strength-only behavior deterministically.

### AC-17 — Feature rollback

Given confidence integration causes issue  \
When release control disables it  \
Then production returns to Current Strength-only behavior without requiring data rollback.

### AC-18 — Version traceability

Given any production Confident Strength  \
When audited  \
Then model, confidence policy and evidence version/as-of are identifiable.

### AC-19 — Point-in-time safety

Given historical replay or monitoring  \
When confidence is evaluated for a past snapshot  \
Then no future evidence relative to that snapshot leaks into the result.

### AC-20 — Phased rollout

Given V2.6 is first deployed  \
When rollout begins  \
Then raw and adjusted scores can be observed together before adjusted score becomes default.

### AC-21 — Production monitoring

Given V2.6 is active  \
When new observed outcomes arrive  \
Then monitoring can compare confidence quality with baseline Current Strength.

### AC-22 — Drift visibility

Given temporal/regime performance changes  \
When monitoring detects degradation  \
Then drift is visible for review and can trigger rollback/research.

### AC-23 — No false probability claim

Given Confident Strength = 80  \
When displayed/documented  \
Then it is not described as “80% probability of hold” unless a separately calibrated probability model exists.

### AC-24 — No Indicator Engine mutation

Given V2.6 confidence integration is enabled  \
When it runs  \
Then no indicator config is activated/deactivated automatically.

### AC-25 — Reproducibility

Given same point-in-time dataset, source evidence, model version and policy version  \
When rerun  \
Then production confidence result is deterministic.

## Non-functional Requirements

- Performance:
  - confidence enrichment phải có bounded latency;
  - không được buộc full historical evaluation trên mỗi UI request;
  - reuse persisted/latest approved evidence.

- Reliability:
  - deterministic fallback;
  - explicit handling of stale/missing evidence;
  - no silent TRAIN-only substitution.

- Observability:
  - monitor coverage, adjustment distribution, DecisionClass distribution;
  - monitor TEST/live outcome performance;
  - monitor drift by time/regime/horizon.

- Explainability:
  - trace Current Strength → source evidence → Historical Reliability → adjustment → Confident Strength.

- Compatibility:
  - rollback được về V2.4/V2.5 Current Strength-only runtime contract;
  - no ranking change unless separately approved.

## Dependencies

- REQ-0022 completed and operational.
- REQ-0023 implemented and independently validated.
- V2.5 promotion evidence package.
- Approved Solution Architecture/ADR for production confidence integration.
- Test Engineer PASS on regression + OOS comparison.
- Release/change request approval.

## Constraints

- GitHub Markdown là engineering SSOT.
- Production behavior change phải có explicit Change Request.
- Numeric weights/thresholds phải versioned and validated.
- No future-data leakage.
- No destructive mutation of V2.4 evidence history.

## Assumptions

- V2.5 demonstrates measurable value before V2.6 is enabled.
- V2.4 recommendations remain the source-governance semantics.
- Existing Current Strength remains available as baseline/fallback.
- R1/S1 ranking remains proximity-based.

## Open Questions

Không có blocking question cho design.

Solution Architecture phải chốt:
- production read contract;
- approved horizon selection behavior;
- confidence adjustment formula/versioning;
- fallback path;
- rollout toggle;
- monitoring thresholds;
- persistence/audit strategy.

Các quyết định phải reference V2.5 empirical evidence.

## Risks

- treating confidence score as probability;
- overfitting adjustment weights;
- low coverage on some tickers/horizons;
- stale Source Effectiveness;
- correlated-source double counting;
- production drift by regime;
- UI users ignoring raw Current Strength;
- excessive confidence suppression from sparse evidence;
- accidental ranking/filtering behavior changes.

## Suggested Routing

- Architecture required: Yes
- Primary next owner: SolutionArchitect
- Validation owner: TestEngineer
- Release owner: CherryStock owner
- Related domain instructions:
  - indicators.instructions.md
  - database.instructions.md
  - testing.instructions.md

## Handoff

```text
REQUIREMENT HANDOFF
Requirement ID: REQ-0024
Outcome: Define R/S V2.6 Production Confidence Integration
Status: READY_FOR_DESIGN
Primary next owner: SolutionArchitect
Material: docs/backlog/requirements/REQ-0024-rs-v2-6-production-confidence-integration.md
Open questions: None blocking; production policy must be derived from V2.5 evidence
Acceptance criteria count: 25
```
