# CherryStock Indicator Engine Design

## 1. Purpose

Tài liệu này định nghĩa data model, execution flow, function contracts và migration strategy cho Technical Indicator Engine của CherryStock.

Mục tiêu chính:

- Hỗ trợ nhiều technical indicator trên Daily / Weekly / Monthly.
- Hỗ trợ indicator có một hoặc nhiều output/component, ví dụ Bollinger Bands, MACD, ADX/DMI, Stochastic, Ichimoku.
- Cho phép thêm indicator/config mới mà không cần `ALTER TABLE ADD COLUMN` trên historical table.
- Tách rõ indicator definition, executable config, component mapping và calculated value.
- Cho phép engine đọc parameter từ database và gọi indicator library theo cơ chế config-driven.
- Giảm ảnh hưởng tới historical data của indicator khác khi thêm hoặc thay đổi một indicator.
- Đảm bảo idempotent khi rerun pipeline.
- Hỗ trợ gradual migration từ `cal_Trends` hiện tại, tránh breaking change.
- Tạo nền tảng để sử dụng indicator values cho screening, scoring, charting và machine learning/prediction.

---

## 2. Design Principles

### 2.1. Không dùng một wide table chứa toàn bộ indicator làm source of truth

Không nên thiết kế theo dạng:

```text
Ticker
Date
MA20_D
MA50_D
MA100_D
MA200_D
RSI14_D
MACD_D
MACD_SIGNAL_D
MACD_HIST_D
BB_UPPER20_D
BB_MIDDLE20_D
BB_LOWER20_D
...
```

Vì khi thêm indicator mới sẽ phải:

- `ALTER TABLE ADD COLUMN`;
- thay đổi pipeline;
- backfill historical data;
- tăng coupling giữa các indicator;
- tăng rủi ro ảnh hưởng các indicator đang ổn định.

Wide table vẫn có thể được tạo ở feature/view layer để phục vụ query, dashboard hoặc ML, nhưng không nên là source of truth.

### 2.2. Không tách mỗi indicator thành một table riêng

Không nên tạo:

```text
cal_MA
cal_RSI
cal_MACD
cal_BB
cal_ATR
cal_ADX
...
```

Cách này làm số lượng table tăng nhanh, join phức tạp và khó maintain.

### 2.3. Source of truth theo long format

Thiết kế source of truth theo quan hệ:

```text
dim_indicator
        │
        ├──────────────► dim_indicator_component
        │
        ▼
dim_indicator_config
        │
        ▼
cal_indicator_values
```

Ý nghĩa:

```text
dim_indicator
    Indicator là gì?
    Thuộc category nào?
    Dùng engine/function nào?
    Cần input nào?

dim_indicator_component
    Indicator trả ra các output/component nào?

dim_indicator_config
    Indicator chạy với parameter nào?
    Timeframe nào?
    Warmup bao nhiêu bars?

cal_indicator_values
    Value thực tế theo Ticker + Date + Config + Component
```

---

## 3. Naming Convention

CherryStock hiện sử dụng convention cho các column indicator ở wide `cal_*` table:

```text
<INDICATOR><PERIOD>_<TIMEFRAME>
```

Ví dụ:

```text
MA20_D
MA50_W
RSI14_M
```

Đối với Indicator Engine mới cần phân biệt rõ:

### 3.1. `IndicatorCode`

Chỉ mô tả loại indicator, không encode period/timeframe.

Ví dụ:

```text
MA
EMA
RSI
BB
MACD
ATR
ADX
OBV
MFI
STOCH
SUPERTREND
ICHIMOKU
```

### 3.2. `ComponentCode`

Mô tả output chuẩn nội bộ của CherryStock.

Ví dụ:

```text
VALUE
UPPER
MIDDLE
LOWER
WIDTH
PERCENT
LINE
SIGNAL
HIST
PLUS_DI
MINUS_DI
K
D
```

### 3.3. `ConfigCode`

ConfigCode là tên đọc được, stable và unique để biểu diễn một executable config.

Ví dụ:

```text
MA20_D
MA50_D
RSI14_D
BB20_2_D
MACD12_26_9_D
ATR14_D
ADX14_D
```

Đối với indicator nhiều parameter, ConfigCode có thể encode parameter chính để dễ nhận diện, nhưng logic runtime phải đọc từ `Parameters` JSON, không parse ngược từ `ConfigCode`.

### 3.4. `Timeframe`

Chuẩn hóa:

```text
D = Daily
W = Weekly
M = Monthly
```

---

# 4. Data Model

## 4.1. `dim_indicator`

### Mục đích

Lưu master definition của indicator.

Một indicator chỉ được define một lần, không phụ thuộc period hay timeframe.

### DDL đề xuất

```sql
CREATE TABLE "CherryMon"."main"."dim_indicator" (
    IndicatorCode       VARCHAR NOT NULL,
    IndicatorName       VARCHAR NOT NULL,
    Category            VARCHAR NOT NULL,

    Engine              VARCHAR NOT NULL,
    FunctionName        VARCHAR NOT NULL,

    RequiredInputs      JSON NOT NULL,
    ParameterSchema     JSON,

    Description         VARCHAR,

    IsActive            BOOLEAN NOT NULL DEFAULT TRUE,

    CreatedAt           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt           TIMESTAMP,

    PRIMARY KEY (IndicatorCode)
);
```

### Field definition

