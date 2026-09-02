# CherryStock Change Request Tracking

Tài liệu này là **master tracking** cho các thay đổi lớn của CherryStock.

Mục tiêu:

- ghi nhận tập trung các release / architecture change / data model change / production change quan trọng;
- liên kết tới Change Request chi tiết;
- theo dõi trạng thái từ design → implementation → validation → production;
- tạo lịch sử thay đổi có thể audit;
- tránh phải tìm release history rải rác trong commit, PR, backlog hoặc architecture docs.

> Đây là tracking/index. Chi tiết kỹ thuật đầy đủ phải nằm trong từng file Change Request riêng dưới `docs/ChangeRequest/**`.

---

## 1. Status Model

| Status | Ý nghĩa |
|---|---|
| **PLANNED** | Đã xác định thay đổi nhưng chưa bắt đầu implementation |
| **IN PROGRESS** | Đang develop / migrate / validate |
| **CODE MERGED** | Code đã merge nhưng chưa hoàn tất production validation |
| **DEPLOYMENT PENDING** | Chờ database/config/deployment step |
| **VALIDATION PENDING** | Đã deploy một phần nhưng validation chưa hoàn tất |
| **PRODUCTION READY** | Tất cả acceptance criteria đã PASS, sẵn sàng production |
| **PRODUCTION DEPLOYED** | Đã triển khai production và validation PASS |
| **ROLLED BACK** | Đã rollback |
| **CANCELLED** | Không tiếp tục triển khai |

---

## 2. Change Classification

Các change lớn nên được ghi vào master tracking khi thuộc ít nhất một nhóm:

| Change Type | Examples |
|---|---|
| **Architecture** | Layering, provider boundary, SSOT, domain redesign |
| **Data Model** | Table/view/schema/metadata contract changes |
| **Calculation Engine** | Indicator Engine, R/S Engine, scoring/model logic |
| **Integration** | MCP, MotherDuck, API, external platform |
| **UI / Presentation** | Major application workflow or chart behavior change |
| **AI / Agent Harness** | Agent architecture, tools, memory, hooks |
| **Operational** | Deployment, sync, observability, DQ framework |
| **Migration / Refactor** | Canonical package migration, legacy replacement |

Không bắt buộc tạo Change Request riêng cho minor typo, isolated bug fix hoặc refactor không thay đổi contract/runtime behavior.

---

## 3. Master Change Tracking

