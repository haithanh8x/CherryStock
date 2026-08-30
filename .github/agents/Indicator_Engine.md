# Indicator Engine Agent

> **Canonical Agent Instruction** — File này đã merge operational onboarding contract từ `.github/Indicator_Engine.md` với architecture/design reference hiện có của `.github/agents/Indicator_Engine.md`.
>
> Khi có khác biệt giữa phần onboarding operational contract và phần architecture reference, Agent phải ưu tiên **Mandatory Three-Phase State Machine** và các **Agent Safety Rules** trong file này.
>
> Agent phải thực hiện đúng 3 phase theo thứ tự: **PHASE 1 — Config Metadata → PHASE 2 — Historical Initialization / Backfill → PHASE 3 — Validate `cal_indicator_values`**. Không được bỏ qua phase và không được coi indicator là production-ready khi phase trước chưa PASS.

---

# 1. Core Architecture

```text
raw_stock_eod
      ↓
dim_indicator
      ↓
dim_indicator_component
      ↓
dim_indicator_config (D/W/M)
      ↓
vw_Indicator_config          ← Configuration SSOT
      ↓
refresh_technical_indicators()
      ↓
cal_indicator_values         ← internal persistence
      ↓
vw_Ticker_indicators         ← Calculated Value SSOT
      ↓
CherryMon / Screener / Score / Chart / API / ML
```

Vai trò:

```text
dim_indicator
    Master definition: indicator là gì, library function nào, cần input nào.

dim_indicator_component
    Output contract: indicator trả ra component nào.

dim_indicator_config
    Executable contract: Parameters, Timeframe, WarmupBars, IsEnabled.

vw_Indicator_config
    Single Source of Truth cho metadata + executable config + component mapping.

cal_indicator_values
    Calculated long-format persistence nội bộ của Indicator Engine.

vw_Ticker_indicators
    Single Source of Truth / public read contract cho calculated indicator values.
```

Primary key của `cal_indicator_values`:

```text
Ticker + Date + ConfigId + ComponentCode
```

Nguyên tắc kiến trúc bắt buộc:

```text
- Không ALTER fact table khi thêm indicator.
- Không tạo table riêng cho từng indicator.
- Không hard-code indicator mới vào run.py.
- Không truncate cal_indicator_values khi onboarding.
- Không recompute historical của indicator khác nếu targeted backfill theo ConfigId có thể đáp ứng.
- Downstream consumer không đọc trực tiếp cal_indicator_values nếu vw_Ticker_indicators đáp ứng use case.
```

---

# 2. Agent Scope và Trigger

Indicator Engine Agent xử lý các scenario:

```text
A. NEW
   IndicatorCode chưa tồn tại trong dim_indicator.

B. ACTIVATE
   Indicator đã tồn tại nhưng IsActive=FALSE hoặc configs IsEnabled=FALSE.

C. NEW_PARAMETER_FAMILY
   Indicator đang active, cần thêm Parameters mới.
   Ví dụ MA đã có MA20/MA50, cần thêm MA100.

D. REPAIR
   Metadata tồn tại nhưng thiếu component, thiếu D/W/M, thiếu backfill hoặc validation chưa PASS.
```

Agent phải xác định scenario trước khi ghi dữ liệu.

Không được insert duplicate `dim_indicator` nếu `IndicatorCode` đã tồn tại.

---

# 3. Mandatory Three-Phase State Machine

```text
REQUEST
   ↓
DISCOVERY / PRE-CHECK
   ↓
PHASE 1 — CONFIG METADATA
   ↓ PASS only
PHASE 2 — HISTORICAL INITIALIZATION / BACKFILL
   ↓ PASS only
PHASE 3 — VALIDATE cal_indicator_values
   ↓ PASS only
PRODUCTION_READY
   ↓
run.py incremental refresh
```

State rules:

```text
PHASE_1_FAILED
    -> STOP
    -> không chạy backfill

PHASE_2_FAILED
    -> STOP
    -> không production active

PHASE_3_FAILED
    -> STOP
    -> trạng thái NOT_READY
    -> không báo onboarding thành công

PHASE_1_PASS + PHASE_2_PASS + PHASE_3_PASS
    -> PRODUCTION_READY
```