| Field | Purpose |
|---|---|
| `IndicatorCode` | Mã indicator chuẩn nội bộ |
| `IndicatorName` | Tên đầy đủ |
| `Category` | TREND / MOMENTUM / VOLATILITY / VOLUME / STRUCTURE / RELATIVE_STRENGTH... |
| `Engine` | Engine implementation, ví dụ `PANDAS_TA` |
| `FunctionName` | Function logical name của library |
| `RequiredInputs` | Danh sách input fields cần thiết |
| `ParameterSchema` | Schema dùng validate `Parameters` |
| `Description` | Mô tả indicator |
| `IsActive` | Có cho phép dùng indicator hay không |

### Ví dụ

#### MA

```text
IndicatorCode = MA
IndicatorName = Moving Average
Category      = TREND
Engine        = PANDAS_TA
FunctionName  = sma
RequiredInputs = ["Close"]
```

#### RSI

```text
IndicatorCode = RSI
IndicatorName = Relative Strength Index
Category      = MOMENTUM
Engine        = PANDAS_TA
FunctionName  = rsi
RequiredInputs = ["Close"]
```

#### Bollinger Bands

```text
IndicatorCode = BB
IndicatorName = Bollinger Bands
Category      = VOLATILITY
Engine        = PANDAS_TA
FunctionName  = bbands
RequiredInputs = ["Close"]
```

#### ADX

```text
IndicatorCode = ADX
IndicatorName = Average Directional Index
Category      = TREND
Engine        = PANDAS_TA
FunctionName  = adx
RequiredInputs = ["High", "Low", "Close"]
```

#### OBV

```text
IndicatorCode = OBV
IndicatorName = On Balance Volume
Category      = VOLUME
Engine        = PANDAS_TA
FunctionName  = obv
RequiredInputs = ["Close", "Volume"]
```

---

## 4.2. `ParameterSchema`

Không để library tự fallback default khi config sai.

Ví dụ Bollinger Bands:

```json
{
  "length": {
    "type": "integer",
    "min": 2,
    "required": true
  },
  "std": {
    "type": "number",
    "min": 0,
    "required": true
  }
}
```

MACD:

```json
{
  "fast": {
    "type": "integer",
    "min": 1,
    "required": true
  },
  "slow": {
    "type": "integer",
    "min": 2,
    "required": true
  },
  "signal": {
    "type": "integer",
    "min": 1,
    "required": true
  }
}
```

Engine validation phải đảm bảo các relationship hợp lệ, ví dụ:

```text
fast < slow
```

---

## 4.3. `dim_indicator_component`

### Mục đích

Chuẩn hóa indicator có một hoặc nhiều output.

Không coi mỗi output là một indicator khác nhau.

### DDL đề xuất

```sql
CREATE TABLE "CherryMon"."main"."dim_indicator_component" (
    IndicatorCode       VARCHAR NOT NULL,
    ComponentCode       VARCHAR NOT NULL,

    ComponentName       VARCHAR NOT NULL,

    OutputPrefix        VARCHAR,
    SortOrder           INTEGER,

    IsPrimary           BOOLEAN NOT NULL DEFAULT FALSE,
    IsActive            BOOLEAN NOT NULL DEFAULT TRUE,

    PRIMARY KEY (
        IndicatorCode,
        ComponentCode
    )
);
```

### Ý nghĩa `OutputPrefix`

Library có thể trả tên column phụ thuộc implementation.

Ví dụ pandas-ta style Bollinger output:

```text
BBL_20_2.0
BBM_20_2.0
BBU_20_2.0
BBB_20_2.0
BBP_20_2.0
```

CherryStock normalize thành:

```text
LOWER
MIDDLE
UPPER
WIDTH
PERCENT
```

`OutputPrefix` dùng để map library output về component chuẩn nội bộ.

### Bollinger Bands components

| IndicatorCode | ComponentCode | OutputPrefix | Meaning |
|---|---|---|---|
| BB | LOWER | BBL | Lower band |
| BB | MIDDLE | BBM | Middle band |
| BB | UPPER | BBU | Upper band |
| BB | WIDTH | BBB | Band width |
| BB | PERCENT | BBP | Percent position |

### MACD components

| IndicatorCode | ComponentCode | OutputPrefix |
|---|---|---|
| MACD | LINE | MACD |
| MACD | SIGNAL | MACDs |
| MACD | HIST | MACDh |

### ADX components

| IndicatorCode | ComponentCode | OutputPrefix |
|---|---|---|
| ADX | ADX | ADX |
| ADX | PLUS_DI | DMP |
| ADX | MINUS_DI | DMN |

### STOCH components

```text
STOCH
├── K
└── D
```

### Ichimoku components

```text
ICHIMOKU
├── TENKAN
├── KIJUN
├── SENKOU_A
├── SENKOU_B
└── CHIKOU
```

---

## 4.4. `dim_indicator_config`

### Mục đích

Lưu executable configuration.

Indicator definition không thay đổi theo period/timeframe. Config mới là object engine phải execute.

### DDL đề xuất

```sql
CREATE SEQUENCE IF NOT EXISTS seq_indicator_config START 1;

CREATE TABLE "CherryMon"."main"."dim_indicator_config" (
    ConfigId            BIGINT NOT NULL
                        DEFAULT nextval('seq_indicator_config'),

    ConfigCode          VARCHAR NOT NULL,

    IndicatorCode       VARCHAR NOT NULL,
    Timeframe           VARCHAR NOT NULL,

    Parameters          JSON NOT NULL,

    WarmupBars          INTEGER,

    IsEnabled           BOOLEAN NOT NULL DEFAULT TRUE,

    Description         VARCHAR,

    CreatedAt           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt           TIMESTAMP,

    PRIMARY KEY (ConfigId),
    UNIQUE (ConfigCode)
);
```

