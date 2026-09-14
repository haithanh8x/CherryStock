# CherryStock Agent Harness — ADLC

## 1. Purpose

This document is the canonical architecture and ownership map for **AI-assisted software delivery in CherryStock**.

CherryStock uses an **ADLC (AI Development Life Cycle)** model: a controlled multi-agent engineering lifecycle in which AI agents do not behave as one unrestricted developer. Each agent owns a specific engineering outcome, produces durable repository artifacts, passes an explicit readiness gate, and hands the work to the next owner.

The model is intentionally **artifact-driven and gate-driven**, not conversation-driven:

```text
User intent
  → route to the correct owner
  → produce a reviewable artifact
  → satisfy an explicit gate
  → hand off with evidence
  → independently validate
  → return findings to the owner of the failed outcome
```

The default repository agent performs orchestration. `.github/copilot-instructions.md` is the executable repository-level router. Files under `.github/agents/` define **WHO owns an outcome**. Files under `.github/instructions/` define **mandatory execution rules by domain**. Files under `docs/` store the durable engineering knowledge and traceability chain.

ADLC does **not** mean every change must pass through every specialist. A clear, bounded change may take a fast path directly to implementation. Independent validation remains mandatory before the implementation is treated as verified.

---

## 2. ADLC control model

CherryStock's ADLC is built around six controls.

### 2.1 Outcome ownership

Each lifecycle outcome has one authoritative owner:

- Business Analyst owns requirement readiness.
- Solution Architect owns design readiness.
- General Coding or an authoritative domain agent owns implementation readiness.
- Test Engineer owns the evidence-backed validation verdict.
- The default repository agent owns routing and handoff, but does not replace specialist ownership.
- The user owns product priority, scope approval and material business decisions.

An agent may contribute information to another stage, but it may certify only the outcome it owns.

### 2.2 Artifact-based handoff

Agents do not hand work off with only a chat summary. A material change should leave durable evidence in the repository.

Canonical trace:

```text
REQ-* / accepted intent
    ↓
Architecture / ADR / contracts
    ↓
Implementation diff
    ↓
Test evidence / runbook evidence
    ↓
PASS | FAIL | BLOCKED | REGRESSION
```

### 2.3 Explicit gates

The primary gate states are:

```text
Business Analyst
  READY_FOR_DESIGN
  or READY_FOR_IMPLEMENTATION

Solution Architect
  APPROVED_FOR_IMPLEMENTATION

Implementation owner
  IMPLEMENTED_PENDING_VALIDATION

Test Engineer
  PASS | FAIL | BLOCKED | REGRESSION
```

A downstream state must not be claimed by an upstream agent.

### 2.4 Separation of duties

Implementation and validation are deliberately separated. General Coding or a domain implementation agent must not mark its own implementation as `PASS`. Its terminal delivery state is `IMPLEMENTED_PENDING_VALIDATION`.

`PASS | FAIL | BLOCKED | REGRESSION` belongs to Test Engineer after reviewing the requirement, architecture contract when applicable, implementation diff and execution evidence.

### 2.5 Smallest sufficient route

The router should use the smallest lifecycle that still preserves correctness.

Examples:

- Material or unclear capability → BA → SA when architecture is affected → Dev → Test.
- Clear requirement with no architecture change → Dev → Test.
- Clear requirement with architecture impact → SA → Dev → Test.
- Concrete indicator lifecycle → Indicator Management → Test, with SA inserted when the change alters architecture/contracts.
- Chart advisory only → Chart Agent → user.
- Chart production integration → Chart Agent / design context → General Coding → Test.

This prevents ADLC from becoming a bureaucratic waterfall.

### 2.6 Feedback to the owner of the failed outcome

Validation findings are classified before rework:

- requirement ambiguity or missing acceptance criteria → Business Analyst;
- architecture/contract/data-model gap → Solution Architect;
- implementation defect → General Coding or the authoritative domain implementation agent;
- environment/dependency blocker → default repository agent routes to the relevant owner or user;
- regression → implementation owner fixes, then Test Engineer reruns the impacted validation scope.

The router coordinates this loop; it does not fix every type of failure itself.

---

## 3. Roles, responsibilities and repository ownership

