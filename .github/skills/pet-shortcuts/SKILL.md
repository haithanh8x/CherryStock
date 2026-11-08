---
name: pet-shortcuts
description: "Create, update and synchronize Cherry-Win shorthand commands as PowerShell profile functions plus matching pet snippets. Use for new command shortcuts, aliases, pet Description updates, or keeping pet and shell commands consistent."
---

# Pet + PowerShell shortcuts

## Purpose and owner

Default outcome owner: repository-root `.github/agents/GeneralCoding.agent.md`.
This skill owns the repeatable shortcut procedure, not runtime/service ownership
or authorization to execute the underlying command.

Use when the user asks to create or modify a shorthand command, a PowerShell
function/alias, a pet snippet, or synchronize their names/descriptions. Future
shortcut requests follow the paired-function-and-snippet convention below unless
the user explicitly limits the scope (for example, Description-only).

Repository paths in this document are relative to the CherryStock root, not the
skill directory. Follow `AGENTS.md`, `.github/copilot-instructions.md` and
`docs/development/Development_Workflow.md`. Do not change unrelated governance.

## Required inputs and inspection

1. Confirm requested shorthand name, underlying script/arguments, working
   directory, shell and machine scope. Reuse an existing script rather than copy
   its business logic into the profile or snippet.
2. Inspect the script: privileges, interactive prompts, long-running behavior,
   mutations, paid calls, network listeners, credentials and exit behavior.
3. Discover profile paths from `$PROFILE` in the target shell. Prefer
   `$PROFILE.CurrentUserAllHosts` for functions shared by that PowerShell edition's
   hosts; Windows PowerShell and PowerShell 7 profiles are distinct. Never assume
   `Documents` is not redirected (OneDrive/redirection is possible).
4. Locate pet with `Get-Command pet`, then inspect user PATH and known installation
   locations if missing. Existing binaries outside the current process PATH are
   not proof that pet needs reinstalling. Check `pet version`.
5. Read pet's actual config and configured `SnippetFile`/`SnippetDirs`. On
   Cherry-Win the observed config is `$env:APPDATA\pet\config.toml`; do not assume
   this path on every machine. Inspect the selector (`fzf`) and `General.Cmd`.
6. Read affected profiles/snippets and check command-name collisions with
   `Get-Command <name> -All`. Distinguish intentional updates from unrelated user
   definitions. Ask before replacing an unrelated function/snippet.

## Paired naming contract

- Use the user's exact name. For proposed names, prefer lowercase `snake_case`.
  Service launchers use `srv_<service>`; other actions use `<subject>_<action>`.
- Create a PowerShell **function**, not a bare alias, when the command needs
  fixed arguments, working-directory handling or multiple steps.
- Create exactly one matching pet snippet. Its Description MUST begin with
  `<function_name> - <purpose>`, keeping relevant side-effect warnings visible.
- Preserve tag style and add a domain tag plus `cherrystock` when appropriate.
- Function and snippet must use the same script, fixed arguments and preparation
  steps; shorthand names alone do not guarantee equivalent behavior.
- Update the existing pair rather than append duplicates. Description-only edits
  leave commands/tags/functions unchanged unless requested otherwise.

Current agreed names (inspect live scripts before reuse):

| Function | Target / preparation | Important effect |
|---|---|---|
| `srv_ssh_server` | `tools/opencode_windows/SSHServer.ps1 -Action --start` | Starts sshd; may prompt for UAC |
| `srv_aws_bedrock` | `tools/opencode_windows/Start-BedrockProxy.ps1` | Long-running proxy; retain actual listener/auth warnings |
| `github_sync` | `scripts/git_auto_sync.ps1` | Adds, commits, rebases and pushes ALL changes |
| `cherrystock_run` | `scripts/run_daily.ps1` | Executes the mutating production `run.py` pipeline |
| `aws_renew_token` | `Unlock-SecretStore`, then `tools/Sync-AwsSsoCache.ps1` | Vault prompt and AWS SSO cache overwrite |

This table identifies shortcut targets; the owning scripts/runbooks remain the
behavioral source of truth. For AWS cache procedure see
`docs/runbook/Aws_Sso_Cache_Sync.md`.

## Implementation procedure

### 1. Confirm write scope

State which user profile and pet files will change. Permission to create a local
shortcut does not authorize Git commits/pushes, service execution, firewall edits,
credential changes, package installation or production pipeline execution.
Follow the repository write-location policy for durable CherryStock artifacts;
local user profile/pet configuration changes require the user's requested scope.

