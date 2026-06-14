#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../" && pwd)"
DIST="$ROOT/dist"
BUILD_VENV="$ROOT/installer/.build-venv"
SPECS="$ROOT/installer/specs"

echo "=== Build Ubuntu Monitor Agent (Linux) ==="
echo "Root: $ROOT"

if [ ! -d "$BUILD_VENV" ]; then
  python3 -m venv "$BUILD_VENV"
fi
# shellcheck source=/dev/null
source "$BUILD_VENV/bin/activate"
pip install -q -r "$ROOT/agent/requirements.txt" -r "$ROOT/installer/requirements-build.txt"

pushd "$SPECS"
pyinstaller --noconfirm --clean agent_linux.spec
popd

OUT="$DIST/ubuntu-monitor-agent-linux"
rm -rf "$OUT"
mkdir -p "$OUT"
cp -a "$SPECS/dist/ubuntu-monitor-agent-linux/." "$OUT/"
cp "$ROOT/installer/templates/start_agent_linux.sh" "$OUT/start_agent.sh"
chmod +x "$OUT/ubuntu-monitor-agent" "$OUT/start_agent.sh"
"$ROOT/installer/scripts/bundle_agent_service_files.sh" "$OUT"

echo
echo "Built: $OUT"
echo "1. Edit config.linux.yaml (server_url, agent_key)"
echo "2. Install service: sudo ./install_service.sh"
echo "   Or run manually: ./start_agent.sh"