| Change ID | Release / Change | Type | Scope | Status | Production Date | Validation | Change Request | PR / Commit |
|---|---|---|---|---|---|---|---|---|
| **CR-RS-V2.0-20260901** | **R/S Ladder V2.0** | Architecture / Calculation Engine / Data Model / UI | MA + BB LEVEL providers, RSI CONFIRMATION, SourceRole/SourceFamily, family-based confluence, ValueSemantic/Unit metadata | **PRODUCTION DEPLOYED** | **2026-09-02** | **PASS — 10/10 pytest + DuckDB + MWG smoke + semantic safety + NiceGUI** | [CR_RS_Ladder_V2_0.md](./CR_RS_Ladder_V2_0.md) | PR #4 / `7ebd6bcb9d0d4faff117f4bff0d99c98c223238b` |
| **CR-RS-V2.1-20260902** | **R/S Ladder V2.1** | Architecture / Calculation Engine / UI | ATR-adaptive clustering/neutral, Swing H/L, Previous W/M H/L, 52W H/L, point-in-time confirmed_at, structural quality | **PRODUCTION DEPLOYED** | **2026-09-02** | **PASS — preflight 5/5 + pytest 17/17 + MA regression + ATR adaptive + structural/no-look-ahead + NiceGUI** | [CR_RS_Ladder_V2_1.md](./CR_RS_Ladder_V2_1.md) | PR #5 / `1d1b82b7023c3ae1142c6c449fc538278ffbe0a3` |
| **CR-RS-V2.2-20260902** | **R/S Ladder V2.2** | Architecture / Calculation Engine / UI | Volume Profile Engine, POC/HVN/LVN, VOLUME_STRUCTURE family cap, volume confirmation, point-in-time profile | **PRODUCTION DEPLOYED** | **2026-09-02** | **PASS — preflight + pytest/regression + V2.1 compatibility + Volume Profile/no-look-ahead + NiceGUI; loader fix KEPT** | [CR_RS_Ladder_V2_2.md](./CR_RS_Ladder_V2_2.md) | PR #6 / `f2eeb815dc6254f4dc28a1eeb1b2d99e3bf9486c` + fix `cc8aeed278936b6ab87632d7707d544de410376c` |
| **CR-RS-V2.3-20260902** | **R/S Ladder V2.3** | Architecture / Calculation Engine / Data Model / Operational | Historical evaluation, hit/break/retest, temporal split, cross-ticker/regime metrics, ablation/calibration, complexity penalty, model versioning, Promotion Gate, golden benchmark | **PRODUCTION DEPLOYED** | **2026-09-02** | **PASS — migration + preflight + pytest + golden + historical evaluation/idempotency + ablation + Promotion Gate dry-run + NiceGUI; 2 focused fixes KEPT** | [CR_RS_Ladder_V2_3.md](./CR_RS_Ladder_V2_3.md) | PR #7 / `74da4ec8ed9f733de6849883e9ee6942a71a2508` + fixes `731795e4`, `d24b2a82` |
| **CR-RS-V2.4-20260902** | **R/S Ladder V2.4** | Architecture / Calculation Engine / Data Model / Operational | Source Effectiveness, canonical source identity, source-config/family ablation, role-aware OOS attribution, research-only Indicator adapter, Source Promotion Gate, public effectiveness SSOT | **PRODUCTION DEPLOYED** | **2026-09-02** | **PASS — migration/idempotency + preflight + pytest + V2.3 golden regression + historical baseline/ablation + effectiveness/view/idempotency + confirmation-role + multi-horizon + Source Promotion Gate dry-run + runtime/NiceGUI; 1 fixture fix KEPT; MA50_D=RESEARCH evidence-driven** | [CR_RS_Ladder_V2_4.md](./CR_RS_Ladder_V2_4.md) | PR #8 / `45a7324825afc0e2d32a166a90dcbc17fe5fb1ac` + validation fix `1a722f82` |
| **CR-RS-V2.4-MONTHLY-20260902** | **R/S V2.4 Monthly Full Evaluation** | Operational / Orchestration / Research Governance | Full-universe monthly H5/H10/H20/H40 baseline reuse, runtime-aligned source discovery, source-config/family ablation, resumable deterministic runs, Promotion Gate dry-run | **PRODUCTION DEPLOYED** | **2026-09-02** | **PASS — focused unit/CLI + plan-only + MWG/FPT/HPG H20 MA50_D smoke + persistence + REUSE + golden regression; no production-code fix; MCP DuckDB lock classified environment-only** | [CR_RS_V2_4_Monthly_Full_Evaluation.md](./CR_RS_V2_4_Monthly_Full_Evaluation.md) | PR #9 / `eed1990c7bccc0475eb9ac83c2c187e3bebf2b65` + golden path restore `8dc1cc76`, `e348991c` |

---

## 4. Production Release Summary

### R/S Ladder V2.0

**Change ID**

```text
CR-RS-V2.0-20260901
```

**Production deployment**

```text
2026-09-02
```

**Final status**

```text
PRODUCTION DEPLOYED
PRODUCTION READY
FINAL VERDICT: PASS
ACTION: KEEP and STOP
```

**Key changes**

```text
R/S V1 MA-only
       ↓
R/S V2.0 Multi-source

LEVEL
├── MA
└── Bollinger Bands LOWER / MIDDLE / UPPER

CONFIRMATION
└── RSI

Confluence
raw source_count
       ↓
source_family_count

Indicator metadata
+ ValueSemantic
+ Unit
```

**DuckDB migration**

```text
src/DuckDB/sql/rs_v2_0_indicator_semantics.sql
```

**Production validation**

| Check | Result |
|---|---|
| DuckDB migration | PASS |
| Semantic metadata | PASS |
| DB reference refresh | PASS |
| Focused pytest | PASS — 10/10 |
| MA-only regression | PASS |
| Default V2.0 MWG real-data smoke | PASS |
| Semantic safety | PASS |
| NiceGUI smoke | PASS |
| Production rollout | PASS |

Detailed change record:

[CR_RS_Ladder_V2_0.md](./CR_RS_Ladder_V2_0.md)

---

## 5. Required Fields for Future Change Requests

