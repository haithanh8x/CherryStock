# Change Request — R/S Ladder V2.0

- **Change ID:** CR-RS-V2.0-20260901
- **Release:** R/S Ladder V2.0
- **Date:** 2026-09-01
- **Production deployment date:** 2026-09-02
- **Status:** **PRODUCTION DEPLOYED / VALIDATED / PASS**
- **Final verdict:** **PASS**
- **Final action:** **KEEP and STOP**
- **Repository:** CherryStock
- **Main merge commit:** `7ebd6bcb9d0d4faff117f4bff0d99c98c223238b`
- **Pull Request:** #4 — feat: upgrade R/S Ladder to V2.0 multi-source architecture

---

## 1. Change Summary

R/S Ladder V2.0 nâng cấp implementation V1 từ mô hình MA-only sang multi-source architecture.

V2.0 sử dụng:

```text
LEVEL SOURCES
├── MA
│   └── SourceFamily = TREND_AVERAGE
└── Bollinger Bands
    ├── LOWER
    ├── MIDDLE
    └── UPPER
        └── SourceFamily = VOLATILITY_BAND

CONFIRMATION
└── RSI
    └── SourceFamily = MOMENTUM_CONFIRMATION
```

ATR14 đã được onboard và backfill trước release này nhưng **không tham gia R/S V2.0 runtime**. ATR được chuẩn bị semantic metadata để sử dụng trong V2.1 adaptive clustering.

---

## 2. Business / Functional Impact

### Before — V1

```text
MA20 / MA50 / MA100 / MA200
D / W / M
      ↓
LevelCandidate
      ↓
R/S Ladder
```

R/S level chỉ được xây dựng từ MA.

### After — V2.0

```text
Indicator Engine Public SSOT
vw_Ticker_indicators
vw_Indicator_config
          │
          ▼
   Source Providers
   ├── MA
   ├── BB
   └── RSI
          │
     ┌────┴─────┐
     ▼          ▼
LevelCandidate  ConfirmationContext
 MA + BB              RSI
     │                 │
     └────────┬────────┘
              ▼
         R/S Engine
```

Functional behavior:

- MA tiếp tục tạo Support / Resistance level.
- Bollinger Band `LOWER`, `MIDDLE`, `UPPER` có thể tạo price level.
- Bollinger Band `WIDTH` và `PERCENT` không được phép tạo price level.
- RSI không tạo Support / Resistance.
- RSI chỉ đóng vai trò confirmation cho Strength.
- S1/R1 vẫn được xác định theo proximity, không theo Strength.
- Strength confluence chuyển từ raw source count sang source-family diversity để giảm double counting giữa các nguồn correlated.

---

## 3. Architecture Changes

### 3.1 Provider Boundary

R/S core không query hoặc xử lý riêng từng indicator trực tiếp.

Provider layer được dùng để chuyển Indicator Engine output thành canonical R/S contract:

```text
vw_Ticker_indicators
+
vw_Indicator_config
        ↓
Indicator Providers
        ↓
LevelCandidate / ConfirmationContext
        ↓
R/S Core
```

Implemented providers:

- `load_ma_level_candidates()`
- `load_bb_level_candidates()`
- `load_rsi_confirmation_contexts()`

Provider registration:

- `_source_provider_registry()`

### 3.2 Source Role

V2.0 định nghĩa:

```text
LEVEL
CONTEXT
CONFIRMATION
```

Current usage:

| Source | Role |
|---|---|
| MA | LEVEL |
| BB LOWER/MIDDLE/UPPER | LEVEL |
| RSI | CONFIRMATION |
| ATR | reserved for V2.1 CONTEXT |

### 3.3 Source Family

V2.0 thêm SourceFamily để tránh coi nhiều correlated indicators/configs là bằng chứng độc lập.

Current families:

```text
TREND_AVERAGE
VOLATILITY_BAND
MOMENTUM_CONFIRMATION
```

Example:

```text
MA20_D
MA50_D
MA100_D
MA200_D

source_count = 4
source_family_count = 1
```

Trong khi:

```text
MA50_D
BB20_2_D:LOWER

source_count = 2
source_family_count = 2
```

Strength confluence sử dụng `source_family_count`.

---

## 4. Indicator Engine Metadata Changes

V2.0 bổ sung semantic metadata generic cho `dim_indicator_component`:

```text
ValueSemantic VARCHAR
Unit          VARCHAR
```

Các field này thuộc Indicator Engine generic metadata, không phải R/S-specific metadata.

Initial mappings:

