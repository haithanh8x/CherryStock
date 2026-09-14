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

Pinned upstream release:

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

Recommended for native PNG/SVG/PDF export:

```text
Draw.io Desktop 30+
```

Core upstream IR/XML/query/test/review workflows use Python 3 only. Draw.io Desktop is needed only for native export.

---

## 2. Install and verify

From CherryStock repository root:

```powershell
.\scripts\install_drawio_skill.ps1
```

The installer:

1. clones the pinned upstream repository to a temporary folder;
2. copies only `skills/drawio-skill` into `%USERPROFILE%\.agents\skills\drawio-skill`;
3. stores the pinned ref in `.cherrystock-upstream-ref`;
4. runs `diagramctl.py doctor`;
5. detects Draw.io Desktop;
6. when Draw.io Desktop exists, runs a real isolated native PNG export probe and validates the PNG signature.

Expected core files:

```text
%USERPROFILE%\.agents\skills\drawio-skill\SKILL.md
%USERPROFILE%\.agents\skills\drawio-skill\scripts\diagramctl.py
%USERPROFILE%\.agents\skills\drawio-skill\scripts\validate.py
```

Expected native capability result when Draw.io Desktop is installed:

```text
Running isolated native PNG export probe...
PASS: native PNG export probe (... bytes)
```

To install the Python skill runtime without probing Draw.io Desktop:

```powershell
.\scripts\install_drawio_skill.ps1 -SkipNativeExportProbe
```

---

## 3. Why CherryStock isolates Draw.io CLI execution

Draw.io Desktop is an Electron single-instance application. Its desktop source calls:

```text
app.requestSingleInstanceLock()
```

and quits a second process when the lock cannot be obtained.

Therefore this failure mode is possible on Windows:

```text
Draw.io GUI already open
        ↓
CLI process starts
        ↓
single-instance lock fails
        ↓
CLI exits with code 0
        ↓
no PNG is produced
```

This explains the misleading historical symptom:

```text
Draw.io returned exit code 0 but did not create PNG
```

CherryStock no longer invokes native export directly from each script. Shared logic is owned by:

```text
scripts\lib\DrawioCli.psm1
```

Every native export receives a unique temporary Chromium/Electron profile:

```text
--user-data-dir=<unique-temp-profile>
```

so it has an independent single-instance namespace and does not interfere with a Draw.io GUI that is already open.

The helper additionally:

- waits for the exported file to become stable;
- validates that the output starts with the PNG signature;
- removes only its own temporary profile;
- returns a structured result with path, byte size and exit code.

Do not close a user's open Draw.io GUI merely to make automated export work.

---

## 4. Run the CherryStock Agent Harness demo

Editable source:

```text
docs\architecture\diagrams\agent-harness-five-components.drawio
```

Run:

```powershell
.\scripts\run_drawio_harness_demo.ps1
```

The runner now uses three explicit gates:

```text
[1/3] Structural validation
      upstream validate.py --score

[2/3] Native CLI isolated export probe
      generated minimal .drawio → PNG
      verify PNG signature

[3/3] Demo native PNG export
      real Harness .drawio → PNG
      wait for stable file
      verify PNG signature
```

Expected successful output includes:

```text
PASS: structural validation
PASS: native CLI probe (... bytes)
PASS: demo native PNG export
```

Final PNG:

```text
docs\architecture\generated\Agent_Harness_Five_Components.png
```

To run only structural validation:

```powershell
.\scripts\run_drawio_harness_demo.ps1 -SkipExport
```

---

## 5. Manual verification

Core skill:

```powershell
Test-Path "$HOME\.agents\skills\drawio-skill\SKILL.md"
Test-Path "$HOME\.agents\skills\drawio-skill\scripts\validate.py"
python "$HOME\.agents\skills\drawio-skill\scripts\diagramctl.py" doctor
```

Expected first two results:

```text
True
True
```

Editable diagram can be opened directly in Draw.io Desktop or diagrams.net:

```text
docs\architecture\diagrams\agent-harness-five-components.drawio
```

The model represents:

```text
Agent        → owns OUTCOME
Skill        → owns PROCEDURE
Instruction  → owns RULES / CONSTRAINTS
Docs         → own KNOWLEDGE / DESIGN
Tool         → provides EXECUTION CAPABILITY
```

Detailed relationship contract:

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
Invoke-DrawioPngExport
    ↓
isolated native export + output integrity check
    ↓
Visual review
    ↓
Commit editable source + required durable docs
```

For approved architecture changes, the existing `SolutionArchitect.agent.md` Archify synchronization rules still apply. Draw.io remains supplemental unless repository governance is deliberately changed.

---

## 7. Updating the upstream skill

Do not silently track upstream `main`.

When upgrading:

1. inspect the upstream release/changelog;
2. update the pinned ref in `.github/skills/drawio-skill/SKILL.md`;
3. update `$UpstreamRef` in `scripts/install_drawio_skill.ps1`;
4. reinstall locally;
5. run `diagramctl.py doctor`;
6. require the isolated native PNG probe to PASS when Draw.io Desktop is installed;
7. run the Harness demo again;
8. validate important existing `.drawio` artifacts if validator/schema behavior changed;
9. record material upgrades under `docs/ChangeRequest/`.

---

## 8. Troubleshooting

### `git` not found

```powershell
git --version
```

### Python not found

```powershell
python --version
py -3 --version
```

### Validator not found

```powershell
.\scripts\install_drawio_skill.ps1
Test-Path "$HOME\.agents\skills\drawio-skill\scripts\validate.py"
```

### `Draw.io Desktop CLI detected: C`

This was an old CherryStock PowerShell bug caused by indexing a scalar string as `[0]`. Pull the latest repository; detection now returns the complete executable path.

### Exit code 0 but no PNG

This was traced to Draw.io Desktop's Electron single-instance lock when a normal GUI instance was already open. The current CherryStock helper resolves it with a unique `--user-data-dir` for every automated export.

Update local code and rerun:

```powershell
git pull
.\scripts\install_drawio_skill.ps1
.\scripts\run_drawio_harness_demo.ps1
```

You do **not** need to close Draw.io Desktop before running CherryStock automation.

### Draw.io Desktop not detected

Common paths:

```text
C:\Program Files\draw.io\draw.io.exe
%LOCALAPPDATA%\Programs\draw.io\draw.io.exe
```

Check:

```powershell
Test-Path "C:\Program Files\draw.io\draw.io.exe"
Test-Path "$env:LOCALAPPDATA\Programs\draw.io\draw.io.exe"
```

### Diagram opens but looks wrong

Do not repair architecture meaning by eye alone. Check canonical docs/ADR first, repair the `.drawio` source, rerun structural validation and native export, and for approved CherryStock architecture confirm mandatory Archify artifacts remain synchronized.
