# Indicator Engine

> Source: Confluence page `Indicator Engine` (page ID `43057153`), synchronized on 2026-08-30.

Với CherryStock, mình khuyên **không nhét toàn bộ indicator vào một table wide duy nhất**, nhưng cũng **không tách mỗi indicator thành một table riêng**. Tối ưu nhất là mô hình **hybrid: một table fact dạng long để lưu indicator value + một số table wide/materialized cho nhóm core dùng thường xuyên**.

Hiện tại `cal_Trends` đang theo kiểu wide: `Ticker`, `Date`, `MA20`, `MA50`, `MA100`, `MA200`, `Close`. Cách này ổn khi số indicator cố định và ít, nhưng về lâu dài cứ thêm RSI, MACD, ATR, Bollinger, ADX, MFI, RS... là phải `ALTER TABLE ADD COLUMN`, rồi xử lý backfill historical data.

## 1. Kiến trúc lưu trữ

```text
cal_indicator_values
-----------------------------
Ticker
Date
IndicatorCode
Timeframe
Value
Version
CalculatedAt
```

Ví dụ:

```text
MWG | 2026-08-24 | MA20  | D | 78.35
MWG | 2026-08-24 | MA50  | D | 75.20
MWG | 2026-08-24 | RSI14 | D | 63.40
MWG | 2026-08-24 | ATR14 | D | 2.15
MWG | 2026-08-24 | MA20  | W | 72.10
MWG | 2026-08-24 | RSI14 | W | 59.20
```

Khi thêm `ADX14`, `MFI14`, `CMF20`, `BB_WIDTH20`, `RS_VNINDEX_60` thì **không cần alter schema**, chỉ insert thêm row.

Nên có metadata `dim_indicator`, và giữ một số table wide/materialized như `cal_technical_core` cho query nhanh, dashboard hoặc model training.

```text
raw_stock_eod
      │
      ▼
vw_Ticker_indicators       ← SINGLE SOURCE OF TRUTH
      │
      ├── Trend
      ├── Momentum
      ├── Volatility
      ├── Volume
      ├── Structure
      └── Relative Strength
             │
             ▼
      cal_technical_core
             │
             ├── CherryMon
             ├── Screener
             ├── Technical Score
             └── ML / Prediction
```

Không nên tách thành `cal_MA`, `cal_RSI`, `cal_MACD`, `cal_ATR`, ... vì sẽ tạo quá nhiều table, join phức tạp và maintenance khó. Cũng không nên giữ một bảng wide 100+ columns vì mỗi lần thêm indicator lại phải thay schema và backfill.

Với DuckDB, cấu trúc mục tiêu:

1. `raw_stock_eod` — raw data.
2. `dim_indicator` — metadata / definition.
3. `vw_Ticker_indicators` — **Single Source of Truth** for all calculated technical indicators; replaces direct consumer access to `cal_indicator_values`.
4. `cal_technical_core` — wide-format core features.
5. `cal_technical_score` — TrendScore, MomentumScore, VolumeScore, VolatilityScore, StructureScore, RelativeStrengthScore, TechnicalScore.

Trong long fact table, **không encode timeframe vào `IndicatorCode`**. Ví dụ `IndicatorCode = MA20`, `Timeframe = D`. Ở wide table thì `MA20_D`, `MA20_W`, `MA20_M`, `RSI14_D` là phù hợp.

## 2. Indicator engine

Sử dụng `pandas-ta-classic` làm engine chính để generate indicator value; TA-Lib có thể làm backend/đối chiếu cho các indicator phổ biến.

```text
dim_indicator
        │
        ▼
dim_indicator_config
        │ đọc IndicatorCode / Timeframe / Parameters
        ▼
Indicator Engine
  pandas-ta-classic
        │
        ▼
normalize output
        │
        ▼
vw_Ticker_indicators
```

Không gọi function tự do trực tiếp từ DB bằng `getattr()`. Phải có **Indicator Registry** whitelist function và required inputs.

