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

## 9. Next Expected Major Change

R/S V2.1 đã hoàn tất production deployment và validation PASS.

Major release tiếp theo theo roadmap là:

```text
R/S V2.2
```

Scope target:

```text
Volume Profile Engine
POC
HVN
LVN
Volume Profile window configuration
Volume confirmation
Volume-family cap
Performance optimization
```

V2.1 đã đáp ứng prerequisite cho V2.2: production deployed, local cross-check PASS và Change Request V2.1 đã được chốt.
