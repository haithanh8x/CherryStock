import assert from "node:assert/strict";
import { test } from "node:test";
import { conflictCopy, conflictId, decide, mapDirectory, parentsFirst, relation, summarize } from "./cdr.mjs";

const msg = (id, text) => ({ id, type: "user", text, time: { created: 1 } });
const transcript = (messages, title = "t", archived = false) => ({
  info: { id: "ses_abc", title, time: { created: 1, updated: 2, ...(archived ? { archived: 3 } : {}) } },
  messages,
});
const S = (msgs, title, archived) => summarize(transcript(msgs, title, archived));

const base = [msg("m1", "a"), msg("m2", "b")];
const B = S(base);
const L3 = S([...base, msg("m3", "local")]);
const P4 = S([...base, msg("m4", "peer")]);

test("summary ignores node-local fields and firstToken", () => {
  const a = transcript([{ id: "m1", type: "assistant", time: { created: 1, firstToken: 5 }, content: [] }]);
  const b = structuredClone(a);
  delete b.messages[0].time.firstToken;
  b.info.location = { directory: "C:\\x" };
  b.info.projectID = "other";
  b.info.time.updated = 999;
  assert.equal(summarize(a).hash, summarize(b).hash);
  assert.notEqual(S(base, "x").hash, S(base, "y").hash);
});

test("relation", () => {
  assert.equal(relation(B, B), "equal");
  assert.equal(relation(B, L3), "local-prefix");
  assert.equal(relation(L3, B), "peer-prefix");
  assert.equal(relation(L3, P4), "diverged");
  assert.equal(relation(B, S(base, "renamed")), "meta-diff");
  assert.equal(relation(B, S([msg("m1", "a"), msg("m2", "edited")])), "diverged");
});

const peer = (summary, extra = {}) => ({ hash: summary.hash, basedOn: null, overrides: null, ...extra });

test("new / deleted / absent", () => {
  assert.equal(decide({ localHash: null, peer: peer(B), peerSummary: B }).action, "import");
  assert.equal(decide({ localHash: null, peer: peer(B), peerSummary: B, state: { known: true } }).action, "skip-deleted");
  assert.equal(decide({ localHash: B.hash, peer: null }).action, "keep");
});

test("identical or unchanged peer", () => {
  assert.equal(decide({ localHash: B.hash, peer: peer(B) }).action, "seen");
  assert.equal(decide({ localHash: L3.hash, peer: peer(B), state: { seenPeer: B.hash } }).action, "keep");
});

test("fast-forward and behind", () => {
  const args = { localHash: B.hash, localSummary: B, peer: peer(L3), peerSummary: L3 };
  assert.equal(decide({ ...args, isPriority: true }).action, "apply");
  assert.equal(decide({ localHash: L3.hash, localSummary: L3, peer: peer(B), peerSummary: B }).action, "seen");
});

test("concurrent message changes: priority node wins, other node keeps a conflict copy", () => {
  assert.equal(decide({ localHash: L3.hash, localSummary: L3, peer: peer(P4), peerSummary: P4, isPriority: true }).action, "override");
  assert.equal(decide({ localHash: L3.hash, localSummary: L3, peer: peer(P4), peerSummary: P4, isPriority: false }).action, "copy-apply");
});

test("priority peer override is applied on the other node", () => {
  const r = decide({
    localHash: L3.hash,
    localSummary: L3,
    peer: peer(P4, { overrides: L3.hash }),
    peerSummary: P4,
    isPriority: false,
  });
  assert.equal(r.action, "copy-apply");
});

test("peer rewrite of the shared version (revert/compaction) is applied, even on the priority node", () => {
  const rewritten = S([msg("m1", "a")]);
  const r = decide({
    localHash: B.hash,
    localSummary: B,
    peer: peer(S([msg("m1", "a"), msg("m9", "x")]), { basedOn: B.hash }),
    peerSummary: S([msg("m1", "a"), msg("m9", "x")]),
    isPriority: true,
  });
  assert.equal(r.action, "apply");
  assert.equal(relation(B, rewritten), "peer-prefix");
});

