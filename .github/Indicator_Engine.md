# CherryStock Indicator Engine Design

> **Canonical operational contract** — Technical Indicator Engine của CherryStock sử dụng metadata-driven architecture và long-format fact table. Indicator mới phải hoàn tất Config → Historical Backfill → Validation trước khi production active.

## 1. Core Architecture

```text
raw_stock_eod
      ↓
dim_indicator
      ↓
dim_indicator_component
      ↓
dim_indicator_config (D/W/M)
      ↓
refresh_technical_indicators()
      ↓
cal_indicator_values
      ↓
vw_Ticker_indicators
```

`cal_indicator_values` là calculated long-format storage. `vw_Ticker_indicators` là Single Source of Truth cho consumer/query layer.

Primary key của calculated values:

```text
Ticker + Date + ConfigId + ComponentCode
```

Không ALTER fact table khi thêm indicator mới và không tạo table riêng cho từng indicator.

---

# 2. Data Model Contract

## 2.1 `dim_indicator`

Mỗi IndicatorCode có đúng một master definition.

Các field chính:

```text
IndicatorCode
IndicatorName
Category
Engine
FunctionName
RequiredInputs
ParameterSchema
Description
IsActive
CreatedAt
UpdatedAt
```

Ví dụ:

```text
RSI -> RequiredInputs=["Close"]
ADX -> RequiredInputs=["High","Low","Close"]
OBV -> RequiredInputs=["Close","Volume"]
MFI -> RequiredInputs=["High","Low","Close","Volume"]
```

`RequiredInputs` là runtime contract, không phải metadata mô tả tham khảo.

## 2.2 `dim_indicator_component`

Mọi indicator phải có ít nhất một active component.

Single-output:

```text
ComponentCode = VALUE
OutputPrefix  = NULL
IsPrimary     = TRUE
IsActive      = TRUE
```

Multi-output ví dụ:

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

## 2.3 `dim_indicator_config`

Một `IndicatorCode + canonical Parameters JSON` là một **config family**.

Mặc định mọi family production phải đủ 3 timeframe:

```text
D = Daily
W = Weekly
M = Monthly
```

Ví dụ:

```text
RSI14_D / RSI14_W / RSI14_M
ATR14_D / ATR14_W / ATR14_M
MA20_D  / MA20_W  / MA20_M
MA50_D  / MA50_W  / MA50_M
```

Không coi `MA20_D + MA50_W + MA50_M` là một family đầy đủ. Completeness được validate theo `IndicatorCode + Parameters`.

## 2.4 WarmupBars

```text
MA20  >= 20
MA200 >= 200
RSI14 >= 14
MACD  >= slow + signal (recommended)
```

Engine load historical source trước checkpoint theo WarmupBars, calculate trên full loaded window nhưng chỉ persist target checkpoint.

---

# 3. Mandatory Onboarding Lifecycle

```text
STEP 0  Verify library function / output design
        ↓
STEP 1  Config dim_indicator
        ↓
STEP 2  Config dim_indicator_component
        ↓
STEP 3  Config dim_indicator_config D/W/M
        ↓
STEP 4  Metadata pre-check
        ↓
STEP 5  Targeted calculation test
        ↓
STEP 6  Historical initialization / backfill
        ↓
STEP 7  Validate cal_indicator_values
        ↓
STEP 8  Production active
        ↓
STEP 9  Incremental refresh through run.py
```

Ba bảng metadata phải được coi như một logical unit:

```text
dim_indicator
+ dim_indicator_component
+ dim_indicator_config
```

---

# 4. PHASE 1 — Config Metadata

## 4.1 Verify library function trước khi config

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

Với `pandas-ta-classic`, FunctionName phải resolve được qua `indicatorRegistry`.

Với multi-output indicator, phải xác định trước mapping từ library output prefix sang CherryStock ComponentCode.

---

## 4.2 Config `dim_indicator`

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

Nếu onboarding metadata từng bước, có thể tạo indicator với `IsActive=FALSE`, sau đó chỉ active khi component/config đã hoàn chỉnh.

---

## 4.3 Config `dim_indicator_component`

Single-output ATR:

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

Multi-output indicator phải config đầy đủ mọi component cần persist. Không enable executable config nếu component mapping chưa hoàn chỉnh.

---

## 4.4 Config `dim_indicator_config` mặc định D/W/M

Mỗi parameter family phải có đúng contract D/W/M.

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

Nếu thêm ATR20 thì phải tạo family riêng:

```text
ATR20_D
ATR20_W
ATR20_M
```

Không enable partial family trong production.

---

## 4.5 Metadata pre-check

