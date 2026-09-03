# Support / Resistance Level Ladder Architecture

> Theme integration: R/S chart presentation defaults consume the centralized tokens defined in [[theme|Theme Architecture]]. Support, resistance, current-price, text, tooltip and grid colors are presentation concerns and are not part of the ladder business contract.

## 1. Purpose

Tài liệu này định nghĩa kiến trúc cho **Chart 2 – Support / Resistance Level Ladder (RS Ladder)** của CherryStock.

Mục tiêu của RS Ladder:

- Thể hiện cấu trúc giá của một ticker theo thứ tự từ các vùng kháng cự phía trên, giá hiện tại, đến các vùng hỗ trợ phía dưới.
- Chuẩn hóa nhiều nguồn price level khác nhau về cùng một data contract.
- Xác định Support / Resistance dựa trên vị trí tương đối so với current price thay vì hard-code theo indicator.
- Gom các level gần nhau thành price zone để tránh hiển thị nhiều mức giá gần như trùng nhau.
- Tính strength/confluence độc lập với ranking S1/S2/R1/R2.
- Hỗ trợ mặc định ba timeframe Daily / Weekly / Monthly.
- Cho phép mở rộng thêm nguồn level mới mà không phải thay đổi downstream ranking và chart rendering.
- Tách rõ data access, calculation/business logic và chart rendering theo architecture hiện tại của CherryStock.

---

# 2. Architecture Principles

RS Ladder tuân thủ các nguyên tắc của `copilot-instructions.md`, `CherryMon.agent.md` và Indicator Engine:

1. `src/calcEngine` chịu trách nhiệm calculation/business logic.
2. `src/Chart` chỉ chịu trách nhiệm presentation/rendering.
3. Renderer không query database và không tính Support / Resistance.
4. Data access, normalization, calculation, validation và rendering phải được tách rõ.
5. Không hard-code indicator configuration nếu metadata/config hiện tại đã có thể resolve từ DuckDB.
6. Downstream technical indicator values sử dụng `vw_Ticker_indicators` làm calculated-value Single Source of Truth; `cal_indicator_values` chỉ là internal persistence của Indicator Engine.
7. Runtime không parse Parameters từ `ConfigCode`; downstream phải resolve Parameters từ public config contract `vw_Indicator_config.Parameters`.
8. Mặc định hỗ trợ ba timeframe:
   - `D` = Daily
   - `W` = Weekly
   - `M` = Monthly
9. Không silent failure nếu lỗi có thể làm sai cấu trúc Support / Resistance.
10. Ưu tiên source-agnostic architecture để bổ sung source mới mà không làm thay đổi downstream pipeline.

---

# 3. High-Level Architecture

```text
raw_stock_eod
      │
      │ Current Price / OHLCV
      ▼
┌────────────────────────┐
│ 1. PriceProvider       │
└───────────┬────────────┘
            │ CurrentPrice
            │
            │
vw_Ticker_indicators
vw_Indicator_config
raw_stock_eod / derived levels
            │
            ▼
┌────────────────────────┐
│ 2. LevelSourceProvider │
└───────────┬────────────┘
            │ LevelCandidate[]
            ▼
┌────────────────────────┐
│ 3. LevelNormalizer     │
└───────────┬────────────┘
            │ NormalizedLevel[]
            ▼
┌────────────────────────┐
│ 4. LevelClusterEngine  │
└───────────┬────────────┘
            │ LevelZone[]
            ▼
┌────────────────────────┐
│ 5. LevelClassifier     │
└───────────┬────────────┘
            │ SUPPORT / RESISTANCE / CURRENT
            ▼
┌────────────────────────┐
│ 6. LevelStrengthEngine │
└───────────┬────────────┘
            │ ScoredLevel[]
            ▼
┌────────────────────────┐
│ 7. LevelRanker         │
└───────────┬────────────┘
            │ S1/S2/S3 + R1/R2/R3
            ▼
┌────────────────────────┐
│ 8. LadderBuilder       │
└───────────┬────────────┘
            │ LevelLadderResult
            ▼
┌────────────────────────┐
│ 9. LevelLadderRenderer │
│ src/Chart              │
└────────────────────────┘
```

Core data flow:

```text
LevelCandidate
      ↓
NormalizedLevel
      ↓
LevelZone
      ↓
ScoredLevel
      ↓
RankedLevel
      ↓
LevelLadderResult
```

---

# 4. Component Summary

| # | Component | Responsibility | Input | Output |
|---|---|---|---|---|
| 1 | `PriceProvider` | Resolve current/reference price | ticker, as_of_date | `CurrentPrice` |
| 2 | `LevelSourceProvider` | Collect candidate price levels | ticker, date, source configs | `LevelCandidate[]` |
| 3 | `LevelNormalizer` | Normalize heterogeneous sources | candidates | `NormalizedLevel[]` |
| 4 | `LevelClusterEngine` | Group nearby levels into zones | levels, threshold | `LevelZone[]` |
| 5 | `LevelClassifier` | Classify Support / Resistance | zones, current price | classified zones |
| 6 | `LevelStrengthEngine` | Calculate strength/confluence | zone, history, config | `ScoredLevel[]` |
| 7 | `LevelRanker` | Assign S1/S2/S3 and R1/R2/R3 | scored levels | `RankedLevel[]` |
| 8 | `LadderBuilder` | Build chart-ready domain model | ranked levels + price | `LevelLadderResult` |
| 9 | `LevelLadderRenderer` | Render Level Ladder chart | `LevelLadderResult` | chart/UI |

---

# 5. Component 1 — PriceProvider

## 5.1 Responsibility

Resolve reference/current price của ticker tại `as_of_date`.

Primary source:

```text
"CherryMon"."main"."raw_stock_eod"
```

Default reference price:

```text
Close
```

## 5.2 Input Contract

```python
ticker: str
as_of_date: date | None
price_field: str = "Close"
```

### Requirements

`ticker`:

- Required.
- Non-empty.
- Normalize uppercase.
- Phải tồn tại trong source price data.

`as_of_date`:

- Optional.
- Nếu `None`, resolve latest valid trading date.
- V1 resolve ngày thực tế bằng latest `raw_stock_eod.Date <= as_of_date`; đây là actual trading-data date và không assume Monday–Friday.
- Khi business rule cần calendar semantics ngoài dữ liệu giá, sử dụng `dimCalendar` hoặc helper hiện có.

`price_field`:

- Default `Close`.
- Field phải tồn tại và có numeric value hợp lệ.

## 5.3 Output Contract

```python
@dataclass
class CurrentPrice:
    ticker: str
    as_of_date: date
    price: float
```

Example:

```json
{
  "ticker": "MWG",
  "as_of_date": "2026-08-28",
  "price": 55200
}
```

## 5.4 Failure Behaviour

- Ticker không tồn tại → `ValueError`.
- Không có EOD data → `ValueError`.
- Price NULL / NaN / <= 0 → validation error.
- Không silent fallback sang ticker/date khác.

---

# 6. Component 2 — LevelSourceProvider

## 6.1 Responsibility

Thu thập tất cả candidate price levels có khả năng trở thành Support hoặc Resistance.

Component này **không classify Support / Resistance**.

Nó chỉ trả về candidate price levels.

## 6.2 Supported Sources

### V1

Technical indicator levels:

```text
MA20
MA50
MA100
MA200
```

trên:

```text
D / W / M
```

Có thể mở rộng các component price-based khác từ Indicator Engine nếu phù hợp, ví dụ:

```text
BB LOWER
BB MIDDLE
BB UPPER
SUPERTREND
ICHIMOKU levels
```

### Future Sources

```text
Swing High / Swing Low
Pivot
Fibonacci
Volume Profile
Previous High / Low
52W High / Low
Historical High / Low
```

Các source mới phải normalize về cùng `LevelCandidate` contract.

## 6.3 Input Contract

```python
ticker: str
as_of_date: date
enabled_sources: tuple[str, ...] | None
timeframes: tuple[str, ...] = ("D", "W", "M")
```

### Requirements

- `ticker` và `as_of_date` phải đồng nhất với `CurrentPrice`.
- `timeframes` chỉ nhận các timeframe được support.
- Indicator config phải được resolve từ metadata/config hiện tại.
- Không parse Parameters từ `ConfigCode`.
- Chỉ lấy active/enabled indicator/config/component.
- Value phải thuộc đúng ticker và date/timeframe cần resolve.

## 6.4 Indicator Data Source

RS Ladder là downstream consumer của Indicator Engine nên public read contracts là bắt buộc:

```text
"CherryMon"."main"."vw_Ticker_indicators"
    = Calculated Value SSOT

"CherryMon"."main"."vw_Indicator_config"
    = Configuration / metadata SSOT
```

Các table nội bộ vẫn giữ vai trò lineage/persistence của Indicator Engine:

```text
dim_indicator
dim_indicator_component
dim_indicator_config
cal_indicator_values
```

