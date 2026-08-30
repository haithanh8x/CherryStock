# CherryStock Indicator Engine Design

## 1. Purpose

Tài liệu này định nghĩa kiến trúc, data model, execution flow, onboarding lifecycle, function contracts và quy trình vận hành Technical Indicator Engine của CherryStock.

Mục tiêu:

- Hỗ trợ thêm technical indicator mà không phải `ALTER TABLE ADD COLUMN`.
- Hỗ trợ indicator có một hoặc nhiều output/component.
- Hỗ trợ mặc định ba timeframe `D/W/M`.
- Sử dụng metadata/config trong DuckDB để gọi `pandas-ta-classic` theo cơ chế config-driven.
- Tách definition, component, executable config và calculated values.
- Dùng cùng checkpoint với `run.py`.
- Tự mở rộng historical window theo `WarmupBars`.
- Rerun idempotent.
- Onboarding indicator mới chủ yếu bằng metadata/config, không hard-code vào pipeline.

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

`IndicatorCode` chỉ mô tả loại indicator, không encode period hoặc timeframe.

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

Runtime không parse Parameters từ `ConfigCode`. Runtime luôn đọc `Parameters` JSON.

## 3.4 Timeframe

```text
D = Daily
W = Weekly
M = Monthly
```

`DEFAULT_TIMEFRAMES = ("D", "W", "M")`.

Mỗi config family mặc định phải có đủ D/W/M.

---

# 4. Data Model

## 4.1 `"CherryMon"."main"."dim_indicator"`

Master definition của indicator.

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

Ví dụ `RequiredInputs`:

```text
RSI -> ["Close"]
ADX -> ["High","Low","Close"]
OBV -> ["Close","Volume"]
MFI -> ["High","Low","Close","Volume"]
```

`RequiredInputs` là runtime source-data contract.

## 4.2 ParameterSchema

Dùng validate `dim_indicator_config.Parameters` trước khi gọi library.

Ví dụ Bollinger Bands:

```json
{
  "length": {"type":"integer","min":2,"required":true},
  "std": {"type":"number","min":0,"required":true}
}
```

Ví dụ MACD:

```json
{
  "fast": {"type":"integer","min":1,"required":true},
  "slow": {"type":"integer","min":2,"required":true},
  "signal": {"type":"integer","min":1,"required":true}
}
```

Ngoài schema validation, engine có thể validate relationship, ví dụ `MACD: fast < slow`.

Không silent fallback sang default parameter của library khi config sai.

## 4.3 `"CherryMon"."main"."dim_indicator_component"`

Lưu output/component chuẩn nội bộ.

Single-output indicator vẫn phải có component:

```text
IndicatorCode = RSI
ComponentCode = VALUE
OutputPrefix  = NULL
IsPrimary     = TRUE
```

Ví dụ multi-output:

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

Database không persist raw library column name trong fact table. Adapter normalize output về `ComponentCode` chuẩn CherryStock.

## 4.4 `"CherryMon"."main"."dim_indicator_config"`

Lưu executable configuration.

Ví dụ RSI14:

```text
RSI14_D | RSI | D | {"length":14}
RSI14_W | RSI | W | {"length":14}
RSI14_M | RSI | M | {"length":14}
```

Ví dụ MA có nhiều parameter family độc lập:

```text
MA20_D / MA20_W / MA20_M
MA50_D / MA50_W / MA50_M
MA100_D / MA100_W / MA100_M
MA200_D / MA200_W / MA200_M
```

Một `IndicatorCode + canonical Parameters JSON` được coi là một **config family**. Mỗi family mặc định phải đủ D/W/M.

## 4.5 WarmupBars

Ví dụ:

```text
MA20      WarmupBars >= 20
MA200     WarmupBars >= 200
RSI14     WarmupBars >= 14
MACD      WarmupBars nên >= slow + signal
```

Engine load thêm historical data trước checkpoint, calculate trên full warmup window nhưng chỉ persist vùng checkpoint cần refresh.

## 4.6 `"CherryMon"."main"."cal_indicator_values"`

Source of truth của calculated values:

```text
Ticker
Date
ConfigId
ComponentCode
Value
CalculatedAt
```

Primary key:

```text
Ticker + Date + ConfigId + ComponentCode
```

