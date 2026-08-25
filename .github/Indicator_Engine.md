# CherryStock Indicator Engine Design

## 1. Purpose

Tài liệu này định nghĩa kiến trúc, data model, execution flow, onboarding lifecycle, function contracts và vận hành Technical Indicator Engine của CherryStock.

Mục tiêu:

- Hỗ trợ nhiều technical indicator mà không phải `ALTER TABLE ADD COLUMN` khi thêm indicator mới.
- Hỗ trợ indicator có một hoặc nhiều output/component.
- Hỗ trợ mặc định ba timeframe: Daily, Weekly và Monthly.
- Cho phép engine đọc metadata/config từ DuckDB rồi gọi `pandas-ta-classic` theo cơ chế config-driven.
- Tách indicator definition, output component, executable config và calculated values.
- Hỗ trợ checkpoint của CherryStock khi chạy `run.py`.
- Tự mở rộng historical window theo `WarmupBars` nhưng chỉ persist vùng checkpoint cần refresh.
- Đảm bảo rerun idempotent.
- Cho phép onboarding indicator mới chủ yếu bằng metadata/config thay vì sửa pipeline.

---

# 2. Core Architecture

Source of truth sử dụng long-format:

```text
raw_stock_eod
      │
      ▼
dim_indicator
      │
      ├──────────────► dim_indicator_component
      │
      ▼
dim_indicator_config
      │
      ▼
refresh_technical_indicators()
      │
      ▼
cal_indicator_values
```

Vai trò:

```text
dim_indicator
    Indicator là gì?
    Dùng engine/function nào?
    Cần OHLCV input nào?
    Parameter schema là gì?

dim_indicator_component
    Indicator trả ra output/component nào?

dim_indicator_config
    Indicator chạy với Parameters nào?
    Timeframe nào?
    WarmupBars bao nhiêu?

cal_indicator_values
    Giá trị thực tế theo:
    Ticker + Date + ConfigId + ComponentCode
```

Không dùng một bảng wide có hàng trăm indicator columns làm source of truth.

Không tách mỗi indicator thành một table riêng.

Wide table/view chỉ nên được tạo ở feature/reporting layer khi cần screener, dashboard hoặc ML.

---

# 3. Naming Convention

## 3.1 IndicatorCode

`IndicatorCode` chỉ mô tả loại indicator, không encode period hay timeframe.

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

## 3.2 ComponentCode

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

## 3.3 ConfigCode

`ConfigCode` biểu diễn một executable configuration.

Ví dụ:

```text
MA20_D
MA20_W
MA20_M
RSI14_D
RSI14_W
RSI14_M
BB20_2_D
BB20_2_W
BB20_2_M
MACD12_26_9_D
MACD12_26_9_W
MACD12_26_9_M
```

Runtime không được parse Parameters từ ConfigCode. Runtime luôn đọc `Parameters` JSON.

## 3.4 Timeframe

Chuẩn mặc định:

```text
D = Daily
W = Weekly
M = Monthly
```

`DEFAULT_TIMEFRAMES = ("D", "W", "M")`.

Khi onboarding một indicator/config mới, mặc định phải tạo đủ cả ba timeframe.

---

# 4. Data Model

## 4.1 `"CherryMon"."main"."dim_indicator"`

Lưu master definition của indicator.

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

Ví dụ:

```text
RSI
RequiredInputs = ["Close"]

ADX
RequiredInputs = ["High", "Low", "Close"]

OBV
RequiredInputs = ["Close", "Volume"]

MFI
RequiredInputs = ["High", "Low", "Close", "Volume"]
```

`RequiredInputs` là contract source-data của engine, không phải mô tả tham khảo.

---

## 4.2 ParameterSchema

Dùng validate `dim_indicator_config.Parameters` trước khi gọi library.

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

Ngoài schema validation, engine có thể validate relationship, ví dụ:

```text
MACD: fast < slow
```

Không silent fallback sang default parameter của library khi config sai.

---

## 4.3 `"CherryMon"."main"."dim_indicator_component"`

Lưu output/component của indicator.

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

### Single-output indicator

Ví dụ RSI:

```text
IndicatorCode = RSI
ComponentCode = VALUE
OutputPrefix  = NULL
IsPrimary     = TRUE
```

### Bollinger Bands

```text
BB
├── LOWER   -> BBL
├── MIDDLE  -> BBM
├── UPPER   -> BBU
├── WIDTH   -> BBB
└── PERCENT -> BBP
```

### MACD

```text
MACD
├── LINE   -> MACD
├── SIGNAL -> MACDs
└── HIST   -> MACDh
```

### ADX

```text
ADX
├── ADX      -> ADX
├── PLUS_DI  -> DMP
└── MINUS_DI -> DMN
```

Database không lưu raw library column name trong fact table. Adapter normalize library output về `ComponentCode` chuẩn của CherryStock.