RS Ladder không đọc trực tiếp `cal_indicator_values` khi public view đáp ứng contract, không duplicate indicator calculation và không fallback sang `cal_Trends` nếu public contract bị thiếu/sai.

## 6.5 Output Contract

```python
@dataclass
class LevelCandidate:
    ticker: str
    price: float

    source_type: str
    source_code: str

    timeframe: str | None

    indicator_code: str | None
    config_id: int | None
    config_code: str | None
    component_code: str | None

    source_date: date
    metadata: dict
```

Example:

```json
{
  "ticker": "MWG",
  "price": 53820,
  "source_type": "INDICATOR",
  "source_code": "MA200_D",
  "timeframe": "D",
  "indicator_code": "MA",
  "config_id": 31,
  "config_code": "MA200_D",
  "component_code": "VALUE",
  "source_date": "2026-08-28",
  "metadata": {
    "parameters": {
      "length": 200
    }
  }
}
```

---

# 7. Component 3 — LevelNormalizer

## 7.1 Responsibility

Normalize heterogeneous level sources về một canonical contract.

Example raw levels:

```text
MA200_D       53,820
Fib 61.8%     53,870
Swing Low     53,750
BB Lower      53,930
```

Sau normalization, downstream pipeline không cần biết cách source được tính.

## 7.2 Input

```python
candidates: list[LevelCandidate]
```

## 7.3 Validation Requirements

Mỗi candidate phải đảm bảo:

```text
price > 0
price != NaN / Inf
source_date <= as_of_date
ticker giống nhau
timeframe ∈ D/W/M/NULL
source_type hợp lệ
indicator config active nếu source là INDICATOR
```

Invalid candidate không được silent ignore nếu lỗi cho thấy source/config sai.

## 7.4 Output

```python
@dataclass
class NormalizedLevel:
    price: float

    source_type: str
    source_code: str

    timeframe: str | None

    weight: float
    metadata: dict
```

`weight` là base source/timeframe weight, chưa phải final strength score.

Weight phải được config-driven khi triển khai; renderer không hard-code weight.

---

# 8. Component 4 — LevelClusterEngine

## 8.1 Responsibility

Gom các candidate level gần nhau thành một price zone.

Ví dụ:

```text
MA200_D       53,820
Fib 61.8%     53,870
Swing Low     53,750
BB Lower      53,930
```

Không nên render thành bốn Support độc lập.

Expected cluster:

```text
Support Zone ≈ 53,840
```

## 8.2 Input

```python
levels: list[NormalizedLevel]
cluster_threshold_pct: float
```

### Requirements

```text
0 < cluster_threshold_pct <= 0.05
```

V1 default proposal:

```text
1% = 0.01
```

Threshold phải là configurable input, không hard-code trong chart renderer.

Future enhancement:

```text
cluster_threshold = max(
    fixed_percentage_threshold,
    ATR_based_threshold
)
```

## 8.3 Representative Price

Representative price có thể sử dụng weighted average:

```text
representative_price =
    Σ(price × weight)
    ─────────────────
        Σ(weight)
```

Algorithm cụ thể phải deterministic để cùng input luôn tạo cùng output.

## 8.4 Output

```python
@dataclass
class LevelZone:
    zone_id: str

    price_low: float
    price_high: float
    representative_price: float

    sources: list[NormalizedLevel]
    source_count: int
```

Example:

```json
{
  "zone_id": "ZONE_001",
  "price_low": 53750,
  "price_high": 53930,
  "representative_price": 53840,
  "source_count": 4
}
```

---

# 9. Component 5 — LevelClassifier

## 9.1 Responsibility

Classify zone theo vị trí tương đối với current price.

Indicator/source không tự định nghĩa một level luôn là Support hoặc luôn là Resistance.

Ví dụ:

```text
MA200 < CurrentPrice → SUPPORT candidate
MA200 > CurrentPrice → RESISTANCE candidate
```

## 9.2 Input

```python
zones: list[LevelZone]
current_price: CurrentPrice
neutral_threshold_pct: float
```

## 9.3 Classification Rules

```text
zone_price < current_price
    → SUPPORT

zone_price > current_price
    → RESISTANCE

zone overlaps current_price
    → CURRENT
```

Có thể sử dụng neutral threshold để tránh classify một zone sát current price một cách giả tạo:

```text
abs(distance_pct) <= neutral_threshold_pct
    → CURRENT
```

## 9.4 Distance Calculation

```text
distance_pct =
    (representative_price - current_price)
    ────────────────────────────────────── × 100
                 current_price
```

Convention:

```text
Support     → distance_pct < 0
Resistance  → distance_pct > 0
Current     → approximately 0
```

---

# 10. Component 6 — LevelStrengthEngine

## 10.1 Responsibility

Tính độ mạnh của từng Support / Resistance zone độc lập với proximity ranking.

Runtime `StrengthScore` hiện tại trong `src/calcEngine/levelLadder.py` được tổng hợp từ các component sau:

| Score | Mục tiêu | Default weight | Công thức | Ví dụ |
|---|---|---:|---|---|
| `SourceConfluenceScore` | Đo mức độ hội tụ của các `SourceFamily` độc lập tại cùng một R/S zone | `0.35` | `min(SourceFamilyCount / 3, 1) × 100` | 3 family khác nhau cùng hội tụ → `100`; chỉ 1 family → `33.33` |
| `TimeframeScore` | Đo mức độ xác nhận của level trên nhiều timeframe | `0.25` | `min(sum(unique TimeframeWeight) / 4.5, 1) × 100`, với `D=1.0, W=1.5, M=2.0` | Có `D + W` → `(1.0 + 1.5) / 4.5 × 100 = 55.56` |
| `TouchScore` | Đo số lần giá đã tương tác với R/S zone trong historical price history | `0.25` | `min(TouchCount / 4, 1) × 100` | 3 touch → `75`; từ 4 touch trở lên → `100` |
| `RecencyScore` | Đo mức độ mới của source gần nhất tạo nên level | `0.15` | `max(0, 1 - AgeDays / 180) × 100` | Source mới nhất cách 30 ngày → `83.33` |
| `ConfirmationScore` | Đo mức confirmation của RSI đối với SUPPORT / RESISTANCE hiện tại | `0.10` nếu có RSI | SUPPORT: `(50 - RSI) / (50 - 30) × 100`; RESISTANCE: `(RSI - 50) / (70 - 50) × 100`; clamp về `0..100`, sau đó weighted theo timeframe | SUPPORT có RSI = 30 → `100`; RSI = 40 → `50`; RESISTANCE có RSI = 70 → `100` |
| `StructuralQualityScore` | Đo độ mới của các source thuộc `MARKET_STRUCTURE` | `0.15` nếu có structural source | Với mỗi structural source: `max(0, 1 - AgeDays / 180) × 100`, sau đó lấy average | `SWING_HIGH` mới 30 ngày và `PREV_MONTH_HIGH` mới 60 ngày → khoảng `75` |
| `VolumeConfirmationScore` | Đo mức xác nhận volume quanh chính R/S zone | `0.10` nếu có volume confirmation | Lấy confirmation context có `reference_price` nằm trong zone ± tolerance, lấy `max(value)` và clamp về `0..100` | Có volume confirmation quanh zone với score `82` → `82` |

Base Strength formula:

```text
BaseStrength =
      SourceConfluenceScore × 0.35
    + TimeframeScore        × 0.25
    + TouchScore            × 0.25
    + RecencyScore          × 0.15
```

Nếu không có additional component thì tổng base weight = `1.0`, vì vậy `BaseStrength = StrengthScore`.

Khi có RSI / structural / volume confirmation, runtime hiện tại sử dụng cơ chế re-normalize:

```text
WeightedScore =
      SourceConfluenceScore   × 0.35
    + TimeframeScore          × 0.25
    + TouchScore              × 0.25
    + RecencyScore            × 0.15
    + ConfirmationScore       × 0.10   nếu có RSI
    + StructuralQualityScore  × 0.15   nếu có structural source
    + VolumeConfirmationScore × 0.10   nếu có volume confirmation

EffectiveWeight =
      1.00
    + 0.10 nếu có RSI
    + 0.15 nếu có structural source
    + 0.10 nếu có volume confirmation

StrengthScore = WeightedScore / EffectiveWeight
```

Ví dụ:

```text
SourceConfluenceScore   = 100
TimeframeScore          = 55.56
TouchScore              = 75
RecencyScore            = 83.33
ConfirmationScore       = 70
StructuralQualityScore  = 80
VolumeConfirmationScore = 75

WeightedScore ≈ 106.64
EffectiveWeight = 1.35
StrengthScore ≈ 78.99
```

Lưu ý:

```text
SourceConfluenceScore
    = mức độ hội tụ của SourceFamily hiện tại

Source Effectiveness
    = historical OOS evidence của từng source/config

Hai khái niệm này hiện chưa được nối trực tiếp với nhau trong Runtime Strength.
```

## 10.2 Input

