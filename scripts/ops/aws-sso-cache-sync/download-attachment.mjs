/**
 * Download a Confluence page attachment (for example cache.zip) through an already
 * running Chrome instance that exposes the DevTools protocol (--remote-debugging-port).
 *
 * The Chrome instance is expected to use the real user profile, so the existing
 * Atlassian session is reused. If the session is missing, the script waits for the
 * user to sign in inside the visible Chrome window.
 *
 * Usage:
 *   node download-attachment.mjs --page-url <url> --out <file>
 *                                [--attachment cache.zip] [--cdp http://127.0.0.1:9222]
 *                                [--timeout-min 5]
 *
 * Exit codes: 0 = success, 2 = not authenticated, 1 = any other failure.
 */
import fsp from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright-core';

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (!key.startsWith('--')) continue;
    const name = key.slice(2).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    const value = argv[i + 1];
    if (value === undefined || value.startsWith('--')) {
      out[name] = true;
    } else {
      out[name] = value;
      i += 1;
    }
  }
  return out;
}

const opts = parseArgs(process.argv.slice(2));
const pageUrl = opts.pageUrl;
const outFile = path.resolve(opts.out ?? 'cache.zip');
const attachmentName = opts.attachment ?? 'cache.zip';
const cdpUrl = opts.cdp ?? 'http://127.0.0.1:9222';
const timeoutMin = Number(opts.timeoutMin ?? 5);

if (!pageUrl) {
  console.error('[error] missing --page-url');
  process.exit(1);
}

const pageId = (pageUrl.match(/\/pages\/(\d+)/) ?? [])[1];
if (!pageId) {
  console.error(`[error] cannot parse the page id from ${pageUrl}`);
  process.exit(1);
}

const isLoginUrl = (url) => /^https:\/\/id\.atlassian\.com\//i.test(url) || /\/login(\?|$)/i.test(url);

async function fetchAttachment(context, page) {
  const origin = new URL(page.url()).origin;
  const listUrl = `${origin}/wiki/rest/api/content/${pageId}/child/attachment?filename=${encodeURIComponent(attachmentName)}`;
  const headers = { Accept: 'application/json', 'X-Atlassian-Token': 'no-check' };

  let meta = null;
  const listResponse = await context.request.get(listUrl, { headers, failOnStatusCode: false });
  if (listResponse.ok()) {
    const json = await listResponse.json();
    meta = (json.results ?? []).find((r) => r.title === attachmentName) ?? json.results?.[0] ?? null;
  }

  if (!meta) {
    // Fallback: run the REST call inside the page so the browser supplies its own session.
    const viaPage = await page.evaluate(async ({ listUrl, attachmentName }) => {
      const res = await fetch(listUrl, { headers: { Accept: 'application/json' } });
      if (!res.ok) return { status: res.status, item: null };
      const json = await res.json();
      return { status: 200, item: (json.results ?? []).find((r) => r.title === attachmentName) ?? json.results?.[0] ?? null };
    }, { listUrl, attachmentName });
    meta = viaPage?.item ?? null;
    if (!meta) throw new Error(`attachment "${attachmentName}" not found on page ${pageId} (HTTP ${viaPage?.status ?? '?'})`);
  }

  const downloadPath = meta?._links?.download;
  if (!downloadPath) throw new Error('attachment metadata has no download link');
  const downloadUrl = downloadPath.startsWith('http')
    ? downloadPath
    : `${origin}${downloadPath.startsWith('/wiki/') ? '' : '/wiki'}${downloadPath}`;

  const response = await context.request.get(downloadUrl, { headers, failOnStatusCode: false });
  if (!response.ok()) throw new Error(`download failed: HTTP ${response.status()}`);

  const buffer = Buffer.from(await response.body());
  if (buffer.length === 0) throw new Error('downloaded file is empty');
  if (buffer.subarray(0, 2).toString() === 'PK') return { buffer, meta };

  const head = buffer.subarray(0, 300).toString('utf8').toLowerCase();
  if (head.includes('<html')) throw new Error('server returned an HTML page instead of the zip (session expired or access denied)');
  throw new Error(`unexpected payload (first bytes: ${buffer.subarray(0, 8).toString('hex')})`);
}

async function main() {
  const browser = await chromium.connectOverCDP(cdpUrl, { timeout: 15_000 });
  const context = browser.contexts()[0];
  if (!context) throw new Error('no browser context available over CDP');

  const page = await context.newPage();
  try {
    await page.goto(pageUrl, { waitUntil: 'domcontentloaded', timeout: 60_000 });

    if (isLoginUrl(page.url())) {
      console.log('[info] Atlassian session not found - sign in inside the opened Chrome window...');
      try {
        await page.waitForURL((url) => !isLoginUrl(url.toString()) && url.toString().includes('/pages/'), {
          timeout: timeoutMin * 60_000
        });
      } catch {
        throw Object.assign(new Error(`timed out after ${timeoutMin} min waiting for the Atlassian sign-in`), { code: 2 });
      }
      await page.waitForLoadState('domcontentloaded');
    }

    const { buffer, meta } = await fetchAttachment(context, page);
    await fsp.writeFile(outFile, buffer);
    console.log(`[ok] ${attachmentName} (${buffer.length} bytes, attachment version ${meta?.version?.number ?? '?'}) -> ${outFile}`);
  } finally {
    await page.close().catch(() => {});
    // Detach only; the Chrome instance itself is managed by the PowerShell wrapper.
    await browser.close().catch(() => {});
  }
}

main().catch((err) => {
  console.error(`[error] ${err.message}`);
  process.exit(err.code ?? 1);
});
