// Pure mapping from OpenCode V2 session/message API objects to OpenSync sync payloads.
// Text-only policy: user prompts and assistant text are sent; tool calls are reduced to
// their names; reasoning, tool input/output, shell, system and synthetic messages are dropped.

export const MAX_TEXT_CHARS = 200_000;

const REDACTIONS = [
  [/-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g, "[REDACTED_PRIVATE_KEY]"],
  [/\bosk_[A-Za-z0-9_-]{8,}/g, "[REDACTED_OPENSYNC_KEY]"],
  [/\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/g, "[REDACTED_AWS_KEY_ID]"],
  [/\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}/g, "[REDACTED_GITHUB_TOKEN]"],
  [/\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}/g, "[REDACTED_API_KEY]"],
  [/\bxox[abposr]-[A-Za-z0-9-]{10,}/g, "[REDACTED_SLACK_TOKEN]"],
  [/(\bBearer\s+)[A-Za-z0-9._~+\/-]{16,}=*/gi, "$1[REDACTED]"],
  [/(\/auth\/connect\/)[A-Za-z0-9_-]+/g, "$1[REDACTED]"],
  [/((?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*)["']?[^\s"']{6,}/gi, "$1[REDACTED]"],
];

export function redact(text) {
  let out = text;
  for (const [pattern, replacement] of REDACTIONS) out = out.replace(pattern, replacement);
  return out;
}

function prepareText(text) {
  const clean = redact(text);
  if (clean.length <= MAX_TEXT_CHARS) return clean;
  return `${clean.slice(0, MAX_TEXT_CHARS)}\n[TRUNCATED by opensync_import: ${clean.length - MAX_TEXT_CHARS} chars omitted]`;
}

export function projectName(directory) {
  if (!directory) return undefined;
  const parts = directory.split(/[\\/]+/).filter(Boolean);
  return parts.at(-1);
}

export function mapSession(session) {
  const directory = session.location?.directory;
  const payload = {
    externalId: session.id,
    source: "opencode",
    title: session.title || "Untitled",
    model: session.model?.id,
    provider: session.model?.providerID,
    projectPath: directory,
    projectName: projectName(directory),
    promptTokens: session.tokens?.input ?? 0,
    completionTokens: session.tokens?.output ?? 0,
    cost: session.cost ?? 0,
    createdAt: session.time?.created,
  };
  return Object.fromEntries(Object.entries(payload).filter(([, v]) => v !== undefined));
}

// Returns an OpenSync message payload, or null when the message is excluded by policy.
export function mapMessage(sessionID, message) {
  if (message.type === "user") {
    const text = (message.text ?? "").trim();
    if (!text) return null;
    const content = prepareText(text);
    return {
      sessionExternalId: sessionID,
      externalId: message.id,
      role: "user",
      textContent: content,
      parts: [{ type: "text", content }],
    };
  }

  if (message.type === "assistant") {
    const blocks = Array.isArray(message.content) ? message.content : [];
    const text = blocks
      .filter((b) => b.type === "text" && b.text)
      .map((b) => b.text)
      .join("\n")
      .trim();
    const tools = blocks.filter((b) => b.type === "tool" && b.name).map((b) => b.name);
    if (!text && tools.length === 0) return null;

    const parts = [];
    let content = "";
    if (text) {
      content = prepareText(text);
      parts.push({ type: "text", content });
    }
    for (const toolName of tools) parts.push({ type: "tool-call", content: { toolName } });

    const payload = {
      sessionExternalId: sessionID,
      externalId: message.id,
      role: "assistant",
      textContent: content,
      parts,
      model: message.model?.id,
      promptTokens: message.tokens?.input,
      completionTokens: message.tokens?.output,
      durationMs:
        message.time?.completed && message.time?.created
          ? message.time.completed - message.time.created
          : undefined,
    };
    return Object.fromEntries(Object.entries(payload).filter(([, v]) => v !== undefined));
  }

  return null;
}

// Split payloads into batches bounded by item count and serialized size.
export function chunk(items, { maxItems = 50, maxBytes = 512_000 } = {}) {
  const batches = [];
  let current = [];
  let size = 0;
  for (const item of items) {
    const itemSize = Buffer.byteLength(JSON.stringify(item));
    if (current.length > 0 && (current.length >= maxItems || size + itemSize > maxBytes)) {
      batches.push(current);
      current = [];
      size = 0;
    }
    current.push(item);
    size += itemSize;
  }
  if (current.length > 0) batches.push(current);
  return batches;
}
