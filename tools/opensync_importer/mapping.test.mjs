import assert from "node:assert/strict";
import { test } from "node:test";
import { chunk, mapMessage, mapSession, MAX_TEXT_CHARS, redact } from "./mapping.mjs";

const session = {
  id: "ses_1",
  title: "Fix login",
  model: { id: "claude", providerID: "bedrock-local" },
  tokens: { input: 10, output: 5, reasoning: 0, cache: { read: 0, write: 0 } },
  cost: 0.5,
  time: { created: 1000, updated: 2000 },
  location: { directory: "C:\\Github\\CherryStock" },
};

test("session maps to OpenSync session payload", () => {
  assert.deepEqual(mapSession(session), {
    externalId: "ses_1",
    source: "opencode",
    title: "Fix login",
    model: "claude",
    provider: "bedrock-local",
    projectPath: "C:\\Github\\CherryStock",
    projectName: "CherryStock",
    promptTokens: 10,
    completionTokens: 5,
    cost: 0.5,
    createdAt: 1000,
  });
});

test("user message keeps text", () => {
  const m = mapMessage("ses_1", { id: "m1", type: "user", text: "hello", time: { created: 1 } });
  assert.equal(m.role, "user");
  assert.equal(m.textContent, "hello");
  assert.deepEqual(m.parts, [{ type: "text", content: "hello" }]);
});

test("assistant drops reasoning and tool input/output, keeps tool name", () => {
  const m = mapMessage("ses_1", {
    id: "m2",
    type: "assistant",
    model: { id: "claude", providerID: "x" },
    tokens: { input: 3, output: 4 },
    time: { created: 10, completed: 25 },
    content: [
      { type: "reasoning", text: "SECRET THINKING" },
      { type: "tool", id: "t", name: "shell", state: { status: "completed", input: { command: "cat .env" }, content: [{ type: "text", text: "TOOL OUTPUT" }] } },
      { type: "text", text: "Done." },
    ],
  });
  const serialized = JSON.stringify(m);
  assert.ok(!serialized.includes("SECRET THINKING"));
  assert.ok(!serialized.includes("cat .env"));
  assert.ok(!serialized.includes("TOOL OUTPUT"));
  assert.deepEqual(m.parts, [
    { type: "text", content: "Done." },
    { type: "tool-call", content: { toolName: "shell" } },
  ]);
  assert.equal(m.durationMs, 15);
  assert.equal(m.completionTokens, 4);
});

test("non-conversation messages are excluded", () => {
  for (const type of ["system", "synthetic", "shell", "skill", "idle", "compaction", "agent-switched"]) {
    assert.equal(mapMessage("ses_1", { id: "x", type, text: "instructions", time: { created: 1 } }), null);
  }
  assert.equal(mapMessage("ses_1", { id: "x", type: "user", text: "  " }), null);
  assert.equal(mapMessage("ses_1", { id: "x", type: "assistant", content: [{ type: "reasoning", text: "r" }] }), null);
});

test("secrets are redacted", () => {
  const text = redact(
    "key osk_ViK2abcdefghijklUcYf and AKIAABCDEFGHIJKLMNOP and ghp_abcdefghijklmnopqrstuvwxyz0123 " +
      "and https://x.opentunnel.xyz/auth/connect/Bz3zFin5ZlSdYt and password=hunter2secret",
  );
  for (const leaked of ["ViK2abcdefghijkl", "AKIAABCDEFGHIJKLMNOP", "ghp_abcdef", "Bz3zFin5ZlSdYt", "hunter2secret"]) {
    assert.ok(!text.includes(leaked), leaked);
  }
});

test("long text is truncated", () => {
  const m = mapMessage("ses_1", { id: "m", type: "user", text: "a".repeat(MAX_TEXT_CHARS + 10) });
  assert.ok(m.textContent.length < MAX_TEXT_CHARS + 100);
  assert.match(m.textContent, /TRUNCATED/);
});

test("chunk respects item and byte limits", () => {
  const items = Array.from({ length: 7 }, (_, i) => ({ i }));
  assert.deepEqual(chunk(items, { maxItems: 3 }).map((b) => b.length), [3, 3, 1]);
  const big = [{ t: "x".repeat(100) }, { t: "x".repeat(100) }];
  assert.equal(chunk(big, { maxBytes: 150 }).length, 2);
});