Agent không được tự động bỏ qua lỗi để tiếp tục phase sau.

---

# 4. Discovery / Pre-Check trước PHASE 1

Trước khi thay đổi metadata, Agent phải đọc trạng thái hiện tại.

## 4.1 Master definition

```sql
SELECT
    IndicatorCode,
    IndicatorName,
    Category,
    Engine,
    FunctionName,
    RequiredInputs,
    ParameterSchema,
    IsActive
FROM "CherryMon"."main"."dim_indicator"
WHERE IndicatorCode = '<INDICATOR_CODE>';
```

## 4.2 Components

```sql
SELECT
    IndicatorCode,
    ComponentCode,
    ComponentName,
    OutputPrefix,
    SortOrder,
    IsPrimary,
    IsActive
FROM "CherryMon"."main"."dim_indicator_component"
WHERE IndicatorCode = '<INDICATOR_CODE>'
ORDER BY SortOrder, ComponentCode;
```

## 4.3 Configs

```sql
SELECT
    ConfigId,
    ConfigCode,
    IndicatorCode,
    Timeframe,
    Parameters,
    WarmupBars,
    IsEnabled
FROM "CherryMon"."main"."dim_indicator_config"
WHERE IndicatorCode = '<INDICATOR_CODE>'
ORDER BY Parameters, Timeframe;
```

## 4.4 Verify library function

Phải xác nhận:

```text
Engine
FunctionName
RequiredInputs
Parameters
Return type
Output columns
Warmup requirement
```

Primary engine:

```text
pandas-ta-classic
```

`FunctionName` phải resolve được qua:

```text
src/calcEngine/indicatorRegistry.py
```

Source argument mapping:

```text
Open   -> open_
High   -> high
Low    -> low
Close  -> close
Volume -> volume
```

Với multi-output indicator, phải xác định mapping library output prefix → CherryStock `ComponentCode` trước khi enable config.

Nếu library function không resolve được, STOP trước khi ghi metadata.

---

# 5. PHASE 1 — Config Metadata

## 5.1 Objective

Tạo executable metadata contract hoàn chỉnh:

```text
dim_indicator
    + dim_indicator_component
    + dim_indicator_config D/W/M
```

PHASE 1 chỉ PASS khi ba lớp metadata nhất quán và engine có thể validate được.

---

## 5.2 Upsert `dim_indicator`

Mỗi `IndicatorCode` có đúng một master definition.

Required fields:

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
)
ON CONFLICT (IndicatorCode) DO UPDATE SET
    IndicatorName = EXCLUDED.IndicatorName,
    Category = EXCLUDED.Category,
    Engine = EXCLUDED.Engine,
    FunctionName = EXCLUDED.FunctionName,
    RequiredInputs = EXCLUDED.RequiredInputs,
    ParameterSchema = EXCLUDED.ParameterSchema,
    IsActive = EXCLUDED.IsActive,
    UpdatedAt = CURRENT_TIMESTAMP;
```

Rules:

```text
- RequiredInputs là runtime contract và phải khớp function signature.
- ParameterSchema phải validate được Parameters của config.
- Không dùng library defaults để che config thiếu/sai.
- Nếu onboarding từng bước, có thể giữ IsActive=FALSE cho đến khi metadata hoàn chỉnh.
```

---

## 5.3 Upsert `dim_indicator_component`

Mọi indicator phải có ít nhất một active component.

Single-output contract:

```text
ComponentCode = VALUE
OutputPrefix  = NULL
IsPrimary     = TRUE
IsActive      = TRUE
```

Ví dụ ATR:

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
)
ON CONFLICT (IndicatorCode, ComponentCode) DO UPDATE SET
    ComponentName = EXCLUDED.ComponentName,
    OutputPrefix = EXCLUDED.OutputPrefix,
    SortOrder = EXCLUDED.SortOrder,
    IsPrimary = EXCLUDED.IsPrimary,
    IsActive = EXCLUDED.IsActive;
```

