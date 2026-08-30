# Development Workflow

## Working model
Open the same local CherryStock repository in both VS Code and Obsidian.

```text
C:\Github\CherryStock
```

GitHub is the versioned Single Source of Truth. Obsidian is the knowledge-navigation layer. VS Code is the implementation workspace.

## Daily flow

```text
1. git pull
2. Open repository in Obsidian
3. Start from docs/00_HOME.md
4. Review/update architecture or ADR if needed
5. Open the same repository in VS Code
6. Implement using repository instructions
7. Run focused tests / real execution
8. git diff
9. Commit on feature branch
10. Open/review Pull Request
```

## Before coding
Read in order:
1. `.github/copilot-instructions.md`
2. `.github/agents/CherryMon.agent.md`
3. matching `.github/instructions/*.instructions.md`
4. related `docs/architecture/*.md` / `docs/adr/*.md`
5. implementation + tests

## Documentation ownership
- AI/developer behavior → `.github/**`
- system architecture/specification → `docs/architecture/**`
- architecture decision/rationale → `docs/adr/**`
- implementation → `src/**`
- validation → `tests/**`
- operational/init/migration entry points → `scripts/**`

Do not duplicate a document solely for Obsidian. Use links/backlinks to navigate the same repository files.

## Recommended Git workflow

```powershell
git pull origin main
git checkout -b feature/<name>
# edit in Obsidian / VS Code
python -m pytest <focused-test> -v
git status
git diff
git add .
git commit -m "<type>: <summary>"
git push -u origin feature/<name>
```

Prefer Pull Requests for architecture/instruction changes because they affect future AI/developer behavior.