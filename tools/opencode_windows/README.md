# CherryStock OpenCode + Bedrock — Windows transfer kit

## Contents and boundaries

This is an online setup kit, not an offline installer or a full CherryStock clone.
It includes a snapshot of the current two proxy source files (including local
changes), root OpenCode harness, agents, instructions, all seven skill folders
and their text/script support files, Markdown knowledge docs, slash commands,
`scripts/lib` and the existing Draw.io skill installer. `manifest.json` lists exact
files and SHA-256 checksums. Python SDK versions are locked in `requirements.txt`.
Mac venvs/binaries cannot be used on Windows; install native dependencies there.

Excluded: AWS credentials/config/cache, OAuth sessions, OpenCode session database,
service password/remote registration, .env, private keys, proxy certificates,
DuckDB data and Draw.io backup files. The OpenCode configuration is reconstructed
with only model metadata and five MCP definitions. No account/credential cloning.

## Windows prerequisites

- Install Python **3.13** with the `py` launcher, AWS CLI v2, Git and OpenCode **V2**.
  Download OpenCode for Windows from <https://opencode.ai/docs/>; use the native
  installer/binary, not a V1 package. Open a fresh PowerShell and verify
  `py -3.13 --version`, `aws --version`, `git --version`, `opencode --version`.
- Internet access to PyPI, GitHub releases, AWS and the MCP endpoints.
- Authorization from your AWS/IT administrator to use the profile on this machine.

Extract the ZIP to a permanent directory, e.g. `C:\Tools\CherryStock-OpenCode-Windows`.
Do not move it after installation/task registration: config and task use this path.

Clone CherryStock separately (or use an existing checkout):

```powershell
git clone https://github.com/haithanh8x/CherryStock.git C:\Github\CherryStock
```

Install from the extracted kit:

```powershell
.\Install.ps1 -RepoPath C:\Github\CherryStock
```

The installer verifies the manifest, refuses to overwrite differing checkout
files, installs a private Python venv, downloads the official GitHub MCP v2.1.0
Windows executable and verifies its release checksum. New snapshot files are
copied into the checkout; differing existing files must be reviewed/merged by you
first. Do not use reset/force-copy to bypass this check. The proxy runs the bundled
snapshot source, not a silently changing checkout file.

Existing global OpenCode JSON causes a stop. Inspect it before using
`-ReplaceGlobalConfig`, which backs it up then **replaces** it, not merges it.
Existing JSONC must be merged manually. The installer honors `XDG_CONFIG_HOME`.
No scheduled task, remote access or paid model call is performed by installation.
On retry, an existing downloaded MCP binary also stops rather than overwriting it.

## AWS SSO and proxy

Create the profile on Windows using organization-approved SSO values:

```powershell
aws configure sso --profile data-app-sit
aws sso login --profile data-app-sit
aws sts get-caller-identity --profile data-app-sit
.\Start-BedrockProxy.ps1
```

Region defaults to `ap-southeast-1`; use `-Profile` and `-Region` to change it.
The listener is **HTTP 127.0.0.1:8765 only**, no local bearer authentication,
direct Bedrock, low tier, 300s timeout, with AWS TLS verification enabled. Never
open this proxy port to your LAN/Internet. Draw.io Desktop's HTTPS requirement is
not addressed by this OpenCode-specific launcher. Ctrl+C stops foreground proxy.

The snapshot of `llm_client.py` currently has `ca_bundle = None` and explicitly
passes `verify=True`. Therefore `AWS_CA_BUNDLE` alone is **not guaranteed** to solve
corporate TLS inspection. If certificate errors occur, stop and obtain an approved
CA-handling implementation from IT; do not disable SSL verification. The kit does
not silently repair or modify your existing source files.

## Start automatically at Windows logon

After the foreground proxy works, stop it and register the optional per-user task:

```powershell
.\Register-ProxyTask.ps1
Start-ScheduledTask -TaskName CherryStock-BedrockProxy
```

This is a Windows **Task Scheduler logon task**, not an SCM service running as
SYSTEM. It uses the logged-in user's AWS profile, stores no Windows password and
does not auto-login/refresh SSO. It cannot guarantee service before login or after
SSO expiration. Repeat `aws sso login` when needed. Logs are under the kit's `logs/`;
rotate/remove old logs deliberately. The task refuses duplicate registration.

To stop/unregister this task only:

```powershell
Stop-ScheduledTask -TaskName CherryStock-BedrockProxy
Unregister-ScheduledTask -TaskName CherryStock-BedrockProxy -Confirm
```

Do not run foreground and task proxy at the same time: both bind port 8765.

## Verify OpenCode without invoking a paid model

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
Invoke-RestMethod http://127.0.0.1:8765/v1/models
Set-Location C:\Github\CherryStock
opencode service start
opencode mcp list
opencode
```

OpenCode creates its own service state/password on Windows. Never import the Mac
`service.json` or database. Authenticate Atlassian, Cloudflare and Figma through
`/mcps`. GitHub's local server uses its browser OAuth flow; Draw.io needs no login.
Use the project root for seven agent adapters and seven skills. Read
`docs/development/OpenCode_Setup.md` for discovery. A model list/health result is
not proof of AWS model permissions; a real prompt costs tokens and should be
performed separately with your approval. Some configured models are explicitly
marked unavailable and remain listed for fidelity to the current Mac config.

## Extra skill runtimes

The seven CherryStock skill contracts are included, but referenced tools are not
all installed runtimes. For full Draw.io validation, the included repository
installer fetches its pinned upstream skill (review before running):

```powershell
Set-Location C:\Github\CherryStock
.\scripts\install_drawio_skill.ps1 -SkipNativeExportProbe
```

Install Draw.io Desktop separately for native export. That existing installer can
replace an existing upstream skill directory; do not run it over user work.
Archify and Flint are not present in the Mac runtime inventory and are **not**
bundled; follow their owning runbooks before authoring/rendering. Product Python
dependencies/DuckDB data require the normal CherryStock setup, not this minimal
proxy venv. Built-in OpenCode/report skills ship with OpenCode, not this kit.

## Build again on Mac

From the repository root (use a new filename each time):

```sh
python3 scripts/package_opencode_windows.py --output docs/reference/data/opencode-setup/CherryStock-OpenCode-Windows.zip
```

Review the manifest before copying; it hashes integrity, not trust/authenticity.
Keep this kit private: while credentials are excluded, it contains project docs
and AWS profile/model names. Do not commit/push this generated bundle without review.

## Start and stop the Windows SSH server

This script controls an already installed Windows OpenSSH Server (`sshd`). Run
it in PowerShell on Cherry-Win, from the repository root:

```powershell
.\tools\opencode_windows\SSHServer.ps1 --start
.\tools\opencode_windows\SSHServer.ps1 --stop
```

If PowerShell is not elevated, the script requests administrator access via a
Windows UAC prompt. Approve it, or run PowerShell as Administrator. UAC requires
an interactive desktop and administrator credentials when prompted; it cannot
automatically elevate an unattended SSH session.

Stopping `sshd` may disconnect active SSH sessions. The script does not install
OpenSSH, change firewall rules or alter its startup type. If `sshd` is configured
to start automatically, stopping it does not prevent it from starting at the next
boot. Check the service with `Get-Service sshd`; allow network access only from
trusted networks.
