---
name: drawio-skill
description: Create and maintain editable draw.io/diagrams.net architecture, workflow, data-flow, UML, ERD and Agent Harness diagrams for CherryStock. Use when the user explicitly requests draw.io/diagrams.net or when an editable diagram is materially useful. This CherryStock adapter uses Agents365-ai/drawio-skill as the upstream implementation and does not replace the mandatory Archify synchronization contract for approved architecture changes.
license: MIT
metadata:
  upstream: https://github.com/Agents365-ai/drawio-skill
  upstream-version: "3.4.0"
  upstream-ref: "7aa92f73819766eb914fffac66762cf2adb5d828"
---

# CherryStock Draw.io Skill

## Purpose

This is the CherryStock project adapter for `Agents365-ai/drawio-skill`.

Use it to create **editable `.drawio` artifacts** for architecture explanation, Agent Harness maps, workflows, sequence/data-flow diagrams, ERDs and review material.

Install the full upstream runtime locally with:

```powershell
.\scripts\install_drawio_skill.ps1
```

Default runtime location:

```text
%USERPROFILE%\.agents\skills\drawio-skill
```

## CherryStock ownership boundary

```text
Agent        = owns the OUTCOME
Skill        = owns the PROCEDURE
Instruction  = owns mandatory RULES / CONSTRAINTS
Docs         = own durable KNOWLEDGE / DESIGN
Tool         = provides EXECUTION CAPABILITY
```

Draw.io belongs to the **Skill → Tool** part of the harness. It does not own architecture decisions.

## Relationship with Archify

- `SolutionArchitect.agent.md` remains the owner of architecture/design readiness.
- Archify remains the preferred and mandatory synchronized architecture visualization path where the current Solution Architect contract requires it.
- Draw.io is supplemental and is especially appropriate when the user explicitly requests `.drawio`, diagrams.net editing, or an editable workshop/review artifact.
- A `.drawio` file is not a replacement for `docs/architecture/**`, ADRs, or canonical Archify typed sources.
- If Draw.io and canonical architecture documentation disagree, the Draw.io artifact is wrong and must be repaired.

## Procedure

1. Read `.github/copilot-instructions.md` and the authoritative agent for the task.
2. Read matching `.github/instructions/*.instructions.md` constraints.
3. Load the smallest relevant durable knowledge set from `docs/00_HOME.md` and `docs/**`.
4. Define diagram purpose, audience, scope and evidence source.
5. For CherryStock architecture, derive nodes and relationships from repository evidence; do not invent topology.
6. Create/edit an uncompressed editable `.drawio` source with stable semantic cell IDs.
7. Keep edge endpoints explicit and every edge geometry relative.
8. Validate with the upstream structural validator:

```powershell
python "$HOME\.agents\skills\drawio-skill\scripts\validate.py" <diagram.drawio> --score
```

9. For CherryStock local native PNG export, **do not call `draw.io.exe` directly from ad-hoc scripts**. Use `scripts/lib/DrawioCli.psm1` or the repository runner:

```powershell
.\scripts\run_drawio_harness_demo.ps1
```

10. When Draw.io Desktop is available, export a draft PNG and visually inspect overlap, clipping, label readability and edge routing.
11. Stop automatic repair after two focused rounds; report any remaining limitation instead of looping.
12. Preserve the editable `.drawio` source as the review artifact; generated PNG/SVG/PDF is presentation output.

## Native export invariant

CherryStock native automation MUST route through:

```text
scripts/lib/DrawioCli.psm1
```

The wrapper owns:

- executable discovery and version reporting;
- synchronous native process execution with a bounded timeout;
- **draw.io 28.x-compatible argv construction using only CLI options registered by Draw.io**;
- update suppression through environment variable `DRAWIO_DISABLE_UPDATE=true`, not the unsupported `--disable-update` argv token;
- stdout/stderr capture for diagnostics;
- output stability checks;
- PNG signature validation.

Do **not** add arbitrary Electron/Chromium flags such as the following to Draw.io 28.x export argv:

```text
--disable-update
--user-data-dir=...
--disable-gpu
```

Draw.io Desktop 28.x uses commander with `allowUnknownOption()`. Unknown flags can leak into `program.args`, become the first candidate input path and cause:

```text
Error: input file/directory not found
```

even when the real `.drawio` path exists.

Do not reimplement native invocation logic in individual Agents, Skills or runbooks.

## File placement

Durable CherryStock architecture diagrams:

```text
docs/architecture/diagrams/*.drawio
```

Locally generated presentation exports:

```text
docs/architecture/generated/*
```

Do not place domain knowledge inside this Skill file. Link to authoritative docs instead.

## Demo

Reference demo:

```text
docs/architecture/diagrams/agent-harness-five-components.drawio
```

Run locally:

```powershell
.\scripts\run_drawio_harness_demo.ps1
```

Focused helper regression test:

```powershell
.\tests\test_drawio_cli_helper.ps1
```

See:

```text
docs/runbook/Drawio_Skill.md
```