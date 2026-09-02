# Change Request — R/S Ladder V2.2

- **Change ID:** CR-RS-V2.2-20260902
- **Release:** R/S Ladder V2.2
- **Date:** 2026-09-02
- **Production deployment date:** 2026-09-02
- **Status:** **PRODUCTION DEPLOYED / VALIDATED**
- **Final verdict:** **PASS**
- **Final action:** **KEEP**
- **Repository:** CherryStock
- **Pull Request:** #6 — feat: upgrade R/S Ladder to V2.2 Volume Profile architecture
- **Main merge commit:** `f2eeb815dc6254f4dc28a1eeb1b2d99e3bf9486c`

---

## 1. Change Summary

R/S Ladder V2.2 bổ sung Volume Profile domain:

```text
LEVEL
└── VOLUME_STRUCTURE
    ├── POC
    ├── HVN
    └── LVN

CONFIRMATION
└── VOLUME_CONFIRMATION
```

V2.2 giữ nguyên V2.1 contracts:

```text
S1 = nearest eligible support
R1 = nearest eligible resistance
Strength = confidence, not rank
source_date <= as_of_date
confirmed_at <= as_of_date
```

---

## 2. Architecture

```text
raw_stock_eod
      │
      │ Date / High / Low / Close / Volume
      ▼
Volume Profile Engine
      │
      ├── POC
      ├── HVN
      └── LVN
      │
      ├───────────────┐
      ▼               ▼
LevelCandidate[]   Volume Confirmation
      │               │
      └───────┬───────┘
              ▼
           R/S Core
```

Volume Profile là domain riêng và **không** được đăng ký vào Indicator Engine.

---

## 3. Daily OHLCV Approximation

Production hiện có daily OHLCV, không có tick-level volume-at-price.

V2.2 dùng deterministic approximation:

1. lấy latest eligible bars với `Date <= as_of_date`;
2. tính High–Low price range;
3. chia range thành price bins;
4. phân bổ Volume của mỗi daily bar đều lên các bins bar đó đi qua;
5. aggregate volume theo bin;
6. derive POC/HVN/LVN.

Không mô tả kết quả này là tick-accurate Volume Profile.

---

## 4. VolumeProfileConfig

Defaults:

```text
window_bars   = 120
bins          = 48
min_records   = 30
hvn_quantile  = 0.80
lvn_quantile  = 0.20
max_hvn       = 4
max_lvn       = 4
```

Validation:

```text
8 <= bins <= 256
min_records > 0
0 < lvn_quantile < hvn_quantile < 1
max_hvn/max_lvn >= 0
```

---

## 5. Level Contracts

POC:

```text
source_code    = VP_POC
source_type    = VOLUME_PROFILE
source_role    = LEVEL
source_family  = VOLUME_STRUCTURE
value_semantic = PRICE_LEVEL
```

HVN:

```text
VP_HVN_01
VP_HVN_02
...
```

LVN:

```text
VP_LVN_01
VP_LVN_02
...
```

All POC/HVN/LVN nodes use `VOLUME_STRUCTURE`.

---

## 6. Volume Family Cap

Multiple profile nodes may increase `source_count`, but they represent only one independent family:

```text
POC + HVN + LVN
      ↓
source_family = VOLUME_STRUCTURE
      ↓
source_family_count increases by at most 1
```

This prevents volume nodes from overpowering unrelated evidence.

---

## 7. Volume Confirmation

The provider returns one bundle:

```text
ProviderBundle
├── LevelCandidate[]
└── ConfirmationContext[]
```

Confirmation contract:

```text
source_family   = VOLUME_CONFIRMATION
reference_price = profile node price
value           = normalized node score 0–100
```

Volume confirmation contributes to Strength only for matching price zones and never changes proximity rank.

---

## 8. Strength V2.2

V2.2 retains:

```text
Family Diversity
Timeframe Confluence
Touch Quality
Recency
RSI Confirmation
Structural Quality
```

and adds:

```text
Volume Confirmation
```

Default:

```text
volume_confirmation_weight = 0.10
```

POC has confirmation score 100. HVN is normalized relative to POC with a minimum 50. LVN stays below 50.

---

## 9. Point-in-Time

Profile input is bounded by:

```text
Date <= as_of_date
```

Generated nodes use:

```text
source_date  = profile.window_end
confirmed_at = profile.window_end
```

Therefore future bars cannot enter historical Volume Profile calculations.

---

## 10. Performance Contract

One profile calculation produces both:

```text
LEVEL candidates
+
Volume confirmations
```

The pure engine is isolated in:

```text
src/calcEngine/volumeProfile.py
```

and has no DuckDB/UI dependency.

---

## 11. Backward Compatibility

V2.1 explicit source-set mode remains available:

```python
build_level_ladder(
    "MWG",
    enabled_sources=(
        "MA",
        "BB",
        "SWING",
        "PREVIOUS_HL",
        "52W_HL",
        "ATR",
        "RSI",
    ),
)
```

Volume-only research mode:

```python
build_level_ladder(
    "MWG",
    enabled_sources=("VOLUME_PROFILE",),
)
```

Default V2.2 includes `VOLUME_PROFILE`.

---

## 12. DuckDB Impact

```text
DDL migration:  NOT REQUIRED
Data migration: NOT REQUIRED
```

V2.2 consumes existing:

```text
raw_stock_eod(Date, High, Low, Close, Volume)
```

Read-only production preflight:

