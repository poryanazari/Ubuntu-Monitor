#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../" && pwd)"
DIST="$ROOT/dist"
OUT="$DIST/ubuntu-monitor-agent-portable-linux"
AGENT="$ROOT/agent"
VENV="$AGENT/venv"

echo "=== Build Ubuntu Monitor Agent (portable venv, Linux) ==="

if [ ! -x "$VENV/bin/python" ]; then
  echo "Creating agent venv ..."
  python3 -m venv "$VENV"
  # shellcheck source=/dev/null
  source "$VENV/bin/activate"
  pip install -q -r "$AGENT/requirements.txt"
fi

rm -rf "$OUT"
mkdir -p "$OUT"

cp -a "$AGENT" "$OUT/agent"
rm -rf "$OUT/agent/venv" "$OUT/agent/__pycache__" 2>/dev/null || true
cp -a "$VENV" "$OUT/venv"

if [ ! -f "$OUT/agent/config.linux.yaml" ]; then
  cp "$OUT/agent/config.linux.yaml.example" "$OUT/agent/config.linux.yaml"
fi

cat > "$OUT/start_agent.sh" <<'EOF'
#!/bin/bash
cd "$(dirname "$0")/agent"
source ../venv/bin/activate
python3 agent_linux.py -c config.linux.yaml
EOF
chmod +x "$OUT/start_agent.sh"

"$ROOT/installer/scripts/bundle_agent_service_files.sh" "$OUT"

echo
echo "Built: $OUT"
echo "1. Edit agent/config.linux.yaml"
echo "2. Install service: sudo ./install_service.sh"
