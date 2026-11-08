# AWS SSO cache sync via Confluence CLI (Windows)

Run from the CherryStock root in an interactive PowerShell session. Entry point:
`tools/Sync-AwsSsoCache.ps1`. No Chrome/CDP or Atlassian `acli` required.

## Prerequisites and secret setup

- Node.js >= 20 and `npm install -g confluence-cli` (tested CLI version: 2.31.0).
- PowerShell >= 5.1; `Microsoft.PowerShell.SecretManagement` and
  `Microsoft.PowerShell.SecretStore` installed for the current Windows user.
- Vault `CherryVault` registered with `Microsoft.PowerShell.SecretStore`.
- Atlassian account has read/download access to page `22413313` on
  `haithanh8x.atlassian.net`.

Store the API token without putting its value in commands/history or the repository:

```powershell
Unlock-SecretStore
$token = Read-Host 'Confluence API token' -AsSecureString
Set-Secret -Vault CherryVault -Name ConfluenceApiToken -Secret $token
Remove-Variable token
```

`Unlock-SecretStore` has **no `-Vault` parameter**. Unlock in the same PowerShell
process that invokes the script; unlocking another terminal does not guarantee
that a background process can read the secret. Do not disable vault authentication
or save its password in the repository to enable unattended operation.

## Run

```powershell
Unlock-SecretStore
.\tools\Sync-AwsSsoCache.ps1
```

Defaults: email `haithanh8x@gmail.com`, page `22413313`, secret
`CherryVault/ConfluenceApiToken`, target `$env:USERPROFILE\.aws\sso\cache`.
All are parameters. The target resolves to `C:\Users\ADMIN\.aws\sso\cache` on
Cherry-Win. The script temporarily passes the token to the CLI through the process
environment, then restores the original environment even when download fails.
The plaintext token must exist briefly in process memory; local processes with
sufficient privileges can inspect it. It is never printed or persisted by the script.

If the token is already in this shell's environment:

```powershell
.\tools\Sync-AwsSsoCache.ps1 -UseEnvironmentToken
```

Use the ZIP already downloaded by the CLI without accessing the vault/network:

```powershell
.\tools\Sync-AwsSsoCache.ps1 -ArchivePath "$env:LOCALAPPDATA\aws-sso-cache-sync\cli\cache.zip"
```

## Safety and recovery

- Accepts flat JSON files or a single `cache/` wrapper; ignores macOS metadata.
- Rejects unsafe paths, duplicate filenames, unsupported layouts, invalid JSON
  and oversized archives **before overwriting cache files**.
- Backups of overwritten files are stored outside the repository under
  `$env:LOCALAPPDATA\aws-sso-cache-sync\backup-*`. Backups contain credentials;
  restrict access and delete them manually when no longer needed.
- Leaves files absent from the ZIP unchanged. Verifies SHA256 after copying and
  attempts restoration of overwritten files if copying fails; if restoration
  itself fails, restore manually from the reported backup directory.
- ZIP/staged files in the unique `run-*` directory are removed in `finally`.
  User-supplied `-ArchivePath` files are not removed.
- Do not run concurrent syncs against the same target directory.
- Copy/hash verification does **not** prove token expiry, AWS access, or portability
  between machines. Use `aws sso login --profile <profile>` for the supported AWS
  refresh flow when the imported tokens are expired or unusable.
- Never commit downloaded ZIPs, cache JSON, API tokens, or credential backups.

## Bounded developer check

Use `-ArchivePath`, a synthetic ZIP, and `-TargetDir`/`-WorkDir` pointing to a private
temporary sandbox to check extraction, metadata filtering, preservation, malformed
JSON rejection and ZIP path rejection without network or live credential mutation.
Live CLI/vault execution requires the user to unlock the vault in the invoking shell.
