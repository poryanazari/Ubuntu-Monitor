#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
WHEELS="$ROOT/installer/wheels"

echo "=== Ubuntu Monitor: download offline packages (Linux) ==="
echo "Root: $ROOT"
mkdir -p "$WHEELS/server-linux" "$WHEELS/agent-linux" "$WHEELS/build"

echo
echo "[1/4] Server wheels (Linux) ..."
pip download -r "$ROOT/server/requirements.txt" -d "$WHEELS/server-linux"
pip download bcrypt -d "$WHEELS/server-linux"

echo
echo "[2/4] Agent wheels (Linux) ..."
pip download -r "$ROOT/agent/requirements.txt" -d "$WHEELS/agent-linux"

echo
echo "[3/4] Build tools ..."
pip download -r "$ROOT/installer/requirements-build.txt" -d "$WHEELS/build"

echo
echo "[4/4] Server wheels (Windows — optional cross-download) ..."
mkdir -p "$WHEELS/server-win"
pip download -r "$ROOT/server/requirements.txt" -d "$WHEELS/server-win" \
  --platform win_amd64 --python-version 311 --only-binary=:all: || true

echo
echo "Done. Wheels saved under installer/wheels/"