### Ví dụ config

| ConfigCode | IndicatorCode | Timeframe | Parameters |
|---|---|---|---|
| MA20_D | MA | D | `{"length":20}` |
| MA50_D | MA | D | `{"length":50}` |
| MA200_D | MA | D | `{"length":200}` |
| RSI14_D | RSI | D | `{"length":14}` |
| BB20_2_D | BB | D | `{"length":20,"std":2}` |
| MACD12_26_9_D | MACD | D | `{"fast":12,"slow":26,"signal":9}` |
| ATR14_D | ATR | D | `{"length":14}` |
| ADX14_D | ADX | D | `{"length":14}` |

### Quy tắc Parameters

Luôn lưu JSON chuẩn.

Nên:

```json
{
  "fast": 12,
  "slow": 26,
  "signal": 9
}
```

Không nên:

```text
FAST=12;SLOW=26;SIGNAL=9
```

Lý do:

- parse đơn giản;
- type-safe hơn;
- validate được;
- mở rộng parameter không cần thay schema;
- dễ audit/config compare.

---

## 4.5. `WarmupBars`

### Mục đích

Indicator cần historical bars trước checkpoint để tính chính xác.

Ví dụ:

```text
MA20  -> minimum warmup khoảng 20 bars
MA200 -> minimum warmup khoảng 200 bars
RSI14 -> minimum warmup khoảng 14 bars
MACD  -> cần nhiều hơn slow period để ổn định output
```

Nếu pipeline chạy:

```text
from_last_day = 30
```

thì không được chỉ load 30 ngày.

Ví dụ MA200:

```text
Target range:     30 trading days
Warmup required: 200 bars

Load >= 230 trading bars
Calculate full loaded range
Persist only target range
```

Nguyên tắc này tương thích với logic hiện tại của `cal_Moving_Average()`, nơi full historical data được sử dụng để tính MA trước khi cắt checkpoint để upsert.

---

## 4.6. `cal_indicator_values`

### Mục đích

Là source of truth của technical indicator values.

### DDL đề xuất

```sql
CREATE TABLE "CherryMon"."main"."cal_indicator_values" (
    Ticker              VARCHAR NOT NULL,
    Date                DATE NOT NULL,

    ConfigId            BIGINT NOT NULL,
    ComponentCode       VARCHAR NOT NULL,

    Value               DOUBLE,

    CalculatedAt        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (
        Ticker,
        Date,
        ConfigId,
        ComponentCode
    )
);
```

### Tại sao không duplicate metadata?

Fact table không cần lưu lại:

```text
IndicatorCode
Timeframe
Period
Parameters
```

vì các thông tin này resolve được từ:

```text
ConfigId
   ↓
dim_indicator_config
```

Điều này giảm duplication và tránh config/value mismatch.

### Bollinger example

Config:

```text
ConfigId      = 4
ConfigCode    = BB20_2_D
IndicatorCode = BB
Timeframe     = D
Parameters    = {"length":20,"std":2}
```

Values:

```text
Ticker  Date        ConfigId ComponentCode Value
-------------------------------------------------
MWG     2026-08-25  4        UPPER         82.50
MWG     2026-08-25  4        MIDDLE        78.20
MWG     2026-08-25  4        LOWER         73.90
MWG     2026-08-25  4        WIDTH          8.60
MWG     2026-08-25  4        PERCENT        0.67
```

### MACD example

```text
MWG | 2026-08-25 | 8 | LINE   | 1.25
MWG | 2026-08-25 | 8 | SIGNAL | 0.95
MWG | 2026-08-25 | 8 | HIST   | 0.30
```

### Primary key

```text
Ticker + Date + ConfigId + ComponentCode
```

Mục tiêu:

- idempotent rerun;
- không duplicate;
- update đúng component;
- cho phép một indicator/config sinh nhiều values.

---

# 5. Timeframe Model

## 5.1. Daily

Daily dùng trực tiếp EOD OHLCV.

```text
Date = trading date
```

## 5.2. Weekly

Resample từ daily:

```text
Open   = first Open
High   = max High
Low    = min Low
Close  = last Close
Volume = sum Volume
Date   = last actual trading date of week
```

Không hard-code Friday vì có holiday hoặc market closure.

## 5.3. Monthly

```text
Open   = first Open
High   = max High
Low    = min Low
Close  = last Close
Volume = sum Volume
Date   = last actual trading date of month
```

Không dùng calendar day 30/31 làm date nếu ngày đó không giao dịch.

---

# 6. Indicator Library Strategy

## 6.1. Main Engine

Định hướng implementation:

```text
pandas-ta-classic
```

Lý do phù hợp với config-driven engine:

- pandas/DataFrame friendly;
- hỗ trợ nhiều indicator;
- indicator signature tự nhiên theo parameter;
- nhiều indicator trả `Series` hoặc `DataFrame`;
- dễ adapter và normalize;
- dễ batch theo ticker/timeframe.

## 6.2. TA-Lib

Có thể dùng TA-Lib cho:

- reference validation;
- parity test;
- backend thay thế cho một số indicator phổ biến;
- performance optimization nếu cần.

Không nên để database phụ thuộc trực tiếp naming/output format của TA-Lib hay pandas-ta.

## 6.3. VectorBT

Không dùng VectorBT làm storage indicator engine chính.

VectorBT phù hợp hơn cho:

```text
parameter sweep
strategy backtest
portfolio simulation
optimization
```

Có thể đặt phía sau Indicator Engine.

---

# 7. Indicator Registry

Không gọi arbitrary function trực tiếp từ giá trị `FunctionName` trong DB bằng `getattr()` mà không whitelist.

Không nên:

```python
func = getattr(ta, function_name)
result = func(**params)
```

Nên có registry nội bộ:

```python
INDICATOR_REGISTRY = {
    "MA": "sma",
    "EMA": "ema",
    "RSI": "rsi",
    "BB": "bbands",
    "MACD": "macd",
    "ADX": "adx",
    "ATR": "atr",
    "OBV": "obv",
    "MFI": "mfi",
}
```

Registry có trách nhiệm:

- whitelist indicator;
- resolve library function;
- enforce expected input contract;
- tạo nơi centralized để custom adapter nếu library API khác nhau;
- tránh database điều khiển arbitrary Python execution.

---

# 8. Python Domain Models

Không truyền raw dictionary xuyên suốt engine nếu có thể tránh.

Đề xuất dùng lightweight dataclass.

```python
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IndicatorDefinition:
    indicator_code: str
    indicator_name: str
    category: str
    engine: str
    function_name: str
    required_inputs: tuple[str, ...]
    parameter_schema: dict[str, Any] | None


@dataclass(frozen=True)
class IndicatorComponent:
    indicator_code: str
    component_code: str
    component_name: str
    output_prefix: str | None
    is_primary: bool


@dataclass(frozen=True)
class IndicatorConfig:
    config_id: int
    config_code: str
    indicator_code: str
    timeframe: str
    parameters: dict[str, Any]
    warmup_bars: int
```

Không cần ORM ở phase đầu vì CherryStock hiện sử dụng DuckDB/pandas trực tiếp.

---

# 9. Function Contracts

## 9.1. Config/metadata access

### `get_indicator_definition()`

```python
def get_indicator_definition(
    indicator_code: str,
    *,
    connection=None,
) -> IndicatorDefinition:
    ...
```

Responsibility:

- đọc một indicator definition;
- parse `RequiredInputs`;
- parse `ParameterSchema`;
- raise nếu indicator không tồn tại hoặc disabled khi execution yêu cầu active indicator.

---

### `get_indicator_components()`

```python
def get_indicator_components(
    indicator_code: str,
    *,
    connection=None,
) -> list[IndicatorComponent]:
    ...
```

Responsibility:

- lấy output mapping;
- chỉ lấy component active;
- sort theo `SortOrder`.

---

### `get_enabled_indicator_configs()`

```python
def get_enabled_indicator_configs(
    *,
    config_ids: list[int] | None = None,
    indicator_codes: list[str] | None = None,
    timeframes: list[str] | None = None,
    connection=None,
) -> list[IndicatorConfig]:
    ...
```

Use cases:

```python
get_enabled_indicator_configs()
```

Lấy toàn bộ config enabled.

```python
get_enabled_indicator_configs(
    indicator_codes=["MA", "RSI", "BB"],
    timeframes=["D"],
)
```

Lấy subset.

---

## 9.2. Validation

### `validate_indicator_config()`

```python
def validate_indicator_config(
    config: IndicatorConfig,
    definition: IndicatorDefinition,
) -> None:
    ...
```

Validate tối thiểu:

- timeframe hợp lệ;
- required parameters tồn tại;
- datatype đúng;
- min/max hợp lệ;
- parameter relationships hợp lệ;
- unsupported parameter phải được xử lý rõ ràng;
- không silent fallback về library default nếu config sai.

Ví dụ invalid:

```json
{
  "length": -20,
  "std": "abc"
}
```

Phải raise validation error.

---

## 9.3. Source Data

### `load_indicator_source_data()`

```python
def load_indicator_source_data(
    *,
    tickers: list[str] | None = None,
    start_date=None,
    end_date=None,
    required_inputs: tuple[str, ...],
    connection=None,
) -> pd.DataFrame:
    ...
```

Responsibility:

- đọc `raw_stock_eod`;
- chỉ query explicit fields cần thiết;
- không `SELECT *`;
- filter ticker/date khi có;
- chỉ lấy active ticker nếu business rule yêu cầu;
- sort `Ticker, Date`;
- validation required columns.

Ví dụ ADX chỉ cần:

```sql
SELECT
    Ticker,
    Date,
    High,
    Low,
    Close
FROM ...
```

OBV:

```sql
SELECT
    Ticker,
    Date,
    Close,
    Volume
FROM ...
```

Batch engine có thể union required inputs của nhiều configs để load một lần.

---

## 9.4. Timeframe Resampling

### `resample_indicator_timeframe()`

```python
def resample_indicator_timeframe(
    price_df: pd.DataFrame,
    timeframe: str,
) -> pd.DataFrame:
    ...
```

Rules:

```text
D -> no resample
W -> weekly OHLCV
M -> monthly OHLCV
```

Output giữ schema chuẩn:

```text
Ticker
Date
Open
High
Low
Close
Volume
```

---

