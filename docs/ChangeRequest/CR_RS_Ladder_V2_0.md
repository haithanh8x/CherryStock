# Change Request — R/S Ladder V2.0

- **Change ID:** CR-RS-V2.0-20260901
- **Release:** R/S Ladder V2.0
- **Date:** 2026-09-01
- **Status:** Code merged / DuckDB migration and local production validation pending
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

Run:

```powershell
python -m pytest tests/test_rs_ladder.py -v
```

Tests cover:

- V1 proximity ranking regression;
- deterministic output;
- BB + MA clustering;
- source-family diversity;
- same-family double counting prevention;
- RSI confirmation changes Strength only;
- non-price semantic rejection.

### Production Data Runbook

Use:

```text
tests/test_R_S_V2_0.md
```

Required validation:

1. DuckDB migration PASS.
2. metadata export refreshed.
3. automated pytest PASS.
4. MA-only MWG smoke PASS.
5. default MA + BB + RSI MWG smoke PASS.
6. semantic safety PASS.
7. NiceGUI R/S smoke PASS.

---

## 11. Current Release Status

At merge time:

| Item | Status |
|---|---|
| Source code merged to main | PASS |
| PR mergeability | PASS |
| Architecture docs | PASS |
| ADR | PASS |
| Migration SQL generated | PASS |
| Unit tests added | PASS |
| GitHub CI | NOT CONFIGURED / NO CHECKS |
| Local DuckDB migration | PENDING |
| Local pytest execution | PENDING |
| MWG real-data validation | PENDING |
| NiceGUI smoke test | PENDING |

Current release state:

```text
CODE MERGED
DATABASE DEPLOYMENT PENDING
PRODUCTION VALIDATION PENDING
```

Do not classify the runtime release as fully production-ready until the local runbook returns PASS.

---

## 12. Deployment Sequence

Run in this exact order:

```text
1. git pull origin main
2. execute src/DuckDB/sql/rs_v2_0_indicator_semantics.sql
3. validate semantic metadata
4. regenerate docs/reference DB metadata snapshots
5. run python -m pytest tests/test_rs_ladder.py -v
6. run MA-only MWG smoke
7. run default V2.0 MWG smoke
8. run NiceGUI R/S smoke
9. mark release production-ready only when all validations PASS
```

---

## 13. Rollback

If migration succeeds but runtime validation fails:

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
