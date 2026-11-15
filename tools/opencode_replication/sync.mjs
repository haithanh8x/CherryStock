#!/usr/bin/env node
// Two-node active-active replication of OpenCode V2 sessions through a shared folder
// (for example a Google Drive for desktop folder). See README.md for the design.

import { execFileSync } from "node:child_process";
import {
  closeSync,
  existsSync,
  mkdirSync,
  openSync,
  readdirSync,
  readFileSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { homedir, hostname } from "node:os";
import { join } from "node:path";
import { gunzipSync, gzipSync } from "node:zlib";
import { conflictCopy, decide, mapDirectory, parentsFirst, summarize } from "./cdr.mjs";

const FORMAT = 1;
const ROOT_NAME = "opencode-replication";
const NODE_RE = /^[a-z0-9][a-z0-9-]{0,31}$/;
const SESSION_RE = /^ses_[A-Za-z0-9]+$/;

// ---------- arguments ----------

const HELP = `
  OpenCode session replication (two nodes, shared folder)

  Usage: node tools/opencode_replication/sync.mjs --dir <shared folder> --node <name> [options]

  Without --execute this is a dry run: decisions are printed, nothing is written.

  Required:
    --dir <path>          Shared folder (e.g. inside Google Drive). "${ROOT_NAME}/" is created in it.
    --node <name>         This node's name, e.g. cherry-mac or cherry-win.

  Options:
    --execute             Apply decisions locally and publish to the shared folder.
    --priority <name>     Node that wins concurrent changes (default: cherry-win).
    --map <from>=<to>     Map a peer project directory to a local one (repeatable).
    --session <id>        Only this session.
    --server <url>        OpenCode server URL (default: the local background service).
    --password <pw>       Server password (default: background service; or OPENCODE_PASSWORD).
    --state-dir <path>    Local state/backup directory (default: ~/.opencode-replication).
`;

function parseArgs(argv) {
  const opts = { maps: [], priority: "cherry-win", execute: false };
  const need = (i) => {
    if (i >= argv.length) throw new Error(`Missing value for ${argv[i - 1]}`);
    return argv[i];
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--dir") opts.dir = need(++i);
    else if (a === "--node") opts.node = need(++i);
    else if (a === "--priority") opts.priority = need(++i);
    else if (a === "--execute") opts.execute = true;
    else if (a === "--session") opts.session = need(++i);
    else if (a === "--server") opts.server = need(++i);
    else if (a === "--password") opts.password = need(++i);
    else if (a === "--state-dir") opts.stateDir = need(++i);
    else if (a === "--map") {
      const v = need(++i);
      const at = v.indexOf("=");
      if (at <= 0 || at === v.length - 1) throw new Error(`--map expects <from>=<to>, got: ${v}`);
      opts.maps.push([v.slice(0, at), v.slice(at + 1)]);
    } else if (a === "-h" || a === "--help") opts.help = true;
    else throw new Error(`Unknown argument: ${a}`);
  }
  if (opts.help) return opts;
  if (!opts.dir) throw new Error("--dir is required");
  if (!opts.node) throw new Error("--node is required");
  for (const n of [opts.node, opts.priority]) {
    if (!NODE_RE.test(n)) throw new Error(`Invalid node name "${n}" (use lowercase letters, digits, '-')`);
  }
  if (opts.session && !SESSION_RE.test(opts.session)) throw new Error(`Invalid session id: ${opts.session}`);
  if (!existsSync(opts.dir) || !statSync(opts.dir).isDirectory()) {
    throw new Error(`Shared folder not found: ${opts.dir}`);
  }
  opts.stateDir ??= join(homedir(), ".opencode-replication");
  return opts;
}

// ---------- file helpers ----------

function writeAtomic(path, data) {
  const tmp = `${path}.tmp-${process.pid}`;
  writeFileSync(tmp, data);
  renameSync(tmp, path);
}

function readJson(path, fallback) {
  if (!existsSync(path)) return fallback;
  return JSON.parse(readFileSync(path, "utf8"));
}

function acquireLock(dir) {
  mkdirSync(dir, { recursive: true });
  const path = join(dir, "sync.lock");
  if (existsSync(path) && Date.now() - statSync(path).mtimeMs > 6 * 3600_000) rmSync(path, { force: true });
  let fd;
  try {
    fd = openSync(path, "wx");
  } catch {
    throw new Error(`Another sync is running (lock: ${path}). Delete it if no sync is running.`);
  }
  writeFileSync(fd, String(process.pid));
  closeSync(fd);
  process.on("exit", () => rmSync(path, { force: true }));
}

// ---------- OpenCode client ----------

function runOpencode(args) {
  const opts = { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] };
  try {
    return execFileSync("opencode", args, opts);
  } catch (error) {
    if (error.code === "ENOENT" && process.platform === "win32") return execFileSync("opencode", args, { ...opts, shell: true });
    throw error;
  }
}

