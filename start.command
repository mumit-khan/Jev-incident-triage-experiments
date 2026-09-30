#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
lab_uv="$(command -v uv || true)"
if [ -z "$lab_uv" ] && [ -x "$HOME/.local/bin/uv" ]; then
    lab_uv="$HOME/.local/bin/uv"
fi
if [ -n "$lab_uv" ]; then
    "$lab_uv" sync --locked
    exec "$lab_uv" run --locked python -m triage_bench.app --port 8766
else
    if [ ! -x .venv/bin/python ]; then
        python3 -m venv .venv
    fi
    .venv/bin/python -m ensurepip --upgrade
    .venv/bin/python -m pip install -r requirements.txt
    exec .venv/bin/python -m triage_bench.app --port 8766
fi
