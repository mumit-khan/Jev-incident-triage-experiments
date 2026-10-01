#!/bin/bash
# Assembles a Gizmos deploy folder outside the repo: gizmos/worker.js, gizmos/wrangler.toml and
# bundle.js, which packs the lab (no .env, no caches) for the Worker to unpack in its container.
# Usage: scripts/build_gizmos_bundle.sh [output-dir]   then: gizmos push --app <name> <output-dir>
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-"${TMPDIR:-/tmp}/jev-triage-gizmos"}
case "$OUT" in "$ROOT"|"$ROOT"/*) echo "Output must be outside the repo; gizmos push skips gitignored files." >&2; exit 1;; esac
mkdir -p "$OUT"
cp "$ROOT/gizmos/worker.js" "$ROOT/gizmos/wrangler.toml" "$OUT/"
TGZ=$(mktemp)
COPYFILE_DISABLE=1 tar -czf "$TGZ" -C "$ROOT" --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' \
  triage_bench data runs docs README.md HANDOFF.md requirements.txt
printf 'export const LAB_TGZ_B64 = "%s";\n' "$(base64 < "$TGZ" | tr -d '\n')" > "$OUT/bundle.js"
printf 'export const LAB_VERSION = "%s";\n' "$(shasum -a 256 "$TGZ" | cut -c1-16)" >> "$OUT/bundle.js"
rm "$TGZ"
echo "$OUT"
