#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../" && pwd)"
DIST="$ROOT/dist"
OUT="$DIST/ubuntu-monitor-server-portable-linux"
SERVER="$ROOT/server"
VENV="$SERVER/venv"

echo "=== Build Ubuntu Monitor Server (portable venv, Linux) ==="

if [ ! -x "$VENV/bin/python" ]; then
  echo "Missing server/venv. On build PC: cd server && python3 -m venv venv && pip install -r requirements.txt"
  exit 1
fi

if [ ! -f "$ROOT/web/dist/index.html" ]; then
  echo "Building web UI ..."
  (cd "$ROOT/web" && npm run build)
fi

rm -rf "$OUT"
mkdir -p "$OUT/server" "$OUT/web/dist"

cp -a "$SERVER/app" "$OUT/server/app"
if [ -f "$SERVER/.env.example" ]; then cp "$SERVER/.env.example" "$OUT/server/.env.example"; fi
cp -a "$VENV" "$OUT/venv"
cp -a "$ROOT/web/dist/." "$OUT/web/dist/"

cat > "$OUT/start_server.sh" <<'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
cd server
export UBUNTU_MONITOR_DATA_DIR="$(pwd)"
export UBUNTU_MONITOR_STATIC_DIR="$(cd ../web/dist && pwd)"
echo "Ubuntu Monitor server"
echo "Dashboard: http://localhost:8000"
echo "Login: admin / admin123"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
EOF
chmod +x "$OUT/start_server.sh"

cat > "$OUT/README.txt" <<'EOF'
Ubuntu Monitor - portable server (Linux)

Copy this folder to target servers. Run ./start_server.sh
Edit server/.env before first run if needed.
EOF

echo
echo "Built: $OUT"