```python
zone: LevelZone
price_history: DataFrame | None
strength_config: StrengthConfig
```

Config contract:

```python
@dataclass
class StrengthConfig:
    confluence_weight: float
    timeframe_weight: float
    touch_weight: float
    recency_weight: float
```

### Requirements

- Weights phải >= 0.
- Final score phải normalize về một scale ổn định.

Recommended scale:

```text
0 → 100
```

## 10.3 Timeframe Confluence

Default importance concept:

```text
Monthly > Weekly > Daily
```

Nhưng actual weights phải nằm trong config/business layer, không hard-code trong renderer.

Một zone có nhiều timeframe cùng hội tụ phải có confluence cao hơn một single-source Daily level nếu các yếu tố khác tương đương.

## 10.4 Output

```python
@dataclass
class ScoredLevel:
    zone: LevelZone

    strength_score: float

    confluence_score: float
    timeframe_score: float
    touch_score: float
    recency_score: float
```

Example:

```json
{
  "price": 53840,
  "strength_score": 82,
  "confluence_score": 30,
  "timeframe_score": 22,
  "touch_score": 18,
  "recency_score": 12
}
```

---

# 11. Component 7 — LevelRanker

## 11.1 Responsibility

Assign proximity rank:

```text
R1 / R2 / R3 / ...
S1 / S2 / S3 / ...
```

## 11.2 Critical Business Rule

`S1` và `R1` biểu diễn **nearest Support / Resistance**, không biểu diễn strongest level.

```text
S1 = nearest support below current price
S2 = second nearest support

R1 = nearest resistance above current price
R2 = second nearest resistance
```

Strength là field độc lập:

```text
rank             = proximity
strength_score   = quality / confidence
```

## 11.3 Input

```python
levels: list[ScoredLevel]
current_price: float
max_support_levels: int = 3
max_resistance_levels: int = 3
```

### Requirements

```text
max_support_levels > 0
max_resistance_levels > 0
```

## 11.4 Ranking Logic

Support:

```text
filter level_type = SUPPORT
sort representative_price DESC
assign S1, S2, S3, ...
```

Resistance:

```text
filter level_type = RESISTANCE
sort representative_price ASC
assign R1, R2, R3, ...
```

## 11.5 Output

```python
@dataclass
class RankedLevel:
    rank: str
    level_type: str

    price: float
    price_low: float
    price_high: float

    distance_pct: float
    strength_score: float

    source_count: int
    sources: list
```

Example:

```json
{
  "rank": "S1",
  "level_type": "SUPPORT",
  "price": 53840,
  "price_low": 53750,
  "price_high": 53930,
  "distance_pct": -2.46,
  "strength_score": 82,
  "source_count": 4
}
```

---

# 12. Component 8 — LadderBuilder

## 12.1 Responsibility

Build final chart-ready domain model.

LadderBuilder không render UI.

## 12.2 Input

```python
ticker: str
as_of_date: date
current_price: CurrentPrice
ranked_levels: list[RankedLevel]
```

## 12.3 Output

```python
@dataclass
class LevelLadderResult:
    ticker: str
    as_of_date: date

    current_price: float

    resistance_levels: list[RankedLevel]
    support_levels: list[RankedLevel]

    nearest_support: RankedLevel | None
    nearest_resistance: RankedLevel | None

    upside_to_r1_pct: float | None
    downside_to_s1_pct: float | None
    risk_reward_ratio: float | None
```

## 12.4 Derived Metrics

```text
upside_to_r1_pct
    = R1 distance_pct

downside_to_s1_pct
    = abs(S1 distance_pct)
```

Risk/reward convention for Ladder V1:

```text
risk_reward_ratio =
    upside_to_r1_pct
    ────────────────
    downside_to_s1_pct
```

Nếu thiếu S1 hoặc R1:

```text
risk_reward_ratio = None
```

Không divide by zero.

## 12.5 Example Output

```json
{
  "ticker": "MWG",
  "as_of_date": "2026-08-28",
  "current_price": 55200,
  "resistance_levels": [
    {
      "rank": "R1",
      "price": 56800,
      "distance_pct": 2.90,
      "strength_score": 76
    },
    {
      "rank": "R2",
      "price": 59400,
      "distance_pct": 7.61,
      "strength_score": 85
    },
    {
      "rank": "R3",
      "price": 62500,
      "distance_pct": 13.22,
      "strength_score": 93
    }
  ],
  "support_levels": [
    {
      "rank": "S1",
      "price": 53800,
      "distance_pct": -2.54,
      "strength_score": 73
    },
    {
      "rank": "S2",
      "price": 51200,
      "distance_pct": -7.25,
      "strength_score": 82
    }
  ],
  "upside_to_r1_pct": 2.90,
  "downside_to_s1_pct": 2.54,
  "risk_reward_ratio": 1.14
}
```

---

# 13. Component 9 — LevelLadderRenderer

## 13.1 Responsibility

Render `LevelLadderResult` thành visual chart/UI.

Recommended location:

```text
src/Chart/
```

Renderer chỉ nhận chart-ready domain model.

## 13.2 Input

```python
ladder: LevelLadderResult
```

Renderer không nhận raw database connection và không query source tables.

## 13.3 Forbidden Responsibilities

Renderer không được thực hiện:

```text
query_database()
calculate_indicator()
calculate_ma()
cluster_levels()
classify_support_resistance()
calculate_strength()
rank_levels()
```

## 13.4 Visual Structure

```text
MWG — PRICE STRUCTURE
Current: 55,200
────────────────────────────────────

R3   62,500    +13.22%    Strength 93
        │
R2   59,400     +7.61%    Strength 85
        │
R1   56,800     +2.90%    Strength 76
        │
PRICE 55,200 ═══════════════════════
        │
S1   53,800     -2.54%    Strength 73
        │
S2   51,200     -7.25%    Strength 82
        │
S3   48,500    -12.14%    Strength 91
```

Y-axis/vertical position nên preserve actual price relationship để khoảng cách giữa các level phản ánh đúng price distance.

Tooltip/details có thể hiển thị:

```text
Rank
Price / Zone
Distance %
Strength
Source Count
Sources
Timeframes
Indicator Configs
```

---

# 14. Public Use-Case Contract

Recommended public business function:

```python
def build_level_ladder(
    ticker: str,
    *,
    as_of_date: date | None = None,
    timeframes: tuple[str, ...] = ("D", "W", "M"),
    max_support_levels: int = 3,
    max_resistance_levels: int = 3,
    enabled_sources: tuple[str, ...] | None = None,
    cluster_threshold_pct: float = 0.01,
) -> LevelLadderResult:
    ...
```

## Input Requirements

| Input | Required | Validation | Default |
|---|---:|---|---|
| `ticker` | Yes | valid/non-empty ticker | — |
| `as_of_date` | No | valid trading date | latest |
| `timeframes` | No | supported timeframe subset | D/W/M |
| `max_support_levels` | No | integer > 0 | 3 |
| `max_resistance_levels` | No | integer > 0 | 3 |
| `enabled_sources` | No | registered/known source | all enabled |
| `cluster_threshold_pct` | No | `0 < value <= 0.05` | 0.01 |

---

# 15. Final Output Contract

```text
LevelLadderResult
│
├── ticker
├── as_of_date
├── current_price
│
├── resistance_levels[]
│   ├── R1
│   ├── R2
│   └── R3
│
├── support_levels[]
│   ├── S1
│   ├── S2
│   └── S3
│
├── nearest_support
├── nearest_resistance
│
├── upside_to_r1_pct
├── downside_to_s1_pct
│
└── risk_reward_ratio
```

Each `RankedLevel`:

```text
RankedLevel
│
├── rank
├── level_type
│
├── price
├── price_low
├── price_high
│
├── distance_pct
├── strength_score
│
├── source_count
│
└── sources[]
     ├── source_type
     ├── source_code
     ├── timeframe
     ├── config_id
     ├── config_code
     └── component_code
```

---

# 16. Proposed Source Structure

Logical responsibility:

```text
src/
│
├── calcEngine/
│   │
│   └── levelLadder.py
│       ├── LevelNormalizer
│       ├── LevelClusterEngine
│       ├── LevelClassifier
│       ├── LevelStrengthEngine
│       ├── LevelRanker
│       └── LadderBuilder
│
├── Chart/
│   │
│   ├── plot.py
│   ├── plotChart.py
│   │
│   └── levelLadderChart.py
│       └── render_level_ladder()
│
└── Ults/
```

Đây là logical design, không bắt buộc tạo toàn bộ file/class ngay lập tức.

Trước implementation phải inspect implementation hiện có trong:

```text
src/calcEngine/
src/Chart/plot.py
src/Chart/plotChart.py
```

Nếu repository đã có pattern/service phù hợp thì phải reuse thay vì tạo abstraction mới.

---

# 17. V1 Scope

Để tránh over-engineering, V1 ưu tiên sử dụng level đã có sẵn từ Indicator Engine.