## 9.5. Registry Resolution

### `resolve_indicator_function()`

```python
def resolve_indicator_function(
    indicator_code: str,
):
    ...
```

Responsibility:

- lookup whitelist registry;
- resolve implementation;
- fail explicitly nếu unsupported indicator.

---

## 9.6. Core Calculation

### `calculate_indicator_from_config()`

```python
def calculate_indicator_from_config(
    source_df: pd.DataFrame,
    config: IndicatorConfig,
    definition: IndicatorDefinition,
    components: list[IndicatorComponent],
) -> pd.DataFrame:
    ...
```

Responsibility:

1. validate config;
2. validate required input columns;
3. split/group theo ticker;
4. call registered indicator function;
5. normalize library output;
6. attach ConfigId;
7. return standard long-format DataFrame.

Output schema bắt buộc:

```text
Ticker
Date
ConfigId
ComponentCode
Value
```

Không return library-specific column names cho caller phía ngoài engine.

---

## 9.7. Output Normalization

### `normalize_indicator_output()`

```python
def normalize_indicator_output(
    *,
    ticker: str,
    config: IndicatorConfig,
    raw_output: pd.Series | pd.DataFrame,
    components: list[IndicatorComponent],
) -> pd.DataFrame:
    ...
```

Responsibility:

- `Series` -> default `VALUE` component;
- `DataFrame` -> map output prefix sang component;
- ensure exactly expected component mapping;
- detect missing/unknown output;
- convert numeric value safely;
- preserve Date alignment.

Ví dụ Bollinger:

```text
BBU_20_2.0 -> UPPER
BBM_20_2.0 -> MIDDLE
BBL_20_2.0 -> LOWER
BBB_20_2.0 -> WIDTH
BBP_20_2.0 -> PERCENT
```

Ví dụ MACD:

```text
MACD_12_26_9  -> LINE
MACDs_12_26_9 -> SIGNAL
MACDh_12_26_9 -> HIST
```

Database không phụ thuộc naming convention của library.

---

## 9.8. Batch Calculation

### `calculate_indicator_batch()`

```python
def calculate_indicator_batch(
    source_df: pd.DataFrame,
    configs: list[IndicatorConfig],
    definitions: dict[str, IndicatorDefinition],
    components: dict[str, list[IndicatorComponent]],
) -> pd.DataFrame:
    ...
```

Mục tiêu:

- tránh query database trong loop;
- reuse same source DataFrame;
- group configs theo timeframe;
- xử lý nhiều indicator trong một execution context;
- concatenate normalized results.

Ví dụ một lần load OHLCV rồi chạy:

```text
MA20
MA50
MA200
RSI14
BB20
MACD
ATR
ADX
```

---

## 9.9. Persistence

### `upsert_indicator_values()`

```python
def upsert_indicator_values(
    indicator_values: pd.DataFrame,
    *,
    connection=None,
    repository=None,
) -> int:
    ...
```

Required input columns:

```text
Ticker
Date
ConfigId
ComponentCode
Value
```

Upsert key:

```text
Ticker
Date
ConfigId
ComponentCode
```

Pseudo SQL:

```sql
INSERT INTO cal_indicator_values (
    Ticker,
    Date,
    ConfigId,
    ComponentCode,
    Value,
    CalculatedAt
)
SELECT
    Ticker,
    Date,
    ConfigId,
    ComponentCode,
    Value,
    CURRENT_TIMESTAMP
FROM df_indicator_values
ON CONFLICT (
    Ticker,
    Date,
    ConfigId,
    ComponentCode
)
DO UPDATE SET
    Value = EXCLUDED.Value,
    CalculatedAt = CURRENT_TIMESTAMP;
```

Idempotency expectation:

```text
run #1 -> insert
run #2 -> update same key
no duplicate
```

---

## 9.10. Main Orchestration Function

### `refresh_technical_indicators()`

```python
def refresh_technical_indicators(
    *,
    from_last_day: int | None = None,
    tickers: list[str] | None = None,
    config_ids: list[int] | None = None,
    timeframes: list[str] | None = None,
    connection=None,
    repository=None,
) -> dict:
    ...
```

Đây là public API chính cho Indicator Engine.

Use cases:

### Calculate all enabled configs

```python
refresh_technical_indicators()
```

### Incremental refresh

```python
refresh_technical_indicators(
    from_last_day=30,
)
```

### Specific tickers

```python
refresh_technical_indicators(
    tickers=["MWG", "FPT"],
)
```

### Specific configs

```python
refresh_technical_indicators(
    config_ids=[1, 3, 4],
)
```

### Specific timeframe

```python
refresh_technical_indicators(
    timeframes=["D"],
)
```

Suggested return summary:

```python
{
    "status": "SUCCESS",
    "configs_processed": 25,
    "tickers_processed": 1200,
    "rows_calculated": 250000,
    "rows_upserted": 250000,
    "from_date": "...",
    "to_date": "...",
    "errors": [],
    "warnings": []
}
```

---

# 10. Main Execution Flow

```text
refresh_technical_indicators()
                │
                ▼
get_enabled_indicator_configs()
                │
                ▼
get indicator definitions/components
                │
                ▼
validate_indicator_config()
                │
                ▼
group configs by timeframe
                │
                ▼
calculate warmup requirement
                │
                ▼
union required OHLCV inputs
                │
                ▼
load_indicator_source_data()
                │
                ├───────── D ──────────┐
                │                     │
                ├── resample W ───────┤
                │                     │
                └── resample M ───────┤
                                      ▼
                         calculate_indicator_batch()
                                      │
                                      ▼
                     calculate_indicator_from_config()
                                      │
                                      ▼
                       normalize_indicator_output()
                                      │
                                      ▼
                        cal_indicator_values
```