```sql
SELECT
    IndicatorCode,
    IndicatorName,
    Engine,
    FunctionName,
    RequiredInputs,
    ParameterSchema,
    IsActive
FROM "CherryMon"."main"."dim_indicator"
WHERE IndicatorCode = '<INDICATOR_CODE>';
```

```sql
SELECT
    IndicatorCode,
    ComponentCode,
    OutputPrefix,
    IsPrimary,
    IsActive
FROM "CherryMon"."main"."dim_indicator_component"
WHERE IndicatorCode = '<INDICATOR_CODE>'
ORDER BY SortOrder, ComponentCode;
```

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

Metadata PASS khi:

```text
[ ] đúng 1 dim_indicator definition
[ ] FunctionName resolve được
[ ] RequiredInputs đúng
[ ] ParameterSchema đúng
[ ] IsActive=TRUE trước production calculation
[ ] >= 1 active component
[ ] OutputPrefix mapping đúng
[ ] mỗi parameter family đủ D/W/M
[ ] WarmupBars hợp lý
[ ] family cần chạy có IsEnabled=TRUE
```

---

# 5. PHASE 2 — Historical Initialization / Backfill

Indicator/config family mới phải được backfill historical data trước khi coi là production-ready. Không chỉ chạy `days_diff`, vì như vậy indicator mới chỉ có dữ liệu gần hiện tại.

## 5.1 Full initialization toàn engine

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
tickers=None       -> toàn bộ ticker active có raw_stock_eod
config_ids=None    -> toàn bộ enabled configs
timeframes=None    -> D/W/M
```

Ticker source mặc định phải thỏa:

```text
raw_lstTicker.status = 'Y'
AND
Ticker tồn tại trong raw_stock_eod
```

## 5.2 Targeted historical backfill cho family mới

Khi chỉ thêm một indicator/config family, ưu tiên backfill theo `config_ids` để không recalculate indicator cũ:

```python
refresh_technical_indicators(
    from_last_day=None,
    tickers=None,
    config_ids=[101, 102, 103],
    connection=connection,
    repository=uow.indicators,
)
```

Ví dụ `101/102/103` tương ứng `ATR14_D/W/M`.

Nguyên tắc:

```text
new ATR14 -> backfill ATR14_D/W/M
không cần recompute MA
không cần recompute RSI
không cần recompute BB
```

Đây là mục tiêu chính của long-format architecture: onboarding độc lập theo ConfigId.

## 5.3 Upsert / idempotency contract

Persistence phải theo cơ chế replace checkpoint + upsert:

```text
resolve target range
    ↓
delete stale rows trong target range
    ↓
insert calculated values
    ↓
ON CONFLICT (Ticker, Date, ConfigId, ComponentCode)
DO UPDATE
```

Primary key:

```text
Ticker + Date + ConfigId + ComponentCode
```

Do đó rerun backfill:

```text
không tạo duplicate
không yêu cầu truncate toàn bộ cal_indicator_values
không xóa historical data của config khác
```

Weekly/Monthly cleanup bắt đầu từ period boundary để thay stale provisional value khi ngày đại diện của tuần/tháng thay đổi.

---

# 6. PHASE 3 — Validate `cal_indicator_values`

Backfill chỉ được coi là hoàn tất khi post-validation PASS.

## 6.1 Coverage theo config/component

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
ORDER BY
    c.ConfigCode,
    v.ComponentCode;
```

Phải thấy đủ expected D/W/M và ComponentCode.

## 6.2 So sánh ticker source và ticker output

Source active tickers:

```sql
SELECT COUNT(DISTINCT eod.Ticker) AS ActiveSourceTickers
FROM "CherryMon"."main"."raw_stock_eod" eod
INNER JOIN "CherryMon"."main"."raw_lstTicker" ticker
    ON ticker.Ticker = eod.Ticker
WHERE ticker.status = 'Y';
```

Indicator output tickers:

```sql
SELECT COUNT(DISTINCT v.Ticker) AS IndicatorTickers
FROM "CherryMon"."main"."cal_indicator_values" v
INNER JOIN "CherryMon"."main"."dim_indicator_config" c
    ON c.ConfigId = v.ConfigId
WHERE c.IndicatorCode = '<INDICATOR_CODE>';
```

Hai số không bắt buộc luôn bằng tuyệt đối vì ticker mới có thể chưa đủ WarmupBars. Tuy nhiên nếu source có hàng trăm ticker mà output chỉ có 1 ticker thì phải coi là lỗi cần điều tra.

## 6.3 Detect enabled config không sinh output

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
GROUP BY
    c.ConfigId,
    c.ConfigCode,
    c.Timeframe