---

## 4.4 `"CherryMon"."main"."dim_indicator_config"`

Lưu executable configuration.

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

Ví dụ một parameter set RSI14 phải có ba executable configs:

```text
RSI14_D | RSI | D | {"length":14}
RSI14_W | RSI | W | {"length":14}
RSI14_M | RSI | M | {"length":14}
```

Bollinger:

```text
BB20_2_D | BB | D | {"length":20,"std":2.0}
BB20_2_W | BB | W | {"length":20,"std":2.0}
BB20_2_M | BB | M | {"length":20,"std":2.0}
```

MA có nhiều parameter set độc lập:

```text
MA20_D / MA20_W / MA20_M
MA50_D / MA50_W / MA50_M
MA100_D / MA100_W / MA100_M
MA200_D / MA200_W / MA200_M
```

Mỗi `IndicatorCode + Parameters` được coi là một **config family** và mặc định phải có đủ `D/W/M`.

---

## 4.5 WarmupBars

Indicator cần historical data trước checkpoint.

Ví dụ:

```text
MA20      WarmupBars >= 20
MA200     WarmupBars >= 200
RSI14     WarmupBars >= 14
MACD      WarmupBars nên >= slow + signal
```

Nếu main cần refresh 10 ngày nhưng MA200 cần 200 bars:

```text
Persist target: khoảng 10 ngày
Read source: checkpoint + ít nhất 200 historical trading bars
```

Engine tính trên full warmup window nhưng chỉ persist target checkpoint.

---

## 4.6 `"CherryMon"."main"."cal_indicator_values"`

Source of truth của calculated indicator values.

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

Ví dụ Bollinger:

```text
MWG | 2026-08-25 | ConfigId=BB20_2_D | LOWER   | 73.90
MWG | 2026-08-25 | ConfigId=BB20_2_D | MIDDLE  | 78.20
MWG | 2026-08-25 | ConfigId=BB20_2_D | UPPER   | 82.50
MWG | 2026-08-25 | ConfigId=BB20_2_D | WIDTH   | 8.60
MWG | 2026-08-25 | ConfigId=BB20_2_D | PERCENT | 0.67
```

Không duplicate `IndicatorCode`, `Timeframe`, `Parameters` trong fact table vì resolve được qua `ConfigId`.

---

# 5. Mandatory Indicator Onboarding Lifecycle

Đây là quy trình bắt buộc khi thêm một indicator mới vào CherryStock.

## 5.1 Thứ tự insert

Luôn theo thứ tự:

```text
STEP 1
"CherryMon"."main"."dim_indicator"
        ↓
STEP 2
"CherryMon"."main"."dim_indicator_component"
        ↓
STEP 3
"CherryMon"."main"."dim_indicator_config"
        ↓
STEP 4
refresh_technical_indicators()
        ↓
"CherryMon"."main"."cal_indicator_values"
```

Không tạo config trước khi definition/component hoàn chỉnh.

Khuyến nghị thực hiện ba bước metadata trong cùng transaction nếu onboarding bằng script.

---

## 5.2 Step 1 — Insert `dim_indicator`

Phải define tối thiểu:

```text
IndicatorCode
IndicatorName
Category
Engine
FunctionName
RequiredInputs
ParameterSchema
IsActive
```

Ví dụ ATR:

```sql
INSERT INTO "CherryMon"."main"."dim_indicator" (
    IndicatorCode,
    IndicatorName,
    Category,
    Engine,
    FunctionName,
    RequiredInputs,
    ParameterSchema,
    IsActive
)
VALUES (
    'ATR',
    'Average True Range',
    'VOLATILITY',
    'PANDAS_TA_CLASSIC',
    'atr',
    '["High","Low","Close"]'::JSON,
    '{"length":{"type":"integer","min":2,"required":true}}'::JSON,
    TRUE
);
```

---

## 5.3 Step 2 — Insert `dim_indicator_component`

Single-output indicator vẫn phải có component metadata.

ATR:

```sql
INSERT INTO "CherryMon"."main"."dim_indicator_component" (
    IndicatorCode,
    ComponentCode,
    ComponentName,
    OutputPrefix,
    SortOrder,
    IsPrimary,
    IsActive
)
VALUES (
    'ATR',
    'VALUE',
    'Average True Range',
    NULL,
    1,
    TRUE,
    TRUE
);
```

Multi-output indicator phải insert đầy đủ mọi output cần persist.

---

## 5.4 Step 3 — Insert `dim_indicator_config`

Mặc định mỗi parameter set phải có đủ:

```text
Daily   -> D
Weekly  -> W
Monthly -> M
```

Ví dụ ATR14:

