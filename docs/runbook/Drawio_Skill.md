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

Pinned upstream skill:

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

Optional for native PNG/SVG/PDF export:

```text
Draw.io Desktop
```

The local machine used while validating this integration has:

```text
Draw.io Desktop 28.1.2
```

Core upstream IR/XML/query/test/review workflows use Python 3 only.

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
6. when Draw.io Desktop exists, runs a real native PNG export probe through `scripts/lib/DrawioCli.psm1`;
7. validates the PNG signature instead of trusting exit code alone.

To install only the Python skill runtime without probing Draw.io Desktop:

```powershell
.\scripts\install_drawio_skill.ps1 -SkipNativeExportProbe
```

---

## 3. Draw.io Desktop 28.x CLI compatibility

### 3.1 Root cause of `input file/directory not found`

Draw.io Desktop **28.1.2** uses `commander` for CLI parsing. Its source registers draw.io options such as:

```text
--export
--format
--output
--width
--transparent
```

and then uses:

```text
program.args[0]
```

as the input file path.

The same source enables:

```text
.allowUnknownOption()
```

This creates an important compatibility trap: arbitrary Electron/Chromium flags may become positional arguments instead of being ignored safely.

The earlier CherryStock helper passed flags such as:

```text
--disable-update
--user-data-dir=...
--disable-gpu
```

Those flags are **not** registered draw.io CLI options in v28.1.2. As a result, Draw.io could treat one of them as `program.args[0]`, execute `fs.statSync()` on that token and emit:

```text
Error: input file/directory not found
```

even though the actual `.drawio` file existed.

This behavior is visible in the tagged upstream implementation:

```text
jgraph/drawio-desktop v28.1.2
src/main/electron.js
```

### 3.2 Correct CherryStock policy

CherryStock now sends **only draw.io-registered CLI options** in native export argv:

```text
--export
--format png
--output <file.png>
[--transparent]
[--width N]
<input.drawio>
```

Disable-update is handled through the environment variable that Draw.io 28.1.2 already supports:

```text
DRAWIO_DISABLE_UPDATE=true
```

Do not add these to native export argv for Draw.io 28.x:

```text
--disable-update
--user-data-dir=...
--disable-gpu
```

### 3.3 Process lifecycle

Native execution is centralized in:

```text
scripts\lib\DrawioCli.psm1
```

The helper uses `System.Diagnostics.Process` with:

```text
UseShellExecute = false
RedirectStandardOutput = true
RedirectStandardError = true
bounded WaitForExit
```

Then it performs:

```text
process exit
    ↓
stdout/stderr diagnostics
    ↓
output stability check
    ↓
PNG signature validation
```

This avoids both false-positive exit handling and hidden CLI diagnostics.

### 3.4 Known `shadow="1"` export issue

Draw.io Desktop has also had a Windows CLI defect where `mxGraphModel shadow="1"` can return exit code 0 without creating PNG output.

CherryStock probe and demo therefore use:

```text
shadow="0"
```

---

## 4. Run the focused helper regression test

Before the real Draw.io test, run:

```powershell
.\tests\test_drawio_cli_helper.ps1
```

The test compiles a temporary fake exporter and verifies two independent contracts:

1. the helper waits for a delayed native process before checking output;
2. the helper does **not** pass the forbidden Draw.io 28.x argv tokens:

```text
--disable-update
--user-data-dir
--disable-gpu
```

Expected:

```text
PASS: DrawioCli waits for delayed process completion
PASS: DrawioCli argv contains only draw.io-registered options
Strategy:  registered-cli-options
```

---

## 5. Run the CherryStock Agent Harness demo

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

[2/3] Native CLI compatibility probe
      minimal .drawio → PNG
      registered CLI options only
      verify stable output + PNG signature

[3/3] Demo native PNG export
      real Harness .drawio → PNG
      same helper
      verify final PNG signature
```

Expected success:

```text
PASS: structural validation
CLI policy: registered draw.io options only; update checks disabled via DRAWIO_DISABLE_UPDATE environment variable.
PASS: native CLI probe (... strategy=registered-cli-options ...)
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

## 6. Manual troubleshooting

### Core skill files

```powershell
Test-Path "$HOME\.agents\skills\drawio-skill\SKILL.md"
Test-Path "$HOME\.agents\skills\drawio-skill\scripts\validate.py"
python "$HOME\.agents\skills\drawio-skill\scripts\diagramctl.py" doctor
```

### Draw.io executable

```powershell
Test-Path "C:\Program Files\draw.io\draw.io.exe"
(Get-Item "C:\Program Files\draw.io\draw.io.exe").VersionInfo | Format-List FileVersion,ProductVersion
```

### Structural validation only

```powershell
python "$HOME\.agents\skills\drawio-skill\scripts\validate.py" `
  "docs\architecture\diagrams\agent-harness-five-components.drawio" `
  --score
```

### Native command contract for Draw.io 28.x

If diagnosing manually, keep the command minimal. Do not insert arbitrary Electron flags before the input path.

Conceptually:

```text
draw.io.exe --export --format png --output output.png input.drawio
```

CherryStock automation should still use `scripts/lib/DrawioCli.psm1` rather than duplicating this command.

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
registered CLI argv + bounded native process execution
    ↓
output integrity check
    ↓
Visual review
    ↓
Commit editable source + required durable docs
```

For approved architecture changes, the existing `SolutionArchitect.agent.md` Archify synchronization rules still apply. Draw.io remains supplemental unless repository governance is deliberately changed.

---

## 8. Updating Draw.io or the upstream skill

When upgrading the upstream skill or Draw.io Desktop:

1. inspect release/changelog;
2. update the pinned upstream skill ref when applicable;
3. run `diagramctl.py doctor`;
4. run `tests\test_drawio_cli_helper.ps1`;
5. require the real native PNG probe to PASS;
6. run the Harness demo;
7. if the Draw.io Desktop major CLI parser changes, inspect its registered options before adding new native argv flags;
8. record material compatibility changes under `docs/ChangeRequest/`.