Khi thêm một major change mới, master tracking phải có tối thiểu:

```text
Change ID
Release / Change Name
Change Type
Scope Summary
Status
Change Request File
PR / Merge Commit
Database Migration Impact
Production Date
Validation Result
Rollback Status
```

Recommended Change ID convention:

```text
CR-<DOMAIN>-<VERSION>-<YYYYMMDD>
```

Examples:

```text
CR-RS-V2.0-20260901
CR-RS-V2.1-202609xx
CR-INDICATOR-V2-202609xx
CR-HARNESS-V1-202609xx
CR-THEME-V1-20260831
```

---

## 6. Update Workflow

Mỗi major change nên đi theo lifecycle:

```text
Design / ADR
     ↓
Change Request created
     ↓
PLANNED
     ↓
IN PROGRESS
     ↓
CODE MERGED
     ↓
DB / Config Migration
     ↓
Validation
     ↓
PRODUCTION READY
     ↓
PRODUCTION DEPLOYED
     ↓
Master Tracking updated
```

### Khi bắt đầu change

1. Tạo file chi tiết trong:

```text
docs/ChangeRequest/
```

2. Add row vào master tracking với status:

```text
PLANNED
```

hoặc:

```text
IN PROGRESS
```

### Khi merge code

Update:

```text
PR
Merge Commit
Status = CODE MERGED
```

### Khi có migration

Ghi rõ:

```text
Migration file
Affected DB objects
Migration status
Validation query/result
```

### Khi production PASS

Update cả:

```text
Detailed Change Request
+
01_Change_Request_Tracking.md
```

với:

```text
Status = PRODUCTION DEPLOYED
Production Date
Validation = PASS
Rollback = NOT REQUIRED
```

---

## 7. Relationship With Other Documentation

```text
docs/backlog/**
    = work chưa hoàn tất / planned work

docs/architecture/**
    = current / target architecture contract

docs/adr/**
    = why architecture decisions were made

docs/ChangeRequest/**
    = what major change was implemented/deployed

01_Change_Request_Tracking.md
    = master release/change index
```

Không dùng Change Request master để thay thế architecture docs hoặc backlog.

---

## 8. Governance Rules

1. Major production change phải có một Change Request record.
2. Master tracking phải được update khi status thay đổi đáng kể.
3. Không đánh dấu **PRODUCTION DEPLOYED** nếu validation chưa PASS.
4. Nếu rollout thất bại, status phải chuyển thành **ROLLED BACK** hoặc **VALIDATION PENDING**, không giữ trạng thái PASS.
5. Database migration phải reference tới SQL/script cụ thể.
6. PR/merge commit phải được ghi để audit.
7. Architecture/data-contract change material phải link tới ADR hoặc architecture docs tương ứng.
8. Validation evidence phải có test/runbook hoặc kết quả cụ thể.
9. Backlog item đã hoàn thành không tự động đồng nghĩa production release; Change Request mới là deployment record.
10. Master tracking là **human-readable release history**, không thay thế Git history.

---

## 9. Current Roadmap Edge

R/S V2.4 đã hoàn tất BA → SA → Dev → Test, DuckDB migration, production validation và merge với Final Verdict = PASS.

V2.4 hiện là major stage mới nhất của roadmap R/S V2.x:

```text
V2.3
Historical evaluation
Ablation / calibration
Model Promotion Gate
Golden regression

        ↓

V2.4
Source Effectiveness
Canonical source identity
Source-config / family ablation
Per-ticker / multi-horizon OOS evidence
Role-aware marginal attribution
Source Promotion Gate
vw_RS_Source_Effectiveness
```

Governance edge sau V2.4:

- không tự động tạo V2.5;
- `APPROVED_FOR_INTEGRATION` chỉ là source-governance approval, không phải production deployment;
- MA50_D hiện là `RESEARCH` với evidence hiện tại và không được tự động thêm weight/runtime behavior;
- indicator/source candidate muốn thay đổi production R/S phải có requirement/change request/release riêng;
- effectiveness result không tự động biến thành ticker-specific production weight;
- V2.4 đã có monthly full-universe operational runner `scripts/run_rs_v2_4_full_evaluation.py`, mặc định dry-run promotion và không thay đổi runtime;
- version tiếp theo chỉ mở khi có requirement/ADR mới.