test("title-only conflicts use metadata actions", () => {
  const LT = S(base, "local title");
  const PT = S(base, "peer title");
  assert.equal(decide({ localHash: LT.hash, localSummary: LT, peer: peer(PT), peerSummary: PT, isPriority: true }).action, "override");
  assert.equal(decide({ localHash: LT.hash, localSummary: LT, peer: peer(PT), peerSummary: PT, isPriority: false }).action, "apply-meta");
  assert.equal(
    decide({ localHash: LT.hash, localSummary: LT, peer: peer(PT, { basedOn: LT.hash }), peerSummary: PT, isPriority: true }).action,
    "apply-meta",
  );
});

test("full two-node scenario converges", () => {
  // Both start from B (win published B, mac imported it).
  // Mac adds m3, Win adds m4 concurrently. Win (priority) syncs first.
  const winState = { seenPeer: null };
  const win = decide({ localHash: P4.hash, localSummary: P4, peer: peer(L3, { basedOn: B.hash }), peerSummary: L3, state: winState, isPriority: true });
  assert.equal(win.action, "override");
  // Win publishes P4 with overrides=L3. Mac syncs.
  const mac = decide({ localHash: L3.hash, localSummary: L3, peer: peer(P4, { basedOn: B.hash, overrides: L3.hash }), peerSummary: P4, isPriority: false });
  assert.equal(mac.action, "copy-apply");
  // Mac now has P4 and publishes it with basedOn=P4. Win sees an identical version.
  assert.equal(decide({ localHash: P4.hash, peer: peer(P4, { basedOn: P4.hash }), isPriority: true }).action, "seen");
});

test("conflict copy gets new deterministic ids and no parent", () => {
  const t = { info: { id: "ses_e4a21e3ddffefm5MLT74oe17GM", title: "x", parentID: "ses_p" }, messages: [msg("msg_1b5dfa261001SI7NDvjCUnIuRa", "a")] };
  const c = conflictCopy(t, "cherry-mac", "salt");
  assert.notEqual(c.info.id, t.info.id);
  assert.equal(c.info.id.length, t.info.id.length);
  assert.match(c.info.id, /^ses_[A-Za-z0-9]+$/);
  assert.equal(c.info.id, conflictId(t.info.id, "salt"));
  assert.equal(c.info.title, "[conflict cherry-mac] x");
  assert.equal(c.info.parentID, undefined);
  assert.notEqual(c.messages[0].id, t.messages[0].id);
  assert.equal(t.info.id, "ses_e4a21e3ddffefm5MLT74oe17GM");
});

test("parents are ordered before children", () => {
  const parents = { c: "p", g: "c" };
  assert.deepEqual(parentsFirst(["g", "c", "x", "p"], (id) => parents[id]), ["p", "c", "g", "x"]);
});

test("directory mapping", () => {
  const maps = [["/Users/blackeyes/CherryStock", "C:\\Github\\CherryStock"]];
  assert.deepEqual(mapDirectory("/Users/blackeyes/CherryStock", { maps }), { directory: "C:\\Github\\CherryStock", mapped: true });
  assert.deepEqual(mapDirectory("/Users/blackeyes/CherryStock/src", { maps }), { directory: "C:\\Github\\CherryStock\\src", mapped: true });
  assert.deepEqual(
    mapDirectory("C:\\Github\\CherryStock", { localProjects: ["/Users/blackeyes/CherryStock", "/Users/blackeyes"] }),
    { directory: "/Users/blackeyes/CherryStock", mapped: true },
  );
  assert.equal(mapDirectory("D:\\Other", { localProjects: ["/Users/blackeyes/CherryStock"] }).mapped, false);
});