Recommended initial sources:

```text
MA20_D / MA50_D / MA100_D / MA200_D
MA20_W / MA50_W / MA100_W / MA200_W
MA20_M / MA50_M / MA100_M / MA200_M
```

Pipeline:

```text
raw_stock_eod
      │
 CurrentPrice
      │
      ├─────────────────────────────┐
      │                             │
      │                    Indicator Engine
      │                             │
      │                    MA D / W / M
      │                             │
      └──────────────┬──────────────┘
                     ▼
             LevelSourceProvider
                     │
             LevelNormalizer
                     │
              LevelCluster
                     │
              LevelClassifier
                     │
              LevelStrength
                     │
                LevelRanker
                     │
               LadderBuilder
                     │
                     ▼
                RS LADDER
```

---

# 18. Extension Architecture

Future source providers có thể bổ sung:

```text
SwingLevelProvider
PivotLevelProvider
FibonacciLevelProvider
VolumeProfileLevelProvider
HistoricalLevelProvider
```

Mọi provider phải output cùng contract:

```text
LevelCandidate[]
```

Do đó downstream pipeline không thay đổi:

```text
New Provider
     │
     ▼
LevelCandidate
     │
     ▼
Normalizer
     │
     ▼
Cluster
     │
     ▼
Classifier
     │
     ▼
Strength
     │
     ▼
Ranker
     │
     ▼
LadderBuilder
     │
     ▼
Renderer
```

Đây là extension boundary chính của RS Ladder.

---

# 19. Validation Contract

Minimum validation trước calculation:

### Request validation

- ticker non-empty.
- timeframe hợp lệ.
- max support/resistance > 0.
- cluster threshold hợp lệ.

### Price validation

- current price tồn tại.
- current price numeric và > 0.
- as_of_date là valid trading date.

### Candidate validation

- candidate price numeric và > 0.
- source metadata hợp lệ.
- source date không lớn hơn as_of_date.
- ticker consistency.

### Cluster validation

- representative price nằm trong `[price_low, price_high]`.
- source_count bằng số source thực tế.
- không tạo empty zone.

### Ranking validation

- mọi `S*` phải nằm dưới current price, ngoại trừ explicit current-zone handling.
- mọi `R*` phải nằm trên current price.
- S1 là support gần nhất.
- R1 là resistance gần nhất.
- rank không duplicate.

### Output validation

- output ticker/date đồng nhất input.
- distance sign đúng convention.
- strength nằm trong normalized range.
- risk/reward chỉ tính khi cả S1 và R1 hợp lệ.

---

# 20. Testing Requirements

Implementation phải có tối thiểu các test sau.

## Happy Path

- Có nhiều support/resistance sources.
- Cluster đúng.
- S1/R1 đúng nearest level.
- Strength được preserve độc lập với rank.

## Empty Input

- Không có candidate levels.
- Current price vẫn hợp lệ.
- Output trả empty support/resistance lists, không crash renderer.

## Invalid Input

- Empty ticker.
- Invalid timeframe.
- Invalid cluster threshold.
- Invalid max level count.

## Boundary Cases

- Level đúng bằng current price.
- Level nằm trong neutral threshold.
- Hai level nằm đúng cluster boundary.
- Chỉ có Support nhưng không có Resistance.
- Chỉ có Resistance nhưng không có Support.

## Failure Cases

- Price source unavailable.
- Indicator source/config inconsistent.
- Candidate chứa NaN/Inf.
- Database dependency failure.

## Determinism / Idempotency

Cùng ticker + as_of_date + config + source data phải tạo cùng:

```text
zones
ranking
strength
LevelLadderResult
```

RS Ladder là read/calculation flow nên không được tạo database side effect nếu chỉ build chart result.

---

# 21. Design Decisions

## Decision 1 — Rank and Strength are independent

```text
R1 / S1 = proximity
Strength = confidence / importance
```

Không rank theo strength.

## Decision 2 — Use zones instead of raw lines

Support/Resistance trong thực tế là vùng giá. Các level gần nhau được cluster trước khi ranking.

## Decision 3 — Source-agnostic downstream pipeline

Downstream chỉ hiểu `LevelCandidate`, không phụ thuộc MA/Fibonacci/Swing implementation.

## Decision 4 — Renderer is presentation-only

Renderer không query DB và không chứa business calculation.

## Decision 5 — Reuse Indicator Engine

Không tính lại technical indicators; RS Ladder đọc calculated values từ public SSOT `vw_Ticker_indicators` và metadata/config từ `vw_Indicator_config`.

## Decision 6 — D/W/M confluence is first-class information

Một zone hội tụ nhiều timeframe phải preserve source/timeframe metadata để Strength Engine và UI có thể sử dụng.

---

# 22. Implementation Sequence

Recommended implementation order:

```text
1. Inspect existing calcEngine / Chart implementation
2. Define domain contracts
3. Implement PriceProvider
4. Implement Indicator LevelSourceProvider
5. Implement normalization
6. Implement clustering
7. Implement classification
8. Implement strength V1
9. Implement ranking
10. Implement LadderBuilder
11. Implement renderer
12. Add unit tests
13. Run real ticker validation (e.g. MWG)
14. Add independent execution command/script if needed
```

Không implement renderer trước khi calculation/output contract ổn định.

---

# 23. Acceptance Criteria

RS Ladder V1 được coi là hoàn thành khi:

1. Nhận một ticker và optional `as_of_date`.
2. Resolve đúng current price.
3. Lấy MA price levels D/W/M từ Indicator Engine mà không duplicate calculation.
4. Normalize thành `LevelCandidate` contract.
5. Cluster các level gần nhau thành zones.
6. Classify đúng Support / Resistance.
7. Tính được normalized strength score.
8. Assign S1/S2/S3 và R1/R2/R3 theo proximity.
9. Output đúng `LevelLadderResult` contract.
10. Renderer chỉ consume `LevelLadderResult`.
11. Empty candidate input không làm chart crash.
12. Invalid critical input fail rõ ràng, không silent fallback.
13. Cùng input tạo deterministic output.
14. Test thực tế ít nhất một ticker có cả Support và Resistance.


---

# 24. V1 Implementation Contract

## 24.1 Scope

V1 được implement với duy nhất nguồn `MA`, gồm 12 configuration mục tiêu:

| Length | Daily | Weekly | Monthly |
|---:|---|---|---|
| 20 | MA20_D | MA20_W | MA20_M |
| 50 | MA50_D | MA50_W | MA50_M |
| 100 | MA100_D | MA100_W | MA100_M |
| 200 | MA200_D | MA200_W | MA200_M |

Runtime chọn family bằng `vw_Indicator_config.Parameters.length`, không parse period từ `ConfigCode`. Các MA length khác nếu tồn tại trong database không tham gia V1.

## 24.2 Runtime Source of Truth

```text
raw_stock_eod
    └── latest valid Close <= as_of_date
            ↓
        CurrentPrice

vw_Ticker_indicators
        +
vw_Indicator_config
        ↓
latest MA value per ConfigId + ComponentCode <= as_of_date
        ↓
LevelCandidate[]
```

Required public columns:

`vw_Ticker_indicators`
- Ticker
- Date
- ConfigId
- ComponentCode
- Value

`vw_Indicator_config`
- ConfigId
- ConfigCode
- IndicatorCode
- Timeframe
- Parameters
- ConfigIsEnabled
- IndicatorIsActive
- ComponentCode
- ComponentIsActive

Implementation phải fail rõ ràng nếu public view không đáp ứng contract. Không silent fallback sang internal persistence.

## 24.3 V1 Strength Model

```text
StrengthScore =
      35% SourceConfluenceScore
    + 25% TimeframeScore
    + 25% TouchScore
    + 15% RecencyScore
```

Default timeframe importance:

```text
D = 1.0
W = 1.5
M = 2.0
```

MA weights dùng khi tính representative price của cluster:

```text
MA20  = 0.80
MA50  = 1.00
MA100 = 1.15
MA200 = 1.30
```

Touch V1:
- history window: 252 observations;
- zone tolerance: 0.3%;
- saturation target: 4 touches.

Recency horizon: 180 days.

Final strength được normalize về 0–100. Strength không thay đổi proximity rank.

## 24.4 Clustering V1

Default:

```text
cluster_threshold_pct = 1%
neutral_threshold_pct = 0.3%
```

Clustering phải deterministic. Candidate được sort theo price/source trước khi cluster; representative price dùng weighted average. Zone gần/current price nằm trong neutral threshold được classify `CURRENT` và không nhận S/R rank.

---

# 25. NiceGUI Integration

V1 tạo tab mới trong:

```text
src/webapp/NiceGUI_chart.py
Tab label: R/S
```

Dependency direction:

```text
NiceGUI R/S Tab
      │
      ▼
build_level_ladder()
src/calcEngine/levelLadder.py
      │
      ▼
LevelLadderResult
      │
      ▼
build_level_ladder_chart_options()
src/Chart/levelLadderChart.py
      │
      ▼
NiceGUI EChart + Level Details Grid
```