```text
src/DuckDB/sql/rs_v2_2_preflight.sql
```

No POC/HVN/LVN persistence object is introduced in V2.2.

---

## 13. Changed Files

Implementation:

```text
src/calcEngine/volumeProfile.py
src/calcEngine/levelLadder.py
src/Chart/levelLadderChart.py
src/webapp/NiceGUI_chart.py
```

DuckDB validation:

```text
src/DuckDB/sql/rs_v2_2_preflight.sql
```

Tests:

```text
tests/test_rs_ladder.py
tests/test_R_S_V2_2.md
```

Documentation:

```text
docs/architecture/RS_Ladder.md
docs/adr/ADR-006-rs-v2-2-volume-profile.md
docs/00_HOME.md
```

---

## 14. Validation Evidence

Run:

```powershell
python -m pytest tests/test_rs_ladder.py -v
```

Then execute:

```text
tests/test_R_S_V2_2.md
```

Production validation completed successfully on 2026-09-02.

Validation result:

```text
FINAL VERDICT: PASS
ACTION: KEEP
```

Validated successfully:

1. DuckDB read-only preflight.
2. focused pytest and full relevant regression suite.
3. V2.1 explicit-source compatibility.
4. VOLUME_PROFILE-only runtime.
5. default V2.2 MWG runtime.
6. historical point-in-time Volume Profile behavior.
7. NiceGUI V2.2 smoke.

All relevant tests remained PASS after the required loader fix described below.

---

## 15. Current Release Status

| Item | Status |
|---|---|
| Architecture contract | PASS |
| ADR | PASS |
| Source code merged to main | PASS |
| PR #6 | MERGED |
| DuckDB DDL migration | NOT REQUIRED |
| DuckDB data migration | NOT REQUIRED |
| Read-only preflight | PASS |
| Automated tests | PASS |
| V2.1 regression smoke | PASS |
| Volume Profile real-data smoke | PASS |
| Historical point-in-time smoke | PASS |
| NiceGUI V2.2 smoke | PASS |
| Required loader bug fix | PASS / KEPT |
| Production deployment | **PASS** |
| Final verdict | **PASS** |

Current state:

```text
CODE MERGED
NO DATABASE MIGRATION REQUIRED
PREFLIGHT PASS
TESTS PASS
V2.1 REGRESSION PASS
VOLUME PROFILE VALIDATION PASS
POINT-IN-TIME VALIDATION PASS
NICEGUI SMOKE PASS
PRODUCTION DEPLOYED
PRODUCTION READY
```

Final action:

```text
KEEP
```

---

## 16. Production Deployment Record

```text
1. git pull origin main                          PASS
2. DuckDB read-only preflight                    PASS
3. pytest / relevant regression suite            PASS
4. V2.1 explicit-source regression               PASS
5. VOLUME_PROFILE-only smoke                     PASS
6. default V2.2 MWG smoke                        PASS
7. historical point-in-time Volume Profile       PASS
8. NiceGUI V2.2 smoke                            PASS
9. production rollout                            PASS
```

No DDL migration or data migration was required.

---

## 17. Rollback

No rollback was required during production validation or deployment.

The following fallback remains documented for contingency use.

Temporary V2.1 fallback:

```python
build_level_ladder(
    ticker,
    enabled_sources=(
        "MA",
        "BB",
        "SWING",
        "PREVIOUS_HL",
        "52W_HL",
        "ATR",
        "RSI",
    ),
)
```

Full code rollback target:

```text
f2eeb815dc6254f4dc28a1eeb1b2d99e3bf9486c
```

---

## 18. Risks

- **Daily OHLCV approximation:** not true tick-level volume-at-price.
- **Parameter sensitivity:** nodes depend on window/bins/quantiles.
- **Volume overweight:** mitigated by one VOLUME_STRUCTURE family.
- **Look-ahead:** mitigated by Date/source_date/confirmed_at point-in-time rules.
- **Runtime cost:** mitigated by one profile calculation for both LEVEL and CONFIRMATION roles.

---

## 19. Production Bug Fix

During V2.2 validation, `_load_structural_history()` exposed a shared-history contract used by both structural providers and the Volume Profile provider.

Root cause before fix:

```text
empty/result schema expected:
Date, High, Low, Close, Volume

but SQL SELECT returned only:
Date, High, Low, Close
```

This caused V2.2 Volume Profile to receive history without the required `Volume` column.

Fix:

```text
SELECT Date, High, Low, Close, Volume
FROM raw_stock_eod
```

Impact assessment:

- required for V2.2 Volume Profile operation;
- no logic change to Swing;
- no logic change to Previous Week/Month H/L;
- no logic change to 52W H/L;
- existing structural providers simply ignore the extra column;
- full relevant test suite remained PASS.

Fix commits:

```text
f2ef37f59cdfbde0aa5dbaa8e5d23996d7dc8433  auto-sync containing functional fix
cc8aeed278936b6ab87632d7707d544de410376c  explicit root-cause contract documentation
```

Final decision:

```text
KEEP
```

---

## 20. References

```text
docs/architecture/RS_Ladder.md
docs/adr/ADR-006-rs-v2-2-volume-profile.md
src/DuckDB/sql/rs_v2_2_preflight.sql
tests/test_rs_ladder.py
tests/test_R_S_V2_2.md

PR #6
Merge commit: f2eeb815dc6254f4dc28a1eeb1b2d99e3bf9486c
```