Không duplicate IndicatorCode, Timeframe, Parameters trong fact table vì resolve được qua ConfigId.

---

# 5. Mandatory Indicator Onboarding Lifecycle

Đây là contract bắt buộc. Không enable config để chạy production trước khi hoàn tất toàn bộ lifecycle.

```text
STEP 0  Verify library function / design
        ↓
STEP 1  dim_indicator
        ↓
STEP 2  dim_indicator_component
        ↓
STEP 3  dim_indicator_config D/W/M
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

Khuyến nghị onboarding bằng script/transaction thay vì insert thủ công rời rạc.

---

## 5.1 STEP 0 — Verify library function và thiết kế output

Trước khi insert database, phải xác nhận:

```text
Engine
FunctionName
RequiredInputs
Parameters
Return type
Output columns
Warmup requirement
```

Với `pandas-ta-classic`, phải xác nhận function tồn tại trong `indicatorRegistry` hoặc có thể resolve qua registry hiện tại.

Không thêm metadata trước rồi mới kiểm tra library function.

Với multi-output indicator, xác định trước mapping từ library output prefix sang CherryStock `ComponentCode`.

---

## 5.2 STEP 1 — Upsert `dim_indicator`

Phải define đầy đủ tối thiểu:

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

### Quy tắc IsActive khi onboarding mới

Khuyến nghị tạo indicator mới với:

```text
IsActive = FALSE
```

trong giai đoạn chuẩn bị metadata, sau đó chuyển `TRUE` khi component và config đã hoàn chỉnh.

Nếu script onboarding thực hiện cả definition + component + config trong cùng transaction và validate trước commit thì có thể set `IsActive=TRUE` ngay.

---

## 5.3 STEP 2 — Upsert `dim_indicator_component`

Mọi indicator phải có ít nhất một active component.

Single-output:

```text
ComponentCode = VALUE
OutputPrefix  = NULL
IsPrimary     = TRUE
IsActive      = TRUE
```

Multi-output phải khai báo đầy đủ component cần persist.

Không enable executable config nếu component mapping chưa hoàn chỉnh.

---

## 5.4 STEP 3 — Upsert `dim_indicator_config`

Mỗi parameter family phải đủ:

```text
D
W
M
```

Ví dụ ATR14:

```text
ATR14_D | ATR | D | {"length":14}
ATR14_W | ATR | W | {"length":14}
ATR14_M | ATR | M | {"length":14}
```

Nếu thêm ATR20 thì ATR20 là family riêng và cũng phải đủ D/W/M.

### Quy tắc IsEnabled khi onboarding mới

Nên tạo config ban đầu với:

```text
IsEnabled = FALSE
```

nếu metadata đang được chuẩn bị từng bước.

Chỉ chuyển cả family D/W/M sang `IsEnabled=TRUE` khi:

```text
dim_indicator.IsActive = TRUE
components đầy đủ và active
Parameters valid
WarmupBars valid
D/W/M đầy đủ
library function resolve được
```

Không enable từng timeframe rời rạc cho normal production refresh.

---

## 5.5 STEP 4 — Metadata pre-check trước khi calculate

Phải kiểm tra tối thiểu:

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

Checklist:

```text
[ ] dim_indicator có đúng 1 definition
[ ] IsActive = TRUE trước production calculation
[ ] RequiredInputs đúng với library function
[ ] ParameterSchema đúng
[ ] >= 1 active component
[ ] OutputPrefix mapping đúng với library output
[ ] mỗi parameter family đủ D/W/M
[ ] WarmupBars đủ lớn
[ ] toàn bộ family cần chạy có IsEnabled=TRUE
```

---

## 5.6 STEP 5 — Targeted calculation test

Trước khi full historical load, nên chạy targeted test cho config mới.

Ví dụ:

```python
refresh_technical_indicators(
    config_ids=[<CONFIG_ID>],
    tickers=["MWG"],
    from_last_day=120,
    connection=connection,
    repository=repository,
)
```

Mục tiêu:

```text
- xác nhận library function chạy được;
- xác nhận RequiredInputs đúng;
- xác nhận Parameters đúng;
- xác nhận component mapping đúng;
- xác nhận output không empty bất thường;
- xác nhận Value có kiểu numeric hợp lệ.
```

Targeted maintenance run được phép chạy subset config/timeframe và bỏ riêng validation completeness D/W/M cho batch filter. Đây chỉ là test/debug/backfill, không phải production contract.

---

## 5.7 STEP 6 — Historical initialization / backfill

### Khi thêm indicator/config family mới

Phải backfill historical data cho config mới trước khi coi indicator là production-ready.

Script full initialization toàn engine:

```powershell
.\.venv\Scripts\python.exe scripts\init_refresh_technical_indicators.py
```

Script sử dụng:

```python
refresh_technical_indicators(
    from_last_day=None,
    tickers=None,
    config_ids=None,
    timeframes=None,
)
```

Nghĩa là:

```text
from_last_day=None -> full historical
 tickers=None       -> toàn bộ ticker active có raw_stock_eod
 config_ids=None    -> toàn bộ enabled configs
 timeframes=None    -> D/W/M