UI không query DuckDB trực tiếp và không tính clustering/classification/strength/ranking.

Controls V1:
- Ticker, default MWG;
- optional As-of date;
- Cluster %;
- Refresh.

Outputs:
- Current Price;
- nearest R1;
- nearest S1;
- Reward/Risk;
- numeric price ladder chart;
- level details table.

Error state phải clear output cũ và hiển thị lỗi rõ ràng.

---

# 26. Physical Implementation

```text
src/calcEngine/levelLadder.py
    CurrentPrice
    LevelCandidate
    NormalizedLevel
    LevelZone
    ScoredLevel
    RankedLevel
    LevelLadderResult
    StrengthConfig
    load_current_price()
    load_ma_level_candidates()
    normalize_levels()
    cluster_levels()
    classify_zones()
    score_zones()
    rank_levels()
    build_level_ladder_from_data()
    build_level_ladder()

src/Chart/levelLadderChart.py
    build_level_ladder_chart_options()
    empty_level_ladder_chart_options()
    ladder_rows()

src/webapp/NiceGUI_chart.py
    rs_tab_content()

tests/test_rs_ladder.py
    focused automated domain tests

tests/test_R_S.md
    local MCP + production data + NiceGUI cross-check guide
```

Tên logical `test_R/S.md` không thể là một filename trên Windows/Git vì `/` là path separator, nên file repository-safe được chuẩn hóa thành `tests/test_R_S.md`.

---

# 27. V1 Failure / Empty-State Contract

- Current price không tồn tại → fail request rõ ràng.
- Public Indicator view thiếu required columns → `RuntimeError`; không fallback internal table.
- Price hợp lệ nhưng không có eligible MA level → trả empty Support/Resistance lists, renderer hiển thị empty state.
- Candidate invalid/NaN/<=0 → validation error.
- Missing S1 hoặc R1 → Reward/Risk = `None`.
- Same source data + same request/config → deterministic result.

---

# 28. MCP Cross-check Handoff

Local agent phải dùng MCP server `cherrymon-duckdb` để verify dữ liệu thật, theo:

```text
tests/test_R_S.md
```

Cross-check bắt buộc:
1. public views tồn tại;
2. schema columns đúng runtime contract;
3. MA20/50/100/200 có D/W/M active family;
4. current MWG Close khớp production output;
5. latest candidate values <= as_of_date khớp public views;
6. S1/R1 proximity invariants;
7. strength range 0–100;
8. NiceGUI R/S tab smoke test.

---

# 29. ADR

**Not required for V1.**

Lý do: implementation này áp dụng các ADR/architecture decision đã có:
- public Indicator Engine views là SSOT;
- read-only DuckDB access;
- calculation và rendering tách biệt.

Không tạo persistence model, database schema hay Source of Truth mới.

---

# 30. V2.0 Implementation Contract

V2.0 upgrades the MA-only implementation into a source-provider architecture while preserving the existing R/S downstream pipeline.

## 30.1 Default V2.0 Sources

```text
LEVEL
├── MA
│   └── TREND_AVERAGE
└── BB
    ├── LOWER
    ├── MIDDLE
    └── UPPER
        └── VOLATILITY_BAND

CONFIRMATION
└── RSI
    └── MOMENTUM_CONFIRMATION
```

Default runtime:

```python
build_level_ladder(
    ticker,
    enabled_sources=None,
)
```

resolves all registered V2.0 sources:

```text
MA + BB + RSI
```

Callers may still request a subset explicitly, for example:

```python
build_level_ladder(
    "MWG",
    enabled_sources=("MA",),
)
```

for MA-only regression comparison.

## 30.2 Indicator Provider Boundary

`vw_Ticker_indicators` and `vw_Indicator_config` are **inputs** to Indicator Providers.

```text
Indicator Engine
      │
      ▼
cal_indicator_values
      │
      ▼
vw_Ticker_indicators       ← calculated-value SSOT
vw_Indicator_config        ← metadata/config SSOT
      │
      │ READ
      ▼
Indicator Providers
      ├── MA Provider
      ├── BB Provider
      └── RSI Provider
      │
      ▼
Canonical R/S Contracts
      ├── LevelCandidate[]       ← MA / BB
      └── ConfirmationContext[]  ← RSI
      │
      ▼
R/S Domain
```

Indicator Providers are code adapters, not DuckDB objects.

They translate generic indicator values into R/S semantics and must not:

- calculate the indicator again;
- cluster levels;
- classify Support/Resistance;
- rank S/R levels;
- hard-code Strength weights.

## 30.3 Source Role and Value Semantic

Only the following combination may enter price normalization/clustering:

```text
SourceRole = LEVEL
AND
ValueSemantic = PRICE_LEVEL
```

V2.0 semantic contract:

| Indicator | Component | SourceRole | SourceFamily | ValueSemantic |
|---|---|---|---|---|
| MA | VALUE | LEVEL | TREND_AVERAGE | PRICE_LEVEL |
| BB | LOWER | LEVEL | VOLATILITY_BAND | PRICE_LEVEL |
| BB | MIDDLE | LEVEL | VOLATILITY_BAND | PRICE_LEVEL |
| BB | UPPER | LEVEL | VOLATILITY_BAND | PRICE_LEVEL |
| BB | WIDTH | not a LEVEL | — | VOLATILITY |
| BB | PERCENT | not a LEVEL | — | RATIO |
| RSI | VALUE | CONFIRMATION | MOMENTUM_CONFIRMATION | OSCILLATOR |

R/S-specific role/family stays in the R/S domain. Generic `ValueSemantic` and `Unit` live in Indicator Engine component metadata.

## 30.4 Family-based Confluence

V1 confluence used raw `source_count`.

V2.0 preserves `source_count` for lineage, but Strength confluence uses:

```text
source_family_count
```

with saturation.

Example:

```text
MA20_D + MA50_D + MA100_D + MA200_D
→ source_count = 4
→ source_family_count = 1
```

while:

```text
MA50_D + BB_LOWER_D
→ source_count = 2
→ source_family_count = 2
```

This prevents multiple correlated configurations from being treated as independent evidence.

## 30.5 RSI Confirmation

RSI does not create a price level.

It may change `strength_score` only.

```text
Support zone
+ lower RSI
→ stronger support confirmation

Resistance zone
+ higher RSI
→ stronger resistance confirmation
```

Invariant:

```text
RSI confirmation MUST NOT change S1/R1 proximity rank.
```

## 30.6 DuckDB Migration Dependency

Existing databases must run:

```text
src/DuckDB/sql/rs_v2_0_indicator_semantics.sql
```

before using V2.0 default runtime.

The migration:

1. adds `ValueSemantic` and `Unit` to `dim_indicator_component`;
2. populates semantics for MA, BB, RSI and ATR;
3. recreates `vw_Indicator_config` with both semantic columns.

ATR is included in the migration because it is already onboarded and will be used as V2.1 `CONTEXT`; ATR is **not consumed by V2.0 R/S**.

After running the migration, regenerate:

```text
docs/reference/DB_Metadata.md
docs/reference/dim_indicator.csv
docs/reference/dim_indicator_component.csv
docs/reference/dim_indicator_config.csv
```

using the existing DuckDB metadata export workflow.

## 30.7 V2.0 Physical Implementation

```text
src/calcEngine/levelLadder.py
    ConfirmationContext
    load_ma_level_candidates()
    load_bb_level_candidates()
    load_rsi_confirmation_contexts()
    _source_provider_registry()
    family-aware normalize / cluster / strength

src/Chart/levelLadderChart.py
    source-family explainability

src/webapp/NiceGUI_chart.py
    V2.0 MA + BB + RSI presentation

src/DuckDB/sql/rs_v2_0_indicator_semantics.sql
    explicit manual DuckDB migration

scripts/seed_dim_indicator_component.py
    fresh-environment semantic seeding
```

## 30.8 V2.0 Acceptance Criteria

V2.0 is complete when:

1. MA-only request still builds a deterministic ladder.
2. Default request includes MA + BB level providers and RSI confirmation.
3. BB LOWER/MIDDLE/UPPER can create `LevelCandidate`.
4. BB WIDTH/PERCENT never enter the price-level pipeline.
5. RSI never creates `LevelCandidate`.
6. `LEVEL` with non-`PRICE_LEVEL` semantic fails clearly.
7. Multiple same-family sources count as one family for confluence.
8. RSI may alter Strength but cannot alter proximity rank.
9. Public Indicator Engine SSOT remains the only technical-indicator read path.
10. Focused automated tests pass.
11. Production DuckDB migration and real-data cross-check pass before rollout.

---

# 31. V2.1 Implementation Contract

V2.1 extends V2.0 with volatility-aware distance rules and observed market-structure levels.

## 31.1 Default V2.1 Source Set

