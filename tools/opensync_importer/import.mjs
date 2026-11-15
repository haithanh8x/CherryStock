#!/usr/bin/env node
// Import OpenCode V2 session history into OpenSync.
// Reads sessions through the OpenCode V2 HTTP API (`opencode api`), never the SQLite file.
// Default mode is a dry run; pass --send to upload.

import { execFileSync } from "node:child_process";
import {
  closeSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  openSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";
import { chunk, mapMessage, mapSession } from "./mapping.mjs";

const STATE_DIR = join(homedir(), ".opensync");
const CREDENTIALS_FILE = join(STATE_DIR, "credentials.json");
const STATE_FILE = join(STATE_DIR, "opencode-v2-import-state.json");

function parseArgs(argv) {
  const opts = { send: false, all: false, includeChildren: false, session: null, limit: null };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--send") opts.send = true;
    else if (arg === "--all") opts.all = true;
    else if (arg === "--include-children") opts.includeChildren = true;
    else if (arg === "--session") opts.session = argv[++i];
    else if (arg === "--limit") opts.limit = Number(argv[++i]);
    else if (arg === "-h" || arg === "--help") opts.help = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  if (opts.limit !== null && !(Number.isInteger(opts.limit) && opts.limit > 0)) {
    throw new Error("--limit must be a positive integer");
  }
  return opts;
}

const HELP = `
  OpenCode V2 -> OpenSync importer

  Usage: node tools/opensync_importer/import.mjs [options]

  Without --send this is a dry run: it reads local sessions and prints what would be
  uploaded. Nothing is sent.

  Options:
    --send               Upload to OpenSync
    --all                Ignore local import state and re-send every session (upsert, safe)
    --session <id>       Only this session
    --limit <n>          At most n sessions (newest first)
    --include-children   Also include subagent (child) sessions
`;

// `opencode api` can truncate large responses written to a pipe, so stdout goes to a temp file.
const OUTPUT_DIR = mkdtempSync(join(tmpdir(), "opensync-import-"));
const OUTPUT_FILE = join(OUTPUT_DIR, "response.json");
process.on("exit", () => rmSync(OUTPUT_DIR, { recursive: true, force: true }));

function runOpencode(args, shell) {
  const fd = openSync(OUTPUT_FILE, "w");
  try {
    execFileSync("opencode", args, { stdio: ["ignore", fd, "pipe"], shell });
  } finally {
    closeSync(fd);
  }
}

function opencodeGet(path) {
  const args = ["api", "get", path];
  const label = path.split("?")[0];
  try {
    runOpencode(args, false);
  } catch (error) {
    if (error.code === "ENOENT" && process.platform === "win32") {
      runOpencode(args, true);
    } else {
      const detail = error.stderr ? String(error.stderr).trim().split("\n").slice(-3).join(" ") : error.message;
      throw new Error(`opencode api get ${label} failed: ${detail}`);
    }
  }
  try {
    return JSON.parse(readFileSync(OUTPUT_FILE, "utf8"));
  } catch {
    throw new Error(`opencode api get ${label} returned non-JSON output`);
  }
}

function* paginate(firstPath, nextPath) {
  let page = opencodeGet(firstPath);
  while (true) {
    yield* page.data;
    const cursor = page.cursor?.next;
    if (!cursor || page.data.length === 0) return;
    page = opencodeGet(nextPath(cursor));
  }
}

function listSessions(opts) {
  if (opts.session) {
    return [opencodeGet(`/api/session/${encodeURIComponent(opts.session)}`).data];
  }
  const filter = opts.includeChildren ? "" : "&parentID=null";
  const sessions = [];
  for (const s of paginate(
    `/api/session?limit=100&order=desc${filter}`,
    (c) => `/api/session?limit=100&cursor=${encodeURIComponent(c)}`,
  )) {
    sessions.push(s);
    if (opts.limit && sessions.length >= opts.limit) break;
  }
  return sessions;
}

function listMessages(sessionID) {
  const base = `/api/session/${encodeURIComponent(sessionID)}/message`;
  return [...paginate(`${base}?limit=200&order=asc`, (c) => `${base}?limit=200&cursor=${encodeURIComponent(c)}`)];
}

function loadCredentials() {
  const envKey = process.env.OPENSYNC_API_KEY;
  const envUrl = process.env.OPENSYNC_URL;
  let file = {};
  if (existsSync(CREDENTIALS_FILE)) file = JSON.parse(readFileSync(CREDENTIALS_FILE, "utf8"));
  const apiKey = envKey || file.apiKey;
  const rawUrl = envUrl || file.convexUrl;
  if (!apiKey || !rawUrl) {
    throw new Error("OpenSync credentials missing: run `opencode-sync login` or set OPENSYNC_API_KEY and OPENSYNC_URL");
  }
  const baseUrl = rawUrl.replace(".convex.cloud", ".convex.site").replace(/\/+$/, "");
  return { apiKey, baseUrl };
}

function loadState() {
  if (!existsSync(STATE_FILE)) return { sessions: {} };
  const state = JSON.parse(readFileSync(STATE_FILE, "utf8"));
  return { sessions: state.sessions ?? {} };
}

function saveState(state) {
  mkdirSync(STATE_DIR, { recursive: true });
  writeFileSync(STATE_FILE, JSON.stringify({ ...state, lastRun: Date.now() }, null, 2), "utf8");
}

async function post(creds, path, body) {
  const delays = [1000, 3000, 9000];
  for (let attempt = 0; ; attempt++) {
    let response;
    try {
      response = await fetch(`${creds.baseUrl}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${creds.apiKey}` },
        body: JSON.stringify(body),
      });
    } catch (error) {
      if (attempt < delays.length) {
        await new Promise((r) => setTimeout(r, delays[attempt]));
        continue;
      }
      throw new Error(`POST ${path} network error: ${error.message}`);
    }
    if (response.ok) return response.json();
    const retryable = response.status === 429 || response.status >= 500;
    if (retryable && attempt < delays.length) {
      const retryAfter = Number(response.headers.get("retry-after"));
      await new Promise((r) => setTimeout(r, retryAfter > 0 ? retryAfter * 1000 : delays[attempt]));
      continue;
    }
    const text = (await response.text()).slice(0, 300);
    throw new Error(`POST ${path} failed: HTTP ${response.status} ${text}`);
  }
}

