# OpenCode V2 — CherryStock integration

## Purpose and source ownership

OpenCode should discover the existing CherryStock harness rather than maintain a
parallel set of roles or procedures. This is a client adapter, not a change to
ADLC ownership, gates, business contracts or diagram topology.

| Material | Responsibility |
|---|---|
| `AGENTS.md` | Cross-client bootstrap and links to canonical policy |
| `opencode.jsonc` | OpenCode V2 discovery and named runtime agent adapters |
| `.github/copilot-instructions.md` | Repository governance and routing |
| `.github/agents/CherryMon.agent.md` | Shared architecture constitution, not a task owner |
| `.github/agents/*.agent.md` | Canonical specialist outcome contracts |
| `.github/instructions/*.instructions.md` | Mandatory domain constraints |
| `.github/skills/*/SKILL.md` | Canonical reusable procedures |
| `docs/00_HOME.md` | Knowledge navigation; docs/ADR/requirements retain their ownership |

Do not move or copy `.github/` contracts into `.opencode/`. The adapter prompts
require the selected agent to read its canonical contract. Links alone do not
load that content. Existing client-specific frontmatter is not used as OpenCode
configuration; only the adapter uses V2 `system`, `mode` and `description` fields.

## Workspace and configuration

Open this repository **root** as the OpenCode workspace. V2 resolves configured
relative skill sources from the active workspace, not from the config file. With
a nested workspace such as `frontend/`, `./.github/skills` will not point at the
root catalog. Return to the root rather than copying skills into each package.

The project config automatically loads governance and constitution as additional
instructions. `AGENTS.md` supplies the remaining routing/navigation bootstrap.
Domain instructions, role contracts and detailed knowledge remain task-scoped:
do not configure a global `docs/**/*.md` or instruction glob that loads everything.

The project does not pin a provider, model, proxy port, credentials or MCP server.
Those remain in the user's global configuration or an explicitly approved
project-specific integration. A local Bedrock proxy and successful model discovery
are separate from harness discovery; do not invoke a paid model to validate this
configuration.

## Agent IDs

| OpenCode ID | Canonical contract / purpose |
|---|---|
| `cherrystock` | Router governed by `.github/copilot-instructions.md` |
| `cherrystock-ba` | `.github/agents/BusinessAnalyst.agent.md` |
| `cherrystock-sa` | `.github/agents/SolutionArchitect.agent.md` |
| `cherrystock-dev` | `.github/agents/GeneralCoding.agent.md` |
| `cherrystock-test` | `.github/agents/TestEngineer.agent.md` |
| `cherrystock-indicators` | `.github/agents/Indicator_Management.agent.md` |
| `cherrystock-chart` | `.github/agents/Chart.agent.md` |

The router is primary; specialists use `mode: all` for explicit primary selection
or authorized child sessions. Changing `default_agent` does not replace the
agent already stored on an existing session. Select the desired agent explicitly
there, or start a new session. Separate role names alone do not prove independent
validation; a validator needs the upstream contract, diff and execution evidence.
Prompts express responsibility, not a permission sandbox; configured permissions
and platform restrictions still control tools.

## Skills

The `skills` array registers the seven procedure directories individually. This
avoids registering the catalog's root `README.md` as an extra flat-file skill.
Expected IDs:

- `architecture-design`
- `indicator-onboarding`
- `regression-testing`
- `data-quality-validation`
- `duckdb-migration`
- `chart-authoring`
- `drawio-skill`

Only names/descriptions are advertised; bodies are loaded when needed. References
such as `.github/...`, `docs/...`, `src/...` and `tests/...` in these CherryStock
procedures denote repository-root paths, not paths inside the skill directory.
Use the actual skill base directory for skill-local scripts/templates. The
catalog `.github/skills/README.md` is an index, not an additional procedure skill.

## Read-only discovery checks

From the repository root, inspect the effective runtime without sending a model
prompt or changing the database:

```sh
opencode api get '/api/agent?location%5Bdirectory%5D=%2Fabsolute%2Fpath%2Fto%2FCherryStock'
opencode api get '/api/skill?location%5Bdirectory%5D=%2Fabsolute%2Fpath%2Fto%2FCherryStock'
opencode api get '/api/config?location%5Bdirectory%5D=%2Fabsolute%2Fpath%2Fto%2FCherryStock'
```

Replace the example value with the URL-encoded absolute repository path. These
commands use the installed API's `location[directory]` deep-object query selector
and may discover/start the shared background service. Confirm `location.directory`
in agent/skill responses is this workspace. The config endpoint may return a
source-list array instead of a location envelope; verify its project `path`.
During setup, omitting the selector targeted
the home directory; `--param` forms did not select the requested location, whereas
the explicit query string did. Do not interpret a home-location listing as a
project registration failure.
Check that all seven agent IDs and seven skill IDs above are present and that the
effective instruction sources include the two canonical files. Do not publish
raw config responses: inherited global settings may contain sensitive values.

Config changes apply automatically; use `/reload` if a full location reload is
needed. Do not restart a healthy service just to apply this configuration.
Discovery checks prove registration, not full agent execution, production data
correctness, diagram synchronization or independent test PASS.

## `/github-sync`

From the CherryStock checkout, `/github-sync` checks the current branch and its
configured GitHub upstream, fetches, commits all eligible non-ignored local
changes, merges upstream changes and pushes normally when needed. It does not
automatically target another branch or set up an upstream. A clean, equal branch
does not produce an empty commit.

Before a merge, the command creates a local backup branch at the pre-merge HEAD.
For conflicting paths it chooses the whole GitHub upstream version, including a
remote deletion; non-conflicting local changes are retained. Complex or ambiguous
conflicts stop for user review. Backup branches remain local until deliberately
removed. Files ignored by Git are not included. The command stops before staging
when it finds potentially sensitive or unexpectedly large files; inspect those
before deciding what may be published. Push rejection, a changed remote, missing
upstream or an in-progress Git operation also stop the command. It never force
pushes or automatically cleans uncommitted files.

This is an OpenCode prompt command, not a deterministic Git executable: its
checks are instructions to the agent and remain subject to the model's behavior,
tool permissions and branch protection. Review the resulting paths and commit
before sharing sensitive work. Invoking `/github-sync` authorizes committing all
eligible changes and a normal push, unlike ordinary coding requests. It does not
authorize force pushes or changing the destination.

## Maintenance

Windows transfer kit: `tools/opencode_windows/README.md`. Build an allowlisted
snapshot with `scripts/package_opencode_windows.py`; dependencies are installed
for Windows, and credentials/service identity are intentionally not copied.

- Update behavior in the owning `.github/` contract or canonical doc first.
- Keep runtime adapters short; change them only for routing/discovery changes.
- When adding a role, update governance and this ID map along with the adapter.
- When adding a skill, give its `SKILL.md` a meaningful description and update
  `.github/skills/README.md` plus the explicit directory list in `opencode.jsonc`.
- Preserve the write-location policy. Local edits require the exception stated
  in governance; commit/push is a separate explicit action, not an automatic side
  effect of setup or validation.

## OpenCode references

- <https://opencode.ai/docs/config>
- <https://opencode.ai/docs/instructions>
- <https://opencode.ai/docs/agents>
- <https://opencode.ai/docs/skills>
