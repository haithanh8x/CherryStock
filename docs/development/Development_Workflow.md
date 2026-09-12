# Development Workflow

## Working model
Open the same local CherryStock repository in both VS Code and Obsidian.

~~~text
C:\Github\CherryStock
~~~

GitHub is the versioned Single Source of Truth. Obsidian is the knowledge-navigation layer. VS Code is the implementation workspace.

## Developer daily flow

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



## Runtime daily data pipeline

The developer workflow above is separate from the production/local data pipeline
executed by `python run.py`.

Canonical runtime documentation:

`docs/runbook/Daily_Data_Pipeline.md`

Runtime ownership:

```text
run.py
→ DuckDBUnitOfWork
→ SyncWritePipelineService.run()
→ EOD / Intraday / DQ / calculations / SmartMoney
→ COMMIT
→ exportDuckDB_metadata()
```

Do not duplicate the daily stage sequence directly in `run.py`; modify the
application service and its nearest orchestration/DQ tests instead.

## Before coding
Read in order:
1. .github/copilot-instructions.md
2. .github/agents/CherryMon.agent.md
3. intent-specific agent:
   - BusinessAnalyst.agent.md for requirement analysis/backlog
   - SolutionArchitect.agent.md for architecture/design
   - Indicator_Management.agent.md for concrete indicator lifecycle
   - GeneralCoding.agent.md for clear general implementation
   - TestEngineer.agent.md for test design/execution
4. matching .github/instructions/*.instructions.md
5. related requirement/architecture/ADR/domain materials routed from docs/00_HOME.md
6. implementation + nearest tests

For any task that creates or changes Python tests, repository-root commands or runnable scripts, also read:

`docs/development/Python_Execution_Conventions.md`

Do not invent a new import/bootstrap convention when the repository already defines one.

## Python execution contract

CherryStock uses a `src` layout, and Python resolves imports differently depending on how a command is invoked.

Canonical details live in:

`docs/development/Python_Execution_Conventions.md`

Key developer obligations:

- documented Python commands must be reproducible from the repository root;
- new tests must not depend on a developer-specific manual `PYTHONPATH`;
- directly executed `scripts/*.py` entry points must bootstrap the repository path themselves when needed;
- pytest collection/import failures must be diagnosed before labeling a failure as behavioral regression;
- use one known-good neighboring test/script as the convention reference instead of repeatedly probing `sys.path`.

When a runbook command works only after setting an absolute local path such as `C:\Github\CherryStock`, treat that as an execution-contract defect unless that path is an explicit project configuration contract.

## Standard handoff

~~~text
BusinessAnalyst (when needed)
→ READY_FOR_DESIGN / READY_FOR_IMPLEMENTATION
→ SolutionArchitect (when needed)
→ APPROVED_FOR_IMPLEMENTATION
→ GeneralCoding or authoritative domain agent
→ IMPLEMENTED_PENDING_VALIDATION
→ TestEngineer
→ PASS / FAIL / BLOCKED / REGRESSION
~~~

Small, explicit changes may route directly to General Coding. No role self-approves the downstream role's outcome.

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

## Role and material ownership
- requirement/backlog readiness → BusinessAnalyst.agent.md + docs/backlog/requirements/**
- architecture/design readiness → SolutionArchitect.agent.md + docs/architecture/** / docs/adr/**
- general implementation readiness → GeneralCoding.agent.md + src/** / scripts/** / affected canonical docs
- concrete indicator lifecycle → Indicator_Management.agent.md
- independent validation verdict → TestEngineer.agent.md + tests/**
- AI/developer behavior → .github/**
- system architecture/specification → docs/architecture/**
- architecture decision/rationale → docs/adr/**
- implementation → src/**
- validation → tests/**
- operational/init/migration entry points → scripts/**
- Python import/execution convention → docs/development/Python_Execution_Conventions.md
- non-obvious implementation guidance only → docs/development/implementation-notes/**

Test runbooks under tests/*.md must be finite execution instructions, not open-ended investigation documents.

Postmortems, issue exports and developer lessons from a completed run belong under `docs/development/implementation-notes/**` when they remain useful. Once their reusable lessons are incorporated into canonical docs/instructions, they must not remain in `tests/**` as a competing contract.

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
