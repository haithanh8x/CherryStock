# R/S V2.4 — Kiến trúc Source Effectiveness & Indicator Promotion

- **Requirement:** REQ-0022
- **Status:** APPROVED_FOR_IMPLEMENTATION
- **Date:** 2026-09-02
- **Primary owner:** SolutionArchitect
- **Affected domains:** R/S Engine, Historical Evaluation, DuckDB, Indicator Governance, Testing

---

## 1. Bối cảnh

R/S V2.3 đã cung cấp historical events, chronological TRAIN/VALIDATION/TEST, regime metrics, cross-ticker evaluation, ablation primitives, model versioning, model Promotion Gate và golden benchmark.

V2.4 tập trung trả lời câu hỏi cụ thể hơn:

> Với một ticker và một source/config cụ thể, source đó có tạo thêm giá trị dự báo Out-of-Sample sau khi đã kiểm soát theo current model hay không, và mức bằng chứng đó có đủ mạnh để phê duyệt cho việc tích hợp R/S trong tương lai hay không?

`Runtime Strength` = mức độ tin cậy/chất lượng của một vùng R/S hiện tại

`Source Effectiveness` = bằng chứng lịch sử cho thấy một source/config có tạo thêm predictive value, tăng mức độ tin cậy cho một ticker/horizon sau khi đã kiểm soát theo current model

## 2. Kiến trúc tổng thể

```text
R/S Runtime Providers
      │
      ▼
Source Identity Contract
      │
      ├──────────────┐
      ▼              ▼
V2.3 Baseline     V2.3 Ablation
      │              │
      └──────┬───────┘
             ▼
 Source Effectiveness Engine
             │
   ┌─────────┼───────────┐
   ▼         ▼           ▼
 LEVEL    CONTEXT     CONFIRMATION
 lineage  marginal      marginal
   │         │           │
   └─────────┼───────────┘
             ▼
 Per-Ticker Effectiveness
             │
     ┌───────┴────────┐
     ▼                ▼
Recommendation   Source Promotion Gate
     │                │
     └───────┬────────┘
             ▼
       DuckDB Persistence
             │
             ▼
vw_RS_Source_Effectiveness
```

V2.4 tuyệt đối không tự động thay đổi runtime registration, runtime weights hay Indicator Engine metadata.

- ### `V2.3 Baseline` & `V2.3 Ablation` 
là hai phiên bản model được chạy song song để đo xem một source có thực sự đóng góp giá trị hay không.

V2.3 Baseline = model đầy đủ, có source đang đánh giá

V2.3 Ablation = model gần như giống hệt Baseline nhưng bỏ source đó ra

Ví dụ đánh giá MA50_D: 

- Baseline có = (MA20_D, MA50_D, SWING_HIGH, VP_POC, RSI14_D)

- Ablation không có MA50_D =  (MA20_D, SWING_HIGH, VP_POC, RSI14_D)

Tính toán `Baseline TestQuality` = 0.72 và `Ablation TestQuality` = 0.69 thì `TestMarginalLift` = Baseline - Ablation = 0.72 - 0.69 = `+0.03` có nghĩa MA50_D thì model tốt hơn khoảng 0.03 quality unit trên TEST

Nếu ngược lại: Baseline = 0.70 và Ablation = 0.73 thì TestMarginalLift = `-0.03`, Bỏ MA50_D ra thì model còn tốt hơn. MA50_D có thể đang làm model kém đi

Với `SOURCE_FAMILY` thì Ablation rộng hơn. Ví dụ đánh giá TREND_AVERAGE: 
- Baseline = có MA20_D + MA50_D + MA100_D + MA200_D
- Family Ablation = bỏ toàn bộ TREND_AVERAGE

`LEVEL` = "Source này tạo ra level tốt không?"

`CONTEXT` = "Nếu bỏ context này, geometry/quality model có xấu đi không?"

`CONFIRMATION` = "Nếu bỏ confirmation này, Strength còn dự báo tốt không?"

- ### `Recommendation` 
là quyết định ở từng row cụ thể của `vw_RS_Source_Effectiveness`, tức theo grain: `Ticker / SourceKey / HorizonBars` với các value CORE / SUPPORTING / CONFIRM_ONLY / CONTEXT_ONLY / RESEARCH / DROP ví dụ `MWG / MA50_D / H20` 

```text
EffectivenessScore  = 78 
TestMarginalLift    = +0.022 
Recommendation      = CORE
```

```sql
SELECT
    "Ticker",
    "SourceKey",
    "HorizonBars",
    "EffectivenessScore",
    "Recommendation"
FROM "CherryMon"."main"."vw_RS_Source_Effectiveness"
WHERE 1=1
ORDER BY
    "Ticker",
    "SourceKey",
    "HorizonBars";
```

- ### `Source Promotion Gate` 
là quyết định ở cấp cross-ticker / governance Source này có đủ tốt trên nhiều ticker và đủ ổn định để được phê duyệt cho bước tích hợp tiếp theo hay chưa?

Ví dụ MA50_D có MWG  → CORE ; FPT  → SUPPORTING ; HPG  → CORE ; VIC  → RESEARCH ; SSI  → SUPPORTING sau đó Source Promotion Gate aggregate các evidence này và kiểm tra policy rồi mới ra một outcome APPROVED_FOR_INTEGRATION / TICKER_SELECTIVE / RESEARCH  / REJECTED

