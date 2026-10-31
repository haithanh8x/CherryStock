/* Public, read-only R2 market-breadth endpoint for CherryStock GitHub Pages.
   Never expose raw R2 credentials or unrestricted object keys. */
const ORIGINS = new Set(["https://haithanh8x.github.io","http://localhost:5173","http://127.0.0.1:5173"]);
const OBJECT_KEY = "market-breadth/v1/latest.json";
function headers(origin) {
  return {
    "Content-Type": "application/json; charset=utf-8",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "public, max-age=300",
    ...(origin && ORIGINS.has(origin) ? {
      "Access-Control-Allow-Origin": origin, "Vary": "Origin",
    } : {}),
  };
}
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");
    if (request.method === "OPTIONS") {
      if (url.pathname !== "/api/v1/breadth" || !ORIGINS.has(origin)) {
        return new Response(null, { status: 403 });
      }
      return new Response(null, { status: 204, headers: {
        "Access-Control-Allow-Origin": origin, "Vary": "Origin",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      } });
    }
    if (request.method !== "GET") return new Response('{"error":"Method not allowed"}', {
      status: 405, headers: headers(origin),
    });
    if (url.pathname === "/health") return new Response('{"ok":true,"service":"cherrystock-breadth"}', {
      status: 200, headers: headers(origin),
    });
    if (url.pathname !== "/api/v1/breadth") return new Response('{"error":"Not found"}', {
      status: 404, headers: headers(origin),
    });
    const object = await env.CHERRYSTOCK_R2.get(OBJECT_KEY);
    if (!object) return new Response('{"error":"Breadth snapshot unavailable"}', {
      status: 503, headers: { ...headers(origin), "Cache-Control": "no-store" },
    });
    return new Response(object.body, {
      headers: { ...headers(origin), "ETag": object.httpEtag },
    });
  },
};