function serviceEndpoint(opts) {
  if (opts.server) {
    const password = opts.password ?? process.env.OPENCODE_PASSWORD;
    if (!password) throw new Error("--server needs --password or OPENCODE_PASSWORD");
    return { url: opts.server.replace(/\/+$/, ""), password };
  }
  const stateDir = runOpencode(["debug", "paths", "state"]).trim();
  const service = readJson(join(stateDir, "service.json"), null);
  if (!service?.url || !service?.password) {
    throw new Error("OpenCode background service not found. Start it with `opencode service start`.");
  }
  return { url: service.url, password: opts.password ?? service.password };
}

function client(endpoint) {
  const headers = {
    Authorization: `Basic ${Buffer.from(`opencode:${endpoint.password}`).toString("base64")}`,
    "Content-Type": "application/json",
  };
  async function call(method, path, body, { allow = [] } = {}) {
    const response = await fetch(endpoint.url + path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const text = await response.text();
    if (!response.ok && !allow.includes(response.status)) {
      throw new Error(`${method} ${path.split("?")[0]} -> HTTP ${response.status} ${text.slice(0, 200)}`);
    }
    return { status: response.status, body: text ? JSON.parse(text) : null };
  }
  return {
    async info() {
      return (await call("GET", "/api/info")).body;
    },
    async listSessions() {
      const out = [];
      let path = "/api/session?limit=100&order=desc";
      for (let page = 0; page < 1000; page++) {
        const { body } = await call("GET", path);
        out.push(...body.data);
        const next = body.cursor?.next;
        if (!next || body.data.length === 0) break;
        path = `/api/session?limit=100&cursor=${encodeURIComponent(next)}`;
      }
      return out;
    },
    async active() {
      return new Set(Object.keys((await call("GET", "/api/session/active")).body.data ?? {}));
    },
    async projects() {
      return (await call("GET", "/api/project")).body.map((p) => p.canonical).filter(Boolean);
    },
    async session(id) {
      const r = await call("GET", `/api/session/${id}`, undefined, { allow: [404] });
      return r.status === 404 ? null : r.body.data;
    },
    async exportSession(id) {
      return (await call("GET", `/api/experimental/session/${id}/export`)).body.data;
    },
    async importSession(transcript, directory) {
      const info = { ...transcript.info, location: { directory } };
      const r = await call(
        "POST",
        "/api/experimental/session/import",
        { info, messages: transcript.messages, location: { directory } },
        { allow: [409] },
      );
      return r.status === 409 ? "exists" : "imported";
    },
    async deleteSession(id) {
      await call("DELETE", `/api/session/${id}`, undefined, { allow: [404] });
    },
    async patchSession(id, patch) {
      await call("PATCH", `/api/session/${id}`, patch);
    },
  };
}

// ---------- shared folder layout ----------

function layout(opts) {
  const root = join(opts.dir, ROOT_NAME);
  const nodeDir = (n) => join(root, "nodes", n);
  return {
    root,
    nodeDir,
    manifest: (n) => join(nodeDir(n), "manifest.json"),
    sessionFile: (n, id, hash) => join(nodeDir(n), "sessions", id, `${hash.slice(0, 32)}.json.gz`),
    sessionDir: (n, id) => join(nodeDir(n), "sessions", id),
    conflicts: (n) => join(nodeDir(n), "conflicts.jsonl"),
  };
}

function peerNodes(paths, self) {
  const dir = join(paths.root, "nodes");
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true })
    .filter((d) => d.isDirectory() && d.name !== self && existsSync(paths.manifest(d.name)))
    .map((d) => d.name);
}

function readPeerTranscript(paths, peer, id, entry) {
  const file = paths.sessionFile(peer, id, entry.hash);
  if (!existsSync(file)) return { error: "peer file not synced yet" };
  let doc;
  try {
    doc = JSON.parse(gunzipSync(readFileSync(file)).toString("utf8"));
  } catch {
    return { error: "peer file incomplete (still syncing?)" };
  }
  const summary = summarize(doc.transcript);
  if (summary.hash !== entry.hash || doc.transcript.info.id !== id) return { error: "peer file hash mismatch" };
  return { transcript: doc.transcript, summary };
}