```python
INDICATOR_REGISTRY = {
    "MA": {"function": ta.sma, "inputs": ["Close"]},
    "RSI": {"function": ta.rsi, "inputs": ["Close"]},
    "BB": {"function": ta.bbands, "inputs": ["Close"]},
    "MACD": {"function": ta.macd, "inputs": ["Close"]},
    "ADX": {"function": ta.adx, "inputs": ["High", "Low", "Close"]},
    "ATR": {"function": ta.atr, "inputs": ["High", "Low", "Close"]},
}
```

Input requirements khác nhau theo indicator:

- MA / RSI / MACD / BB → `Close`.
- ATR / ADX → `High + Low + Close`.
- OBV → `Close + Volume`.
- MFI → `High + Low + Close + Volume`.

Phải có abstraction:

```text
Pandas TA output
       ↓
Indicator Adapter
       ↓
CherryStock ComponentCode
```

Ví dụ mapping:

```python
OUTPUT_MAPPING = {
    "BB": {
        "BBL": "LOWER",
        "BBM": "MIDDLE",
        "BBU": "UPPER",
        "BBB": "WIDTH",
        "BBP": "PERCENT",
    },
    "MACD": {
        "MACD": "LINE",
        "MACDs": "SIGNAL",
        "MACDh": "HIST",
    },
    "ADX": {
        "ADX": "ADX",
        "DMP": "PLUS_DI",
        "DMN": "MINUS_DI",
    },
}
```

Không lưu tên column do library sinh trực tiếp vào database để tránh coupling với implementation.

## 3. Parameter schema

`dim_indicator_config.Parameters` dùng JSON, không dùng chuỗi `FAST=12;SLOW=26;SIGNAL=9`.

```json
{"fast": 12, "slow": 26, "signal": 9}
```

Bollinger:

```json
{"length": 20, "std": 2.0}
```

SuperTrend:

```json
{"length": 10, "multiplier": 3.0}
```

## 4. Data model chốt

```text
dim_indicator
        │
        ├──────────────► dim_indicator_component
        │
        ▼
dim_indicator_config
        │
        ▼
vw_Ticker_indicators
```

### 4.1 `dim_indicator`

Definition của indicator, không chứa period cụ thể.

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

Ví dụ `RequiredInputs`:

| IndicatorCode | FunctionName | RequiredInputs |
| --- | --- | --- |
| MA | `sma` | `["Close"]` |
| RSI | `rsi` | `["Close"]` |
| BB | `bbands` | `["Close"]` |
| MACD | `macd` | `["Close"]` |
| ATR | `atr` | `["High","Low","Close"]` |
| ADX | `adx` | `["High","Low","Close"]` |
| OBV | `obv` | `["Close","Volume"]` |

`ParameterSchema` dùng để validate `dim_indicator_config`. Không được silent fallback sang library defaults khi config sai.

### 4.2 `dim_indicator_component`

Giải quyết indicator có nhiều output.

```sql
CREATE TABLE "CherryMon"."main"."dim_indicator_component" (
    IndicatorCode       VARCHAR NOT NULL,
    ComponentCode       VARCHAR NOT NULL,
    ComponentName       VARCHAR NOT NULL,
    OutputPrefix        VARCHAR,
    SortOrder           INTEGER,
    IsPrimary           BOOLEAN NOT NULL DEFAULT FALSE,
    IsActive            BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (IndicatorCode, ComponentCode)
);
```

Bollinger:

```text
BB
├── UPPER
├── MIDDLE
├── LOWER
├── WIDTH
└── PERCENT
```

MACD:

```text
MACD
├── LINE
├── SIGNAL
└── HIST
```

ADX:

```text
ADX
├── ADX
├── PLUS_DI
└── MINUS_DI
```

### 4.3 `dim_indicator_config`

Quyết định thực tế phải calculate cái gì.