### 2. Safely edit the profile

- Preserve existing content. Back up nonempty affected files before modifying;
  backups may contain sensitive configuration and must not be committed.
- Use a clearly delimited managed block when adding several functions to a
  profile. On rerun update that block; never replace the whole profile.
- Quote script paths and resolve the confirmed checkout location. Use absolute
  paths in machine-local profile/snippets so invocation works from any directory.
  Reusable repository installers must accept/discover the checkout, not hardcode
  another user's path.
- Forward arguments with `@args` only when the target supports them. Fixed-action
  wrappers should not silently reinterpret arbitrary arguments.
- Prefer entry scripts that manage their own working directory. When a wrapper
  needs to change directory, use `Push-Location` and `try/finally { Pop-Location }`.
- Inspect scripts containing `exit`: direct invocation can close the calling
  session. Where needed launch in a child PowerShell process with consistent
  arguments in both wrapper and snippet. Explain child-process scope implications.
- Keep vault unlock and token use in the SAME process. `Unlock-SecretStore` has
  no `-Vault` parameter. Never embed passwords/tokens, disable vault authentication,
  or assume another terminal's unlock/environment is visible.

### 3. Safely edit pet

Use the configured snippet file and valid TOML. Example (substitute confirmed path):

```toml
[[snippets]]
  description = "srv_example - start example service (foreground)"
  command = '''powershell.exe -NoProfile -File "C:\path\CherryStock\tools\Start-Example.ps1"'''
  tag = ["cherrystock", "example"]
```

Single-line TOML literal strings avoid double-escaping Windows backslashes.
Do not insert quotes/newlines without checking TOML syntax.

- pet may execute through `cmd.exe` on Windows or a configured `General.Cmd`;
  inspect this instead of assuming PowerShell quoting or Unix `sh` semantics.
- Prefer explicit `powershell.exe -NoProfile ...` with the same script as the
  profile function; it does not depend on profile loading or function export.
- For multistep preparation use a correctly quoted `-Command` or reuse a wrapper
  script. Ensure interactive input remains available for vault/UAC prompts.
- Do not silently change execution policy. Use `-ExecutionPolicy Bypass` only if
  explicitly approved or preserving an existing accepted launch convention;
  never change persistent user/machine policy just to make a shortcut run.
- Keep existing warnings: ALL-change Git sync, production mutation, LAN listener
  without TLS/authentication, privilege escalation, and credential cache overwrite.
- If pet/fzf is absent, ask before installation. Use official releases/package
  managers with verified checksums; do not overwrite existing binaries.
- Do not run `pet sync` or enable Gist/GitLab auto-sync: local configuration may
  contain private machine paths. Remote sync needs separate authorization.

### 4. Bounded developer checks

Without running the underlying services or mutations:

1. Parse changed profiles/wrappers with PowerShell's language parser.
2. Confirm target scripts and fixed arguments match the inspected entry points.
3. Dot-source only the reviewed definitions (avoid unrelated startup side effects)
   and use `Get-Command` to verify names are functions.
4. Run `pet list` using the actual config; verify one Description prefix and
   command per name, no duplicates, preserved unrelated snippets.
5. Check selector version; interactive `pet exec` is user-tested unless a harmless
   isolated selector test is possible. Do not select live commands for validation.
6. Check function/snippet semantic parity, shell quoting, directory behavior,
   child-process exit effects and secret-process scope. Parsing alone is not proof
   of runtime behavior.

Stop after scoped checks. Runtime acceptance needs explicit authorization and
the appropriate owner; never call implementation checks an independent PASS.

## Output and user activation

Report modified files, name-to-target mapping, checks actually performed,
unverified runtime behavior, warnings and commit/push status. For the all-hosts
profile, the existing terminal can load definitions with:

```powershell
. $PROFILE.CurrentUserAllHosts
```

New terminals of that PowerShell edition load the profile unless started with
`-NoProfile`. Do not tell the user `. $PROFILE` loads all-hosts definitions when
that is a different file. Show `pet list` and `pet exec` for discovery.

## Stop conditions / anti-patterns

Stop and ask for missing/ambiguous target scripts, conflicting names, unsupported
shell quoting, unavailable interactive authorization or unclear write scope.
Never reset user profiles, duplicate snippets, execute `github_sync` merely to
test it, start a paid proxy/pipeline without approval, log secrets, or claim new
terminal/interactive/runtime verification that was not performed.