```sql
SELECT
    "SourceKey",
    "SourceFamily",
    "SourceRole",
    "HorizonBars",
    "Outcome",
    "TickerCount",
    "PositiveTickerCount",
    ROUND("PositiveTickerRatio" * 100, 2) AS "PositiveTickerRatioPct",
    ROUND("AvgEffectivenessScore", 2) AS "AvgEffectivenessScore",
    ROUND("AvgValidationLift", 4) AS "AvgValidationLift",
    ROUND("AvgTestLift", 4) AS "AvgTestLift",
    ROUND("AvgTemporalStability", 4) AS "AvgTemporalStability",
    ROUND("AvgRegimeStability", 4) AS "AvgRegimeStability",
    ROUND("MaxComplexityDelta", 4) AS "MaxComplexityDelta",
    "Applied",
    "DecidedAt",
    "ReasonsJson"
FROM "CherryMon"."main"."sys_rs_source_promotion_audit"
ORDER BY
    "SourceKey",
    "HorizonBars",
    "DecidedAt" DESC;
```

## 3. Stable Source Identity


Module thuần mới:

```text
src/calcEngine/rsSourceIdentity.py
```

Ví dụ:

```text
MA50_D                 → MA50_D
BB20_2_D:LOWER         → BB20_2_D:LOWER
RSI14_D                → RSI14_D
ATR14_D                → ATR14_D
SWING_HIGH_20260820    → SWING_HIGH
SWING_LOW_20260818     → SWING_LOW
VP_POC                 → VP_POC
VP_HVN_01              → VP_HVN
VP_LVN_01              → VP_LVN
VP_HVN_01_CONF         → VP_HVN
```

Các source code không rỗng nhưng chưa biết trước sẽ được normalize thành uppercase exact code. Blank source code phải fail rõ ràng.

## 4. Research Source Filters

`build_level_ladder()` bổ sung các research filters tùy chọn nhưng vẫn backward-compatible:

```python
included_source_keys=None
excluded_source_keys=None
```

Quy tắc:

- mặc định phải giữ nguyên behavior của V2.3 runtime;
- include/exclude sử dụng canonical source identity;
- cùng cơ chế filtering áp dụng cho LEVEL candidates, CONTEXT contexts và CONFIRMATION contexts;
- include set và exclude set không được overlap;
- đây là research/evaluation controls, không phải production source switch.

Ví dụ:

```python
# cô lập MA50_D bên trong MA provider
enabled_sources=("MA",)
included_source_keys=("MA50_D",)

# full model nhưng bỏ MA50_D
excluded_source_keys=("MA50_D",)

# chỉ bỏ RSI14_D confirmation
excluded_source_keys=("RSI14_D",)
```

## 5. Mở rộng khả năng tái lập V2.3 Evaluation

`RSModelSpec` và `cal_rs_evaluation_run` lưu include/exclude source keys để source-config research tạo ra một deterministic model signature riêng biệt.

Các column được bổ sung:

```text
cal_rs_evaluation_run
+ IncludeSourceKeysJson
+ ExcludeSourceKeysJson
```

## 6. Source Effectiveness Engine

Module mới:

```text
src/calcEngine/rsSourceEffectiveness.py
```

Các contract chính:

```text
SourceEffectivenessPolicy
SourceEffectivenessRecord
SourcePromotionPolicy
SourcePromotionDecision
```

Các scope được hỗ trợ:

```text
SOURCE_CONFIG
SOURCE_FAMILY
```

Các attribution mode được hỗ trợ:

```text
LEVEL_LINEAGE
MARGINAL_ONLY
FAMILY_ABLATION
```

### SOURCE_CONFIG và SOURCE_FAMILY khác nhau như thế nào?

`SOURCE_CONFIG` dùng để đánh giá một source/config cụ thể.

Ví dụ:

```text
MA20_D
MA50_D
MA100_D
BB20_2_D:LOWER
RSI14_D
VP_POC
```

Câu hỏi cần trả lời:

> Source cụ thể này có tạo ra giá trị lịch sử cho R/S hay không?

`SOURCE_FAMILY` dùng để đánh giá cả một nhóm source có cùng vai trò/ngữ nghĩa.

Ví dụ:

```text
TREND_AVERAGE
VOLATILITY_BAND
MARKET_STRUCTURE
VOLUME_STRUCTURE
```

Câu hỏi cần trả lời:

> Nếu bỏ toàn bộ family này khỏi R/S model thì model tốt lên hay xấu đi?

Một family có thể bao gồm nhiều source/config. Vì vậy:

```text
SOURCE_CONFIG
    = đánh giá từng source riêng lẻ

SOURCE_FAMILY
    = đánh giá cả nhóm source cùng lúc
```

## 7. Công thức LEVEL Effectiveness

Các source có `SourceRole = LEVEL` sử dụng direct historical event lineage kết hợp với marginal lift giữa baseline và ablation.

Các positive component mặc định:

```text
Hold Rate                25%
Touch Rate               15%
Retest Rate              10%
Directional Edge         20%
Temporal Stability       10%
Regime Stability         10%
Marginal Contribution    10%
                         ----
                         100%
```

Các penalty:

```text
Break Penalty
Complexity Penalty
```

Chuẩn hóa Directional Edge:

```text
DirectionalEdgeScore
= clamp(0.5 + DirectionalEdgePct / 20, 0, 1)
```

Chuẩn hóa Marginal Contribution:

```text
MeanOOSLift = (ValidationLift + TestLift) / 2
MarginalScore = clamp(0.5 + MeanOOSLift / 0.05, 0, 1)
```

## 8. CONTEXT / CONFIRMATION Effectiveness

`CONTEXT` và `CONFIRMATION` không phải price level, vì vậy không được tạo giả các metric Touch/Hold/Retest.

Marginal metric phụ thuộc vào SourceRole:

```text
CONTEXT
    → LEVEL_QUALITY lift
      vì context có thể thay đổi clustering / neutral-zone geometry

CONFIRMATION
    → STRENGTH_BRIER lift
      vì confirmation có thể thay đổi Strength
      mà không thay đổi geometry của S1/R1
```

`STRENGTH_BRIER` sử dụng các touched events và đánh giá xem `Strength / 100` dự báo khả năng touched level giữ được tốt đến đâu.

Điều này ngăn một confirmation-only indicator như RSI bị đánh giá sai là không có giá trị chỉ vì level price/rank không thay đổi.

Công thức role-aware marginal-only score:

```text
Validation Lift Score    35%
Test Lift Score          35%
Temporal Stability       15%
Regime Stability         15%
                         ----
                         100%
```

Recommendation vẫn phải giữ đúng SourceRole:

```text
CONTEXT       → CONTEXT_ONLY / RESEARCH / DROP
CONFIRMATION  → CONFIRM_ONLY / RESEARCH / DROP
```

## 9. Temporal Stability và Regime Stability

Với `LEVEL`:

```text
TemporalStability
= 1 - clamp(abs(ValidationQuality - TestQuality) / 0.10, 0, 1)
```

Với marginal-only:

```text
TemporalStability
= 1 - clamp(abs(ValidationLift - TestLift) / 0.05, 0, 1)
```

Regime Stability:

```text
RegimeRange = max(RegimeQualityOrLift) - min(RegimeQualityOrLift)

RegimeStability
= 1 - clamp(RegimeRange / 0.20, 0, 1)
```

Nếu có ít hơn hai usable regimes, `RegimeStability = NULL` và score được re-normalize trên phần evidence có sẵn. Promotion breadth checks vẫn được đánh giá riêng.

## 10. Recommendation Contract

Mặc định cho `LEVEL`:

```text
CORE
  score >= 75
  validation lift >= +0.01
  test lift >= 0
  sufficient OOS samples

SUPPORTING
  score >= 65
  test lift >= 0

RESEARCH
  score >= 55 hoặc insufficient breadth/sample

DROP
  score < 55 hoặc materially negative TEST lift
```

`CONFIRMATION` và `CONTEXT` sử dụng recommendation đúng role là `CONFIRM_ONLY` / `CONTEXT_ONLY`, thay vì bị chuyển thành LEVEL source.

## 11. Source Promotion Gate

Promotion là governance ở cấp cross-ticker. Nó không giống với Recommendation của một row per-ticker.

Default policy:

```text
min_tickers                 = 3
min_positive_ticker_ratio   = 0.60
min_effectiveness_score     = 65
min_validation_lift         = +0.01
min_test_lift               = 0.00
min_temporal_stability      = 0.70
min_regime_stability        = 0.60
max_complexity_delta        = 0.15
max_negative_test_lift      = -0.01
```

Các outcome:

```text
APPROVED_FOR_INTEGRATION
TICKER_SELECTIVE
RESEARCH
REJECTED
```

Ngay cả khi có explicit apply action, V2.4 chỉ ghi governance/audit metadata.

V2.4 không được tự động thay đổi:

```text
Indicator dimensions/configs
provider registry
runtime source set
Strength weights
production deployment
```

Các thay đổi concrete indicator lifecycle vẫn thuộc ownership của Indicator Management.

## 12. Persistence Model

V2.4 bổ sung:

```text
cal_rs_source_effectiveness_run
cal_rs_source_effectiveness
sys_rs_source_promotion_audit
vw_RS_Source_Effectiveness
```

Grain của `cal_rs_source_effectiveness_run`:

```text
EffectivenessRunId
```

Grain của `cal_rs_source_effectiveness`:

```text
EffectivenessRunId / Ticker / ScopeType / SourceKey / HorizonBars
```

Các result field bao gồm attribution mode, OOS samples, LEVEL metrics khi áp dụng được, validation/test quality, marginal lifts, temporal/regime stability, complexity delta, score, recommendation và evidence JSON.

`sys_rs_source_promotion_audit` lưu decision evidence/policy/reasons nhưng không bao giờ là hot runtime configuration switch.

## 13. Public Read SSOT

Public contract để đọc latest Source Effectiveness:

```text
vw_RS_Source_Effectiveness
```

View chỉ expose row `COMPLETED` mới nhất theo grain:

```text
Ticker / ScopeType / SourceKey / HorizonBars
```

Consumer nên đọc view này thay vì đọc trực tiếp các internal `cal_*` tables.

## 14. Multi-Horizon Strategy

Canonical research horizons hiện tại:

```text
5, 10, 20, 40 trading bars
```

Mỗi horizon giữ evidence baseline/ablation/effectiveness riêng.

V2.4 không tự động average các horizon thành runtime weight.

## 14.1 Historical Evaluation thực sự hoạt động như thế nào?

Historical evaluation không phải daily live prediction loop. Đây là point-in-time backtest trên các historical snapshot được chọn.

Luồng chuẩn:

