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

## Added Artifacts

```text
.github/skills/drawio-skill/SKILL.md
scripts/install_drawio_skill.ps1
scripts/lib/DrawioCli.psm1
scripts/run_drawio_harness_demo.ps1
tests/test_drawio_cli_helper.ps1
docs/architecture/diagrams/agent-harness-five-components.drawio
docs/architecture/agent-harness/AGENT_SKILL_INSTRUCTION_DOC_TOOL.md
docs/runbook/Drawio_Skill.md
```

## Architecture Boundary

Draw.io does **not** replace the architecture Source of Truth or Solution Architect ownership.

```text
SolutionArchitect Agent
    ↓ owns architecture outcome
Drawio Skill
    ↓ owns editable-diagram procedure
Upstream drawio-skill / Draw.io CLI
    ↓ provides validation/render/export capability
.drawio artifact
```

Canonical architecture meaning remains in `docs/architecture/**` and `docs/adr/**`. Existing mandatory Archify synchronization rules remain unchanged.

## Five-Component Demo Semantics

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

### Observed environment

```text
OS: Windows
Draw.io Desktop file version: 28.1.2
Draw.io Desktop product version: 28.1.2.0
```

### Symptom

Structural validation passed, but native export printed:

```text
Error: input file/directory not found
```

for a `.drawio` file that had already been verified to exist.

The process still returned exit code 0 and produced no PNG.

### Exact root cause

The root cause was verified against the tagged upstream implementation:

```text
jgraph/drawio-desktop
Tag: v28.1.2
File: src/main/electron.js
```

Draw.io 28.1.2 uses `commander`, registers a fixed set of draw.io CLI options, enables:

```text
.allowUnknownOption()
```

and later treats:

```text
program.args[0]
```

as the input file path before calling `fs.statSync(paths[0])`.

The earlier CherryStock helper incorrectly mixed Electron/Chromium flags into Draw.io argv:

```text
--disable-update
--user-data-dir=...
--disable-gpu
```

Those are not registered Draw.io CLI options in v28.1.2. With the 28.x commander parser, an unknown token can leak into `program.args` and become `paths[0]`. Draw.io then tries to stat that token instead of the actual `.drawio` file and reports:

```text
Error: input file/directory not found
```

This explains why all three earlier strategies failed identically despite the real input path existing.

### Important correction to previous hypotheses

Two earlier hypotheses were useful diagnostics but were not the final root cause:

1. **single-instance lock** — Draw.io does use `app.requestSingleInstanceLock()`, but in v28.1.2 the `options.export` branch is handled before the normal single-instance application path;
2. **PowerShell GUI timing** — native process lifetime still needs bounded synchronous handling, but timing does not explain the deterministic `input file/directory not found` emitted by v28.1.2.

The final fix is therefore version-compatible argv construction, plus reliable process execution and output integrity checks.

## Corrected Native Export Contract

Native CLI ownership is centralized in:

```text
scripts/lib/DrawioCli.psm1
```

CherryStock now passes only options registered by Draw.io 28.x:

```text
--export
--format png
--output <file.png>
[--transparent]
[--width N]
<input.drawio>
```

Update checks are disabled using the environment variable supported by Draw.io 28.1.2:

```text
DRAWIO_DISABLE_UPDATE=true
```

The following are forbidden in Draw.io 28.x export argv:

```text
--disable-update
--user-data-dir=...
--disable-gpu
```

The helper additionally:

1. resolves the executable deterministically;
2. reports file/product version;
3. executes with `System.Diagnostics.Process` and `UseShellExecute=false`;
4. captures stdout/stderr;
5. waits with a bounded timeout;
6. checks output stability;
7. validates the eight-byte PNG signature;
8. returns structured export evidence.

## Regression Coverage

Focused test:

```text
tests/test_drawio_cli_helper.ps1
```

The fake exporter deliberately:

- sleeps before producing output, proving CherryStock waits for native completion;
- exits with failure if argv contains `--disable-update`, `--user-data-dir` or `--disable-gpu`;
- verifies that an input file is actually present;
- creates a PNG signature only when the command contract is valid.

Expected test evidence:

```text
PASS: DrawioCli waits for delayed process completion
PASS: DrawioCli argv contains only draw.io-registered options
Strategy: registered-cli-options
```

## Demo Validation Contract

Run:

```powershell
git pull
.\tests\test_drawio_cli_helper.ps1
.\scripts\run_drawio_harness_demo.ps1
```

Expected:

```text
PASS: structural validation
PASS: native CLI probe (... strategy=registered-cli-options ...)
PASS: demo native PNG export
```

Final demo output:

```text
docs/architecture/generated/Agent_Harness_Five_Components.png
```

## Repository Validation Already Completed

- demo XML parses successfully;
- all edge source/target IDs resolve;
- all vertices have geometry;
- all edges have relative `mxGeometry`;
- stable semantic IDs are used;
- no reserved `0`/`1` IDs are reused for vertices/edges;
- demo uses `mxGraphModel shadow="0"`;
- upstream structural validator reported `0 error(s), 0 warning(s)` on the user's local machine.

## Compatibility

Backward compatible.

- Existing agents remain unchanged.
- Existing Archify workflow remains unchanged.
- Existing Chart/Flint skill remains unchanged.
- Draw.io support remains additive and task-scoped.
- Native Draw.io execution is centralized and tested against the observed 28.1.2 parser behavior.

## Rollback

Remove:

```text
.github/skills/drawio-skill/
scripts/install_drawio_skill.ps1
scripts/lib/DrawioCli.psm1
scripts/run_drawio_harness_demo.ps1
tests/test_drawio_cli_helper.ps1
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

Reason: this is an additive specialist Skill/tool integration and does not alter canonical runtime architecture, data model, Source of Truth, Agent ownership, or the mandatory Archify design gate.