async function uploadSession(creds, sessionPayload, messagePayloads) {
  await post(creds, "/sync/session", sessionPayload);
  let sent = 0;
  for (const batch of chunk(messagePayloads)) {
    const result = await post(creds, "/sync/batch", { sessions: [], messages: batch });
    if (Array.isArray(result.errors) && result.errors.length > 0) {
      throw new Error(`batch rejected ${result.errors.length} item(s): ${JSON.stringify(result.errors).slice(0, 300)}`);
    }
    sent += batch.length;
  }
  return sent;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    console.log(HELP);
    return 0;
  }

  const creds = opts.send ? loadCredentials() : null;
  const state = loadState();
  const sessions = listSessions(opts);
  const pending = sessions.filter((s) => opts.all || opts.session || state.sessions[s.id] !== s.time?.updated);

  console.log(`\n  ${opts.send ? "Uploading" : "DRY RUN (use --send to upload)"}`);
  console.log(`  Local sessions: ${sessions.length}, to process: ${pending.length}\n`);

  let failures = 0;
  let totalMessages = 0;
  for (const session of pending) {
    const label = (session.title || session.id).slice(0, 60);
    try {
      const sessionPayload = mapSession(session);
      const messages = listMessages(session.id)
        .map((m) => mapMessage(session.id, m))
        .filter(Boolean);
      if (!opts.send) {
        console.log(`  [dry-run] ${label}: ${messages.length} messages`);
        totalMessages += messages.length;
        continue;
      }
      const sent = await uploadSession(creds, sessionPayload, messages);
      state.sessions[session.id] = session.time?.updated;
      saveState(state);
      totalMessages += sent;
      console.log(`  OK  ${label}: ${sent} messages`);
    } catch (error) {
      failures++;
      console.log(`  FAILED  ${label}: ${error.message}`);
    }
  }

  console.log(`\n  Sessions: ${pending.length - failures} ok, ${failures} failed; messages: ${totalMessages}\n`);
  return failures > 0 ? 1 : 0;
}

main().then(
  (code) => process.exit(code),
  (error) => {
    console.error(`\n  ERROR: ${error.message}\n`);
    process.exit(2);
  },
);