```text
LEVEL
├── MA                         TREND_AVERAGE
├── BB LOWER/MIDDLE/UPPER      VOLATILITY_BAND
└── MARKET_STRUCTURE
    ├── Swing High / Low
    ├── Previous Week H/L
    ├── Previous Month H/L
    └── 52W High / Low

CONTEXT
└── ATR14_D                    VOLATILITY_CONTEXT

CONFIRMATION
└── RSI14 D/W/M                MOMENTUM_CONFIRMATION
```

Default `build_level_ladder()` enables all registered V2.1 providers.

Explicit source subsets remain supported for regression and ablation.

## 31.2 ATR Adaptive Distance

ATR is context only and never enters price clustering as a level.

Primary context:

```text
ATR14_D
```

Formula:

```text
ATRPercent
    = ATR14_D / CurrentPrice

ClusterThresholdPct
    = max(
        MinClusterPct,
        ATRPercent × ATRClusterMultiplier
      )

NeutralThresholdPct
    = max(
        MinNeutralPct,
        ATRPercent × ATRNeutralMultiplier
      )
```

Current implementation defaults:

```text
MinClusterPct       = 1.0%
MinNeutralPct       = 0.3%
ATRClusterMultiplier = 0.50
ATRNeutralMultiplier = 0.15
```

If ATR context is unavailable for a historical date, V2.1 falls back to the configured minimum percent thresholds. This fallback is explicit and deterministic.

The actual thresholds used are exposed on `LevelLadderResult`:

```text
cluster_threshold_pct_used
neutral_threshold_pct_used
market_contexts
```

## 31.3 Point-in-Time Contract

Every structural candidate carries:

```text
source_date
confirmed_at
```

Invariant:

```text
source_date <= as_of_date
confirmed_at <= as_of_date
```

Any candidate with future `confirmed_at` must fail before normalization.

### Swing

```text
pivot_date
    = date where local high/low occurs

confirmed_at
    = date of the right-side confirmation bar
```

Default Swing parameters:

```text
left  = 3 bars
right = 3 bars
lookback = 252 bars
max candidates each side = 12
```

A pivot is not usable before enough right-side bars exist.

### Previous Week H/L

Only the last completed ISO week before the current week may be used.

Current partial week must never contribute to `PREV_WEEK_HIGH/LOW`.

### Previous Month H/L

Only the last completed calendar month before the current month may be used.

Current partial month must never contribute to `PREV_MONTH_HIGH/LOW`.

### 52W High/Low

Calculated from:

```text
as_of_date - 365 days
        ↓
as_of_date
```

using only raw bars with `Date <= as_of_date`.

## 31.4 Structural Source Contract

Structural candidates are created directly from `raw_stock_eod` and do not pass through Indicator Engine.

```text
raw_stock_eod
      │
      ├── SwingProvider
      ├── PreviousPeriodProvider
      └── 52WProvider
             │
             ▼
       LevelCandidate[]
```

Common semantics:

```text
source_type   = STRUCTURAL
source_role   = LEVEL
source_family = MARKET_STRUCTURE
value_semantic = PRICE_LEVEL
```

No new DuckDB object is required for these runtime providers in V2.1.

## 31.5 Strength V2.1 Refinement

V2.1 keeps:

- family diversity;
- timeframe confluence;
- touch quality;
- recency;
- RSI confirmation.

and adds:

```text
StructuralQuality
```

StructuralQuality is recency-sensitive evidence from MARKET_STRUCTURE sources.

The structural component is included only when a zone actually contains structural evidence, so indicator-only V2.0 levels are not automatically penalized.

Strength remains confidence only.

Invariant:

```text
Strength MUST NOT change proximity rank.
```

## 31.6 Backward Compatibility

V2.0-compatible source subsets remain valid.

MA-only regression:

```python
build_level_ladder(
    "MWG",
    enabled_sources=("MA",),
)
```

V2.0-like indicator-only comparison:

```python
build_level_ladder(
    "MWG",
    enabled_sources=("MA", "BB", "RSI"),
)
```

V2.1 indicator + ATR without structure:

```python
build_level_ladder(
    "MWG",
    enabled_sources=("MA", "BB", "ATR", "RSI"),
)
```

## 31.7 DuckDB Impact

V2.1 requires **no new schema migration**.

Existing production prerequisites are already satisfied by V2.0 + ATR onboarding:

```text
ATR14_D config
ATR VALUE semantic = VOLATILITY_DISTANCE
ATR Unit = PRICE
vw_Indicator_config exposes ValueSemantic / Unit
vw_Ticker_indicators contains ATR14_D backfill
raw_stock_eod contains historical OHLCV
```

Read-only preflight:

```text
src/DuckDB/sql/rs_v2_1_preflight.sql
```

must be used before production smoke/deployment.

## 31.8 Physical Implementation

```text
src/calcEngine/levelLadder.py
    MarketContext
    confirmed_at on LevelCandidate / NormalizedLevel
    StructuralSourceConfig
    load_atr_market_contexts()
    load_swing_level_candidates()
    load_previous_period_level_candidates()
    load_52w_level_candidates()
    resolve_adaptive_thresholds()
    structural quality scoring
    V2.1 provider registry / orchestration

src/webapp/NiceGUI_chart.py
    V2.1 header
    Min Cluster % floor
    actual adaptive threshold notification

src/Chart/levelLadderChart.py
    V2.1 empty state

src/DuckDB/sql/rs_v2_1_preflight.sql
    read-only production preflight

tests/test_rs_ladder.py
    V2.0 regression + V2.1 unit contracts

tests/test_R_S_V2_1.md
    local production cross-check
```

## 31.9 V2.1 Acceptance Criteria

V2.1 is complete when:

1. V2.0 focused tests remain PASS.
2. ATR14_D is loaded as CONTEXT, never LEVEL.
3. Adaptive cluster threshold uses max(percent floor, ATR distance).
4. Adaptive neutral threshold uses max(percent floor, ATR distance).
5. Swing candidates are unavailable before `confirmed_at`.
6. Previous Week levels exclude the current partial week.
7. Previous Month levels exclude the current partial month.
8. 52W levels use only bars at/before `as_of_date`.
9. Structural sources use MARKET_STRUCTURE family.
10. StructuralQuality can change Strength but never proximity rank.
11. Default V2.1 output preserves `source_family_count <= source_count`.
12. S1/R1 remain nearest eligible zones.
13. NiceGUI renders V2.1 without V2.0 stale text.
14. Read-only DuckDB preflight PASS.
15. Real-data MWG cross-check PASS before production rollout.

---

# 32. V2.2 Implementation Contract

V2.2 adds a dedicated Volume Profile domain to the existing R/S provider architecture.

## 32.1 Design Principle

Volume Profile is **not** registered as a technical indicator.

Reason:

- MA/BB/RSI/ATR are time-series technical indicators managed by Indicator Engine.
- POC/HVN/LVN are price-by-volume structures derived from a price window.
- Volume Profile uses its own calculation semantics and must remain a dedicated domain/provider.

Target flow:

```text
raw_stock_eod
      │
      │ Date / High / Low / Close / Volume
      ▼
Volume Profile Engine
      │
      ├── POC
      ├── HVN
      └── LVN
      │
      ├───────────────┐
      ▼               ▼
LevelCandidate[]   Volume Confirmation
      │               │
      └───────┬───────┘
              ▼
           R/S Core
```

## 32.2 Daily-OHLCV Approximation

Current CherryStock production source is daily OHLCV.

Daily bars do not contain true intraday tick-level volume-at-price.

Therefore V2.2 must not pretend exact exchange-level Volume Profile precision.

The implemented deterministic approximation:

1. select latest configured eligible daily bars;
2. calculate the total High–Low price range;
3. divide the price range into fixed bins;
4. distribute each daily bar's Volume uniformly across the bins crossed by its Low–High range;
5. aggregate volume per price bin;
6. derive POC/HVN/LVN from the aggregated profile.

This approximation is explicit and replaceable by a future intraday/tick provider without changing R/S core contracts.

## 32.3 VolumeProfileConfig

Default runtime contract:

```text
window_bars   = 120
bins          = 48
min_records   = 30

hvn_quantile  = 0.80
lvn_quantile  = 0.20

max_hvn       = 4
max_lvn       = 4
```

Validation:

```text
8 <= bins <= 256
min_records > 0
0 < lvn_quantile < hvn_quantile < 1
max_hvn/max_lvn >= 0
```

The configuration is passed through application/runtime code in V2.2.

No database configuration table is introduced in this release.

## 32.4 POC

POC = price bin with the highest aggregated volume.

Contract:

```text
source_code     = VP_POC
source_type     = VOLUME_PROFILE
source_role     = LEVEL
source_family   = VOLUME_STRUCTURE
value_semantic  = PRICE_LEVEL
```

POC is assigned the strongest Volume Profile representative weight.

## 32.5 HVN

HVN candidates are local volume maxima above the configured high-volume quantile.

Contract:

```text
VP_HVN_01
VP_HVN_02
...
```