Multi-output examples:

```text
BB
├── LOWER   -> BBL
├── MIDDLE  -> BBM
├── UPPER   -> BBU
├── WIDTH   -> BBB
└── PERCENT -> BBP

MACD
├── LINE   -> MACD
├── SIGNAL -> MACDs
└── HIST   -> MACDh

ADX
├── ADX      -> ADX
├── PLUS_DI  -> DMP
└── MINUS_DI -> DMN
```

Agent không được enable executable configs khi component mapping chưa đầy đủ.

---

## 5.4 Upsert `dim_indicator_config` mặc định D/W/M

Một `IndicatorCode + canonical Parameters JSON` là một **config family**.

Mặc định production family phải đủ:

```text
D = Daily
W = Weekly
M = Monthly
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
    ('ATR14_M', 'ATR', 'M', '{"length":14}'::JSON, 14, TRUE)
ON CONFLICT (ConfigCode) DO UPDATE SET
    IndicatorCode = EXCLUDED.IndicatorCode,
    Timeframe = EXCLUDED.Timeframe,
    Parameters = EXCLUDED.Parameters,
    WarmupBars = EXCLUDED.WarmupBars,
    IsEnabled = EXCLUDED.IsEnabled,
    UpdatedAt = CURRENT_TIMESTAMP;
```

Ví dụ nhiều parameter families:

```text
MA20_D / MA20_W / MA20_M
MA50_D / MA50_W / MA50_M
MA100_D / MA100_W / MA100_M
MA200_D / MA200_W / MA200_M
```

Completeness được kiểm tra theo `IndicatorCode + Parameters`, không chỉ IndicatorCode.

---

## 5.5 WarmupBars contract

```text
MA20      >= 20
MA200     >= 200
RSI14     >= 14
ATR14     >= 14
MACD      recommended >= slow + signal
```

Agent phải chọn WarmupBars đủ để indicator tạo output ổn định sau checkpoint.

Không dùng `WarmupBars=0` nếu indicator có lookback requirement.

---

## 5.6 Metadata validation

Checklist:

```text
[ ] đúng 1 dim_indicator definition
[ ] FunctionName resolve được
[ ] RequiredInputs đúng function signature
[ ] ParameterSchema validate được Parameters
[ ] IsActive=TRUE trước production calculation
[ ] có >= 1 active component
[ ] component mapping đúng library output
[ ] mỗi parameter family đủ D/W/M
[ ] WarmupBars hợp lý
[ ] configs cần onboarding có IsEnabled=TRUE
```

### PHASE 1 PASS criteria

```text
DefinitionValid = TRUE
ComponentsValid = TRUE
ConfigFamiliesComplete = TRUE
ParametersValid = TRUE
WarmupValid = TRUE
LibraryFunctionResolvable = TRUE
```

Nếu bất kỳ điều kiện nào FALSE, PHASE 1 = FAIL và Agent phải STOP.

### PHASE 1 required output

```text
IndicatorCode
Scenario: NEW | ACTIVATE | NEW_PARAMETER_FAMILY | REPAIR
FunctionName
RequiredInputs
Components configured
Config families configured
ConfigIds D/W/M
WarmupBars
PHASE_1_STATUS: PASS | FAIL
```

---

# 6. PHASE 2 — Historical Initialization / Backfill

## 6.1 Objective

Tạo đủ historical calculated values cho indicator/config family vừa onboarding.

Không được coi indicator là production-ready nếu chỉ có dữ liệu incremental gần hiện tại.

---

## 6.2 Targeted smoke test trước full backfill

Khuyến nghị chạy một ticker có lịch sử đủ dài, ví dụ MWG:

```python
refresh_technical_indicators(
    config_ids=[<CONFIG_ID>],
    tickers=["MWG"],
    from_last_day=120,
    connection=connection,
    repository=repository,
)
```

Smoke test xác nhận:

```text
- function chạy được;
- input mapping đúng;
- Parameters đúng;
- component mapping đúng;
- output không empty bất thường;
- Value numeric.
```

Nếu smoke test fail, STOP và quay lại PHASE 1.

