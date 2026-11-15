// Conflict Detection and Resolution (CDR) for two-node OpenCode session replication.
// Pure functions without I/O; sync.mjs supplies the inputs and executes the decision.

import { createHash } from "node:crypto";

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((k) => [k, canonical(value[k])]),
    );
  }
  return value;
}

export function sha256(value) {
  return createHash("sha256").update(typeof value === "string" ? value : JSON.stringify(canonical(value))).digest("hex");
}

// OpenCode drops `time.firstToken` on import; exclude it so a session hashes the same on both nodes.
function normalizeMessage(message) {
  const copy = structuredClone(message);
  if (copy.time) delete copy.time.firstToken;
  return copy;
}

// Replicated content of a session: ordered messages + title + archived flag.
// Location, project ID and timestamps are node-local and not part of the hash.
export function summarize(transcript) {
  const messages = transcript.messages.map((m) => [m.id, sha256(normalizeMessage(m))]);
  const meta = { title: transcript.info.title ?? "", archived: Boolean(transcript.info.time?.archived) };
  return { hash: sha256({ meta, messages }), meta, messages };
}

// Relationship of the local transcript to the peer transcript at message level.
export function relation(local, peer) {
  const a = local.messages;
  const b = peer.messages;
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) {
    if (a[i][0] !== b[i][0] || a[i][1] !== b[i][1]) return "diverged";
  }
  if (a.length === b.length) {
    const sameMeta = local.meta.title === peer.meta.title && local.meta.archived === peer.meta.archived;
    return sameMeta ? "equal" : "meta-diff";
  }
  return a.length < b.length ? "local-prefix" : "peer-prefix";
}

/**
 * Decide what to do with one session on this node.
 *
 * Inputs
 *   localHash    effective hash of the local session, or null when it does not exist locally
 *   localSummary summary of the local transcript (needed only when the peer version is new)
 *   peer         peer manifest entry { hash, basedOn, overrides } or null
 *   peerSummary  summary of the peer transcript (needed only when the peer version is new)
 *   state        this node's replication state for the session, or undefined
 *   isPriority   true on the node that wins concurrent changes
 *
 * Version vector in the manifest entry:
 *   basedOn   the peer version this node's current version was built on (it contains it)
 *   overrides the peer version this node discarded when it won a conflict
 *
 * Actions
 *   none          nothing to do
 *   keep          keep local; peer has nothing new
 *   seen          keep local; it already contains the peer version (record basedOn)
 *   import        new on the peer: import it
 *   apply         replace local with the peer version (fast-forward or peer rewrite of a shared version)
 *   apply-meta    only title/archived differ: patch local metadata from the peer
 *   copy-apply    conflict lost: save local as a "[conflict]" copy, then apply the peer version
 *   override      conflict won: keep local and record that it overrides the peer version
 *   skip-deleted  deleted on this node; deletions are not replicated, so do not restore it
 */
export function decide({ localHash, localSummary, peer, peerSummary, state, isPriority }) {
  if (!localHash && !peer) return { action: "none", reason: "absent on both nodes" };
  if (!localHash) {
    if (state?.known) return { action: "skip-deleted", reason: "deleted on this node (not replicated)" };
    return { action: "import", reason: "new on peer" };
  }
  if (!peer) return { action: "keep", reason: "not on peer yet" };
  if (peer.hash === localHash) return { action: "seen", reason: "identical" };
  if (state?.seenPeer === peer.hash) return { action: "keep", reason: "peer unchanged since last sync" };
  if (!localSummary || !peerSummary) throw new Error("localSummary and peerSummary are required");

  const rel = relation(localSummary, peerSummary);
  const result = (action, reason) => {
    if (rel === "meta-diff" && (action === "apply" || action === "copy-apply")) {
      return { action: "apply-meta", reason };
    }
    return { action, reason };
  };

  if (rel === "equal") return { action: "seen", reason: "same content" };
  if (peer.overrides && peer.overrides === localHash) {
    if (rel === "local-prefix") return result("apply", "priority peer won and contains local");
    return result("copy-apply", "priority peer overrode the local version");
  }
  if (peer.basedOn && peer.basedOn === localHash) {
    return result("apply", "peer changed the version it received from this node");
  }
  if (rel === "local-prefix") return { action: "apply", reason: "peer extends local (fast-forward)" };
  if (rel === "peer-prefix") return { action: "seen", reason: "local extends peer" };

  return isPriority
    ? { action: "override", reason: `concurrent ${rel === "meta-diff" ? "title/archive" : "message"} changes, this node has priority` }
    : result("copy-apply", "concurrent message changes, peer has priority");
}

// Deterministic replacement ID for a conflict copy: keep the time-sortable prefix, replace the tail.
export function conflictId(id, salt) {
  const tail = createHash("sha256").update(`${id}:${salt}`).digest("base64url").replace(/[^A-Za-z0-9]/g, "x").slice(0, 10);
  return id.slice(0, Math.max(4, id.length - 10)) + tail;
}

export function conflictCopy(transcript, node, salt) {
  const info = structuredClone(transcript.info);
  info.id = conflictId(info.id, salt);
  info.title = `[conflict ${node}] ${info.title ?? "Untitled"}`;
  delete info.parentID;
  delete info.fork;
  const messages = transcript.messages.map((m) => ({ ...structuredClone(m), id: conflictId(m.id, salt) }));
  return { info, messages };
}

// Order session IDs so that parents come before their children.
export function parentsFirst(ids, parentOf) {
  const set = new Set(ids);
  const done = new Set();
  const out = [];
  const visit = (id, depth) => {
    if (done.has(id) || depth > 64) return;
    const parent = parentOf(id);
    if (parent && set.has(parent)) visit(parent, depth + 1);
    done.add(id);
    out.push(id);
  };
  for (const id of [...ids].sort()) visit(id, 0);
  return out;
}

// Map a peer project directory to the local equivalent.
export function mapDirectory(directory, { maps = [], localProjects = [] } = {}) {
  if (!directory) return { directory, mapped: false };
  const norm = (p) => p.replace(/\\/g, "/").replace(/\/+$/, "");
  const fold = (p) => norm(p).toLowerCase();
  for (const [from, to] of maps) {
    const f = fold(from);
    const d = fold(directory);
    if (d === f || d.startsWith(`${f}/`)) {
      const rest = norm(directory).slice(norm(from).length).replace(/^\//, "");
      const sep = to.includes("\\") ? "\\" : "/";
      return { directory: rest ? `${to.replace(/[\\/]+$/, "")}${sep}${rest.split("/").join(sep)}` : to, mapped: true };
    }
  }
  const base = norm(directory).split("/").pop()?.toLowerCase();
  const matches = localProjects.filter((p) => norm(p).split("/").pop()?.toLowerCase() === base);
  if (matches.length === 1) return { directory: matches[0], mapped: true };
  return { directory, mapped: false };
}