```text
historical trading dates
        ↓
chọn snapshot dates theo snapshot_step
        ↓
build R/S ladder chỉ bằng dữ liệu có tại snapshot đó
        ↓
quan sát future market bars theo H5 / H10 / H20 / H40
        ↓
label historical outcomes
        ↓
aggregate hàng nghìn events
        ↓
tính historical rates / quality / source effectiveness
```

### Snapshot cadence

Với:

```text
snapshot_step = 5
```

evaluator không rebuild ladder ở mọi trading date.

Ví dụ khái niệm:

```text
D1
D2
D3
D4
D5
D6
D7
...

sampled snapshots:

D1
D6
D11
D16
...
```

Warm-up filtering được áp dụng sau bước sampling.

Nếu một sampled date chưa có đủ point-in-time history cho một enabled provider, sampled date đó bị skip; cadence không bị re-base.

### Ý nghĩa H5 / H10 / H20 / H40

```text
H5  = đánh giá 5 market trading bars tiếp theo
H10 = đánh giá 10 market trading bars tiếp theo
H20 = đánh giá 20 market trading bars tiếp theo
H40 = đánh giá 40 market trading bars tiếp theo
```

Đây là trading bars, không phải calendar days.

Có thể hiểu gần đúng:

```text
H5  ≈ very short term
H10 ≈ short term
H20 ≈ khoảng 1 tháng giao dịch
H40 ≈ khoảng 2 tháng giao dịch
```

Các horizon không phải bốn model R/S khác nhau.

Đây là bốn future observation window áp dụng cho cùng một point-in-time R/S signal.

### Ví dụ

Giả sử historical snapshot:

```text
Ticker       MWG
Snapshot     2026-05-04
CurrentPrice 58
S1           55
R1           62
```

R/S Ladder chỉ được tính bằng dữ liệu có sẵn đến ngày 2026-05-04.

Với H20, evaluator quan sát 20 trading bars tiếp theo và trả lời các câu hỏi:

```text
Giá có Touch S1/R1 không?
Nếu Touch thì level có Hold không?
Giá có Break qua level không?
Nếu Break thì có Retest không?
Sau interaction, giá có đi theo hướng kỳ vọng không?
```

Cùng một historical snapshot có thể được đánh giá độc lập ở H5, H10, H20 và H40.

### Event labels

Ở event level, evaluation lưu các concept:

```text
Ticker
AsOfDate
LevelRank
LevelType
HorizonBars
Touched
Held
Broken
Retested
DirectionalEdgePct
Strength
Source lineage
Regime
Temporal split
```

Ví dụ:

```text
MWG / 2026-05-04 / R1 / H20
Touched = TRUE
Held    = TRUE
Broken  = FALSE
Retested= FALSE
```

Một event khác:

```text
MWG / 2026-05-19 / S1 / H20
Touched = TRUE
Held    = FALSE
Broken  = TRUE
Retested= TRUE
```

### Historical rates

Sau khi có nhiều historical events, evaluator aggregate thành các empirical rates:

```text
Touch Rate
Hold Rate
Break Rate
Retest Rate
Directional Edge
LEVEL_QUALITY
STRENGTH_BRIER
```

Ví dụ minh họa:

```text
historical resistance events = 1,000

Touch Rate                  = 42%
Hold Rate given touch       = 68%
Break Rate given touch      = 32%
Retest Rate given break     = 47%
```

Có thể diễn giải đây là historical empirical evidence:

```text
P_historical(Break | Touch, horizon=H20) ≈ 32%
```

### Historical rate không phải current predictive probability

V2.4 hiện không được phép kết luận:

```text
MWG current R1 = 62
Probability of breaking R1 within H20 = 27%
```

trừ khi có thêm một dedicated calibrated predictive layer.

Current V2.4 output chủ yếu là:

```text
historical event outcomes
historical conditional rates
quality metrics
source marginal lift
source effectiveness
promotion evidence
```

Vì vậy:

```text
historical empirical rate
    !=
calibrated per-level forecast probability
```

Một future probability-calibration layer có thể sử dụng historical event dataset để tạo:

```text
P(Break R1 within H20)
P(Hold S1 within H10)
P(Retest after break within H20)
```

nhưng đây chưa nằm trong current V2.4 contract.

### Vì sao horizon lớn nhất phải reserve future bars?

Để label đúng một H40 snapshot, evaluator cần 40 later trading bars.

Vì vậy:

```text
latest raw data date
    !=
latest safe evaluation snapshot date
```

Monthly orchestrator chọn evaluation end sao cho vẫn còn đủ future bars cho horizon lớn nhất.

Ví dụ:

```text
evaluation snapshot date
2026-07-03
        ↓
40 later market trading bars
        ↓
latest observed market date
2026-08-28
```

Mục tiêu là tránh:

```text
immature outcomes
censored labels
look-ahead leakage
```

## 14.2 Decision Playbook — Sáu kịch bản ra quyết định dựa trên dữ liệu

Public decision surface:

```text
"CherryMon"."main"."vw_RS_Source_Effectiveness"
```

View trả lời câu hỏi về **historical source effectiveness** theo grain:

```text
Ticker / ScopeType / SourceKey / HorizonBars
```

Các decision rule dưới đây sử dụng current V2.4 default policy, trừ nơi được ghi rõ là future/research use case.

Boundary cần nhớ:

```text
Source Effectiveness
    = bằng chứng một source/config/family có historically add value hay không

Runtime Strength
    = chất lượng/độ tin cậy hiện tại của một R/S level

Horizon Probability
    = calibrated probability của một current R/S level trong future horizon
      (chưa được implement trong V2.4)
```

Do đó view này hỗ trợ trực tiếp source-governance decision, nhưng không được hiểu là direct probability forecast cho S1/R1 hiện tại.

### Các evidence field dùng chung

| Field | Ý nghĩa khi ra quyết định |
|---|---|
| `Ticker` | ticker mà evidence áp dụng |
| `ScopeType` | evidence cho một source/config hay cả family |
| `SourceKey` | canonical source/config identity |
| `SourceFamily` | source family rộng hơn |
| `SourceRole` | LEVEL / CONTEXT / CONFIRMATION |
| `HorizonBars` | future evaluation window tính theo trading bars |
| `AttributionMode` | phương pháp quy attribution/contribution |
| `MarginalMetric` | LEVEL_QUALITY hoặc STRENGTH_BRIER |
| `LineageEventCount` | historical lineage coverage của LEVEL source |
| `ValidationEventCount` | Validation OOS sample size |
| `TestEventCount` | final Test OOS sample size |
| `TouchRate` | tỷ lệ LEVEL historical events được touch trong horizon |
| `HoldRateGivenTouch` | tỷ lệ hold conditional on touch |
| `BreakRateGivenTouch` | tỷ lệ break conditional on touch |
| `RetestRateGivenBreak` | tỷ lệ retest conditional on break |
| `DirectionalEdgePct` | average favorable move trừ average adverse move |
| `ValidationQuality` | role-aware baseline quality trên VALIDATION |
| `TestQuality` | role-aware baseline quality trên TEST |
| `ValidationMarginalLift` | baseline quality trừ ablation quality trên VALIDATION |
| `TestMarginalLift` | baseline quality trừ ablation quality trên TEST |
| `TemporalStability` | mức ổn định giữa VALIDATION và TEST |
| `RegimeStability` | mức ổn định giữa các market regime |
| `ComplexityDelta` | model complexity tăng thêm do source |
| `EffectivenessScore` | composite source-effectiveness score 0-100 |
| `Recommendation` | per-ticker/source/horizon decision label |
| `EvidenceJson` | regime evidence và policy dùng để tính score |
| `CompletedAt` | timestamp của latest completed evidence row |

Default sample thresholds:

```text
ValidationEventCount >= 20
TestEventCount       >= 10
```

Default positive evidence thresholds trong Source Promotion:

```text
EffectivenessScore      >= 65
ValidationMarginalLift  >= +0.01
TestMarginalLift        >= 0.00
TemporalStability       >= 0.70
RegimeStability         >= 0.60
ComplexityDelta         <= 0.15
```

Material negative TEST result:

```text
TestMarginalLift < -0.01
```

nên được coi là strong negative evidence.

---

### Scenario 1 — Quyết định giữ, tiếp tục research hay loại một indicator/source config

**Câu hỏi nghiệp vụ**

> Một source/config cụ thể như MA50_D, BB20_2_D:LOWER, RSI14_D hay VP_POC có tạo đủ historical value để tiếp tục giữ làm candidate trong R/S model hay không?

**Primary filter**

```sql
ScopeType = 'SOURCE_CONFIG'
AND SourceKey = <candidate source>
```

**Primary columns**

```text
SourceRole
AttributionMode
MarginalMetric
ValidationEventCount
TestEventCount
ValidationMarginalLift
TestMarginalLift
TemporalStability
RegimeStability
EffectivenessScore
Recommendation
ComplexityDelta
```

Nếu là `LEVEL`, cần đọc thêm:

```text
LineageEventCount
TouchRate
HoldRateGivenTouch
BreakRateGivenTouch
RetestRateGivenBreak
DirectionalEdgePct
```

**Decision pattern**

Strong candidate:

```text
ValidationEventCount >= 20
TestEventCount       >= 10
EffectivenessScore   >= 75
ValidationLift       >= +0.01
TestLift             >= 0
TemporalStability    >= 0.70
RegimeStability      >= 0.60
Recommendation       = CORE
```

Useful but secondary:

```text
EffectivenessScore >= 65
TestMarginalLift   >= 0
Recommendation     = SUPPORTING
```

Với non-LEVEL source:

```text
CONFIRMATION → CONFIRM_ONLY
CONTEXT      → CONTEXT_ONLY
```

Research only:

```text
Recommendation = RESEARCH
OR insufficient OOS sample
OR score/lift có tín hiệu tốt nhưng regime breadth còn yếu
```

Removal candidate:

```text
Recommendation = DROP
OR TestMarginalLift < -0.01
OR repeated negative TEST lift across horizons/tickers
```

**Ví dụ**

```text
Ticker                  MWG
SourceKey               MA50_D
ScopeType               SOURCE_CONFIG
SourceRole              LEVEL
HorizonBars             20
ValidationEventCount    34
TestEventCount          18
ValidationMarginalLift  +0.028
TestMarginalLift        +0.017
TemporalStability       0.82
RegimeStability         0.73
EffectivenessScore      79.6
Recommendation          CORE
```

Kết luận:

```text
KEEP như một strong integration candidate cho MWG/H20.
Không được hiểu 79.6 là 79.6% probability.
```

---

### Scenario 2 — Quyết định giữ hay loại cả một SourceFamily

**Câu hỏi nghiệp vụ**