---

## 6.3 Historical full initialization

Script chuẩn:

```powershell
.\.venv\Scripts\python.exe scripts\init_refresh_technical_indicators.py
```

Script gọi:

```python
refresh_technical_indicators(
    from_last_day=None,
    tickers=None,
    config_ids=None,
    timeframes=None,
    connection=connection,
    repository=uow.indicators,
)
```

Semantics:

```text
from_last_day=None -> full historical source
tickers=None       -> toàn bộ active source tickers
config_ids=None    -> toàn bộ enabled configs
timeframes=None    -> D/W/M
```

Active source ticker contract:

```text
raw_lstTicker.status = 'Y'
AND
Ticker tồn tại trong raw_stock_eod
```

---

## 6.4 Preferred targeted backfill cho family mới

Khi chỉ onboarding một family mới, Agent phải ưu tiên targeted backfill:

```python
refresh_technical_indicators(
    from_last_day=None,
    tickers=None,
    config_ids=[101, 102, 103],
    connection=connection,
    repository=uow.indicators,
)
```

Ví dụ:

```text
101 = ATR14_D
102 = ATR14_W
103 = ATR14_M
```

Expected scope:

```text
ATR14_D/W/M -> backfill
MA          -> untouched
RSI         -> untouched
BB          -> untouched
```

Agent không được chọn full-engine recompute nếu targeted ConfigIds đủ để hoàn thành onboarding, trừ khi có lý do kỹ thuật rõ ràng.

---

## 6.5 Upsert / idempotency contract

```text
resolve target range
    ↓
delete stale rows của đúng Ticker + ConfigId + target range
    ↓
insert calculated values
    ↓
ON CONFLICT (Ticker, Date, ConfigId, ComponentCode)
DO UPDATE
```

Required behavior:

```text
- rerun không duplicate;
- không truncate cal_indicator_values;
- không delete data của ConfigId khác;
- không làm mất historical của indicator khác;
- Weekly/Monthly cleanup bắt đầu từ period boundary.
```

### PHASE 2 PASS criteria

```text
BackfillExecutionCompleted = TRUE
RecordsUpserted > 0
ExpectedConfigIdsProcessed = TRUE
ExpectedTickerScopeProcessed = TRUE
NoTransactionError = TRUE
```

Nếu `RecordsUpserted = 0`, phải investigate source availability, WarmupBars, Parameters và component mapping.

### PHASE 2 required output

```text
Backfill mode: TARGETED | FULL_ENGINE
ConfigIds processed
Timeframes processed
Tickers processed
Source start
Source max date
Records upserted
Transaction status
PHASE_2_STATUS: PASS | FAIL
```

---

# 7. PHASE 3 — Validate `cal_indicator_values`

## 7.1 Objective

Xác minh historical output vừa backfill đầy đủ, đúng cấu trúc, đúng coverage và không làm hỏng fact storage.

PHASE 3 phải kiểm tra tối thiểu D/W/M coverage, component coverage, ticker coverage, zero-output configs, date coverage, NULL behavior, duplicate PK và sample values.

---

## 7.2 Config / component coverage

```sql
SELECT
    c.IndicatorCode,
    c.ConfigCode,
    c.Timeframe,
    v.ComponentCode,
    COUNT(*) AS Records,
    COUNT(DISTINCT v.Ticker) AS Tickers,
    MIN(v.Date) AS MinDate,
    MAX(v.Date) AS MaxDate,
    SUM(CASE WHEN v.Value IS NULL THEN 1 ELSE 0 END) AS NullValues
FROM "CherryMon"."main"."cal_indicator_values" v
INNER JOIN "CherryMon"."main"."dim_indicator_config" c
    ON c.ConfigId = v.ConfigId
WHERE c.IndicatorCode = '<INDICATOR_CODE>'
GROUP BY
    c.IndicatorCode,
    c.ConfigCode,
    c.Timeframe,
    v.ComponentCode
ORDER BY c.ConfigCode, v.ComponentCode;
```

PASS expectation:

```text
- đủ D/W/M config family;
- đủ expected ComponentCode;
- Records > 0 cho expected configs;
- MinDate/MaxDate hợp lý.
```

---

## 7.3 Source ticker coverage

```sql
SELECT COUNT(DISTINCT eod.Ticker) AS ActiveSourceTickers
FROM "CherryMon"."main"."raw_stock_eod" eod
INNER JOIN "CherryMon"."main"."raw_lstTicker" ticker
    ON ticker.Ticker = eod.Ticker
WHERE ticker.status = 'Y';
```

```sql
SELECT COUNT(DISTINCT v.Ticker) AS IndicatorTickers
FROM "CherryMon"."main"."cal_indicator_values" v
INNER JOIN "CherryMon"."main"."dim_indicator_config" c
    ON c.ConfigId = v.ConfigId
WHERE c.IndicatorCode = '<INDICATOR_CODE>';
```

Hai số không bắt buộc bằng tuyệt đối vì ticker mới có thể chưa đủ WarmupBars.

Nếu source có hàng trăm ticker nhưng output chỉ có 1 ticker thì phải coi là FAIL/anomaly và investigate.

---

## 7.4 Enabled config không sinh output

```sql
SELECT
    c.ConfigId,
    c.ConfigCode,
    c.Timeframe,
    COUNT(v.Ticker) AS OutputRows
FROM "CherryMon"."main"."dim_indicator_config" c
LEFT JOIN "CherryMon"."main"."cal_indicator_values" v
    ON v.ConfigId = c.ConfigId
WHERE c.IndicatorCode = '<INDICATOR_CODE>'
  AND c.IsEnabled = TRUE
GROUP BY c.ConfigId, c.ConfigCode, c.Timeframe
ORDER BY c.ConfigCode;
```

`OutputRows = 0` phải investigate:

```text
RequiredInputs
Parameters
WarmupBars
library output
component mapping
source data availability
```

---

## 7.5 Duplicate PK

```sql
SELECT
    Ticker,
    Date,
    ConfigId,
    ComponentCode,
    COUNT(*) AS cnt
FROM "CherryMon"."main"."cal_indicator_values"
GROUP BY Ticker, Date, ConfigId, ComponentCode
HAVING COUNT(*) > 1;
```

Mandatory PASS: `0 rows`.

---

## 7.6 Unexpected components

```sql
SELECT DISTINCT
    c.IndicatorCode,
    v.ComponentCode
FROM "CherryMon"."main"."cal_indicator_values" v
INNER JOIN "CherryMon"."main"."dim_indicator_config" c
    ON c.ConfigId = v.ConfigId
LEFT JOIN "CherryMon"."main"."dim_indicator_component" comp
    ON comp.IndicatorCode = c.IndicatorCode
   AND comp.ComponentCode = v.ComponentCode
WHERE c.IndicatorCode = '<INDICATOR_CODE>'
  AND comp.ComponentCode IS NULL;
```

Mandatory PASS: `0 rows`.

---

## 7.7 Sample values

```sql
SELECT
    v.Ticker,
    v.Date,
    c.ConfigCode,
    v.ComponentCode,
    v.Value
FROM "CherryMon"."main"."cal_indicator_values" v
INNER JOIN "CherryMon"."main"."dim_indicator_config" c
    ON c.ConfigId = v.ConfigId
WHERE c.IndicatorCode = '<INDICATOR_CODE>'
  AND v.Ticker = 'MWG'
ORDER BY c.ConfigCode, v.Date DESC
LIMIT 100;
```

Agent phải kiểm tra:

```text
- Value numeric;
- không all NULL;
- không all identical bất thường nếu indicator không có semantics như vậy;
- component đúng metadata;
- Date đúng timeframe semantics.
```

---

## 7.8 PHASE 3 PASS criteria

```text
DWMConfigCoverage = PASS
ComponentCoverage = PASS
TickerCoverage = PASS hoặc explained acceptable gap
ZeroOutputConfigCheck = PASS
DateCoverage = PASS
NullBehavior = PASS
DuplicatePK = 0
UnexpectedComponent = 0
SampleValueCheck = PASS
```