All belong to:

```text
VOLUME_STRUCTURE
```

## 32.6 LVN

LVN candidates are local positive-volume minima below the configured low-volume quantile.

Contract:

```text
VP_LVN_01
VP_LVN_02
...
```

LVN is still a possible structural price boundary, but receives a lower representative weight than POC/HVN.

## 32.7 Volume Family Cap

POC, HVN and LVN are not independent source families.

All use:

```text
SourceFamily = VOLUME_STRUCTURE
```

Therefore:

```text
POC + HVN + LVN in same zone
        ↓
source_count may increase
source_family_count increases by at most 1
```

This prevents a dense Volume Profile from overpowering unrelated evidence such as MARKET_STRUCTURE or TREND_AVERAGE.

## 32.8 Volume Confirmation

The Volume Profile provider returns a bundle:

```text
ProviderBundle
├── LevelCandidate[]          POC/HVN/LVN
└── ConfirmationContext[]     node density confirmation
```

Each confirmation carries:

```text
source_family   = VOLUME_CONFIRMATION
reference_price = profile node price
value           = normalized node score 0–100
```

Volume confirmation contributes to Strength only when its `reference_price` belongs to the evaluated zone.

It never changes proximity rank.

## 32.9 Profile Node Score

Current node scoring:

```text
POC = 100

HVN =
    max(50, node_volume / poc_volume × 100)

LVN =
    bounded below 50 using node_volume / poc_volume
```

This score is a confirmation-strength input, not an S/R rank.

## 32.10 Point-in-Time Contract

Volume Profile input is filtered to:

```text
Date <= as_of_date
```

The selected profile uses the latest `window_bars` eligible rows from that bounded dataset.

For every generated Volume Profile candidate:

```text
source_date  = profile.window_end
confirmed_at = profile.window_end

source_date <= as_of_date
confirmed_at <= as_of_date
```

Future bars cannot influence historical profile calculations.

## 32.11 Performance Contract

V2.2 provider calculates one profile and returns both:

- Level candidates;
- volume confirmations.

It must not calculate the same Volume Profile once for LEVEL and again for CONFIRMATION in a single request.

The pure profile engine has no DuckDB/UI dependency.

Physical boundary:

```text
src/calcEngine/volumeProfile.py
    pure profile calculation

src/calcEngine/levelLadder.py
    DB provider adapter + R/S integration
```

## 32.12 Strength V2.2

Strength V2.2 keeps V2.1 components:

- family diversity;
- timeframe confluence;
- touch quality;
- recency;
- RSI confirmation;
- structural quality.

It adds:

```text
VolumeConfirmation
```

Default dedicated weight:

```text
volume_confirmation_weight = 0.10
```

This component is only included when a matching Volume Profile confirmation exists for the zone.

## 32.13 Backward Compatibility

V2.1 source set can still be requested explicitly:

```python
build_level_ladder(
    "MWG",
    enabled_sources=(
        "MA",
        "BB",
        "SWING",
        "PREVIOUS_HL",
        "52W_HL",
        "ATR",
        "RSI",
    ),
)
```

Volume-only research mode:

```python
build_level_ladder(
    "MWG",
    enabled_sources=("VOLUME_PROFILE",),
)
```

Default V2.2 enables all registered providers including `VOLUME_PROFILE`.

## 32.14 DuckDB Impact

V2.2 requires **no new DuckDB schema migration**.

Required source contract already exists:

```text
raw_stock_eod
├── Date
├── High
├── Low
├── Close
└── Volume
```

Read-only production preflight:

```text
src/DuckDB/sql/rs_v2_2_preflight.sql
```

No POC/HVN/LVN persistence table is introduced in V2.2.

Persistence/evaluation remains part of later architecture phases.

## 32.15 Physical Implementation

```text
src/calcEngine/volumeProfile.py
    VolumeProfileConfig
    VolumeProfileNode
    VolumeProfileResult
    build_volume_profile_from_history()

src/calcEngine/levelLadder.py
    ProviderBundle
    load_volume_profile_bundle()
    VOLUME_STRUCTURE
    VOLUME_CONFIRMATION
    Volume Profile representative weights
    Volume confirmation Strength component
    V2.2 provider registry/orchestration

src/DuckDB/sql/rs_v2_2_preflight.sql
    read-only production-data validation

tests/test_rs_ladder.py
    pure profile + provider + family-cap regression

tests/test_R_S_V2_2.md
    local production cross-check
```

## 32.16 V2.2 Acceptance Criteria

V2.2 is complete when:

1. all V2.1 focused regression tests remain PASS;
2. Volume Profile is calculated from raw OHLCV, not Indicator Engine;
3. POC is deterministic for identical input/config;
4. POC/HVN/LVN use VOLUME_STRUCTURE;
5. POC/HVN/LVN are PRICE_LEVEL candidates;
6. multiple Volume Profile nodes count as at most one family per zone;
7. volume confirmation is separate from level role;
8. volume confirmation may alter Strength but never rank;
9. future bars cannot enter historical profiles;
10. profile configuration validates explicit boundaries;
11. insufficient profile history fails clearly;
12. no new DuckDB schema migration is required;
13. read-only preflight PASS;
14. MWG real-data smoke PASS;
15. NiceGUI V2.2 smoke PASS.

---

# 33. V2.3 Evaluation, Calibration & Model Governance Contract

V2.3 does **not** replace the V2.2 runtime source/scoring behavior by itself.

Its purpose is to add a reproducible evidence layer around the production R/S model:

```text
R/S Runtime Snapshot
      │
      ▼
Historical Evaluation
      │
      ├── Hit / Touch
      ├── Break
      ├── Retest
      ├── Hold
      ├── Favorable / Adverse excursion
      ├── Temporal split
      ├── Ticker scope
      └── Market regime
      │
      ▼
Calibration / Ablation
      │
      ├── Source ablation
      ├── Family ablation
      ├── Weight challengers
      └── Complexity penalty
      │
      ▼
Incremental Promotion Gate
      │
      ├── VALIDATION improvement
      ├── TEST non-regression
      ├── Regime non-regression
      └── Complexity guardrail
      │
      ▼
PROMOTION_APPROVED
      │
      └── explicit later deployment/release required
```

A Promotion Gate approval must **not** silently change the production runtime configuration.

## 33.1 Runtime Model Version

R/S result now exposes:

```text
model_version
```

Default:

```text
RS_V2_3_BASELINE
```

The baseline preserves the production behavior introduced through V2.2.

Model-version tagging exists so every evaluation event can be traced back to the exact model/config being evaluated.

## 33.2 Model Specification

Canonical evaluation model contract:

```text
RSModelSpec
├── model_version
├── enabled_sources
├── strength_config
├── volume_profile_config
├── structural_config
├── parent_version
└── notes
```

Every model spec produces a deterministic signature:

```text
SHA-256(canonical JSON)[:16]
```

Source ordering does not change the signature.

## 33.3 Evaluation Event

Each evaluated ranked level creates one `LevelEvaluationEvent`:

```text
model_version
ticker
as_of_date

level_rank
level_type
level_price
strength_score

horizon_end_date

touched
touch_date

broken
break_date

retested
retest_date

held
bars_to_touch

max_favorable_pct
max_adverse_pct

source_count
source_family_count
sources
source_families

regime
split
```

Evaluation uses future bars only to label outcomes.

The R/S snapshot itself must still be calculated strictly point-in-time at `as_of_date`.

## 33.4 Forward Label Definitions

Default evaluation horizon:

```text
20 trading bars
```

### Touch

A level is touched when the future bar High/Low range intersects:

```text
level ± touch_tolerance_pct
```

Default:

```text
0.5%
```

### Break

Support break:

```text
Close < Level × (1 - break_tolerance_pct)
```

Resistance break:

```text
Close > Level × (1 + break_tolerance_pct)
```

Default break tolerance:

```text
0.5%
```

### Retest

After a confirmed break, a later bar must intersect:

```text
level ± retest_tolerance_pct
```

Default:

```text
0.5%
```

Retest uses its own tolerance and must not reuse touch tolerance implicitly.

### Hold

```text
Touched = TRUE
AND
Broken = FALSE
within evaluation horizon
```

## 33.5 Evaluation Metrics

Aggregated metrics:

```text
event_count
touch_count
break_count
retest_count
hold_count

touch_rate
break_rate_given_touch
retest_rate_given_break
hold_rate_given_touch

avg_bars_to_touch

avg_favorable_pct
avg_adverse_pct
directional_edge_pct

quality_score
```

Current composite quality:

```text
35% Touch Rate
35% Hold Rate Given Touch
10% Retest Rate Given Break
20% Directional Edge Component
```

This composite is an evaluation objective, not a runtime Strength score.

## 33.6 Temporal Split

Default split:

```text
TRAIN       60%
VALIDATION  20%
TEST        20%
```

Splits are chronological and never randomized.

Model selection/calibration may inspect TRAIN.