> Cả family như TREND_AVERAGE, VOLATILITY_BAND, MARKET_STRUCTURE hoặc VOLUME_STRUCTURE có tạo đủ giá trị để justify complexity hay không?

**Primary filter**

```sql
ScopeType = 'SOURCE_FAMILY'
AND SourceFamily = <candidate family>
```

Attribution thường là:

```text
AttributionMode = FAMILY_ABLATION
```

**Primary columns**

```text
SourceFamily
HorizonBars
ValidationEventCount
TestEventCount
ValidationMarginalLift
TestMarginalLift
TemporalStability
RegimeStability
ComplexityDelta
EffectivenessScore
Recommendation
EvidenceJson
```

Với LEVEL family, đọc thêm nếu có:

```text
TouchRate
HoldRateGivenTouch
BreakRateGivenTouch
RetestRateGivenBreak
DirectionalEdgePct
```

**Decision logic**

Giữ family khi việc ablate family làm model xấu đi:

```text
ValidationMarginalLift > 0
TestMarginalLift       >= 0

và:
TemporalStability >= 0.70
RegimeStability   >= 0.60
```

Cần xem xét lại family nếu:

```text
ValidationMarginalLift ≈ 0
TestMarginalLift       ≈ 0
ComplexityDelta         đáng kể
```

Điều này có thể có nghĩa family đang thêm moving parts nhưng không thêm measurable OOS value.

Strong removal/research signal:

```text
TestMarginalLift < -0.01
```

vì bỏ family ra lại làm TEST quality tốt hơn.

**Lưu ý**

Một family có thể yếu globally nhưng một config bên trong vẫn hữu ích cho một số ticker.

Vì vậy:

```text
SOURCE_FAMILY weak
    không đồng nghĩa
mọi SOURCE_CONFIG trong family đều phải xóa
```

Luôn cross-check Scenario 1 trước khi loại cả family khỏi research scope.

---

### Scenario 3 — Xây ticker-specific source profile

**Câu hỏi nghiệp vụ**

> Source nào phù hợp nhất cho MWG, FPT, HPG, VIC...?

View vốn đã có grain theo ticker, vì vậy có thể phát hiện cùng một source nhưng hiệu quả khác nhau trên từng mã.

**Primary grouping**

```text
group by:
    Ticker
    SourceKey
    HorizonBars
```

**Primary columns**

```text
Ticker
SourceKey
SourceFamily
SourceRole
HorizonBars
ValidationEventCount
TestEventCount
TestMarginalLift
TemporalStability
RegimeStability
EffectivenessScore
Recommendation
```

**Decision pattern**

Ticker-specific positive source:

```text
EffectivenessScore >= 65
ValidationMarginalLift >= +0.01
TestMarginalLift >= 0
TemporalStability >= 0.70
RegimeStability >= 0.60
sufficient OOS sample
```

Ticker-specific weak source:

```text
Recommendation in (RESEARCH, DROP)
OR TestMarginalLift < 0
```

**Ví dụ**

```text
MA50_D / H20

MWG:
    Score     78
    TestLift +0.025
    CORE

FPT:
    Score     67
    TestLift +0.006
    SUPPORTING

HPG:
    Score     51
    TestLift -0.018
    DROP
```

Kết luận:

```text
Không được giả định MA50_D có một quality chung cho mọi ticker.

Nó có thể:
    mạnh với MWG,
    supporting với FPT,
    có hại với HPG.
```

Scenario này là nền tảng cho một future Adaptive Indicator Engine.

**Governance boundary**

V2.4 không tự động thay đổi provider registration theo ticker. View chỉ cung cấp evidence.

---

### Scenario 4 — Nghiên cứu evidence-based weight cho future Strength scoring

**Câu hỏi nghiệp vụ**

> Thay vì coi mọi source đóng góp ngang nhau, có thể dùng historical effectiveness để đề xuất weight tốt hơn khi tính current R/S Strength hay không?

Đây là **future/research use case**, chưa phải current V2.4 runtime behavior.

V2.4 không tự động mutate runtime Strength weights.

**Candidate input columns**

```text
Ticker
SourceKey
SourceFamily
SourceRole
HorizonBars
EffectivenessScore
ValidationMarginalLift
TestMarginalLift
TemporalStability
RegimeStability
ComplexityDelta
Recommendation
```

Với LEVEL source, thêm:

```text
HoldRateGivenTouch
BreakRateGivenTouch
DirectionalEdgePct
```

**Candidate eligibility trước khi một source được phép ảnh hưởng future weight**

```text
ValidationEventCount >= 20
TestEventCount       >= 10
TestMarginalLift     >= 0
Recommendation       not in (RESEARCH, DROP)
```

Ưu tiên source có:

```text
high EffectivenessScore
high TestMarginalLift
high TemporalStability
high RegimeStability
low ComplexityDelta
```

**Illustrative research transformation only**

Một future weighting layer có thể xây normalized research weight từ:

```text
EffectivenessScore
× OOS marginal contribution
× temporal stability
× regime stability
```

Ví dụ khái niệm:

```text
RawWeight
    = ScoreFactor
    × LiftFactor
    × StabilityFactor
```

sau đó normalize giữa các source cùng đóng góp vào một current R/S zone.

Công thức này cố ý chưa nằm trong V2.4 production contract.

**Kết luận**

