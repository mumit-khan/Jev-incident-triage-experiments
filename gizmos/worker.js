// Runs the Python triage lab inside a per-viewer container and proxies requests to it.
// The lab listens on the container's loopback only; nothing is exposed publicly.
//
// exec() calls share one session shell and run one at a time, so anything slow (the boot) runs
// as a background process, and nothing in the container touches network storage. The Worker
// copies each viewer's runs between R2 and the container instead.
import { LAB_TGZ_B64, LAB_VERSION } from "./bundle.js";

const PORT = 8766;
const NEEDS_BOOT = new Set([7, 99]); // curl: connection refused; 99: code version mismatch
const RUNS_LOCAL = "/workspace/lab/runs/app";
const RESTORE = "/workspace/restore"; // runs fetched from R2, merged in by the boot script
const BOOT_WAIT_MS = 240_000;

const shq = (s) => `'${String(s).replace(/'/g, `'\\''`)}'`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Stable per-viewer R2 prefix that doesn't put the raw subject id in storage paths.
async function runsPrefix(sub) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(sub));
  const hex = [...new Uint8Array(digest)].slice(0, 12).map((b) => b.toString(16).padStart(2, "0")).join("");
  return `users/${hex}/runs/`;
}

// Only plain relative paths like "<run-id>/<file>" move between R2 and the container.
const safeRel = (rel) => /^[A-Za-z0-9_.-]+(\/[A-Za-z0-9_.-]+)*$/.test(rel) && !rel.split("/").includes("..");

const BOOT = `set -uo pipefail
exec >>/workspace/boot.log 2>&1
log() { echo "$(date -u +%H:%M:%S) $*"; }
state() { echo "$*" > /workspace/boot.state; }
exec 9>/tmp/boot-${LAB_VERSION}.lock
flock -n 9 || { log "boot already running"; exit 0; }
log "boot ${LAB_VERSION} pid $$"
up() { curl -s -o /dev/null --max-time 2 http://127.0.0.1:${PORT}/; }
if up && [ "$(cat /workspace/lab/.version 2>/dev/null)" = "${LAB_VERSION}" ]; then log UP; state STARTED; exit 0; fi
pkill -f triage_bench.app; sleep 0.5
[ -x "$HOME/.local/bin/uv" ] || python3 -m pip install --quiet --user uv || { log UV_FAILED; state FAILED UV_FAILED; exit 1; }
UV="$HOME/.local/bin/uv"
log unpack
rm -rf /workspace/lab.new && mkdir -p /workspace/lab.new
base64 -d /workspace/lab.tgz.b64 | tar -xz -C /workspace/lab.new || { log UNPACK_FAILED; state FAILED UNPACK_FAILED; exit 1; }
# Merge the viewer's saved runs (from R2) and any made in this container; bundled runs win on conflict.
mkdir -p /workspace/lab.new/runs/app
# -p keeps modification times, so files changed since the last upload are still seen as changed.
[ -d ${RESTORE} ] && cp -rnp ${RESTORE}/. /workspace/lab.new/runs/app/
[ -d ${RUNS_LOCAL} ] && cp -rnp ${RUNS_LOCAL}/. /workspace/lab.new/runs/app/
rm -rf /workspace/lab && mv /workspace/lab.new /workspace/lab
# Files older than this marker are already in R2 or in the bundle; only newer ones are uploaded.
[ -f /workspace/.synced ] || touch /workspace/.synced
log "install packages"
[ -x /workspace/venv/bin/python ] || "$UV" venv --python 3.12 /workspace/venv || { log VENV_FAILED; state FAILED VENV_FAILED; exit 1; }
VIRTUAL_ENV=/workspace/venv "$UV" pip install --quiet -r /workspace/lab/requirements.txt || { log PIP_FAILED; state FAILED PIP_FAILED; exit 1; }
echo "${LAB_VERSION}" > /workspace/lab/.version
log "start server"
cd /workspace/lab && setsid nohup /workspace/venv/bin/python -m triage_bench.app --port ${PORT} > /workspace/server.log 2>&1 < /dev/null &
for i in $(seq 1 60); do up && { log STARTED; state STARTED; exit 0; }; sleep 0.5; done
log START_FAILED; tail -20 /workspace/server.log; state FAILED START_FAILED; exit 1`;

// Copies the viewer's saved runs from R2 into the container for the boot script to merge in.
async function restoreRuns(env, c, prefix) {
  await c.exec(`rm -rf ${RESTORE} && mkdir -p ${RESTORE}`);
  let cursor;
  do {
    const page = await env.RUNS.list({ prefix, cursor });
    for (const { key } of page.objects) {
      const rel = key.slice(prefix.length);
      if (!safeRel(rel)) continue;
      const obj = await env.RUNS.get(key);
      if (!obj) continue;
      await c.exec(`mkdir -p ${shq(`${RESTORE}/${rel}`.replace(/\/[^/]+$/, ""))}`);
      await c.writeFile(`${RESTORE}/${rel}`, await obj.text());
    }
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor);
}

// Page loads send several requests at once; the first claims the boot and the rest wait for it.
// A claim older than 5 minutes belongs to a boot that died and is taken over.
async function boot(env, c, prefix) {
  const claim = `/workspace/boot-claim-${LAB_VERSION}`;
  const claimed = (await c.exec(`bash -c ${shq(`find ${claim} -maxdepth 0 -mmin +5 -exec rm -rf {} + 2>/dev/null
mkdir ${claim} 2>/dev/null && { rm -f /workspace/boot.state; echo CLAIMED; }`)}`)).stdout.includes("CLAIMED");
  if (claimed) {
    await c.writeFile("/workspace/lab.tgz.b64", LAB_TGZ_B64);
    await c.writeFile("/workspace/boot.sh", BOOT);
    try {
      await restoreRuns(env, c, prefix);
    } catch (err) {
      console.warn(`run restore failed; starting without saved runs: ${err?.message || err}`);
    }
    await c.startProcess("bash /workspace/boot.sh");
  }
  for (const deadline = Date.now() + BOOT_WAIT_MS; Date.now() < deadline; await sleep(2000)) {
    const s = (await c.exec("cat /workspace/boot.state 2>/dev/null")).stdout.trim();
    if (s === "STARTED") {
      if (claimed) await c.exec(`rm -rf ${claim}`);
      return;
    }
    if (s.startsWith("FAILED")) break;
  }
  // Release the claim so the next request can retry.
  await c.exec(`rm -rf ${claim}`);
  const log = await c.exec("tail -30 /workspace/boot.log");
  throw new Error(`Lab failed to start. Boot log:\n${log.stdout}`);
}

// Uploads run files changed since the last sync. Runs after the response, so it never delays it.
async function syncRuns(env, c, prefix) {
  const r = await c.exec(`bash -c ${shq(`cd ${RUNS_LOCAL} 2>/dev/null || exit 0
touch /workspace/.sync-next
find . -type f -newer /workspace/.synced -printf '%P\\n'
mv /workspace/.sync-next /workspace/.synced`)}`);
  for (const rel of r.stdout.split("\n").filter(safeRel)) {
    const { content, encoding } = await c.readFile(`${RUNS_LOCAL}/${rel}`);
    const body = encoding === "base64" ? Uint8Array.from(atob(content), (ch) => ch.charCodeAt(0)) : content;
    await env.RUNS.put(prefix + rel, body);
  }
}

async function forward(c, req) {
  const url = new URL(req.url);
  const id = crypto.randomUUID();
  const args = ["curl", "-sS", "-i", "--max-time", "110", "-X", req.method,
                "-H", `Accept: ${req.headers.get("accept") || "*/*"}`];
  const type = req.headers.get("content-type");
  if (type) args.push("-H", `Content-Type: ${type}`);
  const hasBody = !["GET", "HEAD"].includes(req.method);
  if (hasBody) {
    await c.writeFile(`/tmp/req-${id}`, await req.text());
    args.push("--data-binary", `@/tmp/req-${id}`);
  }
  args.push(`http://127.0.0.1:${PORT}${url.pathname}${url.search}`);
  const cmd = `[ "$(cat /workspace/lab/.version 2>/dev/null)" = "${LAB_VERSION}" ] || exit 99
${args.map(shq).join(" ")}; rc=$?; rm -f /tmp/req-${id}; exit $rc`;
  // Run in a child bash: exec() shares one session shell, and `exit` there kills the session.
  return c.exec(`bash -c ${shq(cmd)}`, { timeout: 120_000 });
}