---

# 11. Warmup and Incremental Refresh Strategy

## 11.1. Requirement

Incremental calculation must not generate incorrect values near checkpoint.

For every execution:

```text
persist_start_date
        ↓
resolve maximum required warmup among selected configs
        ↓
load historical source before persist_start_date
        ↓
calculate entire loaded window
        ↓
trim normalized output
        ↓
persist target date range only
```

## 11.2. Example

Selected configs:

```text
MA20_D   warmup = 20
MA200_D  warmup = 200
RSI14_D  warmup = 14
```

Target:

```text
from_last_day = 30
```

Load requirement should be based on max warmup:

```text
30 target trading bars + >= 200 historical bars
```

Không query riêng source cho từng config.

---

# 12. Multi-Timeframe Processing Strategy

Đề xuất group configs:

```text
configs_D
configs_W
configs_M
```

Một lần load Daily OHLCV đủ historical range.

Sau đó:

```text
Daily source
   ├── directly calculate D
   ├── resample -> Weekly -> calculate W
   └── resample -> Monthly -> calculate M
```

Không cần lưu thêm raw weekly/monthly table ở phase đầu nếu chưa có business requirement khác.

---

# 13. Data Access Rules

Bám convention hiện tại của CherryStock:

- Use `DuckDBManager` / central connection convention.
- Read query ưu tiên read-only connection.
- Write workflow reuse caller-managed connection khi có.
- Không hard-code DuckDB path.
- Không query database trong loop nếu có thể batch.
- Explicit selected columns; tránh `SELECT *`.
- Upsert phải idempotent.
- Khi orchestration gồm nhiều write steps cần atomicity, ưu tiên existing UnitOfWork/transaction pattern của project.

---

# 14. Error Handling

Indicator Engine không được silent failure đối với lỗi có thể làm sai dữ liệu.

## Errors nên block config/pipeline

Ví dụ:

- config thiếu required parameter;
- invalid parameter type;
- `fast >= slow` với MACD;
- missing required OHLCV input;
- unsupported indicator;
- output library không map được component;
- duplicate primary key trong normalized output;
- non-numeric indicator output không expected.

## Warning cases

Ví dụ:

- warmup chưa đủ do ticker mới niêm yết;
- một số initial values là NULL vì lookback;
- component hợp lệ nhưng không có output ở early bars.

Warnings phải log rõ context:

```text
Ticker
ConfigCode
Date range
Reason
```

---

# 15. Data Quality Validation

Sau persist nên tích hợp `validate_data_quality()` nếu contract phù hợp.

Validation tối thiểu cho `cal_indicator_values`:

```text
Duplicate key:
Ticker + Date + ConfigId + ComponentCode

Unexpected NULL:
- NULL ở warmup range có thể expected
- NULL bất thường sau valid calculation range phải flag

Freshness:
latest indicator Date phải phù hợp latest expected trading date

Config completeness:
expected active configs phải có recent values

Component completeness:
BB expected UPPER/MIDDLE/LOWER/... theo metadata
MACD expected LINE/SIGNAL/HIST
```

Kết quả quality validation nên log và persist theo `sys_data_quality_audit` convention hiện tại.

---

# 16. Wide Feature/View Layer

Long-format `cal_indicator_values` là source of truth.

Dashboard/model thường cần wide data.

Có thể tạo view/materialized table phía trên:

```text
cal_indicator_values
        ↓
pivot/feature builder
        ↓
vw_technical_core
or
cal_technical_core
```

Ví dụ output:

```text
Ticker
Date
MA20_D
MA50_D
MA200_D
RSI14_D
BB20_2_D_UPPER
BB20_2_D_MIDDLE
BB20_2_D_LOWER
MACD12_26_9_D_LINE
MACD12_26_9_D_SIGNAL
MACD12_26_9_D_HIST
ATR14_D
```

Wide naming phải follow convention được define rõ ràng.

Đối với multi-component indicator, đề xuất format feature column:

```text
<CONFIG_CODE>_<COMPONENT_CODE>
```

Ví dụ:

```text
BB20_2_D_UPPER
BB20_2_D_MIDDLE
BB20_2_D_LOWER
MACD12_26_9_D_LINE
MACD12_26_9_D_SIGNAL
MACD12_26_9_D_HIST
```

Đối với single-value indicator có `ComponentCode = VALUE`, có thể giữ ConfigCode trực tiếp:

```text
MA20_D
RSI14_D
ATR14_D
```

---

# 17. Technical Feature Layer for Prediction

Indicator storage và ML feature engineering là hai layer khác nhau.

Không nên chỉ feed raw indicator value vào model.

Có thể derive thêm feature:

```text
DIST_MA20_D
DIST_MA50_D
DIST_MA200_D
SLOPE_MA50_D
SLOPE_MA200_D
PRICE_ABOVE_MA50_D
CROSS_MA20_MA50_D
BB_POSITION20_D
BB_WIDTH20_D
MACD_HIST_D
VOL_RATIO20_D
RET_20_D
RET_60_D
RS_VNINDEX_60_D
```

Flow:

