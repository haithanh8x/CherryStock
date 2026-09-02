# Change Request — R/S Ladder V2.1

- **Change ID:** CR-RS-V2.1-20260902
- **Release:** R/S Ladder V2.1
- **Date:** 2026-09-02
- **Production deployment date:** 2026-09-02
- **Status:** **PRODUCTION DEPLOYED / VALIDATED**
- **Final verdict:** **PASS**
- **Final action:** **KEEP**
- **Repository:** CherryStock
- **Pull Request:** #5 — feat: upgrade R/S Ladder to V2.1 adaptive structural architecture
- **Main merge commit:** `1d1b82b7023c3ae1142c6c449fc538278ffbe0a3`

---

## 1. Change Summary

R/S Ladder V2.1 nâng cấp V2.0 theo hai hướng chính:

1. **Adaptive volatility**
   - ATR14_D trở thành CONTEXT.
   - Cluster threshold và neutral threshold tự điều chỉnh theo ATR.
2. **Observed market structure**
   - Swing High / Low.
   - Previous Week High / Low.
   - Previous Month High / Low.
   - Rolling 52W High / Low.
   - Point-in-time / no-lookahead contract.

V2.1 không thay đổi invariant:

```text
S1 = nearest eligible support
R1 = nearest eligible resistance
Strength = confidence, not rank
```

---

## 2. Source Model

### LEVEL

```text
MA                         TREND_AVERAGE
BB LOWER/MIDDLE/UPPER      VOLATILITY_BAND
Swing High/Low             MARKET_STRUCTURE
Previous Week H/L          MARKET_STRUCTURE
Previous Month H/L         MARKET_STRUCTURE
52W High/Low               MARKET_STRUCTURE
```

### CONTEXT

```text
ATR14_D                    VOLATILITY_CONTEXT
```

### CONFIRMATION

```text
RSI14_D/W/M                MOMENTUM_CONFIRMATION
```

ATR không tạo LevelCandidate.

RSI không tạo LevelCandidate.

---

## 3. ATR Adaptive Clustering

Formula:

```text
ATRPercent = ATR14_D / CurrentPrice

ClusterThresholdPct =
    max(
        MinClusterPct,
        ATRPercent × ATRClusterMultiplier
    )

NeutralThresholdPct =
    max(
        MinNeutralPct,
        ATRPercent × ATRNeutralMultiplier
    )
```

Current defaults:

```text
MinClusterPct         = 1.0%
MinNeutralPct         = 0.3%
ATRClusterMultiplier  = 0.50
ATRNeutralMultiplier  = 0.15
```

Nếu ATR context không có tại historical `as_of_date`:

```text
fallback = configured percent floor
```

không fail toàn bộ ladder.

Actual runtime thresholds được expose trong:

```text
LevelLadderResult.cluster_threshold_pct_used
LevelLadderResult.neutral_threshold_pct_used
LevelLadderResult.market_contexts
```

---

## 4. Point-in-Time Contract

V2.1 bổ sung:

```text
source_date
confirmed_at
```

cho level candidates.

Mandatory invariant:

```text
source_date <= as_of_date
confirmed_at <= as_of_date
```

Nếu `confirmed_at > as_of_date`, normalization fail rõ ràng.

### Swing

```text
source_date
    = pivot date

confirmed_at
    = right-side confirmation bar date
```

Default:

```text
left = 3
right = 3
lookback = 252 bars
max candidates each side = 12
```

Swing pivot chưa đủ right-side bars không được dùng.

### Previous Week

Chỉ dùng completed previous ISO/calendar week.

Current partial week bị loại.

### Previous Month

Chỉ dùng completed previous calendar month.

Current partial month bị loại.

### 52W

Rolling window:

```text
as_of_date - 365 days
        ↓
as_of_date
```

Không dùng future bar.

---

## 5. Structural Providers

V2.1 đọc trực tiếp:

```text
raw_stock_eod
```

cho structural sources.

Không tạo technical-indicator metadata giả cho Swing/Previous H-L/52W.

Common structural contract:

```text
source_type    = STRUCTURAL
source_role    = LEVEL
source_family  = MARKET_STRUCTURE
value_semantic = PRICE_LEVEL
```

Implemented functions:

```text
load_swing_level_candidates()
load_previous_period_level_candidates()
load_52w_level_candidates()
```

---

## 6. Strength V2.1

V2.1 giữ:

```text
Family Diversity
Timeframe Confluence
Touch Quality
Recency
RSI Confirmation
```

và thêm:

```text
StructuralQuality
```

StructuralQuality dựa trên MARKET_STRUCTURE evidence và recency.

Structural component chỉ được thêm khi zone thực sự chứa structural source.

Điều này tránh tự động penalize các indicator-only levels của V2.0.

