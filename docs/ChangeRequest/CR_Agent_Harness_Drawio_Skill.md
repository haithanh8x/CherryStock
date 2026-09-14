# Change Request — Agent Harness Draw.io Skill Integration

## Summary

Integrate `Agents365-ai/drawio-skill` into the CherryStock Agent Harness as a project-level diagram-authoring Skill, while preserving the existing Archify architecture synchronization contract.

## Upstream

```text
Repository: https://github.com/Agents365-ai/drawio-skill
Version: 3.4.0
Pinned ref: 7aa92f73819766eb914fffac66762cf2adb5d828
License: MIT
```

## Reason for Change

CherryStock already distinguishes:

```text
Agent        = owns outcome
Skill        = owns procedure
Instruction  = owns mandatory rules
Docs         = own durable knowledge
Tool         = provides execution capability
```

A Draw.io Skill adds an editable-diagram procedure for architecture/workflow/data-flow/UML/ERD artifacts and provides a concrete example of the Skill → Tool relationship in the Harness.

## Before

- Native CherryStock skill: `chart-authoring`.
- Flint available as MCP tooling for chart authoring.
- Archify used by Solution Architect for architecture visualization/validation.
- No Draw.io-specific project skill or local runbook.
- No editable `.drawio` reference model for the five Harness components.

## After

Added project adapter:

```text
.github/skills/drawio-skill/SKILL.md
```

Added reproducible local upstream installer:

```text
scripts/install_drawio_skill.ps1
```

Added shared Windows/native CLI wrapper:

```text
scripts/lib/DrawioCli.psm1
```

Added demo validator/export runner:

```text
scripts/run_drawio_harness_demo.ps1
```

Added editable reference artifact:

```text
docs/architecture/diagrams/agent-harness-five-components.drawio
```

Added durable relationship documentation:

```text
docs/architecture/agent-harness/AGENT_SKILL_INSTRUCTION_DOC_TOOL.md
```

Added local runbook:

```text
docs/runbook/Drawio_Skill.md
```

## Architecture Boundary

Draw.io does **not** replace the existing architecture Source of Truth or Solution Architect ownership.

```text
SolutionArchitect Agent
    ↓ owns architecture outcome
Drawio Skill
    ↓ owns editable-diagram procedure
Upstream drawio-skill / Draw.io CLI
    ↓ provides validation/render/export capability
.drawio artifact
```

Canonical architecture meaning remains in `docs/architecture/**` and `docs/adr/**`.

The mandatory Archify synchronization rule in `SolutionArchitect.agent.md` remains unchanged. Draw.io is supplemental, especially for explicit Draw.io/diagrams.net requests and editable review/workshop artifacts.

## Five-Component Demo Semantics

The committed `.drawio` model expresses:

```text
Instruction → Agent : governs / constrains
Docs        → Agent : provides context / knowledge
Agent       → Skill : selects / invokes
Instruction → Skill : constrains procedure
Docs        → Skill : supplies authoritative reference
Skill       → Tool  : executes through capability
Tool        → Agent : returns evidence / result
```

## Native Export Defect Found During Local Validation

### Symptom

The upstream structural validator passed, but Draw.io Desktop native export returned process exit code `0` without creating a PNG.

Observed pattern:

```text
0 error(s), 0 warning(s)
PASS: structural validation
Draw.io exit code: 0
PNG: missing
```

### Root cause

Draw.io Desktop is an Electron single-instance application. Its desktop implementation uses `app.requestSingleInstanceLock()` and exits a second process when that lock is already held.

On Windows this means an already-open normal Draw.io GUI can consume/block a CLI launch. The second process may exit successfully without executing the requested export, making `exit code 0` insufficient evidence that a PNG was produced.

### Fix

Native CLI ownership was centralized in:

```text
scripts/lib/DrawioCli.psm1
```

Every automated export now uses a unique temporary Electron/Chromium profile:

```text
--user-data-dir=<unique-temp-profile>
```

This isolates the CLI process from the normal Draw.io GUI single-instance namespace.

The wrapper additionally:

1. detects the Draw.io executable deterministically;
2. invokes explicit `--export --format png --output <file>` syntax;
3. waits/polls until the output file is non-empty and stable;
4. validates the eight-byte PNG signature;
5. removes only its dedicated temporary profile;
6. returns structured export evidence.

The installer now performs a real native export probe when Draw.io Desktop is available. The demo runner now has three gates:

```text
[1/3] upstream structural validation
[2/3] isolated native CLI smoke-test using a minimal generated diagram
[3/3] real Agent Harness PNG export + PNG signature validation
```

This prevents future regressions from being mistaken for successful installation merely because an executable exists or returns exit code `0`.

## Validation

### Repository/demo structure

- XML parses successfully.
- all edge source/target IDs resolve;
- all vertices have geometry;
- all edges have relative `mxGeometry`;
- stable semantic IDs are used;
- no reserved `0`/`1` IDs are reused for vertices/edges.

### Local validation contract

Run:

```powershell
.\scripts\install_drawio_skill.ps1
.\scripts\run_drawio_harness_demo.ps1
```

Expected terminal evidence when Draw.io Desktop is installed:

```text
PASS: native PNG export probe
PASS: structural validation
PASS: native CLI probe
PASS: demo native PNG export
```

The demo output is:

```text
docs/architecture/generated/Agent_Harness_Five_Components.png
```

## Compatibility

Backward compatible.

- Existing agents remain unchanged.
- Existing Archify workflow remains unchanged.
- Existing Chart/Flint skill remains unchanged.
- The new skill is additive and task-scoped.
- Existing open Draw.io Desktop sessions no longer need to be closed for CherryStock CLI export.

## Rollback

Remove the following files if the capability is retired:

```text
.github/skills/drawio-skill/
scripts/install_drawio_skill.ps1
scripts/lib/DrawioCli.psm1
scripts/run_drawio_harness_demo.ps1
docs/runbook/Drawio_Skill.md
docs/architecture/agent-harness/AGENT_SKILL_INSTRUCTION_DOC_TOOL.md
docs/architecture/diagrams/agent-harness-five-components.drawio
```

Local upstream runtime can then be deleted from:

```text
%USERPROFILE%\.agents\skills\drawio-skill
```

## ADR

**Not required for this change.**

Reason: this is an additive specialist Skill/tool integration and does not alter the canonical runtime architecture, data model, Source of Truth, Agent ownership, or the existing mandatory Archify design gate. If Draw.io later replaces Archify or becomes a mandatory architecture lifecycle contract, that change should require an ADR.