```sql
CREATE SEQUENCE IF NOT EXISTS seq_indicator_config START 1;

CREATE TABLE "CherryMon"."main"."dim_indicator_config" (
    ConfigId            BIGINT NOT NULL DEFAULT nextval('seq_indicator_config'),
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

Ví dụ:

| ConfigCode | Indicator | TF | Parameters |
| --- | --- | --- | --- |
| MA20_D | MA | D | `{"length":20}` |
| MA50_D | MA | D | `{"length":50}` |
| RSI14_D | RSI | D | `{"length":14}` |
| BB20_2_D | BB | D | `{"length":20,"std":2}` |
| MACD12_26_9_D | MACD | D | `{"fast":12,"slow":26,"signal":9}` |
| ATR14_D | ATR | D | `{"length":14}` |

`WarmupBars` phải đủ để tính chính xác vùng target. Ví dụ MA200 cần load thêm ít nhất 200 bars trước vùng persist.

### 4.4 `vw_Ticker_indicators`

`"CherryMon"."main"."vw_Ticker_indicators"` là **Single Source of Truth (SSOT)** cho toàn bộ technical indicator mà các downstream consumer phải sử dụng. View này **thay thế vai trò source of truth của `cal_indicator_values`**.

`cal_indicator_values` có thể tiếp tục tồn tại như physical persistence/staging table nội bộ của Indicator Engine, nhưng **không được xem là contract đọc dữ liệu chính** cho CherryMon, Screener, Technical Score, charting, API hay ML feature consumption.

Nguyên tắc:

```text
Indicator Engine
      │
      ▼
cal_indicator_values        ← internal persistence / implementation detail
      │
      ▼
vw_Ticker_indicators       ← SINGLE SOURCE OF TRUTH / public read contract
      │
      ├── CherryMon
      ├── Screener
      ├── Technical Score
      ├── Chart / Level analysis
      ├── API
      └── ML / Prediction
```

Mọi logic downstream khi cần indicator phải ưu tiên query:

```sql
SELECT ...
FROM "CherryMon"."main"."vw_Ticker_indicators"
```

thay vì đọc trực tiếp từ `cal_indicator_values`.

```sql
CREATE TABLE "CherryMon"."main"."cal_indicator_values" (
    Ticker              VARCHAR NOT NULL,
    Date                DATE NOT NULL,
    ConfigId            BIGINT NOT NULL,
    ComponentCode       VARCHAR NOT NULL,
    Value               DOUBLE,
    CalculatedAt        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (Ticker, Date, ConfigId, ComponentCode)
);
```

Không duplicate `IndicatorCode`, `Timeframe`, `Period`, `Parameters` trong fact table; resolve qua `ConfigId`.

Ví dụ Bollinger:

```text
Ticker  Date        ConfigId ComponentCode Value
MWG     2026-08-25  4        UPPER         82.50
MWG     2026-08-25  4        MIDDLE        78.20
MWG     2026-08-25  4        LOWER         73.90
MWG     2026-08-25  4        WIDTH          8.60
MWG     2026-08-25  4        PERCENT        0.67
```

Primary key đảm bảo rerun idempotent.

## 5. Timeframe convention

Không cần `Timeframe` trong fact table vì nằm trong config.

Quy ước `Date`:

- `D` → trading date.
- `W` → ngày giao dịch cuối cùng của tuần.
- `M` → ngày giao dịch cuối cùng của tháng.

Không hard-code Friday hoặc ngày 30/31 vì holiday.

Resample OHLCV:

- Open = first
- High = max
- Low = min
- Close = last
- Volume = sum
- Date = last trading date

## 6. Python models

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

Không cần ORM; project dùng DuckDB + pandas trực tiếp.

## 7. Function contracts

| Function | Responsibility |
| --- | --- |
| `get_indicator_definition()` | lấy metadata indicator |
| `get_indicator_components()` | lấy component mapping |
| `get_enabled_indicator_configs()` | lấy config cần chạy |
| `validate_indicator_config()` | validate Parameters |
| `load_indicator_source_data()` | load OHLCV |
| `resample_indicator_timeframe()` | D → W/M |
| `calculate_indicator_from_config()` | gọi engine tính một config |
| `normalize_indicator_output()` | library output → CherryStock component |
| `calculate_indicator_batch()` | tính nhiều config trên một dataset |
| `upsert_indicator_values()` | persist idempotent |
| `refresh_technical_indicators()` | orchestration chính |

### Config access

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

### Validate config

```python
def validate_indicator_config(
    config: IndicatorConfig,
    definition: IndicatorDefinition,
) -> None:
    ...