```

### Khuyến nghị khi chỉ thêm một config family mới

Để tránh recalculate toàn bộ indicator cũ, ưu tiên backfill có filter `config_ids` của family mới nếu có script/tool phù hợp.

Không cần xóa hay recompute historical data của indicator khác.

---

## 5.8 STEP 7 — Validate calculated values

Sau backfill phải kiểm tra:

```sql
SELECT
    c.ConfigCode,
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
GROUP BY c.ConfigCode, v.ComponentCode
ORDER BY c.ConfigCode, v.ComponentCode;
```

Phải kiểm tra:

```text
[ ] Có data cho config D/W/M
[ ] Có đủ expected ComponentCode
[ ] Có nhiều ticker, không chỉ ticker test
[ ] MinDate/MaxDate hợp lý
[ ] NULL rate hợp lý theo warmup behavior
[ ] Không duplicate PK
[ ] Không xuất hiện output component ngoài metadata
```

Kiểm tra duplicate:

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

Kết quả phải là 0 row.

---

## 5.9 STEP 8 — Production activation

Indicator được coi là **production active** khi đồng thời thỏa:

```text
dim_indicator.IsActive = TRUE
AND
>= 1 dim_indicator_component.IsActive = TRUE
AND
config family D/W/M đầy đủ
AND
các config cần chạy IsEnabled = TRUE
AND
historical backfill đã hoàn tất
AND
post-validation PASS
```

Sau thời điểm này không cần thêm hard-code riêng vào `run.py`.

`refresh_technical_indicators()` tự discover enabled configs.

---

## 5.10 STEP 9 — Incremental refresh trong `run.py`

`run.py` có step:

```text
Refresh Technical Indicators
```

và gọi:

```python
refresh_technical_indicators(
    from_last_day=days_diff,
    connection=connection,
    repository=uow.indicators,
)
```

Từ lần chạy production tiếp theo, indicator mới được refresh incremental cùng các indicator khác.

---

# 6. SOP: Active một indicator đã tồn tại

Trường hợp indicator đã có trong `dim_indicator` nhưng đang inactive hoặc chưa có executable config.

Không insert duplicate definition. Thực hiện theo thứ tự sau.

## 6.1 Trường hợp A — `dim_indicator.IsActive = FALSE`

```text
1. Kiểm tra FunctionName / RequiredInputs / ParameterSchema còn đúng.
2. Kiểm tra component metadata đã tồn tại và đúng.
3. Bổ sung/sửa component nếu thiếu.
4. Kiểm tra config family D/W/M.
5. Bổ sung config còn thiếu với IsEnabled=FALSE trước.
6. Set dim_indicator.IsActive=TRUE.
7. Set toàn bộ config family D/W/M cần chạy IsEnabled=TRUE cùng lúc.
8. Chạy targeted test.
9. Chạy historical backfill cho config family vừa active.
10. Validate cal_indicator_values.
11. Để run.py tiếp tục incremental refresh.
```

## 6.2 Trường hợp B — Indicator active nhưng config đang `IsEnabled = FALSE`

Không cần tạo lại `dim_indicator` hoặc component nếu metadata vẫn đúng.

Thứ tự:

```text
1. Xác nhận dim_indicator.IsActive=TRUE.
2. Xác nhận component metadata active.
3. Xác nhận parameter family đủ D/W/M.
4. Validate Parameters/WarmupBars.
5. Enable toàn bộ D/W/M của family cùng lúc.
6. Targeted test.
7. Historical backfill cho family vừa enable.
8. Post-validation.
9. Production incremental qua run.py.
```

## 6.3 Trường hợp C — Thêm parameter family mới cho indicator đã active

Ví dụ đã có `MA20`, muốn thêm `MA100`.

Không sửa `dim_indicator` hoặc component nếu cùng function/output contract.

Chỉ cần:

```text
1. Tạo MA100_D/W/M với cùng canonical Parameters family.
2. Set WarmupBars phù hợp.
3. Validate đủ D/W/M.
4. Enable family.
5. Targeted test MA100.
6. Historical backfill MA100.
7. Validate output.
```

Không recompute MA20/MA50 nếu không cần.

---

# 7. Activation Safety Rules

## 7.1 Không enable partial family trong production

Không hợp lệ:

```text
RSI14_D = TRUE
RSI14_W = TRUE
RSI14_M = FALSE
```

Normal full refresh enforce D/W/M completeness theo `IndicatorCode + Parameters`.

## 7.2 Không enable config nếu parent indicator inactive

Logical rule:

```text
IsEnabled config = TRUE
requires
IsActive indicator = TRUE
```

## 7.3 Không disable component đang được enabled config sử dụng

Nếu thay đổi output mapping, phải validate targeted calculation trước khi production refresh.

## 7.4 Không đổi Parameters trên cùng ConfigCode nếu semantics thay đổi

Nếu một config đã có historical data và cần thay đổi parameter semantics, ưu tiên tạo ConfigCode mới hoặc thực hiện controlled migration/backfill.

Không để cùng `ConfigCode` đại diện hai công thức khác nhau qua thời gian.

## 7.5 Không xóa historical data của indicator khác khi onboarding

Long-format architecture cho phép backfill độc lập theo ConfigId.

---

# 8. Onboarding Validation Contract

`refresh_technical_indicators()` validate metadata trước calculation.

Normal full refresh phải validate:

```text
- enabled config tồn tại;
- active dim_indicator definition tồn tại;
- active component metadata tồn tại;
- RequiredInputs hợp lệ;
- Parameters hợp lệ;
- WarmupBars hợp lệ;
- mỗi IndicatorCode + Parameters family đủ D/W/M;
- library function resolve được.
```

Nếu lifecycle không hoàn chỉnh, engine phải fail trước persistence.

Targeted run có `config_ids` hoặc `timeframes` có thể bỏ riêng D/W/M completeness check của filtered batch nhưng không bỏ các validation khác.

---

# 9. Indicator Registry / Library Adapter

Primary engine library:

```text
pandas-ta-classic
```

Flow:

```text
dim_indicator.FunctionName
        ↓