---

## 7. Backward Compatibility

MA-only regression vẫn hỗ trợ:

```python
build_level_ladder(
    "MWG",
    enabled_sources=("MA",),
)
```

V2.0-like indicator-only mode:

```python
build_level_ladder(
    "MWG",
    enabled_sources=("MA", "BB", "RSI"),
)
```

Indicator + ATR without structure:

```python
build_level_ladder(
    "MWG",
    enabled_sources=("MA", "BB", "ATR", "RSI"),
)
```

Default V2.1:

```python
build_level_ladder("MWG")
```

enables all registered V2.1 providers.

---

## 8. DuckDB Impact

### Schema Migration

```text
NO NEW DDL MIGRATION REQUIRED
```

V2.1 reuse các production objects đã có:

```text
raw_stock_eod
vw_Ticker_indicators
vw_Indicator_config
ATR14_D
ValueSemantic
Unit
```

ATR14 đã onboard/backfill trước release này.

### Required Preflight

Read-only SQL:

```text
src/DuckDB/sql/rs_v2_1_preflight.sql
```

Preflight validates:

- ATR14_D config;
- ATR semantic metadata;
- ATR calculated-value coverage;
- MWG benchmark ATR;
- raw_stock_eod structural-history coverage;
- benchmark latest eligible raw date.

No DDL/DML is executed by this SQL.

---

## 9. Source Code Changes

Main files:

```text
src/calcEngine/levelLadder.py
src/Chart/levelLadderChart.py
src/webapp/NiceGUI_chart.py
src/DuckDB/sql/rs_v2_1_preflight.sql
```

Validation:

```text
tests/test_rs_ladder.py
tests/test_R_S_V2_1.md
```

Documentation:

```text
docs/architecture/RS_Ladder.md
docs/adr/ADR-005-rs-v2-1-adaptive-structural.md
docs/00_HOME.md
```

---

## 10. UI Changes

NiceGUI R/S header:

```text
V2.1: ATR adaptive + MA/BB + Swing/Previous H-L/52W; RSI confirmation
```

Cluster control đổi thành:

```text
Min Cluster %
```

vì input hiện chỉ là floor; actual threshold có thể lớn hơn do ATR.

Refresh notification expose:

```text
actual cluster %
actual neutral %
```

Level Details tiếp tục hiển thị Families và có thể xuất hiện:

```text
MARKET_STRUCTURE
```

---

## 11. Validation Evidence

Focused automated test:

```powershell
python -m pytest tests/test_rs_ladder.py -v
```

V2.1 tests cover:

- ATR adaptive threshold;
- ATR fallback;
- future confirmed candidate rejection;
- confirmed swing pivots;
- previous period current-partial exclusion;
- 52W point-in-time bound;
- structural family Strength contribution;
- all existing V2.0 regression tests.

Production runbook:

```text
tests/test_R_S_V2_1.md
```

Production validation completed successfully on 2026-09-02.

### Seq 1 — Git sync: PASS

Main contained merge commit `1d1b82b7023c3ae1142c6c449fc538278ffbe0a3`.

### Seq 2 — DuckDB preflight: PASS — 5/5

Read-only preflight via MCP validated:

- ATR14_D ConfigId=37.
- ValueSemantic=VOLATILITY_DISTANCE.
- Unit=PRICE.
- all active flags TRUE.
- ATR coverage=1,112,839 records / 349 tickers / 0 NULL.
- max ATR date=2026-08-28.
- MWG ATR14_D=1.9615 at 2026-08-28.
- MWG raw_stock_eod=256 records in one-year window.
- 0 NULL High/Low/Close.
- latest eligible date=2026-08-28.

### Seq 3 — pytest: PASS

```text
17 passed
```

### Seq 4 — MA-only regression: PASS

```text
S1=73.36
R1=76.70
cluster floor=1.0%
neutral floor=0.3%
```

Only TREND_AVERAGE sources were present.

### Seq 5 — ATR adaptive smoke: PASS

```text
ATRPercent = 1.9615 / 75 = 2.615%
Cluster    = 1.3077%
Neutral    = 0.3923%
```

Values match the configured ATR formula exactly.

### Seq 6 — Structural providers: PASS

Validated:

```text
SWING
PREVIOUS_HL
52W_HL
```

All structural candidates satisfy:

```text
source_date <= as_of_date
confirmed_at <= as_of_date
source_family = MARKET_STRUCTURE
value_semantic = PRICE_LEVEL
```

Runtime correctly rejects unsupported aliases and reports the supported source set.

### Seq 7 — Default V2.1 MWG smoke: PASS

```text
AsOfDate=2026-08-28
CurrentPrice=75.0

S1=73.28 | Strength=79.87 | 9 sources | 3 families
R1=76.68 | Strength=71.53 | 3 sources | 2 families
```