```

Config sai phải raise rõ ràng; không silent fallback.

### Load source data

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

Chỉ query các field cần thiết, không `SELECT *`.

### Resample timeframe

```python
def resample_indicator_timeframe(
    price_df: pd.DataFrame,
    timeframe: str,
) -> pd.DataFrame:
    ...
```

### Calculate one config

```python
def calculate_indicator_from_config(
    source_df: pd.DataFrame,
    config: IndicatorConfig,
    definition: IndicatorDefinition,
    components: list[IndicatorComponent],
) -> pd.DataFrame:
    ...
```

Output luôn có schema:

```text
Ticker
Date
ConfigId
ComponentCode
Value
```

### Normalize output

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

### Batch calculation

Không query DuckDB bên trong loop từng config nếu có thể batch.

```python
def calculate_indicator_batch(
    source_df: pd.DataFrame,
    configs: list[IndicatorConfig],
    definitions: dict[str, IndicatorDefinition],
    components: dict[str, list[IndicatorComponent]],
) -> pd.DataFrame:
    ...
```

### Persist

```python
def upsert_indicator_values(
    indicator_values: pd.DataFrame,
    *,
    connection=None,
    repository=None,
) -> int:
    ...
```

Upsert key: `Ticker + Date + ConfigId + ComponentCode`.

### Public orchestrator

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

`refresh_technical_indicators()` mặc định calculate tất cả active configs; có thể filter theo date window, ticker, config hoặc timeframe.

## 8. Processing flow

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
calculate warmup requirements
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
                        vw_Ticker_indicators
```

Sau khi persist/upsert vào internal storage, view `vw_Ticker_indicators` là lớp contract cuối cùng expose dữ liệu cho downstream consumers.

## 9. File structure

```text
src/
├── calcEngine/
│   ├── calcIndicators.py
│   └── indicatorRegistry.py
├── DuckDB/
│   ├── Data.py
│   └── sql/
│       └── create_indicator_tables.sql
└── Ults/
    └── ...
```

`calcIndicators.py` chứa models, validation, resampling, calculation, normalization, batch và orchestration. `indicatorRegistry.py` chỉ chứa registry/library adapter. Data access reuse connection convention hiện tại của project.

## 10. Migration từ `cal_Trends`

**Chưa xóa `cal_Trends`.** Phase đầu chạy song song:

```text
cal_Moving_Average()
       ↓
cal_Trends

refresh_technical_indicators()
       ↓
cal_indicator_values (internal persistence)
       ↓
vw_Ticker_indicators (SSOT)
```

Sau khi validation:

```text
MA20 old == MA20 new
MA50 old == MA50 new
MA100 old == MA100 new
MA200 old == MA200 new
```

mới migrate. Cuối cùng `cal_Trends` có thể trở thành compatibility view/pivot được derive từ `vw_Ticker_indicators` thay vì đọc trực tiếp `cal_indicator_values`.

## 11. Thiết kế chốt

```text
dim_indicator
        ↓
indicator definition

dim_indicator_component
        ↓
multi-output definition

dim_indicator_config
        ↓
executable ParamSet + timeframe

cal_indicator_values
        ↓
internal persistence

vw_Ticker_indicators
        ↓
SINGLE SOURCE OF TRUTH / downstream read contract
```

Public orchestration:

```python
refresh_technical_indicators()
```

Với model này, thêm `RSI21`, `BB50(2.5)`, `SuperTrend(10,3)`, `MACD(8,21,5)`, `Ichimoku` phần lớn chỉ cần insert metadata/config, không phải thay đổi schema database.
