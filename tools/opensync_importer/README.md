# OpenCode V2 → OpenSync importer

`opencode-sync-plugin` 0.3.7 only reads the legacy JSON layout
(`~/.local/share/opencode/storage/session`). OpenCode V2 stores history in
`opencode.db`, so `opencode-sync sync --all` reports *No OpenCode sessions found*
([OpenSync #34](https://github.com/waynesutton/opensync/issues/34)). This importer
replaces only that history import step.

It is one-way: it uploads history to the OpenSync dashboard. It does not bring
conversations back into OpenCode on another machine.

## How it works

- Reads sessions and messages through the OpenCode V2 HTTP API (`opencode api get`),
  never the SQLite file, so it needs a running/startable local OpenCode service.
- Sends to OpenSync `POST /sync/session` and `POST /sync/batch` (upsert by
  `externalId`, so re-sending is safe).
- Reuses the credentials written by `opencode-sync login`
  (`~/.opensync/credentials.json`), or `OPENSYNC_API_KEY` + `OPENSYNC_URL`.
- Tracks imported sessions in `~/.opensync/opencode-v2-import-state.json`; a
  session is re-sent only when its `time.updated` changes.

### Content policy (text only)

| Sent | Not sent |
|---|---|
| Session title, project path/name, model, token totals, cost | Reasoning |
| User prompt text | Tool input and output (file contents, commands) |
| Assistant reply text | Shell, system, synthetic, skill, compaction messages |
| Tool **names** only | Attachments |

Text is passed through a best-effort secret redactor (OpenSync/AWS/GitHub/API keys,
bearer tokens, private keys, `password=`-style values, OpenCode pairing links) and
truncated at 200 000 characters per message. Redaction is heuristic: review what
you send, and do not rely on it for highly sensitive conversations.

## Usage

Requirements: Node.js 18+, OpenCode V2 on `PATH`, and `opencode-sync login` done
once on that machine. Run from the repository root on **each** machine (Mac and
Windows have separate databases):

```sh
# Dry run: lists sessions and message counts, uploads nothing
node tools/opensync_importer/import.mjs

# Upload new/changed root sessions
node tools/opensync_importer/import.mjs --send
```

Options:

| Option | Effect |
|---|---|
| `--send` | Upload. Without it the run is a dry run. |
| `--session <id>` | Only one session. |
| `--limit <n>` | At most `n` sessions, newest first. |
| `--all` | Ignore local state and re-send everything (upsert). |
| `--include-children` | Also include subagent sessions. |

Exit codes: `0` all ok, `1` some sessions failed (they are retried next run),
`2` fatal error (for example missing credentials or OpenCode unavailable).

Do not add `opencode-sync-plugin` to `plugins` in OpenCode V2 config: it is a V1
plugin and is not needed for this importer.

## Known limitations

- OpenSync's batch endpoint ignores `createdAt`, so message timestamps on the
  dashboard reflect upload time; the session `createdAt` is preserved.
- Deleting a session locally does not delete it in OpenSync.
- `opencode api` can truncate large responses written to a pipe; the importer
  therefore redirects each response to a temporary file.

## Tests

```sh
node --test tools/opensync_importer/mapping.test.mjs
```