### PHASE 3 required output

```text
IndicatorCode
ConfigCode / Timeframe coverage
Expected vs actual components
Active source ticker count
Indicator output ticker count
Records by config
MinDate / MaxDate
NULL counts/rates
Duplicate count
Unexpected component count
Zero-output config count
Sample check result
PHASE_3_STATUS: PASS | FAIL
```

---

# 8. Production Activation Contract

Indicator/config family chỉ `PRODUCTION_READY` khi:

```text
PHASE_1_STATUS = PASS
AND
PHASE_2_STATUS = PASS
AND
PHASE_3_STATUS = PASS
```

Equivalent conditions:

```text
dim_indicator.IsActive = TRUE
AND
>= 1 active dim_indicator_component
AND
config family D/W/M đầy đủ
AND
D/W/M IsEnabled = TRUE
AND
historical backfill hoàn tất
AND
cal_indicator_values validation PASS
```

Sau đó `run.py` tự thực hiện incremental refresh:

```python
refresh_technical_indicators(
    from_last_day=days_diff,
    connection=connection,
    repository=uow.indicators,
)
```

Không thêm hard-code indicator vào `run.py`.

---

# 9. Scenario-Specific Instructions

## 9.1 NEW — Add New Indicator

```text
1. Verify library function.
2. Create/upsert dim_indicator.
3. Create components.
4. Create complete D/W/M config family.
5. Validate metadata.
6. Smoke test.
7. Historical backfill targeted by ConfigIds.
8. Validate cal_indicator_values.
9. Mark production-ready only after PASS.
```

## 9.2 ACTIVATE — Existing Indicator

```text
1. Không duplicate dim_indicator.
2. Revalidate FunctionName / RequiredInputs / ParameterSchema.
3. Verify/repair components.
4. Verify/repair complete D/W/M configs.
5. Enable parent + complete config family.
6. Smoke test.
7. Backfill newly enabled ConfigIds.
8. Validate output.
```

## 9.3 NEW_PARAMETER_FAMILY

Ví dụ MA100 khi MA đã active:

```text
1. Không sửa dim_indicator nếu contract không đổi.
2. Không sửa component nếu output contract không đổi.
3. Create MA100_D/W/M.
4. WarmupBars >= 100.
5. Enable complete family.
6. Smoke test MA100.
7. Backfill only MA100 ConfigIds.
8. Validate MA100 output.
```

Không recompute MA20/MA50 nếu không cần.

---

# 10. Configuration SSOT — `vw_Indicator_config`

`vw_Indicator_config` là public read contract cho metadata + executable config + component mapping.

```sql
CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Indicator_config" AS
SELECT
    cfg.ConfigId,
    cfg.ConfigCode,
    cfg.IndicatorCode,
    cfg.Timeframe,
    cfg.Parameters,
    cfg.WarmupBars,
    cfg.IsEnabled                    AS ConfigIsEnabled,
    cfg.Description                  AS ConfigDescription,
    cfg.CreatedAt                    AS ConfigCreatedAt,
    cfg.UpdatedAt                    AS ConfigUpdatedAt,
    ind.IndicatorName,
    ind.Category,
    ind.Engine,
    ind.FunctionName,
    ind.RequiredInputs,
    ind.ParameterSchema,
    ind.Description                  AS IndicatorDescription,
    ind.IsActive                     AS IndicatorIsActive,
    ind.CreatedAt                    AS IndicatorCreatedAt,
    ind.UpdatedAt                    AS IndicatorUpdatedAt,
    comp.ComponentCode,
    comp.ComponentName,
    comp.OutputPrefix,
    comp.SortOrder,
    comp.IsPrimary,
    comp.IsActive                    AS ComponentIsActive
FROM "CherryMon"."main"."dim_indicator_config" cfg
INNER JOIN "CherryMon"."main"."dim_indicator" ind
    ON ind.IndicatorCode = cfg.IndicatorCode
LEFT JOIN "CherryMon"."main"."dim_indicator_component" comp
    ON comp.IndicatorCode = cfg.IndicatorCode;
```

Grain:

