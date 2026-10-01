// Serves the frozen study walkthrough: responses pre-rendered by scripts/build_gizmos_doc.py,
// in the same shapes and routes as the local server. No container, no Python, no live computation.
import { GROUPS, MANIFEST } from "./bundle.js";

const LIVE_ONLY = `This frozen copy only contains saved results. The ML microscope and sandbox compute live: open this case in the app at ${MANIFEST.app_url}`;
const CSP = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'";
const ASSETS = {
  "/explorer": ["explorer.html", "text/html; charset=utf-8"],
  "/explorer.js": ["explorer.js", "text/javascript; charset=utf-8"],
  "/explorer.css": ["explorer.css", "text/css; charset=utf-8"],
  "/study.css": ["study.css", "text/css; charset=utf-8"],
  "/study.js": ["study.js", "text/javascript; charset=utf-8"],
};

// Each group is decompressed on first use and kept for the isolate's lifetime.
const cache = new Map();
async function group(name) {
  if (!cache.has(name)) {
    cache.set(name, (async () => {
      const bytes = Uint8Array.from(atob(GROUPS[name]), (ch) => ch.charCodeAt(0));
      const text = await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"))).text();
      return JSON.parse(text);
    })());
  }
  return cache.get(name);
}

function send(status, body, type = "application/json; charset=utf-8", extra = {}) {
  return new Response(typeof body === "string" ? body : JSON.stringify(body), {
    status,
    headers: { "content-type": type, "cache-control": "no-store", "x-content-type-options": "nosniff",
               "content-security-policy": CSP, ...extra },
  });
}
const fail = (message, status = 400) => send(status, { error: message });

// A case entry holds the pre-serialized case and both Jev request exports.
async function caseEntry(split, id) {
  if (!Object.hasOwn(GROUPS, `cases-${split}`)) throw new Error("Unknown split.");
  const cases = await group(`cases-${split}`);
  if (!Object.hasOwn(cases, id)) throw new Error("Unknown case.");
  return cases[id];
}

async function exportBody(p) {
  const kind = p.get("kind");
  if (kind === "results") {
    const text = (await group("core"))[`export/results/${p.get("split")}`];
    if (!text) throw new Error("No saved results for this split.");
    return text;
  }
  if (kind === "lens") throw new Error(LIVE_ONLY);
  const entry = await caseEntry(p.get("split"), p.get("id"));
  if (["case", "original-request", "focused-request"].includes(kind)) return entry[kind];
  throw new Error("Unknown export type.");
}

export default {
  async fetch(req) {
    const url = new URL(req.url);
    const p = url.searchParams;
    if (req.method === "POST" && url.pathname === "/api/sandbox") return fail(LIVE_ONLY);
    if (req.method !== "GET" && req.method !== "HEAD") return fail("This copy is read-only.", 405);
    try {
      if (url.pathname === "/") return Response.redirect(`${url.origin}/explorer`, 302);
      const core = await group("core");
      if (Object.hasOwn(ASSETS, url.pathname)) {
        const [key, type] = ASSETS[url.pathname];
        return send(200, core[key], type);
      }
      switch (url.pathname) {
        case "/api/study": return send(200, core["api/study"]);
        case "/api/case": return send(200, (await caseEntry(p.get("split"), p.get("id"))).case);
        case "/api/microscope": return fail(LIVE_ONLY);
        case "/api/export":
          return send(200, await exportBody(p), undefined,
                      { "content-disposition": 'attachment; filename="Northstar-inspection.json"' });
        case "/study": {
          const page = core[`study/${p.get("doc") || "overview"}`];
          return page ? send(200, page, "text/html; charset=utf-8") : fail("Unknown study document.");
        }
        case "/study.md": {
          const page = core[`study.md/${p.get("doc") || "overview"}`];
          return page ? send(200, page, "text/markdown; charset=utf-8") : fail("Unknown study document.");
        }
        case "/__doc/manifest": return send(200, MANIFEST);
      }
      return fail("Not found.", 404);
    } catch (err) {
      return fail(String(err?.message || err));
    }
  },
};