| Indicator | Component | ValueSemantic | Unit |
|---|---|---|---|
| MA | VALUE | PRICE_LEVEL | PRICE |
| BB | LOWER | PRICE_LEVEL | PRICE |
| BB | MIDDLE | PRICE_LEVEL | PRICE |
| BB | UPPER | PRICE_LEVEL | PRICE |
| BB | WIDTH | VOLATILITY | PERCENT |
| BB | PERCENT | RATIO | RATIO |
| RSI | VALUE | OSCILLATOR | INDEX |
| ATR | VALUE | VOLATILITY_DISTANCE | PRICE |

Rule bắt buộc:

```text
SourceRole = LEVEL
AND
ValueSemantic = PRICE_LEVEL
```

mới được phép đi vào R/S normalization/clustering pipeline.

---

## 5. DuckDB Change

### 5.1 Required Migration

Existing CherryMon databases phải chạy:

```text
src/DuckDB/sql/rs_v2_0_indicator_semantics.sql
```

Migration thực hiện:

1. add `ValueSemantic` vào `dim_indicator_component`;
2. add `Unit` vào `dim_indicator_component`;
3. populate semantic metadata cho MA, BB, RSI và ATR;
4. recreate `vw_Indicator_config`;
5. expose:
   - `ValueSemantic`
   - `Unit`
   qua Configuration SSOT.

### 5.2 Data Write Impact

Migration chỉ thay đổi metadata/configuration layer.

Không:

- truncate `cal_indicator_values`;
- delete historical indicator values;
- recalculate MA/BB/RSI;
- modify `raw_stock_eod`;
- modify R/S historical persistence vì V2.0 vẫn là read/calculation flow.

### 5.3 Idempotency

Migration sử dụng:

```sql
ADD COLUMN IF NOT EXISTS
```

và deterministic metadata UPDATE nên có thể rerun an toàn trong cùng schema version.

---

## 6. Source Code Changes

Main affected files:

```text
src/calcEngine/levelLadder.py
src/Chart/levelLadderChart.py
src/webapp/NiceGUI_chart.py
src/DuckDB/sql/rs_v2_0_indicator_semantics.sql

scripts/seed_dim_indicator_component.py

src/cherrystock/infrastructure/database/repositories/
    indicator_repository.py

tests/test_rs_ladder.py
tests/test_R_S_V2_0.md
```

Documentation:

```text
docs/architecture/RS_Ladder.md
docs/architecture/Indicator_Engine.md
docs/adr/ADR-004-rs-v2-source-semantics.md
docs/00_HOME.md
```

---

## 7. UI Changes

NiceGUI R/S tab được đổi từ V1 sang V2.0.

Header:

```text
V2.0: MA + Bollinger Bands; RSI dùng làm confirmation
```

Level details bổ sung:

- source families;
- source family count;
- existing source/config lineage vẫn được preserve.

Chart empty state không còn sử dụng message MA-only V1.

---

## 8. Compatibility

### Backward Compatibility

MA-only mode vẫn được hỗ trợ:

```python
build_level_ladder(
    "MWG",
    enabled_sources=("MA",),
)
```

Điều này cho phép:

- regression comparison V1 vs V2;
- ablation testing;
- isolate source contribution.

### Default V2.0

Nếu không truyền `enabled_sources`:

```python
build_level_ladder("MWG")
```

runtime sử dụng:

```text
MA
BB
RSI
```

---

## 9. Strength Model Change

### V1

Confluence dựa trên:

```text
source_count
```

Điều này có nguy cơ double counting correlated indicators/configurations.

### V2.0

Confluence dựa trên:

```text
source_family_count
```

và có saturation target.

RSI confirmation có thể thay đổi `strength_score`, nhưng không thay đổi rank.

Invariant:

```text
S1 = nearest Support
R1 = nearest Resistance
```

Strength và Rank tiếp tục là hai concept độc lập.

---

## 10. Validation

### Automated Test

Executed:

```powershell
python -m pytest tests/test_rs_ladder.py -v
```

Result:

```text
10 passed in 1.27s
```

Status: **PASS**

Tests cover:

- V1 proximity ranking regression;
- deterministic output;
- BB + MA clustering;
- source-family diversity;
- same-family double counting prevention;
- RSI confirmation changes Strength only;
- non-price semantic rejection.

### Production Data Runbook

Runbook:

```text
tests/test_R_S_V2_0.md
```

Final result: **PASS**

All production cross-check steps completed successfully:

1. DuckDB migration — PASS.
2. DB reference refresh — PASS.
3. automated pytest — PASS.
4. MA-only MWG regression — PASS.
5. default MA + BB + RSI MWG smoke — PASS.
6. semantic safety — PASS.
7. NiceGUI smoke — PASS.