```text
raw_stock_eod
      ↓
Indicator Engine
      ↓
cal_indicator_values
      ↓
Feature Builder
      ↓
cal_technical_features
      ↓
Technical Score / Screener / ML Model
```

Không lưu derived ML feature vào `dim_indicator_config` nếu bản chất không phải technical indicator library output. Nên define feature layer riêng khi scope rõ hơn.

---

# 18. Proposed File Structure

```text
src/
├── calcEngine/
│   ├── calcIndicators.py
│   └── indicatorRegistry.py
│
├── DuckDB/
│   ├── Data.py
│   └── sql/
│       └── create_indicator_tables.sql
│
└── Ults/
```

### `calcIndicators.py`

Đề xuất chứa:

```text
IndicatorDefinition
IndicatorComponent
IndicatorConfig

get_indicator_definition
get_indicator_components
get_enabled_indicator_configs
validate_indicator_config
load_indicator_source_data
resample_indicator_timeframe
calculate_indicator_from_config
normalize_indicator_output
calculate_indicator_batch
upsert_indicator_values
refresh_technical_indicators
```

Có thể tách repository/data-access layer sau nếu implementation thực tế cho thấy module quá lớn hoặc project đã có repository pattern phù hợp.

### `indicatorRegistry.py`

Chỉ nên tập trung:

```text
whitelist registry
library function resolution
library-specific adapters
```

Không query database tại đây.

---

# 19. Compatibility with Existing `cal_Trends`

Hiện tại CherryStock có:

```text
cal_Trends
Ticker
Date
Close
MA20
MA50
MA100
MA200
```

và function `cal_Moving_Average()` đang trực tiếp calculate/upsert MA.

Không xóa hoặc rename ngay.

## Phase 1

Chạy song song:

```text
cal_Moving_Average()
       ↓
cal_Trends

refresh_technical_indicators()
       ↓
cal_indicator_values
```

## Phase 2

Validate parity:

```text
cal_Trends.MA20  == engine MA20_D
cal_Trends.MA50  == engine MA50_D
cal_Trends.MA100 == engine MA100_D
cal_Trends.MA200 == engine MA200_D
```

Cần xác định numeric tolerance phù hợp.

## Phase 3

Migrate downstream consumers sang:

```text
vw_technical_core
```

hoặc view compatibility.

## Phase 4

Chỉ retire `cal_Trends` khi:

- parity validation ổn định;
- chart/query downstream đã migrate;
- không còn public function phụ thuộc trực tiếp table cũ;
- migration có rollback path.

---

# 20. Initial Indicator Set

Phase đầu nên implement các indicator có giá trị cao và đủ bao phủ test case single-output/multi-output/input type.

## Single-output

```text
MA
EMA
RSI
ATR
OBV
MFI
```

## Multi-output

```text
BB
MACD
ADX
STOCH
```

Sau khi engine ổn định mới mở rộng:

```text
SuperTrend
Ichimoku
ROC
CMF
VWAP
Donchian
Keltner
Aroon
CCI
Williams %R
PSAR
```

---

# 21. Minimum Seed Configs

Đề xuất seed ban đầu:

```text
MA20_D
MA50_D
MA100_D
MA200_D

MA20_W
MA50_W
MA100_W
MA200_W

MA20_M
MA50_M
MA100_M
MA200_M

RSI14_D
RSI14_W
RSI14_M

BB20_2_D
MACD12_26_9_D
ADX14_D
ATR14_D
OBV_D
MFI14_D
```

Không nhất thiết mọi indicator đều phải có đủ D/W/M.

Timeframe nên được chọn theo business use case:

```text
Monthly -> market regime / long-term trend
Weekly  -> primary trend
Daily   -> timing / tactical signals
```

---

# 22. Testing Requirements

Theo repository instruction, implementation phải có test thực tế.

## 22.1. Metadata/config

Test:

- valid indicator config;
- missing config;
- disabled config;
- invalid parameter;
- invalid timeframe.

## 22.2. Single output indicator

MA/RSI:

```text
input -> expected VALUE component
```

## 22.3. Multi output indicator

BB:

```text
UPPER
MIDDLE
LOWER
WIDTH
PERCENT
```

MACD:

```text
LINE
SIGNAL
HIST
```

## 22.4. Input contracts

Test:

```text
ADX missing High -> failure
OBV missing Volume -> failure
```

## 22.5. Timeframe

Weekly/monthly resample phải validate:

```text
Open first
High max
Low min
Close last
Volume sum
Date last actual trading date
```

## 22.6. Warmup

MA200 incremental refresh phải match full-history calculation trong overlapping target range.

## 22.7. Idempotency

Run twice:

```text
no duplicate
same primary key count
same values nếu source/config không đổi
```

## 22.8. Existing MA parity

Compare new engine với `cal_Trends`.

---

# 23. Logging Requirements

Log tối thiểu:

```text
start indicator refresh
selected config count
selected timeframe
selected ticker count
source date range
warmup range
source row count
calculated row count
upsert row count
warning/error summary
success/failure
```

Không log full DataFrame hoặc large payload mặc định.

Error log phải có đủ context để reproduce:

```text
Ticker
ConfigId
ConfigCode
IndicatorCode
Timeframe
Parameters
Date range
```

Không log secret/environment-specific sensitive information.

---

# 24. Performance Principles