```sql
INSERT INTO "CherryMon"."main"."dim_indicator_config" (
    ConfigCode,
    IndicatorCode,
    Timeframe,
    Parameters,
    WarmupBars,
    IsEnabled
)
VALUES
    ('ATR14_D', 'ATR', 'D', '{"length":14}'::JSON, 14, TRUE),
    ('ATR14_W', 'ATR', 'W', '{"length":14}'::JSON, 14, TRUE),
    ('ATR14_M', 'ATR', 'M', '{"length":14}'::JSON, 14, TRUE);
```

Nếu thêm một parameter set khác, ví dụ ATR20, ATR20 cũng phải có D/W/M:

```text
ATR20_D
ATR20_W
ATR20_M
```

Không được coi việc có `ATR14_D`, `ATR20_W`, `ATR20_M` là đủ. Engine kiểm tra completeness theo **IndicatorCode + Parameters**, không chỉ IndicatorCode.

---

## 5.5 Step 4 — Refresh calculated values

Sau khi metadata đầy đủ:

```python
refresh_technical_indicators()
```

Engine tự discover toàn bộ config `IsEnabled = TRUE`.

Không cần sửa `run.py` hoặc thêm hard-code riêng cho indicator mới nếu library/function/component mapping đã được hỗ trợ.

---

# 6. Onboarding Validation Contract

`refresh_technical_indicators()` validate metadata trước khi đọc source/calculation.

## 6.1 Component validation

Mọi IndicatorCode xuất hiện trong enabled config phải có ít nhất một row active trong:

```text
"CherryMon"."main"."dim_indicator_component"
```

Nếu thiếu:

```text
raise ValueError
```

Không fallback ngầm về `VALUE` trong main refresh.

## 6.2 Default timeframe validation

Trong normal full refresh, với mỗi:

```text
IndicatorCode + canonical Parameters JSON
```

engine yêu cầu:

```text
D
W
M
```

Ví dụ hợp lệ:

```text
RSI + {"length":14}
    D
    W
    M
```

Ví dụ không hợp lệ:

```text
RSI + {"length":14}
    D
    W
    # thiếu M
```

Engine fail trước khi persist bất kỳ calculated value nào.

## 6.3 Targeted maintenance run

Các run có filter:

```python
refresh_technical_indicators(config_ids=[...])
```

hoặc:

```python
refresh_technical_indicators(timeframes=["D"])
```

được phép chạy subset để debug/backfill.

Trong trường hợp này engine bỏ qua chỉ riêng validation D/W/M completeness của batch đã filter, nhưng vẫn validate:

- config tồn tại và enabled;
- definition active;
- component metadata tồn tại;
- RequiredInputs hợp lệ;
- Parameters hợp lệ;
- library function hợp lệ.

Normal `run.py` không truyền `config_ids`/`timeframes`, vì vậy luôn enforce D/W/M đầy đủ.

---

# 7. Indicator Registry / Library Adapter

Engine chính sử dụng:

```text
pandas-ta-classic
```

Luồng:

```text
dim_indicator.FunctionName
        ↓
indicatorRegistry
        ↓
approved pandas-ta-classic callable
```

Không gọi arbitrary `getattr()` từ raw database string mà không whitelist/validate.

`RequiredInputs` được map từ CherryStock column sang library argument:

```text
Open   -> open_
High   -> high
Low    -> low
Close  -> close
Volume -> volume
```

Ví dụ:

```text
ADX RequiredInputs
["High","Low","Close"]

        ↓

adx(high=..., low=..., close=..., **Parameters)
```

---

# 8. Timeframe Resampling

Source gốc:

```text
"CherryMon"."main"."raw_stock_eod"
```

## Daily

Không resample.

## Weekly

```text
Open   = first
High   = max
Low    = min
Close  = last
Volume = sum
Date   = last actual trading date of week
```

## Monthly

```text
Open   = first
High   = max
Low    = min
Close  = last
Volume = sum
Date   = last actual trading date of month
```

Không hard-code Friday hoặc ngày 30/31 làm Date.

---

# 9. Checkpoint Contract

`run.py` resolve checkpoint bằng `get_last_point()` và truyền `days_diff` xuống write pipeline.

Indicator Engine nhận cùng contract:

```python
refresh_technical_indicators(
    from_last_day=days_diff,
    connection=connection,
    repository=indicator_repository,
)
```

Nguyên tắc:

```text
from_last_day
    ↓
resolve checkpoint target
    ↓
calculate required WarmupBars
    ↓
load historical source trước checkpoint
    ↓
calculate full loaded window
    ↓
persist only checkpoint target
```

Weekly/monthly cleanup bắt đầu từ đầu kỳ chứa checkpoint để tránh giữ stale provisional value trong cùng tuần/tháng.

---

# 10. `refresh_technical_indicators()` Contract

Public function:

