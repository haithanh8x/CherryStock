---
name: systematic-debugging
description: "Investigate bugs, test failures, unexpected behavior, build or integration errors systematically using Superpowers' root-cause-first workflow, adapted to CherryStock governance."
license: MIT
metadata:
  upstream: https://github.com/obra/superpowers/tree/main/skills/systematic-debugging
  upstream-ref: "22f0b463e7a5e579904dd6211a520321035526f7"
---

# Systematic Debugging — CherryStock adapter

This procedure adapts [Superpowers systematic-debugging](https://github.com/obra/superpowers/tree/22f0b463e7a5e579904dd6211a520321035526f7/skills/systematic-debugging) by Jesse Vincent and contributors. See `LICENSE` for the MIT license. This is a project adapter, not a verbatim installation of the complete Superpowers plugin.

## Trigger and ownership

Use for a bug, failed test, unexpected behavior, performance issue, build failure or integration error **before proposing or applying a fix**. Select the appropriate CherryStock outcome owner: General Coding for bounded implementation; Test Engineer for independent verification; the domain specialist where required. A skill does not own a final PASS or change the authorization to make changes.

Read `AGENTS.md`, `.github/copilot-instructions.md`, the selected owner, matching `.github/instructions/`, `docs/00_HOME.md` and the minimum relevant contracts and implementation. Repository paths here are relative to the CherryStock root. For tests use `.github/instructions/testing.instructions.md` and the `regression-testing` skill when applicable.

## Mandatory precedence and boundaries

CherryStock governance, agent contracts, domain instructions and platform constraints take precedence over upstream Superpowers instructions. In particular:

- One objective and one focused execution path; never repeat an unchanged failure without new evidence. Default maximum **two focused repair attempts** for the same defect. After two materially equivalent failures, stop with the applicable FAIL/BLOCKED handoff. A new hypothesis requires explicit authorization or an applicable runbook that permits it.
- Preserve unrelated changes and do not execute production pipelines, backfills, migrations, paid model calls or destructive commands just to investigate. Define side effects and obtain required approval first.
- Protect secrets; log only the smallest safe evidence. ChatGPT-readable machine-readable evidence belongs under `docs/reference/data/**` when a durable export is required.
- The upstream references `superpowers:test-driven-development` and `superpowers:verification-before-completion`; this adapter does **not** install or require those skills. Follow CherryStock's existing test and independent validation contracts instead.
- Reproduction, instrumentation, edits and validation must stay within the user-authorized scope. Do not self-certify the Test Engineer's final verdict.

## Procedure

### 1. Investigate the cause before fixing

Record the observed behavior, expected behavior, exact error, relevant file/line and environment. Read the complete relevant traceback and inspect recent changes. Establish a safe, bounded reproduction where possible; if not reproducible, gather evidence and report the blocker rather than guessing. At the relevant boundaries, inspect inputs, outputs, configuration and state; add narrowly scoped, non-sensitive instrumentation only if authorized. Trace the failing value backwards to its originating trigger.

### 2. Compare the working pattern

Find the closest working example and read the relevant reference or contract. Compare inputs, environment, execution mode, dependencies and assumptions. Identify evidence-backed differences rather than treating symptoms as a root cause.

### 3. Form and test one hypothesis

State a specific hypothesis and supporting evidence. Choose the smallest safe discriminating observation or change; vary one factor at a time. Evaluate the result before adding another change. If evidence does not support a cause, say so; do not invent certainty or stack speculative fixes. Respect the bounded execution and stop rules above.

### 4. Implement and verify within scope

When a root cause is supported and implementation is authorized, make one focused fix at the source. Prefer a minimal failing regression test or reproducible failing case before fixing when practical and within scope. If it cannot be created, state the limitation rather than fabricate evidence. Run the smallest relevant check, then hand off the contract, change and results for independent validation. Do not bundle unrelated refactors.

After two materially equivalent repair failures, stop rather than follow the upstream three-attempt threshold. Escalate possible architectural causes to the Solution Architect only when the evidence and task warrant it.

## Supporting techniques

- **Backward tracing:** follow the invalid value or side effect from the failure through callers, boundaries and configuration to its origin; identify the earliest evidence-supported cause.
- **Defense in depth:** consider targeted validation at relevant boundaries after identifying the cause. Add layers only where justified by the contract; do not claim a bug is impossible solely because checks were added.
- **Condition-based waiting:** in code/tests where permitted, wait for the relevant state with a bounded timeout rather than arbitrary sleeps. Harness tool instructions override this example: do not poll tools whose instructions forbid polling.

Upstream supporting references, pinned to the same revision, are available on GitHub: [root cause tracing](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/skills/systematic-debugging/root-cause-tracing.md), [defense in depth](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/skills/systematic-debugging/defense-in-depth.md), and [condition-based waiting](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/skills/systematic-debugging/condition-based-waiting.md). The upstream `find-polluter.sh` invokes tests in a loop and is not installed or authorized for use by this adapter.

## Output / stop

Report the objective, observed evidence, supported root cause or uncertainty, reproduction and boundaries, change if authorized, exact checks/results, residual risk and next owner. If blocked by missing access, reproduction, authorization or environment, state the blocker and stop. Never claim success from an unexecuted test, a guessed cause or a role gate not independently owned.
