# Support / Resistance Level Ladder Architecture

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
6. Technical indicator values sử dụng `cal_indicator_values` làm source of truth.
7. Runtime không parse Parameters từ `ConfigCode`; Parameters phải được resolve từ `dim_indicator_config.Parameters`.
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
cal_indicator_values
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
- Trading date phải sử dụng `dimCalendar` hoặc helper hiện có của CherryStock.
- Không tự assume Monday–Friday là trading calendar.

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

Indicator Engine source of truth:

```text
dim_indicator
        │
dim_indicator_component
        │
dim_indicator_config
        │
cal_indicator_values
```

Reporting/read-side có thể ưu tiên các Single Source of Truth views hiện có khi contract phù hợp:

```text
"CherryMon"."main"."vw_Ticker_indicators"
"CherryMon"."main"."vw_Indicator_config"
```

Provider không được duplicate indicator calculation nếu giá trị đã tồn tại trong Indicator Engine.

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

V1 model:

```text
StrengthScore =
      SourceConfluenceScore
    + TimeframeScore
    + TouchScore
    + RecencyScore
```

Future model có thể bổ sung:

```text
VolumeScore
RejectionScore
ATRContextScore
HistoricalBreakScore
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

Không tính lại technical indicators đã tồn tại trong `cal_indicator_values` / reporting views.

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
