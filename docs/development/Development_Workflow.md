# Development Workflow

## Working model
Open the same local CherryStock repository in both VS Code and Obsidian.

~~~text
C:\Github\CherryStock
~~~

GitHub is the versioned Single Source of Truth. Obsidian is the knowledge-navigation layer. VS Code is the implementation workspace.

## Daily flow

~~~text
1. git pull
2. Open repository in Obsidian
3. Start from docs/00_HOME.md
4. Review/update architecture or ADR if needed
5. Open the same repository in VS Code
6. Implement using repository instructions
7. Run focused tests / real execution
8. Stop when acceptance criteria are decided
9. git diff
10. Commit on feature branch
11. Open/review Pull Request
~~~

## Before coding
Read in order:
1. .github/copilot-instructions.md
2. .github/agents/CherryMon.agent.md
3. intent-specific agent:
   - SolutionArchitect.agent.md for architecture/design
   - TestEngineer.agent.md for test design/execution
4. matching .github/instructions/*.instructions.md
5. related docs/architecture/*.md / docs/adr/*.md
6. implementation + nearest tests

## Bounded execution rule

All local-agent execution should converge.

~~~text
DEFINE objective
→ CHANGE/TEST
→ EVIDENCE
→ PASS / FAIL / BLOCKED / REGRESSION
→ KEEP / REVERT / STOP
~~~

Rules:
- one active objective/hypothesis at a time;
- do not rerun unchanged failed commands;
- default maximum two repair attempts for the same failure;
- do not expand to unrelated files or hypotheses automatically;
- after a terminal verdict, stop the current task;
- create a new task/runbook for the next hypothesis.

This is especially important when using fast/small models such as Flash-class LLMs.

## Documentation ownership
- AI/developer behavior → .github/**
- system architecture/specification → docs/architecture/**
- architecture decision/rationale → docs/adr/**
- implementation → src/**
- validation → tests/**
- operational/init/migration entry points → scripts/**

Test runbooks under tests/*.md must be finite execution instructions, not open-ended investigation documents.

Do not duplicate a document solely for Obsidian. Use links/backlinks to navigate the same repository files.

## Recommended Git workflow

~~~powershell
git pull origin main
git checkout -b feature/<name>
# edit in Obsidian / VS Code
python -m pytest <focused-test> -v
git status
git diff
git add .
git commit -m "<type>: <summary>"
git push -u origin feature/<name>
~~~

Prefer Pull Requests for architecture/instruction changes because they affect future AI/developer behavior.
