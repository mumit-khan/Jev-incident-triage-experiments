# Hosting on Gizmos

Two Gizmos apps serve the study behind TELUS sign-in. Both are private until shared.

| App | What it is |
|---|---|
| [jev-triage-experiments-app](https://jev-triage-experiments-app.telus.gizmos.run) | The full lab: comparison lab, walkthrough, ML microscope, sandbox and new Jev comparisons. |
| [jev-triage-experiments-doc](https://jev-triage-experiments-doc.telus.gizmos.run) | A frozen, read-only copy of the walkthrough and study reader with the saved results. |

## The app

Gizmos serves Cloudflare Workers, so `gizmos/worker.js` runs the unchanged Python app inside a Gizmos container and forwards each request to it over the container's loopback.

- Each signed-in viewer gets their own container. A Jev key entered in **Model settings** stays in that viewer's session.
- On the first request, or after a code change, the Worker unpacks the bundled lab, installs Python 3.12 and the pinned requirements with `uv`, and starts `python -m triage_bench.app`. Expect 10–30 seconds.
- Comparison runs made in the container are saved to the app's R2 storage under a per-viewer prefix. The Worker uploads changed run files in the background after job requests, and copies the viewer's saved runs back into the container when it boots. The bundled historical runs come from the bundle, not R2.
- The container never mounts R2. A FUSE mount hung during testing, and because `exec()` calls share one session shell and run one at a time, a process stuck on the mount blocked every later request until the container was reset.
- The boot runs as a background process that the Worker polls, so a slow boot can't block the shared shell either.
- The Worker refuses cross-origin writes before it drops the `Origin` header, which preserves the app's localhost-only check.
- `/__lab/boot-log` shows the viewer's boot steps with timestamps; `/__lab/server-log` shows the last 100 lines of the server log.

## Deploy the app

```bash
OUT=$(scripts/build_gizmos_bundle.sh)
gizmos push --app jev-triage-experiments-app-dev -m "what changed" "$OUT"   # optional staging copy
gizmos push --app jev-triage-experiments-app -m "what changed" "$OUT"
```

A staging copy is a separate app with its own storage and egress rules.

The build script assembles the deploy folder outside the repo, because `gizmos push` skips gitignored files and `runs/` is ignored. It excludes `.env`. Restore the historical runs ([run bundle](run-bundle.md)) before building, or the deployed study is incomplete.

### Container egress

Each app's container blocks outbound traffic except a default list that includes PyPI. Add these allow rules once per app under **Settings → Containers → RUNNER**:

| Host | Needed for |
|---|---|
| `release-assets.githubusercontent.com` | Downloading Python 3.12 (the container image ships 3.10) |
| `api.typesafe.ai` | Jev comparisons |

### Limits

- An idle container shuts down and loses everything except R2. The next request reinstalls in about 30 seconds.
- A Jev run in progress when the container shuts down stops; it does not resume. Results uploaded before then are kept.
- If requests time out and even `/__lab/boot-log` hangs, the container's shell is wedged: reset it under **Settings → Containers → RUNNER → Reset**. Reset affects every viewer's container; saved runs in R2 are kept.
- Gizmos can refuse new containers when the platform is at capacity. The Worker returns 503.
- Changing the app name or deleting it does not move R2 data.

## The frozen doc

`scripts/build_gizmos_doc.py` renders every response the walkthrough reads with the same code the local server uses: the study catalog, all 1,064 cases, the result and request exports, and the study reader's documents. `gizmos-doc/worker.js` serves them from a compressed bundle. There is no container, no Python and no live computation, so it loads at once and never changes until rebuilt.

```bash
OUT=$(uv run --locked python scripts/build_gizmos_doc.py)
gizmos push --app jev-triage-experiments-doc -m "freeze <commit>" "$OUT"
```

- The ML microscope and sandbox compute live, so the doc returns a note that links to the app for them. Their full output runs to gigabytes and does not fit a frozen copy.
- The comparison-lab links point to the app.
- `/__doc/manifest` records the build time, source commit, whether study sources had uncommitted changes, and the run ID behind each split's results.
- Build from a committed tree with the historical runs restored; the build warns otherwise.