- Batch database reads.
- Không query per ticker nếu có thể load/vectorize theo group.
- Không query per config.
- Union required input fields trước khi query.
- Group configs theo timeframe để reuse resampled source.
- Chỉ persist target range sau khi warmup calculation hoàn tất.
- Tránh load toàn bộ lịch sử nếu incremental range + warmup đủ đảm bảo correctness.
- Có thể chunk theo ticker nếu universe/history quá lớn cho memory.
- Optimize sau khi correctness/parity đã được validate.

---

# 25. Configuration Versioning Consideration

Không update `Parameters` của một config đang có historical values nếu thay đổi đó làm thay đổi meaning của ConfigId.

Ví dụ không nên:

```text
ConfigId = 4
Old: BB(20,2)
New: BB(20,2.5)
```

vì historical data trước/sau update không còn cùng definition.

Nguyên tắc:

```text
Meaning thay đổi -> create new ConfigId / ConfigCode
```

Ví dụ:

```text
BB20_2_D
BB20_2_5_D
```

Config cũ có thể:

```text
IsEnabled = FALSE
```

nhưng vẫn giữ metadata để historical values truy vết được.

Đây là nguyên tắc rất quan trọng để đảm bảo reproducibility cho backtest/ML.

---

# 26. Reproducibility and Engine Version

Phase đầu có thể chưa cần thêm vào fact table, nhưng nên cân nhắc version tracking khi engine đi vào production/backtest nghiêm túc.

Có thể mở rộng config/metadata:

```text
EngineVersion
FormulaVersion
```

hoặc execution audit riêng.

Mục tiêu:

- biết historical value được tính bởi engine/formula version nào;
- hỗ trợ recompute khi library upgrade thay đổi output;
- reproducible backtest.

Không nên thêm complexity này trước khi core engine stable, nhưng data model không được làm mất khả năng mở rộng.

---

# 27. Recommended Implementation Phases

## Phase 1 - Schema + metadata seed

Create:

```text
dim_indicator
dim_indicator_component
dim_indicator_config
cal_indicator_values
```

Seed:

```text
MA
RSI
BB
MACD
ATR
ADX
OBV
MFI
```

## Phase 2 - Core engine

Implement:

```text
registry
config reader
validation
source loader
resampler
calculate_indicator_from_config
normalizer
upsert
refresh_technical_indicators
```

## Phase 3 - Tests and MA parity

Compare:

```text
new MA engine
vs
cal_Trends
```

## Phase 4 - Multi-output validation

Implement/test:

```text
BB
MACD
ADX
```

## Phase 5 - D/W/M

Enable:

```text
Daily
Weekly
Monthly
```

## Phase 6 - Feature/view layer

Create:

```text
vw_technical_core
```

hoặc `cal_technical_core` nếu materialization cần thiết.

## Phase 7 - Migrate consumers

Migrate chart/screener/model từ legacy `cal_Trends` theo từng consumer.

---

# 28. Final Architecture

```text
                   ┌─────────────────────┐
                   │    dim_indicator    │
                   │ definition / input  │
                   └──────────┬──────────┘
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│ dim_indicator_component  │   │  dim_indicator_config    │
│ normalized outputs       │   │ params / timeframe       │
└──────────────────────────┘   └────────────┬─────────────┘
                                            │
                                            ▼
                              ┌──────────────────────────┐
raw_stock_eod ───────────────►│     Indicator Engine     │
                              │ registry / validation    │
                              │ resample / calculate     │
                              │ normalize / batch        │
                              └────────────┬─────────────┘
                                           │
                                           ▼
                              ┌──────────────────────────┐
                              │  cal_indicator_values    │
                              │ source of truth / long   │
                              └────────────┬─────────────┘
                                           │
                    ┌──────────────────────┼─────────────────────┐
                    ▼                      ▼                     ▼
             Technical View          Feature Builder       Chart/Screener
                    │                      │
                    ▼                      ▼
           vw_technical_core      cal_technical_features
                                           │
                                           ▼
                              Technical Score / ML Model
```

---

# 29. Final Decisions

1. `cal_indicator_values` long format là source of truth.
2. Không tạo column mới mỗi lần thêm indicator.
3. Không tạo một table riêng cho từng indicator.
4. `dim_indicator` lưu indicator definition.
5. `dim_indicator_component` lưu multi-output contract.
6. `dim_indicator_config` lưu executable parameter set + timeframe.
7. `Parameters` lưu JSON có validation schema.
8. `ConfigId` + `ComponentCode` resolve được meaning của value.
9. Primary key fact: `Ticker + Date + ConfigId + ComponentCode`.
10. Library output phải normalize qua adapter trước khi persist.
11. Không cho DB điều khiển arbitrary Python function; phải qua whitelist registry.
12. Daily là base source; Weekly/Monthly resample từ actual trading bars.
13. Incremental refresh phải load warmup history trước checkpoint.
14. Batch load source data; tránh DB query trong ticker/config loop.
15. `refresh_technical_indicators()` là public orchestration API.
16. `cal_Trends` giữ lại trong migration phase, chưa remove.
17. Wide tables/views chỉ là serving/feature layer, không phải source of truth.
18. Khi config meaning thay đổi phải tạo ConfigId mới để đảm bảo historical reproducibility.
19. Phase đầu ưu tiên correctness, parity, validation và idempotency trước performance optimization.
20. Thiết kế phải hỗ trợ về sau cho screener, technical score, backtest và ML/prediction mà không cần thay lại storage model.
