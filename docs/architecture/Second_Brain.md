# Second Brain Architecture

## Goal
Use one version-controlled repository as the shared knowledge system for GitHub, VS Code and Obsidian.

```text
GitHub
  = Source of Truth + History

Local Git checkout
  = shared physical workspace

VS Code
  = implementation + AI execution

Obsidian
  = knowledge graph + navigation
```

## Core principle
Obsidian is a **view over the repository**, not another document store.

Open the local CherryStock root directly as the Obsidian Vault, for example:

```text
C:\Github\CherryStock
```

Do not create duplicated copies of instruction or architecture Markdown in a separate Obsidian folder.

## Knowledge layers

```text
L0 .github/copilot-instructions.md
    Global AI governance

L1 .github/agents/CherryMon.agent.md
    Architecture constitution

L2 .github/instructions/*.instructions.md
    Domain policy

L3 docs/architecture/*.md + docs/adr/*.md
    System specification + decision memory

L4 src/** + tests/** + scripts/**
    Implementation + validation + execution
```

## Ownership model
Each rule has one owner. Higher-level files reference domain rules instead of duplicating them.

| Concern | Owner |
|---|---|
| Global AI workflow | `.github/copilot-instructions.md` |
| Project architecture principles | `.github/agents/CherryMon.agent.md` |
| DuckDB/data-quality policy | `.github/instructions/database.instructions.md` |
| Indicator policy | `.github/instructions/indicators.instructions.md` |
| Chart policy | `.github/instructions/chart.instructions.md` |
| Crawler policy | `.github/instructions/crawler.instructions.md` |
| Test policy | `.github/instructions/testing.instructions.md` |
| System design | `docs/architecture/*.md` |
| Architecture decisions | `docs/adr/*.md` |

## Daily workflow

```text
git pull
   ↓
Obsidian: think/design/link knowledge
   ↓
VS Code/Copilot: implement
   ↓
tests + real execution
   ↓
git diff
   ↓
commit / pull request
   ↓
GitHub history
```

Start from [[../00_HOME|00_HOME]].