| Role | Primary responsibility | Inputs | Durable outputs / evidence | Exit state |
|---|---|---|---|---|
| **User / Product Owner** | Goal, priority, scope and material business decision | Business need, issue, feature request | Approved intent / decision context | Request accepted, changed or rejected |
| **Default repository agent / ADLC Router** | Classify intent, choose owner, preserve context, coordinate handoffs, consolidate response | User request + repository governance | Normally no duplicate domain document | Correct owner selected / next handoff prepared |
| **Business Analyst** | Make behavior complete and testable | User intent, existing requirements, domain context | `docs/backlog/requirements/REQ-*.md` | `READY_FOR_DESIGN` or `READY_FOR_IMPLEMENTATION` |
| **Solution Architect** | Define technical design, boundaries, contracts, data model, failure handling and design decisions | Ready requirement + architecture evidence | `docs/architecture/**`, `docs/adr/**`, Archify typed source + generated artifact when required | `APPROVED_FOR_IMPLEMENTATION` |
| **General Coding** | Implement approved behavior without changing business/architecture semantics implicitly | Ready requirement/design | `src/**`, `scripts/**`, affected docs, optional implementation notes | `IMPLEMENTED_PENDING_VALIDATION` |
| **Authoritative domain agent** | Implement or author specialist outcomes where a domain agent exists | Ready requirement/design + domain instructions | Domain-owned source/docs/artifacts | Domain-specific ready state, normally followed by independent validation |
| **Test Engineer** | Independently verify acceptance criteria, contracts, regression and operational behavior | Requirement + design + implementation diff | `tests/**`, focused evidence, related `docs/runbook/**` where durable | `PASS`, `FAIL`, `BLOCKED` or `REGRESSION` |

Current specialist domain agents include `Indicator_Management.agent.md` and `Chart.agent.md`. They are not extra lifecycle stages by default; they replace or augment the generic owner only when the routed domain requires their specialist contract.

---

## 4. Canonical ADLC workflow

### Phase 0 — Intake and routing

**Owner:** default repository agent  
**Governance:** `.github/copilot-instructions.md`

The router:

1. interprets the user's intended outcome;
2. identifies affected domains;
3. decides whether the request is sufficiently clear;
4. decides whether architecture/design work is required;
5. selects the authoritative implementation owner;
6. loads only the instructions and repository context needed for that route;
7. establishes the next expected gate.

The router is a traffic controller, not a hidden super-agent. It must not duplicate BA requirements, SA design or Test verdicts.

### Phase 1 — Requirement definition

**Owner:** `BusinessAnalyst.agent.md`

Use BA when behavior, scope, business rules, acceptance criteria, edge cases or priorities are materially unclear.

BA should establish at minimum:

- objective and business outcome;
- in-scope / out-of-scope behavior;
- business rules and invariants;
- input/output expectations where known;
- acceptance criteria;
- edge/error cases;
- dependencies and assumptions;
- requirement identifier and traceability.

Durable output:

```text
docs/backlog/requirements/REQ-*.md
```

Possible exits:

- `READY_FOR_DESIGN` — technical design is required;
- `READY_FOR_IMPLEMENTATION` — requirement is clear and existing architecture already covers it.

### Phase 2 — Solution design

**Owner:** `SolutionArchitect.agent.md`

SA begins from repository evidence, not from the prompt alone. It reads the requirement and the smallest relevant architecture/source set, then defines the implementable contract.

A material design should cover as applicable:

- current-state architecture;
- target components and responsibilities;
- dependency direction;
- API/interface/input/output contracts;
- logical and physical data model;
- grain, keys, relationships, lineage and ownership;
- Source of Truth;
- persistence/transaction/idempotency behavior;
- failure handling;
- observability;
- backward compatibility and migration/backfill;
- testing/validation strategy;
- ADR requirement.

Durable output:

```text
docs/architecture/**
docs/adr/ADR-*.md                  # when a durable cross-module decision is required
docs/architecture/diagrams/**      # Archify typed source
docs/architecture/generated/**     # generated presentation artifact
```

Archify is a **Solution Architect tool**, not an architecture authority. The Markdown/ADR and repository evidence remain the engineering Source of Truth.

A design may exit as `APPROVED_FOR_IMPLEMENTATION` only when its required Markdown/ADR, Archify typed source and generated HTML are synchronized and Archify validation succeeds.

### Phase 3 — Implementation

**Owner:** `GeneralCoding.agent.md` or authoritative domain agent

Implementation consumes the approved behavior and design. The implementation owner should:

1. inspect the exact files/contracts in scope;
2. preserve existing public behavior outside the approved change;
3. implement the smallest coherent change;
4. add/update relevant automated tests where implementation ownership permits;
5. update affected canonical docs/runbooks when runtime behavior changed;
6. report changed files and any residual risks;
7. hand off to independent validation.

Typical durable outputs:

```text
src/**
scripts/**
tests/**                            # implementation-side automated tests when in scope
docs/development/implementation-notes/**
affected canonical docs
```

The implementation owner exits with:

```text
IMPLEMENTED_PENDING_VALIDATION
```

It must not self-certify `PASS`.

### Phase 4 — Independent validation

**Owner:** `TestEngineer.agent.md`

Test Engineer validates the delivered system against the upstream contracts rather than trusting the implementation summary.

Validation may include:

- acceptance criteria;
- unit/integration/regression tests;
- database/data-quality assertions;
- idempotency/rerun behavior;
- migration/backfill correctness;
- failure-path behavior;
- CLI/runbook checks;
- compatibility with existing public contracts;
- evidence that the expected files/data/artifacts were actually produced.

Terminal outcomes:

```text
PASS
FAIL
BLOCKED
REGRESSION
```

The verdict must state evidence and scope. A `PASS` for a focused area must not be presented as proof of unrelated system behavior.

### Phase 5 — Close, user decision and feedback

After validation:

- `PASS` → router consolidates the change, evidence and remaining caveats for the user;
- `FAIL` → router classifies the failure and returns it to BA, SA or implementation owner;
- `BLOCKED` → router surfaces the dependency/environment decision needed to continue;
- `REGRESSION` → implementation owner fixes the regression, then Test Engineer reruns validation.

At CherryStock's current single-user scale there is no separate Delivery Lead, PM or Runtime Operator agent in the canonical flow. The default repository agent coordinates the lifecycle and the user retains final product decisions.

---

## 5. Routing patterns

### 5.1 Material / unclear new capability

```text
User
  → Router
  → Business Analyst
  → READY_FOR_DESIGN
  → Solution Architect
  → APPROVED_FOR_IMPLEMENTATION
  → General Coding / Domain Agent
  → IMPLEMENTED_PENDING_VALIDATION
  → Test Engineer
  → PASS | FAIL | BLOCKED | REGRESSION
  → User / feedback loop
```

Use this when the request changes behavior materially, introduces a new data model or contract, crosses modules, changes persistence, or contains important ambiguity.

### 5.2 Clear change, architecture already established

```text
User
  → Router
  → General Coding / Domain Agent
  → IMPLEMENTED_PENDING_VALIDATION
  → Test Engineer
  → verdict
```

Use this for bounded changes where acceptance criteria and existing architecture are already explicit.

### 5.3 Requirement work needed, but no new design needed

```text
User
  → Router
  → Business Analyst
  → READY_FOR_IMPLEMENTATION
  → General Coding / Domain Agent
  → Test Engineer
```

### 5.4 Clear architecture/design request

```text
User
  → Router
  → Solution Architect
  → APPROVED_FOR_IMPLEMENTATION
  → General Coding / Domain Agent
  → Test Engineer
```

If SA discovers material requirement ambiguity, the request is returned to BA before design is approved.

### 5.5 Specialist route — indicator lifecycle

```text
User
  → Router
  → Indicator Management
  → IMPLEMENTED_PENDING_VALIDATION
  → Test Engineer
```

Insert BA or SA only when requirement ambiguity or architecture change justifies it.

### 5.6 Specialist route — chart

Advisory/specification only:

```text
User → Router → Chart Agent → User
```

Production integration:

```text
User → Router → Chart Agent / design context → General Coding → Test Engineer
```

---

## 6. Gate contracts

| Gate | Owner | Minimum condition | Handoff target |
|---|---|---|---|
| `READY_FOR_DESIGN` | BA | Scope, rules, acceptance criteria and important edge cases are testable; design work is explicitly needed | SA |
| `READY_FOR_IMPLEMENTATION` | BA | Requirement is complete and existing architecture already defines the implementation contract | General Coding / domain agent |
| `APPROVED_FOR_IMPLEMENTATION` | SA | Design is implementable; contracts/ownership/data model are explicit; required ADR and Archify artifacts are synchronized and validated | General Coding / domain agent |
| `IMPLEMENTED_PENDING_VALIDATION` | Dev/domain agent | Code/artifacts changed as required, implementation checks completed, changed scope documented | Test Engineer |
| `PASS` | Test Engineer | Required acceptance/contract/regression evidence passes | Router → User |
| `FAIL` | Test Engineer | Expected behavior/contract is violated | Router → failed outcome owner |
| `BLOCKED` | Test Engineer | Validation cannot complete due to an external/dependency/environment blocker | Router → relevant owner/User |
| `REGRESSION` | Test Engineer | Previously supported behavior is broken by the change | Router → implementation owner, then retest |