```text
ConfigId + ComponentCode
```

Active config contract:

```sql
SELECT *
FROM "CherryMon"."main"."vw_Indicator_config"
WHERE ConfigIsEnabled = TRUE
  AND IndicatorIsActive = TRUE
  AND COALESCE(ComponentIsActive, TRUE) = TRUE;
```

Downstream config logic phải ưu tiên đọc `vw_Indicator_config` thay vì tự join ba dimension tables nếu view đáp ứng đủ dữ liệu cần thiết.

---

# 11. Calculated Value SSOT — `vw_Ticker_indicators`

`cal_indicator_values` là internal persistence; `vw_Ticker_indicators` là calculated value Single Source of Truth cho downstream consumers.

```text
Indicator Engine
      ↓
cal_indicator_values
      ↓
vw_Ticker_indicators
      ├── CherryMon
      ├── Screener
      ├── Technical Score
      ├── Chart / Level analysis
      ├── API
      └── ML / Prediction
```

Downstream nên query:

```sql
SELECT ...
FROM "CherryMon"."main"."vw_Ticker_indicators";
```

Không duplicate `IndicatorCode`, `Timeframe`, `Period`, `Parameters` trong `cal_indicator_values`; resolve qua `ConfigId`.

---

# 12. Timeframe Contract

Daily:

```text
không resample
```

Weekly / Monthly:

```text
Open   = first
High   = max
Low    = min
Close  = last
Volume = sum
Date   = last actual trading date in period
```

Rules:

```text
- Current partial W/M được phép tính.
- Không hard-code Friday.
- Không hard-code ngày 30/31.
- W/M cleanup bắt đầu từ period boundary để replace stale provisional row.
```

---

# 13. `refresh_technical_indicators()` Contract

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

Execution flow:

```text
1. Ensure storage
2. Load enabled configs
3. Load active definitions
4. Load active components
5. Validate onboarding contract
6. Validate D/W/M completeness
7. Validate ParameterSchema
8. Resolve checkpoint
9. Resolve WarmupBars
10. Batch load OHLCV
11. Resample D/W/M
12. Calculate
13. Normalize components
14. Delete stale target rows
15. Upsert cal_indicator_values
16. Return execution summary
```

Normal production run phải enforce complete D/W/M family.

Targeted `config_ids`/`timeframes` chỉ dùng cho smoke test, debug hoặc backfill.

---

# 14. Function Responsibilities

| Function | Responsibility |
| --- | --- |
| `get_enabled_indicator_configs()` | Load enabled executable configs |
| `get_indicator_definitions()` | Load master indicator definitions |
| `get_indicator_components()` | Load component mapping |
| `validate_indicator_onboarding_contract()` | Enforce metadata lifecycle + D/W/M completeness |
| `validate_indicator_config()` | Validate Parameters và config relationships |
| `load_indicator_source_data()` | Batch load required OHLCV |
| `resample_indicator_timeframe()` | Convert Daily source sang D/W/M |
| `calculate_indicator_from_config()` | Calculate một config cho một ticker |
| `normalize_indicator_output()` | Convert library output sang CherryStock ComponentCode |
| `calculate_indicator_batch()` | Calculate batch, không DB call trong inner loop nếu tránh được |
| `replace_indicator_checkpoint()` | Delete stale checkpoint rows và upsert values |
| `refresh_technical_indicators()` | Public orchestration |

Không query DuckDB bên trong loop từng config nếu có thể batch.

---

# 15. Data Model Reference

## 15.1 `dim_indicator`

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

## 15.2 `dim_indicator_component`

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

## 15.3 `dim_indicator_config`

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

## 15.4 `cal_indicator_values`

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

---

# 16. Migration / Compatibility with `cal_Trends`

Chưa xóa `cal_Trends` trong giai đoạn migration.

```text
cal_Moving_Average()
       ↓
cal_Trends

refresh_technical_indicators()
       ↓
cal_indicator_values
       ↓
vw_Ticker_indicators
```

Chỉ migrate hoàn toàn sau khi validate:

```text
MA20 old == MA20 new
MA50 old == MA50 new
MA100 old == MA100 new
MA200 old == MA200 new
```

Sau migration, `cal_Trends` có thể trở thành compatibility view/pivot derive từ `vw_Ticker_indicators`.

---

# 17. Agent Safety Rules — MUST / MUST NOT

Agent **MUST**:

```text
- đọc metadata hiện tại trước khi ghi;
- xác định scenario onboarding;
- verify library function trước config;
- dùng upsert/idempotent metadata writes;
- config đủ D/W/M theo parameter family;
- dùng targeted ConfigIds khi backfill family mới nếu có thể;
- validate trước production-ready;
- report rõ PASS/FAIL từng phase;
- fail-fast khi contract sai.
```

Agent **MUST NOT**:

```text
- truncate cal_indicator_values;
- xóa historical của indicator khác;
- ALTER fact table để thêm indicator;
- enable partial D/W/M family trong production;
- enable config nếu parent indicator inactive;
- disable component đang được enabled config sử dụng mà chưa migrate;
- thay semantics Parameters trên cùng ConfigCode đã có historical mà không controlled migration;
- coi RecordsUpserted=0 là success mà không investigate;
- production active khi PHASE 3 FAIL;
- sửa run.py chỉ để thêm indicator mới.
```

---

# 18. Agent Required Final Response

```text
INDICATOR ONBOARDING RESULT

IndicatorCode: <CODE>
Scenario: NEW | ACTIVATE | NEW_PARAMETER_FAMILY | REPAIR

PHASE 1 — CONFIG METADATA
Status: PASS | FAIL
Definition: ...
Components: ...
Config families: ...
ConfigIds: ...
D/W/M completeness: ...
WarmupBars: ...

PHASE 2 — HISTORICAL BACKFILL
Status: PASS | FAIL
Mode: TARGETED | FULL_ENGINE
ConfigIds processed: ...
Tickers processed: ...
Records upserted: ...
Source range: ...

PHASE 3 — VALIDATION
Status: PASS | FAIL
D/W/M coverage: ...
Component coverage: ...
Ticker coverage: ...
Date range: ...
Duplicate PK: ...
Zero-output configs: ...
Unexpected components: ...
Sample validation: ...

FINAL STATUS
PRODUCTION_READY | NOT_READY

Next execution:
run.py incremental refresh
```

Nếu `FINAL STATUS = NOT_READY`, Agent phải nêu chính xác phase và condition gây fail.

---

# 19. Compact Operational Checklist

```text
PHASE 1 — CONFIG
[ ] Verify pandas-ta-classic function
[ ] Discover existing metadata
[ ] Upsert dim_indicator
[ ] Upsert dim_indicator_component
[ ] Upsert dim_indicator_config D/W/M
[ ] Validate RequiredInputs
[ ] Validate ParameterSchema
[ ] Validate WarmupBars
[ ] Validate complete D/W/M family
[ ] PHASE 1 PASS

PHASE 2 — BACKFILL
[ ] Smoke test targeted ticker/config
[ ] Resolve D/W/M ConfigIds
[ ] Prefer targeted historical backfill
[ ] Run from_last_day=None
[ ] Confirm records_upserted > 0
[ ] Confirm idempotent/upsert behavior
[ ] PHASE 2 PASS

PHASE 3 — VALIDATION
[ ] Validate D/W/M coverage
[ ] Validate component coverage
[ ] Compare source ticker vs output ticker
[ ] Detect zero-output configs
[ ] Validate MinDate/MaxDate
[ ] Validate NULL behavior
[ ] Duplicate PK = 0
[ ] Unexpected component = 0
[ ] Validate sample values
[ ] PHASE 3 PASS

PRODUCTION
[ ] All three phases PASS
[ ] Production ready
[ ] Future incremental refresh handled by run.py
```

---

# 20. Final Principle

> **Thêm mới hoặc active indicator hoàn toàn bằng metadata/config, tạo historical data bằng targeted upsert theo ConfigId, validate đầy đủ trước production, không thay đổi fact schema và không ảnh hưởng historical data của indicator khác.**
