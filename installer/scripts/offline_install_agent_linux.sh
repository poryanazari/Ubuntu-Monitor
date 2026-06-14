#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../" && pwd)"
TARGET="${1:-$ROOT/dist/ubuntu-monitor-agent-offline-linux}"
WHEELS="$ROOT/installer/wheels/agent-linux"

if [ ! -d "$WHEELS" ]; then
  echo "Missing wheels. On an internet PC run: installer/scripts/download_offline_packages.sh"
  exit 1
fi

echo "Installing agent to $TARGET ..."
mkdir -p "$TARGET"
cp -a "$ROOT/agent/." "$TARGET/agent/"
if [ ! -f "$TARGET/agent/config.linux.yaml" ]; then
  cp "$TARGET/agent/config.linux.yaml.example" "$TARGET/agent/config.linux.yaml"
fi

python3 -m venv "$TARGET/venv"
# shellcheck source=/dev/null
source "$TARGET/venv/bin/activate"
pip install --no-index --find-links="$WHEELS" -r "$ROOT/agent/requirements.txt"

cat > "$TARGET/start_agent.sh" <<'EOF'
#!/bin/bash
cd "$(dirname "$0")/agent"
source ../venv/bin/activate
python3 agent_linux.py -c config.linux.yaml
EOF
chmod +x "$TARGET/start_agent.sh"
"$ROOT/installer/scripts/bundle_agent_service_files.sh" "$TARGET"

echo "Done. Edit agent/config.linux.yaml"
echo "Install service: sudo ./install_service.sh"
echo "Or run manually: ./start_agent.sh"