### Production Validation Evidence

#### Step 1 — DuckDB migration: PASS

Migration:

```text
src/DuckDB/sql/rs_v2_0_indicator_semantics.sql
```

was applied successfully and verified idempotent.

Validated semantic metadata:

| Indicator | Component | ValueSemantic | Unit |
|---|---|---|---|
| MA | VALUE | PRICE_LEVEL | PRICE |
| BB | LOWER | PRICE_LEVEL | PRICE |
| BB | MIDDLE | PRICE_LEVEL | PRICE |
| BB | UPPER | PRICE_LEVEL | PRICE |
| BB | WIDTH | VOLATILITY | PERCENT |
| BB | PERCENT | RATIO | RATIO |
| RSI | VALUE | OSCILLATOR | INDEX |
| ATR | VALUE | VOLATILITY_DISTANCE | PRICE |

`vw_Indicator_config` exposes both `ValueSemantic` and `Unit`.

Operational note: the first attempt encountered a DuckDB file lock because an old MCP Python process was still holding the database file. The process was stopped and MCP restarted successfully. This was classified as an **environment/operation issue, not a V2.0 code defect**.

#### Step 2 — DB reference refresh: PASS

`exportDuckDB_metadata()` completed successfully.

Generated references now include the semantic columns in both:

```text
dim_indicator_component
vw_Indicator_config
```

Verified in `docs/reference/DB_Metadata.md`.

#### Step 3 — Focused pytest: PASS

```text
tests/test_rs_ladder.py
10 passed
```

#### Step 4 — MA-only regression: PASS

Execution with:

```python
enabled_sources=("MA",)
```

returned:

```text
Support:
S1 = 73.36
S2 = 70.62
S3 = 59.59

Resistance:
R1 = 76.70
R2 = 79.94
```

Only MA sources were present and proximity ranking remained correct.

#### Step 5 — Default V2.0 production-data smoke: PASS

Production smoke result:

```text
AsOfDate    = 2026-08-28
CurrentPrice = 75.0

Support:
S1 = 73.30 | Strength 73.11 | 5 sources | 2 families
S2 = 70.61 | 2 sources | 2 families
S3 = 67.54 | 1 source  | 1 family

Resistance:
R1 = 76.55 | Strength 71.53 | 4 sources | 2 families
R2 = 79.94 | Strength 60.92 | 2 sources | 1 family
R3 = 85.74 | Strength 55.87 | 1 source  | 1 family
```

RSI confirmation values:

```text
RSI14_D = 55.43
RSI14_W = 47.47
RSI14_M = 53.85
```

Validated:

- RSI appears only in `confirmations`;
- RSI does not leak into level sources;
- `source_family_count <= source_count` for every ranked level;
- S1 is nearest support below current price;
- R1 is nearest resistance above current price;
- all Strength scores are inside `[0,100]`.

#### Step 6 — Semantic safety: PASS

A deliberately invalid RSI level candidate with:

```text
value_semantic = OSCILLATOR
```

was rejected with:

```text
ValueError:
LEVEL candidate must have ValueSemantic=PRICE_LEVEL:
RSI14_D=OSCILLATOR
```

This confirms non-price indicator values cannot enter the price-level pipeline.

#### Step 7 — NiceGUI production smoke: PASS

Validated UI behavior:

- header shows `V2.0: MA + Bollinger Bands; RSI dùng làm confirmation`;
- chart renders correctly;
- R/S ladder displays live V2.0 levels;
- Level Details includes `Families`;
- visible families include `TREND_AVERAGE` and `VOLATILITY_BAND`;
- source lineage includes BB and MA configurations;
- Refresh for MWG works;
- observed Reward/Risk approximately `0.91`;
- no stale V1 MA-only empty-state text remains.

Final cross-check result:

```text
FINAL VERDICT: PASS
ACTION: KEEP and STOP
```

---

## 11. Current Release Status

Production deployment and validation completed successfully.

| Item | Status |
|---|---|
| Source code merged to main | PASS |
| PR mergeability | PASS |
| Architecture docs | PASS |
| ADR | PASS |
| Migration SQL | PASS |
| DuckDB migration applied | PASS |
| Semantic metadata validation | PASS |
| DB reference refresh | PASS |
| Unit tests | PASS — 10/10 |
| MA-only regression | PASS |
| Default V2.0 MWG real-data validation | PASS |
| Semantic safety | PASS |
| NiceGUI smoke test | PASS |
| GitHub CI | NOT CONFIGURED / NO CHECKS |
| Production deployment | **PASS** |
| Final verdict | **PASS** |