```text
Source Effectiveness chỉ dùng để nominate/compare candidate weights.

Không được:
- ghi EffectivenessScore trực tiếp thành Runtime Strength;
- hiểu EffectivenessScore là probability;
- tự động thay đổi Strength weighting.

Mọi thay đổi Runtime Strength weighting phải có
architecture decision + regression validation riêng.
```

---

### Scenario 5 — Làm training features cho future Horizon Probability model

**Câu hỏi nghiệp vụ**

> Historical source-effectiveness evidence có thể giúp ước lượng P(Hold), P(Break), P(Retest) cho current R/S level theo một horizon cụ thể hay không?

Có thể dùng làm **input evidence**, nhưng V2.4 hiện chưa cung cấp calibrated current-level probability.

**Relevant columns**

Identity/context:

```text
Ticker
SourceKey
SourceFamily
SourceRole
HorizonBars
```

Historical behavior features cho LEVEL:

```text
TouchRate
HoldRateGivenTouch
BreakRateGivenTouch
RetestRateGivenBreak
DirectionalEdgePct
```

Reliability features:

```text
ValidationEventCount
TestEventCount
ValidationQuality
TestQuality
ValidationMarginalLift
TestMarginalLift
TemporalStability
RegimeStability
EffectivenessScore
Recommendation
```

Các current-state feature phải đến từ runtime R/S ladder, không phải view này:

```text
current LevelPrice
current LevelType / Rank
current Strength
distance from current price
current source lineage
current regime/context
level age/lifecycle khi được implement
```

**Boundary đúng về modeling**

Nếu:

```text
HoldRateGivenTouch = 0.72
```

thì chỉ có nghĩa:

```text
72% historical touched events trong evidence cohort đã Hold
```

Không có nghĩa:

```text
P(current R1 holds over H20) = 72%
```

Future calibration model phải kết hợp current-level features với historical evidence và validate calibration Out-of-Sample.

**Candidate output của future layer**

```text
P(Touch current R1 within H)
P(Hold current R1 | Touch, H)
P(Break current R1 | Touch, H)
P(Retest | Break, H)
```

Trong đó H có thể là bất kỳ configured research horizon nào, kể cả các horizon tương lai như H60/H250, với điều kiện historical evaluator có đủ future outcome bars.

---

### Scenario 6 — Hỗ trợ quyết định trên current R/S level

**Câu hỏi nghiệp vụ**

> Khi current ladder hiển thị S1/R1, nên kết hợp current Strength và historical Source Effectiveness như thế nào để đánh giá level có đáng chú ý không?

Scenario này cần kết hợp hai lớp evidence:

```text
Current R/S Ladder
    +
vw_RS_Source_Effectiveness
```

**Current ladder cung cấp**

```text
Ticker
current S/R level price
LevelRank: S1/S2/R1/R2/...
current Strength
current source lineage
current SourceFamily composition
current market context
```

**Source Effectiveness view cung cấp**

Với từng contributing `SourceKey / SourceFamily / HorizonBars`:

```text
EffectivenessScore
Recommendation
TestMarginalLift
TemporalStability
RegimeStability
```

Với LEVEL source:

```text
TouchRate
HoldRateGivenTouch
BreakRateGivenTouch
RetestRateGivenBreak
DirectionalEdgePct
```

**Pattern cho current level có confidence cao hơn**

Một current R/S level đáng tin cậy hơn khi nhiều independent contributing source có:

```text
Recommendation in:
    CORE
    SUPPORTING
    CONFIRM_ONLY
    CONTEXT_ONLY

TestMarginalLift >= 0
TemporalStability >= 0.70
RegimeStability   >= 0.60
sufficient OOS samples
```

và LEVEL contributors có favorable historical behavior:

```text
HoldRateGivenTouch tương đối cao
BreakRateGivenTouch tương đối thấp
DirectionalEdgePct > 0
```

**Pattern cần thận trọng**

```text
current Strength cao
NHƯNG
major contributing sources có:
    DROP / RESEARCH
    negative TestMarginalLift
    poor TemporalStability
    poor RegimeStability
    insufficient OOS sample
```

Cách hiểu:

```text
Current geometry/confluence có thể đang mạnh,
nhưng historical evidence của underlying sources lại yếu hoặc không ổn định.
```

Đây là lý do để giảm confidence, không phải direct BUY/SELL rule.

**Illustrative decision matrix**

| Current Strength | Source evidence | Cách hiểu |
|---|---|---|
| Cao | Strong/stable OOS evidence | R/S case được historical evidence hỗ trợ mạnh nhất |
| Cao | Weak/negative source evidence | cấu trúc hiện tại mạnh nhưng historical reliability đáng nghi |
| Trung bình | Strong source evidence | vẫn đáng chú ý dù current confluence chỉ trung bình |
| Thấp | Strong source evidence | source historically tốt nhưng current level geometry yếu |
| Thấp | Weak source evidence | level có priority thấp nhất |

**Critical boundary**

View này không được dùng một mình để tạo:

```text
BUY
SELL
exact stop loss
exact target
current Hold/Break probability
```

cho đến khi có runtime decision/calibration layer tương ứng.

---

### Tổng hợp 6 decision scenario

