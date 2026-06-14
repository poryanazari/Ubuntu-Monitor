#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../" && pwd)"
DIST="$ROOT/dist"
BUILD_VENV="$ROOT/installer/.build-venv"
SPECS="$ROOT/installer/specs"

echo "=== Build Ubuntu Monitor Server (Linux) ==="
echo "Root: $ROOT"

if [ ! -f "$ROOT/web/dist/index.html" ]; then
  echo "Building web UI ..."
  pushd "$ROOT/web"
  npm run build
  popd
fi

if [ ! -d "$BUILD_VENV" ]; then
  python3 -m venv "$BUILD_VENV"
fi
# shellcheck source=/dev/null
source "$BUILD_VENV/bin/activate"
pip install -q -r "$ROOT/server/requirements.txt" -r "$ROOT/installer/requirements-build.txt"

pushd "$SPECS"
pyinstaller --noconfirm --clean --collect-all uvicorn --collect-all fastapi --collect-all sqlalchemy server.spec
popd

OUT="$DIST/ubuntu-monitor-server-linux"
rm -rf "$OUT"
mkdir -p "$OUT"
cp -a "$SPECS/dist/ubuntu-monitor-server/." "$OUT/"
cat > "$OUT/start_server.sh" <<'EOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "Dashboard: http://localhost:8000"
./ubuntu-monitor-server
EOF
chmod +x "$OUT/ubuntu-monitor-server" "$OUT/start_server.sh"

echo
echo "Built: $OUT"
