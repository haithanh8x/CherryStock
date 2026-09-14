---
name: regression-testing
description: "Run focused CherryStock regression, acceptance, bug-fix, integration, or execution verification with minimum sufficient evidence, bounded retries, and an explicit PASS/FAIL/BLOCKED/REGRESSION verdict."
---

# CherryStock Regression Testing Skill

## Owner and purpose

Default owner: `.github/agents/TestEngineer.agent.md`.

This Skill defines the repeatable verification procedure. Test Engineer owns the final evidence-backed verdict.

Mandatory constraints:
- `.github/instructions/testing.instructions.md`;
- matching domain Instructions.

## Procedure

### 1. Define one objective

Write one observable behavior to decide. Record:
- in scope;
- out of scope;
- production files/contracts under test;
- allowed test/repair files;
- acceptance criteria;
- stop condition.

Do not add a second objective during execution.

### 2. Select minimum validation depth

Classify exactly one according to testing Instructions:

```text
BUG FAST VALIDATION
INTEGRATION VALIDATION
FULL RELEASE / MONTHLY VALIDATION
```

Start with the narrowest level that can prove the contract. Escalate only when evidence or the canonical testing policy requires it.

### 3. Inspect the contract

Read the smallest relevant set:
- requirement/acceptance criteria;
- architecture/ADR when applicable;
- implementation handoff/diff;
- production code;
- nearest tests/runbooks;
- matching Instructions.

Identify input, output, side effects, failure behavior and regression boundary.

### 4. Design deterministic cases

Prefer:
- one focused regression case per defect;
- stable fixtures;
- explicit assertions;
- boundary/error case when contract-relevant;
- idempotency/rerun check for data workflows;
- minimal real-data reproduction only when synthetic evidence cannot prove the behavior.

### 5. Execute narrowest command first

Run the smallest command that can decide the objective. Capture:
- command;
- exit/result;
- relevant assertion/output;
- environment blocker if any.

Do not rerun an identical failed command unchanged.

### 6. Evaluate

Choose exactly one:

```text
PASS
FAIL
BLOCKED
REGRESSION
```

If failure is caused by the current implementation, one focused repair/retest may be handed to the implementation owner within the repository retry budget. A second repair is allowed only with materially new evidence. No third repair cycle without explicit authorization.

### 7. Report and stop

Return:

```text
TEST VERDICT
Objective:
Validation depth:
Commands/evidence:
Verdict: PASS | FAIL | BLOCKED | REGRESSION
Action: KEEP | REVERT | FIX_ONCE | STOP
Scope proven:
Unproven / residual risk:
Next owner:
```

A focused PASS proves only the tested scope.

## Handoff routing

- missing/ambiguous acceptance criteria → Business Analyst;
- architecture/contract gap → Solution Architect;
- implementation defect/regression → General Coding or authoritative domain owner;
- dataset quality issue requiring specialized checks → use `data-quality-validation` Skill;
- environment/dependency blocker → Router/User.

## Anti-patterns

- broadening a bug fix into a repository-wide investigation without evidence;
- alternating endlessly between hypotheses;
- repeated static reasoning after runtime evidence is sufficient;
- claiming PASS from code review alone;
- repairing unrelated failures during a focused test task;
- continuing after a terminal verdict.