RSI appears only in confirmations; ATR appears only in contexts. All proximity, family-count and strength-range invariants PASS.

### Seq 8 — Historical point-in-time: PASS

Validated dates:

```text
2026-08-15
2026-07-31
2026-06-30
```

Result: **0 look-ahead violations**.

### Seq 9 — NiceGUI smoke: PASS

Validated:

- V2.1 header;
- Min Cluster % control;
- full ladder render;
- current price marker;
- MARKET_STRUCTURE family;
- SWING/PREV_MONTH/PREV_WEEK lineage;
- Refresh.

Final result:

```text
FINAL VERDICT: PASS
ACTION: KEEP
```

---

## 12. Current Release Status

| Item | Status |
|---|---|
| Architecture contract | PASS |
| ADR | PASS |
| Source code merged to main | PASS |
| PR #5 | MERGED |
| DuckDB DDL migration | NOT REQUIRED |
| DuckDB read-only preflight | PASS (executed 2026-09-02) |
| Automated tests added | PASS |
| Local pytest execution | PASS (17 passed) |
| ATR real-data validation | PASS (cluster 1.3077% / neutral 0.3923% adaptive) |
| Structural real-data validation | PASS (SWING / PREVIOUS_HL / 52W_HL) |
| Historical no-lookahead smoke | PASS (2026-08-15, 2026-07-31, 2026-06-30) |
| NiceGUI V2.1 smoke | PASS (header, Min Cluster %, MARKET_STRUCTURE families) |
| Production deployment | PASS |

Current state:

```text
CODE MERGED
NO DATABASE MIGRATION REQUIRED
PRODUCTION PREFLIGHT PASS
PRODUCTION VALIDATION PASS
PRODUCTION DEPLOYED
```

V2.1 has completed the local runbook with PASS and is classified as **PRODUCTION READY / PRODUCTION DEPLOYED**.

---

## 13. Production Deployment Record

```text
1. git pull origin main                          PASS
2. DuckDB read-only preflight                    PASS — 5/5
3. pytest                                        PASS — 17/17
4. MA-only regression                            PASS
5. ATR adaptive smoke                            PASS
6. structural provider smoke                     PASS
7. default V2.1 MWG smoke                        PASS
8. historical point-in-time comparison           PASS
9. NiceGUI smoke                                 PASS
10. production rollout                           PASS
```

No DDL migration, data migration or rollback was required.

---

## 14. Rollback

No rollback was required during deployment.

For contingency use, if a future V2.1 regression occurs, V2.0-compatible source subsets remain available.

Temporary indicator-only fallback:

```python
build_level_ladder(
    ticker,
    enabled_sources=("MA", "BB", "RSI"),
)
```

Full code rollback target:

```text
Merge commit: 1d1b82b7023c3ae1142c6c449fc538278ffbe0a3
```

No database rollback is required because V2.1 introduces no schema migration.

---

## 15. Risks

### Look-ahead in Swing

Mitigation:

```text
confirmed_at <= as_of_date
```

enforced before normalization.

### Partial period contamination

Mitigation:

- Previous Week excludes current week.
- Previous Month excludes current month.

### ATR as false price level

Mitigation:

```text
ATR → MarketContext
Role = CONTEXT
```

### High-volatility threshold

Adaptive resolved threshold may exceed the user-entered percent floor.

Core cluster/classification accepts resolved volatility-driven thresholds rather than failing at the old fixed upper bound.

### Structural over-weighting

All structural sources belong to one:

```text
MARKET_STRUCTURE
```

family, so multiple structural observations do not become independent families.

---

## 16. Production Notes

Canonical runtime source keys:

```text
MA
BB
SWING
PREVIOUS_HL
52W_HL
ATR
RSI
```

Do not use aliases such as `PREVIOUS_PERIOD` or `FIFTY_TWO_WEEK`; runtime intentionally rejects unsupported keys and returns the supported-source list.

Database impact:

```text
DDL migration:       NOT REQUIRED
Data migration:      NOT REQUIRED
Preflight SQL:       READ ONLY
Rollback DB action:  NOT REQUIRED
```

---

## 17. References

Architecture:

```text
docs/architecture/RS_Ladder.md
```

ADR:

```text
docs/adr/ADR-005-rs-v2-1-adaptive-structural.md
```

DuckDB preflight:

```text
src/DuckDB/sql/rs_v2_1_preflight.sql
```

Tests:

```text
tests/test_rs_ladder.py
tests/test_R_S_V2_1.md
```

GitHub:

```text
PR #5
Merge commit: 1d1b82b7023c3ae1142c6c449fc538278ffbe0a3
```