| # | Decision | Primary Scope | Field quan trọng nhất | V2.4 hỗ trợ trực tiếp? |
|---|---|---|---|---|
| 1 | Giữ/loại một indicator config | SOURCE_CONFIG | Score, Recommendation, Val/Test Lift, Stability, sample | YES |
| 2 | Giữ/loại một SourceFamily | SOURCE_FAMILY | Family Ablation Lift, Stability, Complexity, Score | YES |
| 3 | Ticker-specific source selection | per Ticker + SOURCE_CONFIG | Score, Test Lift, Recommendation, Stability | YES ở mức evidence; chưa auto-runtime |
| 4 | Source weighting cho Strength | SOURCE_CONFIG/FAMILY | Score, Lift, Stability, Complexity | RESEARCH INPUT ONLY |
| 5 | Horizon Probability | per Ticker/Source/Horizon | historical rates + reliability fields | TRAINING INPUT ONLY; chưa calibrated |
| 6 | Current R/S decision support | current ladder + view | Strength + source lineage + effectiveness evidence | PARTIAL; chỉ decision-support evidence |

### Thứ tự ưu tiên evidence

Khi các field cho tín hiệu mâu thuẫn, ưu tiên:

```text
1. TEST evidence
2. sufficient OOS sample
3. Validation/Test consistency
4. Regime Stability
5. Marginal Lift
6. EffectivenessScore
7. historical Touch/Hold/Break/Retest statistics
8. TRAIN evidence chỉ dùng làm background
```

Không promote một source chỉ vì `EffectivenessScore` cao nếu TEST evidence materially negative hoặc sample chưa đủ.

## 15. Performance và Operational Strategy

1. Reuse persisted V2.3 evaluation events/metrics.
2. Không recalculates compatible baseline nếu không cần thiết.
3. Chỉ chạy source-config ablation cho candidate đang được nghiên cứu.
4. Load run events theo set-based.
5. Compute per-ticker effectiveness trong memory.
6. Persist result trong một short writer transaction.
7. Đọc latest result qua public view.

### Monthly full evaluation

Canonical operational service:

```text
src/Orchestrator/rs_v2_4_full_evaluation.py
```

Stable CLI entry point:

```text
scripts/run_rs_v2_4_full_evaluation.py
```

CLI wrapper delegate sang Orchestrator service; không được duplicate R/S calculation/business logic.

Monthly orchestrator:

```text
resolve eligible ticker universe
        ↓
reserve future outcome bars
        ↓
baseline × H5/H10/H20/H40
        ↓
source-config ablation/effectiveness
        ↓
source-family ablation/effectiveness
        ↓
Source Promotion Gate dry-run
        ↓
vw_RS_Source_Effectiveness
```

Quy tắc:

- full evaluation là research/governance workload, không phải daily runtime workload;
- default cadence là monthly, có thể event-driven rerun sau material source/model changes;
- latest raw market date được reserve cho outcome observation; evaluation end phải để lại đủ later trading bars cho largest requested horizon;
- một compatible baseline per horizon được reuse giữa các source/family ablation;
- deterministic run IDs + metadata compatibility checks hỗ trợ resumable execution;
- SOURCE_CONFIG LEVEL evaluation yêu cầu observable baseline lineage;
- SOURCE_FAMILY ablation phải remove toàn bộ discovered family membership;
- promotion mặc định dry-run và không thay đổi runtime weights/providers.

Operational procedure:

```text
docs/runbook/RS_V2_4_Monthly_Full_Evaluation.md
```

## 16. Failure / Blocking Rules

BLOCK khi:

- baseline và ablation datasets/horizons/split contracts không compatible;
- required run chưa `COMPLETED`;
- required OOS split bị thiếu;
- LEVEL source không tồn tại trong historical lineage.

Insufficient regime breadth hoặc sample size phải đưa về `RESEARCH`, không được silent approve dựa trên TRAIN-only evidence.

## 17. Compatibility

Khi không truyền include/exclude source filters, V2.4 phải giữ nguyên V2.3 runtime behavior và golden outputs.

V2.3 model Promotion Gate giữ nguyên.

V2.4 chỉ bổ sung một Source Promotion Gate riêng biệt.

## 18. Migration

Additive/idempotent migration:

```text
src/DuckDB/sql/rs_v2_4_source_effectiveness.sql
```

Thực thi bên ngoài read-only MCP bằng:

```text
scripts/run_rs_v2_4_migration.py
```

## 19. Validation Strategy

Unit tests phải cover:

```text
canonical identity
filters
role-aware scoring
score bounds
temporal/regime stability
negative TEST protection
recommendations
global/ticker-selective promotion
persistence dataframe contracts
```

Regression yêu cầu V2.3 golden benchmark và existing R/S tests vẫn PASS khi không supply research filters.

Integration validation phải cover baseline/ablation compatibility, effectiveness persistence, public view, idempotency và promotion dry-run.

## 20. ADR

**Required** vì V2.4 đưa vào:

```text
stable source identity
research filters trong R/S API
source-specific promotion governance layer
new persistence/public SSOT
explicit non-deploying approval boundary
```

ADR:

```text
docs/adr/ADR-008-rs-v2-4-source-effectiveness-promotion.md
```

## 21. Implementation Handoff

```text
DESIGN HANDOFF
Requirement: REQ-0022
Outcome: R/S V2.4 Source Effectiveness & Indicator Promotion Framework
Status: APPROVED_FOR_IMPLEMENTATION
Primary next owner: GeneralCoding
Architecture: docs/architecture/RS_Source_Effectiveness.md
ADR: docs/adr/ADR-008-rs-v2-4-source-effectiveness-promotion.md
Database migration: required, additive/idempotent, generated only
Validation owner: TestEngineer
```
