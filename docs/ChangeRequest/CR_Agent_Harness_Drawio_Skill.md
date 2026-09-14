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

CherryStock distinguishes:

```text
Agent        = owns outcome
Skill        = owns procedure
Instruction  = owns mandatory rules
Docs         = own durable knowledge
Tool         = provides execution capability
```

A Draw.io Skill adds an editable-diagram procedure for architecture/workflow/data-flow/UML/ERD artifacts and provides a concrete example of the Skill → Tool relationship in the Harness.

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

The upstream structural validator passed, but Draw.io Desktop native export repeatedly appeared to return success before the expected PNG existed.

Observed pattern:

```text
0 error(s), 0 warning(s)
PASS: structural validation
native invocation appears complete
PNG: missing at check time
Draw.io console output appears later
```

### Root cause refinement

The first hypothesis was Draw.io's Electron single-instance lock. That remains a real compatibility concern, but subsequent local evidence showed it was **not sufficient to explain the failure** because a minimal isolated-profile probe still reproduced the problem.

The decisive observation was that Draw.io console output appeared **after** the PowerShell script had already thrown and returned the prompt. `draw.io.exe` is a Windows GUI/Electron executable, so using PowerShell's call operator:

```powershell
& $drawioExe ...
```

did not provide a reliable synchronous process boundary for export. CherryStock was checking the output before the native GUI process had definitively completed.

### Corrected fix

Native CLI ownership is centralized in:

```text
scripts/lib/DrawioCli.psm1
```

The helper now uses:

```text
Start-Process -PassThru
        ↓
Process.WaitForExit(timeout)
        ↓
short output-stability check
        ↓
PNG signature validation
```

It no longer trusts `$LASTEXITCODE` from a GUI application invocation.

The helper also handles Draw.io/Electron compatibility through deterministic strategies:

```text
1. documented-cli
2. isolated-profile
3. isolated-profile-disable-gpu
```

If no normal Draw.io GUI process is detected, the official documented CLI form is attempted first for maximum version compatibility. If needed, later attempts use a unique `--user-data-dir`; the last attempt adds `--disable-gpu`.

### Additional guards

- Draw.io executable file/product version is reported in native diagnostics.
- Minimal probe uses `shadow="0"` because Draw.io Desktop has a known Windows CLI defect where `mxGraphModel shadow="1"` can return exit code `0` without creating PNG output.
- Final output must pass the PNG eight-byte signature check.
- A dedicated regression test compiles a delayed fake GUI exporter and verifies the helper waits for process completion:

```text
tests/test_drawio_cli_helper.ps1
```

## Validation

### Repository/demo structure

- XML parses successfully.
- all edge source/target IDs resolve;
- all vertices have geometry;
- all edges have relative `mxGeometry`;
- stable semantic IDs are used;
- no reserved `0`/`1` IDs are reused for vertices/edges;
- demo `mxGraphModel` uses `shadow="0"`.

### Local validation contract

Run in this order:

```powershell
git pull
.\tests\test_drawio_cli_helper.ps1
.\scripts\run_drawio_harness_demo.ps1
```

Optional reinstall verification:

```powershell
.\scripts\install_drawio_skill.ps1
```

Expected terminal evidence:

```text
PASS: DrawioCli helper waits for delayed GUI process completion
PASS: structural validation
PASS: native CLI probe (... strategy=...)
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
- Native Draw.io execution is now centralized instead of duplicated across scripts.

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

Reason: this is an additive specialist Skill/tool integration and does not alter the canonical runtime architecture, data model, Source of Truth, Agent ownership, or the existing mandatory Archify design gate. If Draw.io later replaces Archify or becomes a mandatory architecture lifecycle contract, that change should require an ADR.
