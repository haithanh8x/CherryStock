# Draw.io Skill — Local Setup and Validation Runbook

## Purpose

This runbook installs and runs the upstream `Agents365-ai/drawio-skill` for CherryStock local development.

CherryStock uses a lightweight project adapter at:

```text
.github/skills/drawio-skill/SKILL.md
```

The full upstream runtime is installed outside the repository by default at:

```text
%USERPROFILE%\.agents\skills\drawio-skill
```

This avoids vendoring the entire third-party repository while keeping local execution reproducible.

Pinned upstream release for this integration:

```text
Version: 3.4.0
Ref: 7aa92f73819766eb914fffac66762cf2adb5d828
Repository: https://github.com/Agents365-ai/drawio-skill
License: MIT
```

---

## 1. Prerequisites

Required:

```text
Git
Python 3
PowerShell
```

Recommended for native image/PDF export:

```text
Draw.io Desktop 30+
```

Core upstream IR/XML/query/test/review workflows use Python 3 only. Draw.io Desktop is needed for native PNG/SVG/PDF export.

---

## 2. Install the upstream skill runtime

From CherryStock repository root:

```powershell
.\scripts\install_drawio_skill.ps1
```

The installer:

1. clones the upstream repository to a temporary folder;
2. checks out the pinned upstream commit;
3. copies only `skills/drawio-skill` into `%USERPROFILE%\.agents\skills\drawio-skill`;
4. stores the pinned ref in `.cherrystock-upstream-ref`;
5. runs `diagramctl.py doctor` when available;
6. detects Draw.io Desktop CLI when installed.

Expected core files after installation:

```text
%USERPROFILE%\.agents\skills\drawio-skill\SKILL.md
%USERPROFILE%\.agents\skills\drawio-skill\scripts\diagramctl.py
%USERPROFILE%\.agents\skills\drawio-skill\scripts\validate.py
%USERPROFILE%\.agents\skills\drawio-skill\references\...
```

---

## 3. Verify installation manually

```powershell
Test-Path "$HOME\.agents\skills\drawio-skill\SKILL.md"
Test-Path "$HOME\.agents\skills\drawio-skill\scripts\validate.py"
python "$HOME\.agents\skills\drawio-skill\scripts\diagramctl.py" doctor
```

Expected:

```text
True
True
```

and `diagramctl doctor` should complete without a fatal Python/runtime error.

---

## 4. Run the CherryStock demo

The committed editable source is:

```text
docs\architecture\diagrams\agent-harness-five-components.drawio
```

Run:

```powershell
.\scripts\run_drawio_harness_demo.ps1
```

The script first executes the upstream structural validator:

```text
validate.py <diagram> --score
```

If Draw.io Desktop CLI is found, it also exports:

```text
docs\architecture\generated\Agent_Harness_Five_Components.png
```

If Draw.io Desktop is not installed, structural validation still completes and export is skipped with a warning.

To validate without native export:

```powershell
.\scripts\run_drawio_harness_demo.ps1 -SkipExport
```

---

## 5. Open/edit the diagram

Open this file in Draw.io Desktop or diagrams.net:

```text
docs\architecture\diagrams\agent-harness-five-components.drawio
```

The demo models five Harness components:

```text
Agent        → owns OUTCOME
Skill        → owns PROCEDURE
Instruction  → owns RULES / CONSTRAINTS
Docs         → own KNOWLEDGE / DESIGN
Tool         → provides EXECUTION CAPABILITY
```

Relationship details are documented in:

```text
docs\architecture\agent-harness\AGENT_SKILL_INSTRUCTION_DOC_TOOL.md
```

---

## 6. Expected workflow for future diagrams

```text
Repository evidence / approved design
    ↓
Authoritative Agent
    ↓
Drawio Skill
    ↓
Create/update editable .drawio
    ↓
validate.py --score
    ↓
Draw.io CLI export when available
    ↓
Visual review
    ↓
Commit editable source + required durable docs
```

For an approved architecture change, the existing `SolutionArchitect.agent.md` Archify synchronization rules still apply. Draw.io is supplemental unless repository governance is deliberately changed later.

---

## 7. Updating the upstream skill

Do not silently track upstream `main` for architecture work.

When upgrading:

1. inspect the new upstream release/changelog;
2. update the pinned commit in `.github/skills/drawio-skill/SKILL.md`;
3. update the default `$UpstreamRef` in `scripts/install_drawio_skill.ps1`;
4. reinstall locally;
5. run `diagramctl.py doctor`;
6. run this demo again;
7. validate existing important `.drawio` artifacts if the upstream validator/schema behavior changed;
8. record the upgrade in `docs/ChangeRequest/` when material.

---

## 8. Troubleshooting

### `git` not found

Install Git for Windows and confirm:

```powershell
git --version
```

### Python not found

Confirm one of:

```powershell
python --version
py -3 --version
```

### Validator not found

Reinstall:

```powershell
.\scripts\install_drawio_skill.ps1
```

Then confirm:

```powershell
Test-Path "$HOME\.agents\skills\drawio-skill\scripts\validate.py"
```

### Draw.io export skipped

Install Draw.io Desktop and verify one of the common Windows paths:

```text
C:\Program Files\draw.io\draw.io.exe
%LOCALAPPDATA%\Programs\draw.io\draw.io.exe
```

Then rerun:

```powershell
.\scripts\run_drawio_harness_demo.ps1
```

### Diagram opens but looks wrong

Do not repair architecture meaning by eye alone. Check the canonical docs/ADR first, then repair the `.drawio` source and rerun the structural validator. For approved CherryStock architecture, also confirm the mandatory Archify source/output remains synchronized.