Promotion decisions require independent VALIDATION and TEST evidence.

## 33.7 Market Regime

Regime classification uses only observations available at/before each `as_of_date`.

Current categories:

```text
BULL_LOW_VOL
BULL_HIGH_VOL

BEAR_LOW_VOL
BEAR_HIGH_VOL

RANGE_LOW_VOL
RANGE_HIGH_VOL

UNKNOWN
```

Default regime lookback:

```text
60 bars
```

Default trend threshold:

```text
±8%
```

Default high-volatility daily return standard-deviation threshold:

```text
2.5%
```

Promotion Gate may reject a challenger if a material regime degrades beyond policy tolerance.

## 33.8 Source / Family Ablation

Canonical source-family mapping:

```text
MA              → TREND_AVERAGE
BB              → VOLATILITY_BAND

SWING           → MARKET_STRUCTURE
PREVIOUS_HL     → MARKET_STRUCTURE
52W_HL          → MARKET_STRUCTURE

VOLUME_PROFILE  → VOLUME_STRUCTURE

ATR             → VOLATILITY_CONTEXT
RSI             → MOMENTUM_CONFIRMATION
```

V2.3 can generate:

```text
FULL

DROP_SOURCE_<SOURCE>

DROP_FAMILY_<FAMILY>
```

Ablation variants use the same historical dataset/split/horizon as the baseline.

## 33.9 Calibration and Complexity Penalty

Calibration candidates are ranked by:

```text
PenalizedScore
=
QualityScore
-
ComplexityLambda × ComplexityScore
```

Default complexity proxy includes:

- number of enabled provider sources;
- number of Strength config overrides;
- number of Volume Profile config overrides;
- number of structural config overrides.

Purpose:

> A slightly more accurate model should not automatically beat a materially more complex model.

## 33.10 Incremental Promotion Gate

Default policy:

```text
min_validation_events = 200
min_test_events       = 100

min_validation_quality_delta = +0.02
min_test_quality_delta       =  0.00

max_regime_quality_degradation = 0.05
max_complexity_delta           = 0.15
```

A challenger is approved only when all mandatory conditions pass.

Output:

```text
PromotionDecision
├── promote
├── validation_quality_delta
├── test_quality_delta
├── complexity_delta
├── worst_regime_delta
└── reasons[]
```

## 33.11 Promotion Approval vs Runtime Deployment

Critical governance rule:

```text
Promotion Gate PASS
      ↓
PROMOTION_APPROVED
      ≠
automatic production model switch
```

The script:

```text
scripts/promote_rs_v2_3_model.py
```

defaults to dry-run.

With `--apply`, it records the Promotion Gate audit and marks the challenger:

```text
PROMOTION_APPROVED
```

It does **not** change the runtime default config.

A later explicit release/change must deploy an approved challenger.

## 33.12 Historical Evaluation Persistence

V2.3 introduces:

```text
dim_rs_model_version
cal_rs_evaluation_run
cal_rs_evaluation_event
cal_rs_evaluation_metric
sys_rs_model_promotion_audit
```

Ownership:

```text
dim_* = model/config registry
cal_* = calculated evaluation artifacts
sys_* = governance/audit
```

Migration:

```text
src/DuckDB/sql/rs_v2_3_evaluation_governance.sql
```

The migration is additive and idempotent.

## 33.13 Persistence Idempotency

Evaluation persistence uses stable keys.

Events:

```text
EvaluationRunId / Ticker / AsOfDate / LevelRank
```

Metrics:

```text
EvaluationRunId / ScopeType / ScopeKey / MetricCode
```

Rerunning persistence for the same `EvaluationRunId` replaces that run's events/metrics instead of accumulating duplicates.

## 33.14 Writer-Lock Contract

Historical model evaluation can be long-running.

Therefore:

```text
Historical calculations
    = read-only connection

Persistence
    = short writer UnitOfWork
```

V2.3 must not hold a DuckDB writer transaction throughout the historical backtest.

## 33.15 Cross-Ticker Evaluation

The evaluation runner accepts multiple tickers:

```text
--tickers MWG,FPT,HPG
```

Metrics are persisted at:

```text
OVERALL
SPLIT
TICKER
REGIME
LEVEL_TYPE
```

This enables detection of a model that improves aggregate results while degrading individual tickers or regimes.

## 33.16 Golden Regression Benchmark

Golden benchmark definition:

```text
tests/fixtures/rs_v2_3_golden_cases.json
```

Runner:

```text
scripts/run_rs_v2_3_golden.py
```

Golden invariants include:

- deterministic rank naming;
- proximity ordering;
- Strength in [0,100];
- source_family_count <= source_count;
- no future source_date;
- no future confirmed_at;
- support below current price;
- resistance above current price.

The golden benchmark checks runtime-contract regressions; it is separate from statistical model evaluation.

## 33.17 Physical Implementation

```text
src/calcEngine/levelLadder.py
    RS_MODEL_VERSION
    LevelLadderResult.model_version

src/calcEngine/rsEvaluation.py
    EvaluationConfig
    TemporalSplitConfig
    RSModelSpec
    LevelEvaluationEvent
    EvaluationMetrics
    AblationVariant
    PromotionPolicy
    PromotionDecision
    CalibrationScore
    event labeling
    aggregation
    temporal split
    regime classification
    ablation generation
    calibration ranking
    complexity penalty
    promotion gate
    golden invariant validation
    batch DataFrame contracts

src/cherrystock/infrastructure/database/repositories/
    rs_evaluation_repository.py

src/cherrystock/infrastructure/database/unit_of_work.py
    rs_evaluations repository

scripts/run_rs_v2_3_evaluation.py
scripts/promote_rs_v2_3_model.py
scripts/run_rs_v2_3_golden.py

src/DuckDB/sql/rs_v2_3_evaluation_governance.sql
src/DuckDB/sql/rs_v2_3_preflight.sql

tests/test_rs_evaluation.py
tests/test_R_S_V2_3.md
tests/fixtures/rs_v2_3_golden_cases.json
```

## 33.18 V2.3 Acceptance Criteria

V2.3 is complete when:

1. V2.0–V2.2 runtime regressions remain PASS.
2. runtime result exposes deterministic `model_version`.
3. event labels support touch/break/retest/hold.
4. outcome bars may be future, but signal generation remains point-in-time.
5. temporal split is chronological.
6. regime classification is point-in-time.
7. cross-ticker metrics are available.
8. source and family ablation variants are reproducible.
9. calibration applies a complexity penalty.
10. Promotion Gate validates VALIDATION + TEST + regimes + complexity.
11. Promotion Gate is dry-run by default.
12. approved challenger is not auto-deployed.
13. evaluation persistence is idempotent.
14. historical calculation does not hold a long writer lock.
15. DuckDB migration PASS.
16. read-only preflight PASS.
17. focused V2.3 pytest PASS.
18. golden benchmark PASS.
19. baseline multi-ticker historical evaluation persists events/metrics.
20. NiceGUI V2.3 smoke PASS.

---

# 34. V2.4 Source Effectiveness & Indicator Promotion

Detailed architecture:

```text
docs/architecture/RS_Source_Effectiveness.md
```

Requirement:

```text
REQ-0022
```

ADR:

```text
ADR-008
```

V2.4 preserves V2.3 R/S runtime behavior by default and adds a research/governance layer for determining whether a source/config adds incremental out-of-sample predictive value for each ticker.

Core separation:

```text
Runtime Strength
    !=
Source Effectiveness
    !=
Model Promotion Gate
    !=
Source Promotion Gate
```

New source research contract:

```text
build_level_ladder(
    ...,
    included_source_keys=None,
    excluded_source_keys=None,
)
```

Default `None` values preserve the existing runtime source set.

V2.4 persistence/public contracts:

```text
cal_rs_source_effectiveness_run
cal_rs_source_effectiveness
sys_rs_source_promotion_audit
vw_RS_Source_Effectiveness
```

Promotion approval remains non-deploying:

```text
APPROVED_FOR_INTEGRATION
    !=
automatic Indicator Engine change
    !=
automatic R/S registry/weight change
    !=
automatic production deployment
```

Concrete technical-indicator onboarding after approval remains owned by Indicator Management and requires a separate release/change request.



## 34.1 BB non-positive PRICE_LEVEL handling

Bollinger Band arithmetic may legitimately produce a non-positive LOWER value during extreme price acceleration:

```text
LOWER = MIDDLE - K * STD
```

For the R/S LEVEL domain:

```text
finite BB PRICE_LEVEL > 0
    -> valid LEVEL candidate

finite BB PRICE_LEVEL <= 0
    -> invalid tradable level
    -> skip candidate

NaN / Infinity
    -> data defect
    -> raise
```

This is a provider-normalization rule, not a change to the Indicator Engine formula.

The BB provider must preserve valid MIDDLE/UPPER candidates when a LOWER candidate is skipped.

The rule must not weaken ValueSemantic validation or silently swallow malformed indicator values.
