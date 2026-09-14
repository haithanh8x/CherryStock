# Draw.io Skill — Local Setup and Validation Runbook

## Purpose

This runbook installs and runs the upstream `Agents365-ai/drawio-skill` for CherryStock local development.

CherryStock project adapter:

```text
.github/skills/drawio-skill/SKILL.md
```

Full upstream runtime is installed outside the repository by default:

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
5. detects Draw.io Desktop and reports file/product version;
6. when Draw.io Desktop exists, runs a real native PNG export probe through the shared CherryStock CLI helper;
7. validates the PNG signature rather than trusting exit code alone.

Expected core files:

```text
%USERPROFILE%\.agents\skills\drawio-skill\SKILL.md
%USERPROFILE%\.agents\skills\drawio-skill\scripts\diagramctl.py
%USERPROFILE%\.agents\skills\drawio-skill\scripts\validate.py
```

To install only the Python skill runtime without probing Draw.io Desktop:

```powershell
.\scripts\install_drawio_skill.ps1 -SkipNativeExportProbe
```

---

## 3. Windows native export behavior and CherryStock fix

Two independent Windows/Electron behaviors matter.

### 3.1 GUI executable lifecycle

`draw.io.exe` is a Windows GUI/Electron executable. Calling it with the PowerShell call operator:

```powershell
& $drawioExe ...
```

can return PowerShell control before the GUI process has actually finished exporting. This creates a race:

```text
PowerShell continues
    ↓
script reads stale/zero exit state
    ↓
script checks output too early
    ↓
Draw.io finishes later
```

CherryStock therefore does **not** use the call operator for native export. The shared helper:

```text
scripts\lib\DrawioCli.psm1
```

uses:

```text
Start-Process -PassThru
        ↓
Process.WaitForExit(timeout)
        ↓
short filesystem stability check
        ↓
PNG signature validation
```

This is the primary fix for the observed `exit 0 / no PNG yet` race.

### 3.2 Draw.io single-instance behavior

Draw.io Desktop also uses Electron single-instance locking. If required, CherryStock retries with an isolated temporary profile:

```text
--user-data-dir=<unique-temp-profile>
```

The helper uses deterministic strategies in order:

```text
1. documented-cli
   --export --format png --output <file> <input>

2. isolated-profile
   same export + unique --user-data-dir

3. isolated-profile-disable-gpu
   isolated profile + --disable-gpu
```

If Draw.io GUI is not running, the documented CLI path is tried first for maximum version compatibility. If a GUI process is already running, the helper skips directly to isolated strategies.

The helper reports the strategy that actually succeeded.

### 3.3 Known Draw.io CLI issue guarded by the probe

Draw.io Desktop has had a Windows CLI defect where `mxGraphModel shadow="1"` can return exit code 0 without producing PNG output. CherryStock probe diagrams deliberately use:

```text
shadow="0"
```

The committed Harness demo also uses `shadow="0"`.

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

The runner uses three gates:

```text
[1/3] Structural validation
      upstream validate.py --score

[2/3] Native CLI export probe
      minimal .drawio → PNG
      wait for native process completion
      verify stable output + PNG signature

[3/3] Demo native PNG export
      real Harness .drawio → PNG
      same deterministic helper
      verify final PNG signature
```

A successful run reports:

```text
PASS: structural validation
PASS: native CLI probe (... strategy=...)
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

## 5. Regression test for the GUI-process race

CherryStock includes a focused regression test:

```text
tests\test_drawio_cli_helper.ps1
```

Run:

```powershell
.\tests\test_drawio_cli_helper.ps1
```

The test compiles a temporary fake GUI exporter that deliberately waits before creating PNG output. It then verifies that `Invoke-DrawioPngExport` does not return early.

Expected:

```text
PASS: DrawioCli helper waits for delayed GUI process completion
```

This test protects against reintroducing the original async-process race when the helper is refactored.

---

## 6. Manual verification

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

Editable diagram:

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

## 7. Expected workflow for future diagrams

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
wait for native process completion
    ↓
output stability + PNG signature check
    ↓
Visual review
    ↓
Commit editable source + required durable docs
```

For approved architecture changes, the existing `SolutionArchitect.agent.md` Archify synchronization rules still apply. Draw.io remains supplemental unless repository governance is deliberately changed.

---

## 8. Updating the upstream skill

Do not silently track upstream `main`.

When upgrading:

1. inspect the upstream release/changelog;
2. update the pinned ref in `.github/skills/drawio-skill/SKILL.md`;
3. update `$UpstreamRef` in `scripts/install_drawio_skill.ps1`;
4. reinstall locally;
5. run `diagramctl.py doctor`;
6. run `tests\test_drawio_cli_helper.ps1`;
7. require the native PNG probe to PASS when Draw.io Desktop is installed;
8. run the Harness demo;
9. validate important existing `.drawio` artifacts if validator/schema behavior changed;
10. record material upgrades under `docs/ChangeRequest/`.

---

## 9. Troubleshooting

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

This was an old CherryStock PowerShell scalar-indexing bug. Pull the latest repository; executable detection now returns the full path.

### Native export still fails

Run:

```powershell
git pull
.\tests\test_drawio_cli_helper.ps1
.\scripts\run_drawio_harness_demo.ps1
```

The current helper prints:

```text
File version
Product version
whether a GUI process was detected
strategy attempted
native exit/timeout state
elapsed time
```

If all three deterministic strategies fail, the final error contains one diagnostic record per strategy. That output is sufficient to distinguish a CherryStock process-control failure from a Draw.io Desktop build/runtime problem.

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