```python
def refresh_technical_indicators(
    *,
    from_last_day: int | None = None,
    tickers: list[str] | None = None,
    config_ids: list[int] | None = None,
    timeframes: list[str] | None = None,
    connection=None,
    repository=None,
) -> dict[str, object]:
    ...
```

## Normal main execution

```python
refresh_technical_indicators(
    from_last_day=days_diff,
    connection=uow.connection,
    repository=uow.indicators,
)
```

Hành vi:

1. Ensure indicator storage tables tồn tại.
2. Load all `IsEnabled = TRUE` configs.
3. Load active definitions.
4. Load active components.
5. Validate onboarding contract.
6. Enforce D/W/M cho từng `IndicatorCode + Parameters` family.
7. Validate each config/ParameterSchema.
8. Resolve checkpoint.
9. Resolve warmup window.
10. Batch load OHLCV source.
11. Resample D/W/M.
12. Calculate indicator values.
13. Normalize output component.
14. Delete/replace checkpoint region.
15. Upsert `cal_indicator_values`.
16. Return execution summary.

Summary gồm tối thiểu:

```text
status
checkpoint_start
source_start
source_max_date
records_upserted
configs_processed
indicators_processed
tickers_processed
default_timeframes_validated
```

---

# 11. Function Responsibilities

| Function | Responsibility |
|---|---|
| `get_enabled_indicator_configs()` | Load enabled executable configs |
| `get_indicator_definitions()` | Load master indicator definition |
| `get_indicator_components()` | Load component/output mapping |
| `validate_indicator_onboarding_contract()` | Enforce metadata lifecycle + D/W/M completeness |
| `validate_indicator_config()` | Validate Parameters and config relationships |
| `load_indicator_source_data()` | Batch load required OHLCV inputs |
| `resample_indicator_timeframe()` | Convert Daily source to D/W/M |
| `calculate_indicator_from_config()` | Calculate one config for one ticker |
| `normalize_indicator_output()` | Convert library output to CherryStock long format |
| `calculate_indicator_batch()` | Calculate all configs without DB calls inside loops |
| `replace_indicator_checkpoint()` | Delete stale checkpoint rows and upsert new values |
| `refresh_technical_indicators()` | Public orchestration function |

---

# 12. Idempotency

Fact primary key:

```text
Ticker
Date
ConfigId
ComponentCode
```

Rerun cùng checkpoint:

```text
không duplicate
```

Engine replace checkpoint region trước khi insert, đặc biệt cần cho Weekly/Monthly vì ngày đại diện của kỳ hiện tại có thể thay đổi sau mỗi phiên giao dịch.

---

# 13. Data Quality

Sau Technical Indicator Engine trong main pipeline, nếu có records được upsert, chạy data-quality validation cho:

```text
"CherryMon"."main"."cal_indicator_values"
```

Key:

```text
Ticker
Date
ConfigId
ComponentCode
```

Required:

```text
Ticker
Date
ConfigId
ComponentCode
Value
```

Các lỗi metadata/config phải fail trước calculated-value persistence.

---

# 14. Adding a New Indicator — Operational Checklist

Ví dụ thêm ATR:

```text
[1] Verify pandas-ta-classic function
    atr

[2] Insert dim_indicator
    IndicatorCode = ATR
    RequiredInputs = [High, Low, Close]

[3] Insert dim_indicator_component
    VALUE

[4] Define parameter set
    {"length":14}

[5] Insert dim_indicator_config
    ATR14_D
    ATR14_W
    ATR14_M

[6] Confirm all configs IsEnabled=TRUE

[7] Run targeted test if needed
    refresh_technical_indicators(config_ids=[...])

[8] Run normal refresh
    refresh_technical_indicators()

[9] Validate cal_indicator_values

[10] No schema alteration required
```

Ví dụ thêm MACD:

```text
[1] dim_indicator
    MACD / macd / RequiredInputs=[Close]

[2] dim_indicator_component
    LINE
    SIGNAL
    HIST

[3] dim_indicator_config
    MACD12_26_9_D
    MACD12_26_9_W
    MACD12_26_9_M

[4] refresh_technical_indicators()
```

---

# 15. Rule Summary

Các rule bắt buộc:

```text
1 indicator definition
    = 1 row trong dim_indicator

1 indicator
    = >= 1 row trong dim_indicator_component

1 Parameter set
    = mặc định 3 config rows: D + W + M

1 calculated output
    = Ticker + Date + ConfigId + ComponentCode + Value
```

Onboarding order:

```text
dim_indicator
    ↓
dim_indicator_component
    ↓
dim_indicator_config (D/W/M)
    ↓
refresh_technical_indicators()
    ↓
cal_indicator_values
```

Normal main refresh phải fail nếu configured indicator chưa hoàn tất lifecycle trên.

Mục tiêu cuối cùng là: **thêm indicator mới bằng metadata/config, không thay đổi fact schema và không ảnh hưởng historical data của indicator khác**.