// ---------- main ----------

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    console.log(HELP);
    return 0;
  }

  const paths = layout(opts);
  const localDir = join(opts.stateDir, opts.node);
  const statePath = join(localDir, "state.json");
  const backupDir = join(localDir, "backup");
  if (opts.execute) acquireLock(localDir);

  const oc = client(serviceEndpoint(opts));
  const info = await oc.info();
  const state = readJson(statePath, { node: opts.node, sessions: {} });
  if (state.node !== opts.node) throw new Error(`State at ${statePath} belongs to node ${state.node}`);

  const ownManifest = readJson(paths.manifest(opts.node), null);
  if (ownManifest && ownManifest.host !== hostname()) {
    throw new Error(
      `Node "${opts.node}" in the shared folder was written by host "${ownManifest.host}". ` +
        "Each machine needs its own --node name.",
    );
  }

  const peers = peerNodes(paths, opts.node);
  if (peers.length > 1) throw new Error(`Only two nodes are supported; found peers: ${peers.join(", ")}`);
  const peer = peers[0] ?? null;
  if (peer && opts.priority !== opts.node && opts.priority !== peer) {
    throw new Error(`--priority ${opts.priority} is neither this node (${opts.node}) nor the peer (${peer})`);
  }
  const isPriority = opts.priority === opts.node;
  const peerManifest = peer ? readJson(paths.manifest(peer), null) : null;
  if (peerManifest && peerManifest.format !== FORMAT) throw new Error(`Unsupported peer manifest format ${peerManifest.format}`);
  const peerSessions = peerManifest?.sessions ?? {};

  console.log(`\n  ${opts.execute ? "EXECUTE" : "DRY RUN (add --execute to apply)"}`);
  console.log(`  OpenCode ${info.version} | node ${opts.node}${isPriority ? " (priority)" : ""} | peer ${peer ?? "none yet"}`);

  const localList = await oc.listSessions();
  const active = await oc.active();
  const localProjects = await oc.projects();
  const local = new Map(localList.map((s) => [s.id, s]));
  const parentOf = (id) => local.get(id)?.parentID ?? peerSessions[id]?.parentID;

  let ids = [...new Set([...local.keys(), ...Object.keys(peerSessions)])];
  if (opts.session) ids = ids.filter((id) => id === opts.session);
  ids = parentsFirst(ids, parentOf);

  const counts = {};
  const deferred = [];
  const exported = new Map();

  async function localTranscript(id) {
    if (!exported.has(id)) exported.set(id, await oc.exportSession(id));
    return exported.get(id);
  }

  async function localHashOf(session) {
    const st = state.sessions[session.id];
    if (st?.localHash && st.localUpdated === session.time.updated) return st.localHash;
    return summarize(await localTranscript(session.id)).hash;
  }

  function descendants(id) {
    const out = [];
    const walk = (p) => {
      for (const s of local.values()) if (s.parentID === p) {
        out.push(s.id);
        walk(s.id);
      }
    };
    walk(id);
    return out;
  }

  function backup(id, transcripts) {
    const dir = join(backupDir, id);
    mkdirSync(dir, { recursive: true });
    const file = join(dir, `${new Date().toISOString().replace(/[:.]/g, "-")}.json.gz`);
    writeAtomic(file, gzipSync(JSON.stringify(transcripts)));
    return file;
  }

  async function refreshLocal(id) {
    exported.delete(id);
    const s = await oc.session(id);
    if (s) local.set(id, s);
    else local.delete(id);
    return s;
  }

  async function alignMeta(id, meta) {
    const t = await localTranscript(id);
    const patch = {};
    if ((t.info.title ?? "") !== meta.title) patch.title = meta.title;
    if (Boolean(t.info.time?.archived) !== meta.archived) patch.archived = meta.archived;
    if (Object.keys(patch).length) {
      await oc.patchSession(id, patch);
      await refreshLocal(id);
    }
  }

  // Replace a local session with the peer transcript; children are preserved and restored on failure.
  async function replaceLocal(id, peerTranscript, directory) {
    const kids = descendants(id);
    if ([id, ...kids].some((k) => active.has(k))) return "deferred: session or child is running";
    const own = await localTranscript(id);
    const kidTranscripts = [];
    for (const k of kids) kidTranscripts.push(await localTranscript(k));
    const file = backup(id, { session: own, children: kidTranscripts });
    const current = await oc.session(id);
    if (!current || current.time.updated !== local.get(id).time.updated) return "deferred: changed during sync";

    await oc.deleteSession(id);
    try {
      await oc.importSession(peerTranscript, directory);
    } catch (error) {
      await oc.importSession(own, own.info.location?.directory ?? directory);
      for (const k of kidTranscripts) await oc.importSession(k, k.info.location?.directory ?? directory);
      throw new Error(`import failed, local version restored: ${error.message}`);
    }
    const failedKids = [];
    for (const k of kidTranscripts) {
      try {
        await oc.importSession(k, k.info.location?.directory ?? directory);
      } catch {
        failedKids.push(k.info.id);
      }
    }
    if (failedKids.length) throw new Error(`children not restored (backup: ${file}): ${failedKids.join(", ")}`);
    return null;
  }

  function logConflict(record) {
    if (!opts.execute) return;
    mkdirSync(paths.nodeDir(opts.node), { recursive: true });
    const line = `${JSON.stringify({ at: new Date().toISOString(), node: opts.node, ...record })}\n`;
    writeFileSync(paths.conflicts(opts.node), line, { flag: "a" });
  }

  for (const id of ids) {
    const session = local.get(id);
    const entry = peerSessions[id] ?? null;
    const st = state.sessions[id];
    const label = (session?.title ?? entry?.title ?? id).slice(0, 50);

    try {
      if (session && active.has(id)) {
        deferred.push(id);
        console.log(`  defer        ${label}: running`);
        continue;
      }
      const localHash = session ? await localHashOf(session) : null;
      let localSummary = null;
      let peerData = null;
      const needsPeer = entry && entry.hash !== localHash && st?.seenPeer !== entry.hash;
      if (needsPeer) {
        peerData = readPeerTranscript(paths, peer, id, entry);
        if (peerData.error) {
          deferred.push(id);
          console.log(`  defer        ${label}: ${peerData.error}`);
          continue;
        }
        if (session) localSummary = summarize(await localTranscript(id));
      }

      const decision = decide({
        localHash,
        localSummary,
        peer: entry,
        peerSummary: peerData?.summary,
        state: st,
        isPriority,
      });
      counts[decision.action] = (counts[decision.action] ?? 0) + 1;
      if (!["keep", "none"].includes(decision.action) || !opts.execute) {
        if (decision.action !== "none") console.log(`  ${decision.action.padEnd(12)} ${label}: ${decision.reason}`);
      }
      if (!opts.execute) continue;

      const next = { ...(st ?? {}), known: true };
      const peerDir = () => {
        const m = mapDirectory(entry.directory ?? peerData.transcript.info.location?.directory, {
          maps: opts.maps,
          localProjects,
        });
        if (!m.mapped) console.log(`               warning: no local path for ${m.directory}; imported as-is`);
        return m.directory;
      };
      const parentMissing = () => entry?.parentID && !local.has(entry.parentID);

      switch (decision.action) {
        case "none":
        case "keep":
          break;
        case "skip-deleted":
          state.sessions[id] = { ...next, deleted: true, seenPeer: entry?.hash };
          continue;
        case "seen":
          next.basedOn = entry.hash;
          next.overrides = null;
          break;
        case "override":
          next.overrides = entry.hash;
          logConflict({ session: id, title: label, winner: opts.node, discarded: entry.hash, kept: localHash });
          break;
        case "import": {
          if (parentMissing()) {
            deferred.push(id);
            console.log(`               deferred: parent ${entry.parentID} not present`);
            continue;
          }
          await oc.importSession(peerData.transcript, peerDir());
          const s = await refreshLocal(id);
          if (s) await alignMeta(id, peerData.summary.meta);
          next.basedOn = entry.hash;
          next.overrides = null;
          break;
        }
        case "apply-meta":
          await alignMeta(id, peerData.summary.meta);
          next.basedOn = entry.hash;
          next.overrides = null;
          break;
        case "copy-apply":
        case "apply": {
          if (decision.action === "copy-apply") {
            const own = await localTranscript(id);
            const copy = conflictCopy(own, opts.node, entry.hash);
            await oc.importSession(copy, own.info.location?.directory ?? peerDir());
            logConflict({ session: id, title: label, winner: peer, copy: copy.info.id, discarded: localHash });
            console.log(`               local version kept as "${copy.info.title.slice(0, 60)}" (${copy.info.id})`);
          }
          const directory = session.location?.directory ?? peerDir();
          const problem = await replaceLocal(id, peerData.transcript, directory);
          if (problem) {
            deferred.push(id);
            console.log(`               ${problem}`);
            continue;
          }
          await refreshLocal(id);
          await alignMeta(id, peerData.summary.meta);
          next.basedOn = entry.hash;
          next.overrides = null;
          break;
        }
        default:
          throw new Error(`unknown action ${decision.action}`);
      }
      if (entry) next.seenPeer = entry.hash;
      state.sessions[id] = next;
    } catch (error) {
      deferred.push(id);
      counts.error = (counts.error ?? 0) + 1;
      console.log(`  ERROR        ${label}: ${error.message}`);
    }
  }

  if (opts.execute) {
    // Refresh the local view (imports and conflict copies created new sessions) and publish.
    const finalList = await oc.listSessions();
    const finalActive = await oc.active();
    local.clear();
    for (const s of finalList) local.set(s.id, s);
    const manifest = { format: FORMAT, node: opts.node, host: hostname(), opencode: info.version, sessions: {} };
    let published = 0;

    for (const [id, entry] of Object.entries(ownManifest?.sessions ?? {})) {
      if (opts.session || finalActive.has(id) || deferred.includes(id)) manifest.sessions[id] = entry;
    }
    for (const s of finalList) {
      if (opts.session && s.id !== opts.session) continue;
      if (finalActive.has(s.id) || deferred.includes(s.id)) continue;
      try {
        const st = (state.sessions[s.id] ??= { known: true });
        const previous = ownManifest?.sessions?.[s.id];
        if (
          previous &&
          st.localHash === previous.hash &&
          st.localUpdated === s.time.updated &&
          (st.basedOn ?? null) === previous.basedOn &&
          (st.overrides ?? null) === previous.overrides &&
          existsSync(paths.sessionFile(opts.node, s.id, previous.hash))
        ) {
          manifest.sessions[s.id] = previous;
          continue;
        }
        exported.delete(s.id);
        const transcript = await oc.exportSession(s.id);
        const sum = summarize(transcript);
        const file = paths.sessionFile(opts.node, s.id, sum.hash);
        if (!existsSync(file)) {
          mkdirSync(paths.sessionDir(opts.node, s.id), { recursive: true });
          const doc = { format: FORMAT, node: opts.node, hash: sum.hash, exportedAt: Date.now(), transcript };
          writeAtomic(file, gzipSync(JSON.stringify(doc)));
          published++;
        }
        Object.assign(st, { known: true, localHash: sum.hash, localUpdated: s.time.updated });
        manifest.sessions[s.id] = {
          hash: sum.hash,
          basedOn: st.basedOn ?? null,
          overrides: st.overrides ?? null,
          parentID: s.parentID ?? null,
          title: s.title ?? "",
          directory: s.location?.directory ?? null,
          messages: sum.messages.length,
          updated: s.time.updated,
        };
      } catch (error) {
        console.log(`  ERROR        publish ${s.id}: ${error.message}`);
      }
    }

    // Keep the current and the previous version of each session file.
    for (const [id, entry] of Object.entries(manifest.sessions)) {
      const dir = paths.sessionDir(opts.node, id);
      if (!existsSync(dir)) continue;
      const keep = new Set([`${entry.hash.slice(0, 32)}.json.gz`]);
      const prev = ownManifest?.sessions?.[id]?.hash;
      if (prev) keep.add(`${prev.slice(0, 32)}.json.gz`);
      for (const f of readdirSync(dir)) if (!keep.has(f)) rmSync(join(dir, f), { force: true });
    }

    mkdirSync(paths.nodeDir(opts.node), { recursive: true });
    const before = JSON.stringify(ownManifest?.sessions ?? null);
    if (before !== JSON.stringify(manifest.sessions) || !ownManifest) {
      writeAtomic(paths.manifest(opts.node), JSON.stringify({ ...manifest, generatedAt: Date.now() }, null, 2));
    }
    mkdirSync(localDir, { recursive: true });
    writeAtomic(statePath, JSON.stringify(state, null, 2));
    console.log(`\n  Published ${published} new session version(s) to ${paths.nodeDir(opts.node)}`);
  }

  const summaryLine = Object.entries(counts)
    .map(([k, v]) => `${k}=${v}`)
    .join(" ");
  console.log(`  Sessions: ${ids.length} | ${summaryLine || "nothing to do"}${deferred.length ? ` | deferred=${deferred.length}` : ""}\n`);
  return counts.error ? 1 : 0;
}

main().then(
  (code) => process.exit(code),
  (error) => {
    console.error(`\n  ERROR: ${error.message}\n`);
    process.exit(2);
  },
);