function toResponse(raw) {
  const split = raw.indexOf("\r\n\r\n");
  const head = raw.slice(0, split).split("\r\n");
  const status = Number(head[0].split(" ")[1]) || 502;
  const headers = new Headers();
  for (const line of head.slice(1)) {
    const i = line.indexOf(":");
    const name = line.slice(0, i).trim().toLowerCase();
    if (["content-type", "content-disposition", "cache-control"].includes(name)) headers.set(name, line.slice(i + 1).trim());
  }
  return new Response(raw.slice(split + 4), { status, headers });
}

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    // The lab trusts only same-origin writes; enforce that here before dropping Origin.
    if (!["GET", "HEAD"].includes(req.method)) {
      const origin = req.headers.get("origin");
      if ((origin && origin !== url.origin) || req.headers.get("sec-fetch-site") === "cross-site")
        return Response.json({ error: "Cross-origin request refused." }, { status: 403 });
    }
    // One container per signed-in viewer: their Jev key and runs stay in their own session.
    const viewer = req.headers.get("x-gizmos-sub") || "anonymous";
    const c = env.RUNNER.instance(viewer);
    try {
      if (url.pathname === "/__lab/server-log")
        return new Response((await c.exec("tail -100 /workspace/server.log")).stdout);
      if (url.pathname === "/__lab/boot-log")
        return new Response((await c.exec("tail -100 /workspace/boot.log")).stdout);
      const prefix = await runsPrefix(viewer);
      let r = await forward(c, req);
      if (NEEDS_BOOT.has(r.exitCode)) {
        await boot(env, c, prefix);
        r = await forward(c, req);
      }
      if (r.exitCode !== 0) return Response.json({ error: "Lab request failed.", detail: r.stderr }, { status: 502 });
      // Jobs write runs; polling their status uploads progress as it lands.
      if (url.pathname.startsWith("/api/jobs") || url.pathname === "/api/cancel")
        ctx.waitUntil(syncRuns(env, c, prefix).catch((err) => console.warn(`run sync failed: ${err?.message || err}`)));
      return toResponse(r.stdout);
    } catch (err) {
      const message = String(err?.message || err);
      const status = message.startsWith("[container_capacity]") ? 503 : 500;
      return Response.json({ error: message }, { status });
    }
  },
};
