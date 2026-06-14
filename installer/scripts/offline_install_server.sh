#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../" && pwd)"
TARGET="${1:-$ROOT/dist/ubuntu-monitor-server-offline-linux}"
WHEELS="$ROOT/installer/wheels/server-linux"

if [ ! -d "$WHEELS" ]; then
  echo "Missing wheels. On an internet PC run: installer/scripts/download_offline_packages.sh"
  exit 1
fi

echo "Installing server to $TARGET ..."
mkdir -p "$TARGET"
cp -a "$ROOT/server/." "$TARGET/server/"
cp -a "$ROOT/web/dist/." "$TARGET/web/dist/"
if [ ! -f "$TARGET/server/.env" ] && [ -f "$ROOT/server/.env.example" ]; then
  cp "$ROOT/server/.env.example" "$TARGET/server/.env.example"
fi

python3 -m venv "$TARGET/venv"
# shellcheck source=/dev/null
source "$TARGET/venv/bin/activate"
pip install --no-index --find-links="$WHEELS" -r "$ROOT/server/requirements.txt"
pip install --no-index --find-links="$WHEELS" bcrypt

cat > "$TARGET/start_server.sh" <<'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
cd server
export UBUNTU_MONITOR_DATA_DIR="$(pwd)"
export UBUNTU_MONITOR_STATIC_DIR="$(cd ../web/dist && pwd)"
echo "Dashboard: http://localhost:8000"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
EOF
chmod +x "$TARGET/start_server.sh"

echo "Done. Copy folder to target machine and run ./start_server.sh"
