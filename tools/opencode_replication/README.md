# OpenCode session replication — Cherry-Mac ↔ Cherry-Win

Two-node, active-active replication of OpenCode V2 sessions through one shared
folder (Google Drive for desktop syncs that folder between the machines). Each
machine keeps its own `opencode.db` (shared-nothing); both accept new work.

This is not a database-level stream like Oracle GoldenGate: OpenCode exposes no
change-log apply API. The unit of replication is a **session transcript**
(exported and imported through the OpenCode V2 HTTP API), and the redo log is
replaced by per-node, immutable transcript files plus a manifest.

## Usage

Requirements on each machine: Node.js 18+, OpenCode V2 with its background
service running (`opencode service status`), and the shared Drive folder.

```sh
# Cherry-Mac
node tools/opencode_replication/sync.mjs \
  --dir "/Users/blackeyes/Library/CloudStorage/GoogleDrive-<account>/My Drive/<folder>" \
  --node cherry-mac \
  --map "C:\Github\CherryStock=/Users/blackeyes/CherryStock"

# Cherry-Win (PowerShell)
node tools/opencode_replication/sync.mjs `
  --dir "G:\My Drive\<folder>" `
  --node cherry-win `
  --map "/Users/blackeyes/CherryStock=C:\Github\CherryStock"
```

Without `--execute` the command is a dry run that prints every decision. Add
`--execute` to apply and publish. Run it on one machine, wait for Google Drive to
finish uploading, then run it on the other.

| Option | Meaning |
|---|---|
| `--dir <path>` | Shared folder (required). `opencode-replication/` is created inside it. |
| `--node <name>` | This machine's node name (required), e.g. `cherry-mac`, `cherry-win`. Never reuse a name on two machines. |
| `--execute` | Apply decisions and publish. Default is dry run. |
| `--priority <name>` | Node that wins concurrent changes. Default `cherry-win`. Use the same value on both machines. |
| `--map <from>=<to>` | Map a peer project directory to the local one (repeatable). Without a map, a local project with the same folder name is used when unambiguous. |
| `--session <id>` | Only one session. |
| `--server`, `--password` | Use an explicit OpenCode server instead of the background service. |
| `--state-dir <path>` | Local state and backups. Default `~/.opencode-replication`. |

Exit codes: `0` ok, `1` some sessions failed (retried next run), `2` fatal.

## Shared-folder layout

```text
<dir>/opencode-replication/nodes/
├── cherry-mac/
│   ├── manifest.json                      # written last, atomically
│   ├── sessions/<sessionID>/<hash>.json.gz
│   └── conflicts.jsonl                    # conflict audit log
└── cherry-win/ …
```

- **Single writer per directory.** A node writes only `nodes/<its name>/` and
  only reads the peer's directory, so Google Drive never sees concurrent writes
  to the same file and never creates "conflicted copy" files.
- Session files are immutable and named by content hash; a node keeps the current
  and previous version of each session.
- Files are written to a temporary name and renamed; the manifest is written
  after the session files. A reader verifies the hash of every peer file and
  defers the session when the file is missing, partial or mismatched (Drive still
  syncing). The next run retries.
- Full transcripts are stored **unencrypted**, including tool input and output
  (file contents, commands, possible secrets). Anyone with access to the Drive
  folder can read them.

Local state (`~/.opencode-replication/<node>/state.json`) and pre-replacement
backups (`…/backup/<sessionID>/*.json.gz`) never go to the shared folder.

## Conflict detection

Each session's replicated content is its ordered messages plus title and
archived flag. Its hash ignores node-local fields (directory, project ID,
timestamps, and `firstToken`, which OpenCode drops on import), so the same
session hashes equally on both machines.

Each manifest entry carries a two-node version vector:

| Field | Meaning |
|---|---|
| `hash` | Current version on the publishing node |
| `basedOn` | Peer version this version already contains |
| `overrides` | Peer version this node discarded when it won a conflict |

For each session the node compares its local version `L` with the peer version
`P`, using its state (`seenPeer`, the last peer version it processed):

| Situation | Action |
|---|---|
| Only on the peer | `import` |
| Deleted locally after a previous sync | `skip-deleted` (deletions are not replicated and not restored) |
| `L = P`, or `P` unchanged since the last sync | `seen` / `keep` |
| `P.basedOn = L` (peer built on our version, including revert/compaction) | `apply` |
| `P.overrides = L` (priority peer discarded our version) | `copy-apply` |
| `L` is a prefix of `P` | `apply` (fast-forward) |
| `P` is a prefix of `L` | `seen` (we are ahead; publish) |
| Both changed (diverged messages or title/archive) | **conflict** |

Detection uses content and version vectors, not wall-clock time, so clock skew
between Mac and Windows does not affect it.

## Conflict resolution (custom rule, priority node)

| Data | Rule |
|---|---|
| Messages | **Priority node wins** (default `cherry-win`). The losing node keeps its version as a new session titled `[conflict <node>] <title>`, which then replicates like any other session. Nothing is lost. |
| Title, archived | Priority node wins. |
| Tokens, cost | Not merged; recomputed by OpenCode from each session's messages. Additive merging would double-count shared history. |
| Project directory | Never replicated; mapped to the local path (`--map`). |
| Deletion | Not replicated in this version. |
| Running session | Deferred until idle (`/api/session/active`). |

Last-write-wins is not used for messages because it would silently discard a
whole branch of a conversation.

## Applying a peer version

OpenCode rejects importing an existing session (HTTP 409) and deleting a session
also deletes its child sessions. To replace a local session the tool:

1. skips it if it or a child is running, or if it changed since it was exported;
2. backs up the session and its children locally;
3. deletes the session, imports the peer version, then re-imports the children;
4. on import failure restores the backup.

Parents are processed before children; a child whose parent is not present
yet is deferred.

## Validation performed

- `node --test tools/opencode_replication/cdr.test.mjs` (13 unit tests of the CDR
  decision table, hashing, ID remapping, ordering and path mapping).
- End-to-end on two temporary OpenCode servers with separate databases and a
  temporary shared folder, using copies of real sessions: initial replication,
  fast-forward, concurrent edits with either node syncing first, parent
  replacement with a child session preserved, deleted session not restored, and
  convergence to a stable state.

Not yet validated: real Google Drive propagation, Windows paths and services,
and continuing a replicated session with a model.

## Known limitations

- Experimental OpenCode APIs (`/api/experimental/session/export|import`).
- Not real-time: replication happens when the command runs.
- Attachments and file snapshots used for revert may not be part of the export.
- Replacing a session changes its local `time.updated`.
- Two nodes only.

## Tests

```sh
node --test tools/opencode_replication/cdr.test.mjs
```