ORDER BY c.ConfigCode;
```

`OutputRows = 0` phải được investigate: RequiredInputs, Parameters, WarmupBars, component mapping hoặc library output.

## 6.4 Duplicate validation

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

Kết quả bắt buộc: `0 row`.

## 6.5 Sample value validation

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

Kiểm tra Value numeric hợp lý và output component đúng metadata.

## 6.6 Validation checklist

```text
[ ] Có data cho D/W/M
[ ] Có đủ expected ComponentCode
[ ] Có nhiều ticker, không chỉ ticker test
[ ] MinDate/MaxDate hợp lý
[ ] NULL rate hợp lý theo warmup behavior
[ ] Không duplicate PK
[ ] Không có enabled config OutputRows=0 bất thường
[ ] Không có component ngoài metadata
[ ] Sample values hợp lý
```

---

# 7. Production Activation

Indicator được coi là production-ready khi:

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

Sau đó `run.py` thực hiện incremental refresh:

```python
refresh_technical_indicators(
    from_last_day=days_diff,
    connection=connection,
    repository=uow.indicators,
)
```

Không cần hard-code indicator mới vào `run.py`.

---

# 8. Active Existing Indicator / Add Parameter Family

Nếu indicator đã tồn tại nhưng inactive:

```text
1. Verify FunctionName / RequiredInputs / ParameterSchema.
2. Verify/bổ sung component metadata.
3. Verify/bổ sung config family D/W/M.
4. Validate Parameters + WarmupBars.
5. Set dim_indicator.IsActive=TRUE.
6. Enable cả family D/W/M cùng lúc.
7. Targeted test.
8. Historical backfill family vừa active.
9. Validate cal_indicator_values.
10. Để run.py incremental refresh.
```

Nếu chỉ thêm parameter family mới, ví dụ MA100 khi MA đã active:

```text
1. Không tạo lại dim_indicator.
2. Không tạo lại component nếu output contract không đổi.
3. Tạo MA100_D/W/M.
4. Set WarmupBars >= 100.
5. Enable complete family.
6. Targeted test.
7. Historical backfill MA100 only.
8. Validate output.
```

Không recompute MA20/MA50 nếu không cần.

---

# 9. Timeframe Resampling

Daily không resample.

Weekly/Monthly:

```text
Open   = first
High   = max
Low    = min
Close  = last
Volume = sum
Date   = last actual trading date in period
```

Current partial W/M được phép tính. Không hard-code Friday hoặc ngày 30/31 làm Date.

---

# 10. `refresh_technical_indicators()` Contract

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

Targeted runs có `config_ids` hoặc `timeframes` có thể chạy subset cho debug/backfill. Normal production run phải enforce complete D/W/M family.

---

# 11. Safety Rules

```text
1. Không enable partial D/W/M family trong production.
2. Không enable config nếu parent dim_indicator inactive.
3. Không disable component đang được enabled config sử dụng.
4. Không thay đổi semantics của Parameters trên cùng ConfigCode nếu đã có historical data; ưu tiên ConfigCode mới hoặc controlled migration.
5. Không truncate cal_indicator_values khi onboarding một indicator.
6. Không recompute historical data của indicator khác nếu có thể targeted backfill theo ConfigId.
7. Metadata/config errors phải fail trước persistence.
8. Rerun phải idempotent.
```

---

# 12. Final Operational Checklist

```text
CONFIG
[ ] Verify pandas-ta-classic function
[ ] Upsert dim_indicator
[ ] Upsert dim_indicator_component
[ ] Upsert dim_indicator_config D/W/M
[ ] Validate RequiredInputs / ParameterSchema / WarmupBars
[ ] Validate complete D/W/M family

BACKFILL
[ ] Targeted calculation test
[ ] Run historical initialization/backfill
[ ] Prefer config_ids for newly added family
[ ] Confirm upsert/idempotent behavior

VALIDATION
[ ] Validate config/component coverage
[ ] Validate D/W/M coverage
[ ] Compare active source ticker count vs output ticker count
[ ] Detect enabled config with zero output
[ ] Validate MinDate/MaxDate
[ ] Validate NULL behavior
[ ] Validate duplicate PK = 0
[ ] Validate sample values

PRODUCTION
[ ] Mark indicator/config family production active only after PASS
[ ] Future incremental refresh handled by run.py
```

Mục tiêu cuối cùng: **thêm hoặc active indicator bằng metadata/config, backfill historical theo ConfigId bằng cơ chế upsert, validate output đầy đủ, không thay đổi fact schema và không ảnh hưởng historical data của indicator khác**.