Current release state:

```text
CODE MERGED
DATABASE MIGRATION COMPLETED
DB REFERENCE REFRESHED
UNIT TEST PASS
PRODUCTION DATA VALIDATION PASS
NICEGUI SMOKE PASS
PRODUCTION DEPLOYED
PRODUCTION READY
```

Final action:

```text
KEEP and STOP
```

R/S Ladder V2.0 is now the deployed production implementation.

---

## 12. Production Deployment Record

Deployment completed in the intended sequence:

```text
1. git pull origin main                                      PASS
2. execute rs_v2_0_indicator_semantics.sql                  PASS
3. validate semantic metadata                              PASS
4. regenerate docs/reference DB metadata snapshots         PASS
5. python -m pytest tests/test_rs_ladder.py -v             PASS — 10/10
6. MA-only MWG regression smoke                            PASS
7. default V2.0 MWG production-data smoke                  PASS
8. semantic safety test                                    PASS
9. NiceGUI R/S smoke                                       PASS
10. production rollout                                     PASS
```

Deployment date:

```text
2026-09-02
```

No code rollback or database rollback was required.

---

## 13. Rollback

No rollback was required during production deployment.

The following rollback path remains documented for contingency use.

If a future regression requires rollback:

### Code rollback

Revert merge commit:

```text
7ebd6bcb9d0d4faff117f4bff0d99c98c223238b
```

or temporarily invoke:

```python
build_level_ladder(
    ticker,
    enabled_sources=("MA",),
)
```

to isolate V2.0 sources.

### Database rollback

The two new metadata columns are additive and backward-compatible.

Normal rollback does **not** require dropping:

```text
ValueSemantic
Unit
```

because V1 consumers ignore them.

If required by an explicit schema rollback, recreate `vw_Indicator_config` using the previous contract and remove columns only after confirming no downstream consumer uses them.

---

## 14. Risks

### Risk — Correlated level sources

Mitigation:

```text
source_family_count
```

instead of raw source count for confluence.

### Risk — Non-price components entering clustering

Mitigation:

```text
SourceRole == LEVEL
AND ValueSemantic == PRICE_LEVEL
```

validation.

### Risk — RSI incorrectly becoming a price level

Mitigation:

RSI provider outputs `ConfirmationContext`, not `LevelCandidate`.

### Risk — Existing DB schema mismatch

Mitigation:

mandatory migration before V2.0 default runtime.

Production outcome: **mitigated successfully**. Migration was applied and validated.

### Operational Risk — DuckDB file lock from MCP process

Observed during production cross-check:

```text
old Python MCP process held CherryMon.duckdb file lock
```

Resolution:

```text
stop stale Python process
restart MCP server
rerun validation
```

Classification:

```text
environment / operational issue
not a V2.0 code defect
```

### Risk — Historical indicator data unavailable

MA/BB/RSI must already have sufficient backfilled values in `vw_Ticker_indicators`.

---

## 15. Next Planned Release

R/S V2.1 target:

```text
ATR-adaptive clustering
Swing High / Low
Previous Week / Month High-Low
52W High / Low
Point-in-time / no-lookahead contract
Strength Engine V2 refinement
```

ATR14 is already onboarded/backfilled and semantic metadata is prepared by this V2.0 migration.

---

## 16. References

Architecture:

```text
docs/architecture/RS_Ladder.md
docs/architecture/Indicator_Engine.md
```

ADR:

```text
docs/adr/ADR-004-rs-v2-source-semantics.md
```

Migration:

```text
src/DuckDB/sql/rs_v2_0_indicator_semantics.sql
```

Validation:

```text
tests/test_rs_ladder.py
tests/test_R_S_V2_0.md
```

GitHub:

```text
PR #4
Merge commit: 7ebd6bcb9d0d4faff117f4bff0d99c98c223238b
```

Production validation summary:

```text
DuckDB migration       PASS
DB reference refresh   PASS
pytest                  PASS — 10/10
MA-only regression     PASS
V2.0 real-data smoke   PASS
semantic safety        PASS
NiceGUI smoke          PASS

FINAL VERDICT           PASS
ACTION                  KEEP and STOP
RELEASE STATUS          PRODUCTION DEPLOYED / PRODUCTION READY
```

Operational cleanup note:

```text
scripts/query_mwg_price.py
```

was a one-off query script from an earlier session and was explicitly undone before final production sign-off. No rollback action is required for that file.