---

## 7. Standard handoff payload

Every non-trivial handoff should make the next owner able to work without reconstructing the whole conversation.

Minimum payload:

```text
Requirement / objective
Source-of-Truth paths inspected
REQ-* identifier, when one exists
In-scope / out-of-scope
Upstream gate and owner
Acceptance criteria
Approved contracts / invariants
Affected modules/files
Known assumptions
Known risks/blockers
Expected next output
Expected next gate
```

Example:

```text
From: Solution Architect
State: APPROVED_FOR_IMPLEMENTATION
Requirement: REQ-00xx
Design: docs/architecture/<feature>.md
ADR: docs/adr/ADR-00xx-<decision>.md (if required)
Archify source: docs/architecture/diagrams/<feature>.<type>.json
Generated diagram: docs/architecture/generated/<feature>.html
Implementation scope: src/... + scripts/...
Must preserve: <public contract / business invariant>
Validation focus: <acceptance criteria + regression scope>
Next owner: General Coding
Expected exit: IMPLEMENTED_PENDING_VALIDATION
```

---

## 8. Folder-to-ADLC mapping

```text
CherryStock/
├── .github/
│   ├── copilot-instructions.md          # ADLC router / repository governance
│   ├── agents/
│   │   ├── BusinessAnalyst.agent.md     # requirement outcome owner
│   │   ├── SolutionArchitect.agent.md   # architecture/design outcome owner
│   │   ├── GeneralCoding.agent.md       # general implementation owner
│   │   ├── TestEngineer.agent.md        # independent validation owner
│   │   ├── Indicator_Management.agent.md
│   │   └── Chart.agent.md
│   ├── instructions/
│   │   ├── database.instructions.md     # domain execution constraints
│   │   ├── indicators.instructions.md
│   │   ├── testing.instructions.md
│   │   ├── crawler.instructions.md
│   │   ├── chart.instructions.md
│   │   └── archify.instructions.md
│   └── skills/                          # reusable specialist skills
│
├── docs/
│   ├── 00_HOME.md                       # durable knowledge map
│   ├── backlog/
│   │   ├── requirements/
│   │   │   └── REQ-*.md                 # BA requirement artifacts
│   │   ├── Architecture_Backlog.md
│   │   └── Harness_Backlog.md
│   ├── architecture/
│   │   ├── agent-harness/
│   │   │   └── README.md                # this canonical ADLC/harness document
│   │   ├── diagrams/
│   │   │   └── cherrystock-adlc-agent-harness.workflow.json
│   │   ├── generated/
│   │   │   └── CherryStock_ADLC_Agent_Harness.html
│   │   └── <domain architecture>.md
│   ├── adr/
│   │   └── ADR-*.md                     # material architecture decisions
│   ├── development/
│   │   └── implementation-notes/        # optional durable implementation notes
│   ├── runbook/                          # operational/test execution knowledge
│   ├── reference/                        # generated/reference evidence, e.g. DB metadata
│   └── ChangeRequest/                    # release/change history when applicable
│
├── src/                                  # product implementation
├── scripts/                              # operational/dev/migration utilities
└── tests/                                # independent and regression test assets
```

Folder rules:

- `.github/**` = executable governance and agent behavior.
- `docs/**` = durable engineering knowledge.
- `src/**` / `scripts/**` = implementation.
- `tests/**` = verification assets/evidence.
- Do not copy the same rule into several folders when one authoritative document can be linked.
- Backlog describes planned behavior; implemented behavior must be reflected in the relevant canonical architecture/domain/runbook material.
- Architecture documents should link to `REQ-*` when a requirement artifact exists.
- Test evidence should be traceable to the requirement/design and implementation scope.

---

## 9. Archify representation of the ADLC

The durable Archify source for this workflow is:

```text
docs/architecture/diagrams/cherrystock-adlc-agent-harness.workflow.json
```

Expected generated presentation artifact:

```text
docs/architecture/generated/CherryStock_ADLC_Agent_Harness.html
```

The workflow uses lanes for:

1. User / Product;
2. default repository agent / router;
3. Business Analyst;
4. Solution Architect;
5. General Coding / domain implementation owner;
6. Test Engineer;
7. repository artifacts/evidence.

It contains four guided views:

- **Material change** — canonical BA → SA → Dev → Test path;
- **Clear small change** — fast path that may bypass BA/SA;
- **Failure routing** — feedback to the owner of the failed outcome;
- **Repository evidence** — requirement → architecture → implementation → test trace.

Archify is used because a workflow diagram communicates lanes, gates, alternate routes and feedback loops more clearly than a static component diagram.

### Render locally

Use the dedicated repository wrapper:

```powershell
.\scripts\render_archify_agent_harness.ps1
```

Equivalent Archify core commands:

```powershell
$archify = "$env:USERPROFILE\.agents\skills\archify\bin\archify.mjs"

node $archify validate workflow `
  docs/architecture/diagrams/cherrystock-adlc-agent-harness.workflow.json `
  --quality showcase --json

node $archify deliver workflow `
  docs/architecture/diagrams/cherrystock-adlc-agent-harness.workflow.json `
  docs/architecture/generated/CherryStock_ADLC_Agent_Harness.html `
  --quality showcase --json
```

The generated HTML is presentation output only. Do not manually edit it as the Source of Truth.

---

## 10. Example — adding a new SmartMoney capability

A representative material change illustrates how the lifecycle behaves.

### Step 1 — User request

The user requests a new SmartMoney factor with persistence and daily calculation.

### Step 2 — Router

The router identifies:

- new behavior;
- data-model/persistence impact;
- analytics domain impact;
- need for acceptance criteria and design.

It routes first to BA.

### Step 3 — BA

BA creates/updates a `REQ-*` covering:

- business meaning of the factor;
- calculation inputs/outputs;
- historical/backfill expectation;
- missing-data behavior;
- acceptance criteria;
- out-of-scope behavior.

Exit: `READY_FOR_DESIGN`.

### Step 4 — SA

SA inspects the requirement, SmartMoney architecture, database metadata and existing calculation patterns. It defines:

- calculation ownership;
- input/output contract;
- target persistence grain/key;
- lineage and public exposure;
- rerun/idempotency behavior;
- failure/data-quality behavior;
- migration/backfill;
- validation strategy.

It updates the canonical architecture and required Archify artifacts.

Exit: `APPROVED_FOR_IMPLEMENTATION`.

### Step 5 — Implementation owner

General Coding or the relevant domain implementation owner changes the calculation/persistence pipeline and supporting tests without silently redefining the approved business rule.

Exit: `IMPLEMENTED_PENDING_VALIDATION`.

### Step 6 — Test Engineer

Test Engineer independently checks:

- formula/acceptance examples;
- historical and daily behavior;
- duplicate/NULL/data-quality conditions;
- rerun/idempotency;
- regression of existing SmartMoney output.

Possible result:

- `PASS` → close to user;
- calculation mismatch → `FAIL` back to implementation owner;
- missing business rule → route to BA;
- data-model contract flaw → route to SA;
- environment/data source unavailable → `BLOCKED`.

This feedback behavior is why CherryStock's ADLC is a controlled loop rather than a one-way code-generation pipeline.

---

## 11. Definition of Done for an ADLC change

A material CherryStock change is complete only when the applicable items are true:

- user intent is traceable to an explicit requirement or unambiguous accepted scope;
- architecture/design exists when the change affects contracts, boundaries, persistence, data model or cross-module behavior;
- required Archify source and generated artifact are synchronized for architecture changes;
- implementation matches the approved contract;
- implementation owner has handed off as `IMPLEMENTED_PENDING_VALIDATION`;
- Test Engineer has issued an evidence-backed terminal verdict;
- regressions or blockers are explicit;
- durable docs/runbooks reflect implemented behavior where relevant;
- the router's final response distinguishes what was designed, implemented and independently verified.

---

## 12. Governance summary

```text
User decides WHAT matters
        ↓
Router decides WHO owns the next outcome
        ↓
BA defines WHAT the system must do
        ↓
SA defines HOW the system should be structured
        ↓
Dev / Domain Agent changes the system
        ↓
Test Engineer proves whether the delivered behavior satisfies the contract
        ↓
Router closes the loop or sends the finding back to the correct owner
```

This separation is the core of CherryStock ADLC: AI accelerates each engineering function, while explicit ownership, repository artifacts, gates and independent evidence keep the delivery process controlled and auditable.