indicatorRegistry
        ↓
approved pandas-ta-classic callable
```

Source argument mapping:

```text
Open   -> open_
High   -> high
Low    -> low
Close  -> close
Volume -> volume
```

Không persist raw pandas-ta column names trực tiếp vào fact table.

---

# 10. Timeframe Resampling

Source:

```text
"CherryMon"."main"."raw_stock_eod"
```

Weekly/Monthly aggregation:

```text
Open   = first
High   = max
Low    = min
Close  = last
Volume = sum
Date   = last actual trading date in period
```

Current partial W/M được phép tính. Cleanup bắt đầu từ đầu kỳ chứa checkpoint để thay provisional row cũ khi Date đại diện thay đổi.

---

# 11. Checkpoint Contract

`run.py` resolve `days_diff` và Indicator Engine nhận cùng checkpoint.

```text
from_last_day
    ↓
resolve checkpoint target
    ↓
resolve WarmupBars
    ↓
load historical source
    ↓
calculate full loaded window
    ↓
persist only checkpoint target
```

`from_last_day=None` nghĩa là full historical refresh.

---

# 12. `refresh_technical_indicators()` Contract

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

Normal main execution:

```python
refresh_technical_indicators(
    from_last_day=days_diff,
    connection=uow.connection,
    repository=uow.indicators,
)
```

Execution flow:

```text
1. Ensure storage.
2. Load enabled configs.
3. Load active definitions.
4. Load active components.
5. Validate onboarding contract.
6. Validate D/W/M completeness.
7. Validate configs/ParameterSchema.
8. Resolve checkpoint.
9. Resolve warmup window.
10. Batch load required OHLCV source.
11. Resample D/W/M.
12. Calculate values.
13. Normalize components.
14. Delete/replace checkpoint region.
15. Upsert cal_indicator_values.
16. Return summary.
```

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

# 13. Function Responsibilities

| Function | Responsibility |
|---|---|
| `get_enabled_indicator_configs()` | Load enabled executable configs |
| `get_indicator_definitions()` | Load master indicator definition |
| `get_indicator_components()` | Load component/output mapping |
| `validate_indicator_onboarding_contract()` | Enforce metadata lifecycle + D/W/M completeness |
| `validate_indicator_config()` | Validate Parameters and relationships |
| `load_indicator_source_data()` | Batch load required OHLCV inputs |
| `resample_indicator_timeframe()` | Convert Daily source to D/W/M |
| `calculate_indicator_from_config()` | Calculate one config for one ticker |
| `normalize_indicator_output()` | Convert library output to CherryStock long format |
| `calculate_indicator_batch()` | Calculate all configs without DB calls inside loops |
| `replace_indicator_checkpoint()` | Delete stale checkpoint rows and upsert values |
| `refresh_technical_indicators()` | Public orchestration function |

---

# 14. Idempotency and Data Quality

Fact PK:

```text
Ticker + Date + ConfigId + ComponentCode
```

Rerun cùng checkpoint không duplicate.

Sau Technical Indicator Engine, data-quality validation cần kiểm tra:

```text
Ticker
Date
ConfigId
ComponentCode
Value
```

Metadata/config errors phải fail trước calculated-value persistence.

---

# 15. Operational Checklist — New Indicator

Ví dụ ATR:

```text
[ ] 0. Verify pandas-ta-classic function `atr`
[ ] 1. Define RequiredInputs = [High, Low, Close]
[ ] 2. Define ParameterSchema
[ ] 3. Insert/upsert dim_indicator
[ ] 4. Insert/upsert component VALUE
[ ] 5. Define parameter family {"length":14}
[ ] 6. Create ATR14_D / ATR14_W / ATR14_M
[ ] 7. Set correct WarmupBars
[ ] 8. Validate metadata lifecycle
[ ] 9. Enable definition + complete config family
[ ] 10. Run targeted test
[ ] 11. Run historical backfill
[ ] 12. Validate ticker/config/component/date coverage
[ ] 13. Confirm no duplicate PK
[ ] 14. Let run.py perform future incremental refresh
[ ] 15. No fact-table schema alteration required
```

---

# 16. Operational Checklist — Activate Existing Indicator

```text
[ ] 1. Find existing dim_indicator row
[ ] 2. Verify FunctionName / RequiredInputs / ParameterSchema
[ ] 3. Verify active components
[ ] 4. Verify or create complete D/W/M config family
[ ] 5. Verify Parameters and WarmupBars
[ ] 6. Set dim_indicator.IsActive=TRUE if needed
[ ] 7. Set complete config family IsEnabled=TRUE
[ ] 8. Run targeted test
[ ] 9. Historical backfill for newly activated family
[ ] 10. Validate cal_indicator_values
[ ] 11. Continue incremental refresh through run.py
```

---

# 17. Rule Summary

```text
1 indicator definition
    = 1 row dim_indicator

1 indicator
    = >= 1 active dim_indicator_component row

1 parameter family
    = default D + W + M configs

production active
    = IsActive definition
      + active components
      + complete enabled D/W/M family
      + historical backfill
      + validation PASS

1 calculated output
    = Ticker + Date + ConfigId + ComponentCode + Value
```

Mandatory onboarding order:

```text
verify function/design
    ↓
dim_indicator
    ↓
dim_indicator_component
    ↓
dim_indicator_config D/W/M
    ↓
metadata validation
    ↓
targeted test
    ↓
historical backfill
    ↓
post-validation
    ↓
production active
    ↓
run.py incremental refresh
```

Mục tiêu cuối cùng: **thêm hoặc active indicator bằng metadata/config, không thay đổi fact schema và không ảnh hưởng historical data của indicator khác**.
